"""The shopping cart: add, change and remove items, with stock and printing checks.

A signed-in user has one cart. A guest gets a cart identified by a random token, which the browser
sends back as the X-Cart-Token header. After signing in, claim() merges the guest cart into the
user's cart.
"""

import re
import secrets
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Cart, CartItem, Product, ProductVariant, ShippingMethod, User
from app.services.pricing import shipping_cost, unit_price

MAX_PER_LINE = 10
NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÿ' .-]{1,12}$")  # what fits on the back of a shirt


@dataclass
class Personalization:
    name: str | None
    number: int | None

    @property
    def is_set(self) -> bool:
        return self.name is not None or self.number is not None


def normalize_personalization(name: str | None, number: int | None) -> Personalization:
    clean = " ".join(name.split()).upper() if name else None
    if clean is not None and not NAME_PATTERN.match(clean):
        raise BadRequestError("The name can have up to 12 letters (spaces, dots, hyphens and apostrophes allowed)")
    if number is not None and not 0 <= number <= 99:
        raise BadRequestError("The shirt number must be between 0 and 99")
    return Personalization(clean or None, number)


@dataclass
class CartTotals:
    item_count: int
    subtotal: Decimal
    shipping_estimate: Decimal  # standard shipping to the Netherlands
    free_shipping_remaining: Decimal


class CartService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- finding the cart -----------------------------------------------------------------------

    def _load(self, *conditions: object) -> Cart | None:
        query = (
            select(Cart)
            .options(
                selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.product).selectinload(Product.team)
            )
            .where(*conditions)  # type: ignore[arg-type]
        )
        return self.db.scalar(query)

    def find(self, user: User | None, token: str | None) -> Cart | None:
        if user is not None:
            return self._load(Cart.user_id == user.id)
        if token:
            return self._load(Cart.token == token, Cart.user_id.is_(None))
        return None

    def find_or_create(self, user: User | None, token: str | None) -> Cart:
        cart = self.find(user, token)
        if cart is None:
            cart = Cart(user_id=user.id) if user else Cart(token=secrets.token_urlsafe(32))
            self.db.add(cart)
            self.db.flush()
        return cart

    # --- changing it ----------------------------------------------------------------------------

    def add_item(self, cart: Cart, variant_id: int, quantity: int, personalization: Personalization) -> Cart:
        variant = self.db.get(ProductVariant, variant_id)
        if variant is None or not variant.product.is_active:
            raise NotFoundError("This product or size doesn't exist")
        if personalization.is_set and not variant.product.personalizable:
            raise BadRequestError("Name and number printing isn't available for this product")

        existing = next(
            (
                i
                for i in cart.items
                if i.variant_id == variant_id
                and i.personalization_name == personalization.name
                and i.personalization_number == personalization.number
            ),
            None,
        )
        new_quantity = quantity + (existing.quantity if existing else 0)
        self._check_quantity(variant, new_quantity, cart, ignore=existing)
        if existing:
            existing.quantity = new_quantity
        else:
            cart.items.append(
                CartItem(
                    variant_id=variant_id,
                    variant=variant,
                    quantity=quantity,
                    personalization_name=personalization.name,
                    personalization_number=personalization.number,
                )
            )
        self.db.commit()
        return cart

    def update_quantity(self, cart: Cart, item_id: int, quantity: int) -> Cart:
        item = self._item(cart, item_id)
        self._check_quantity(item.variant, quantity, cart, ignore=item)
        item.quantity = quantity
        self.db.commit()
        return cart

    def remove_item(self, cart: Cart, item_id: int) -> Cart:
        cart.items.remove(self._item(cart, item_id))
        self.db.commit()
        return cart

    def claim(self, user: User, token: str) -> Cart:
        """Merge a guest cart into the signed-in user's cart (quantities capped by stock), then delete it."""
        cart = self.find_or_create(user, None)
        guest = self.find(None, token)
        if guest is None or guest.id == cart.id:
            return cart
        for item in list(guest.items):
            target = next(
                (
                    i
                    for i in cart.items
                    if i.variant_id == item.variant_id
                    and i.personalization_name == item.personalization_name
                    and i.personalization_number == item.personalization_number
                ),
                None,
            )
            in_other_lines = sum(i.quantity for i in cart.items if i.variant_id == item.variant_id and i is not target)
            room = min(MAX_PER_LINE, item.variant.stock - in_other_lines)
            if target:
                target.quantity = max(1, min(room, target.quantity + item.quantity))
            elif room > 0:
                cart.items.append(
                    CartItem(
                        variant_id=item.variant_id,
                        variant=item.variant,
                        quantity=min(room, item.quantity),
                        personalization_name=item.personalization_name,
                        personalization_number=item.personalization_number,
                    )
                )
        self.db.delete(guest)
        self.db.commit()
        return cart

    def clear(self, cart: Cart) -> None:
        cart.items.clear()

    # --- helpers --------------------------------------------------------------------------------

    def _item(self, cart: Cart, item_id: int) -> CartItem:
        item = next((i for i in cart.items if i.id == item_id), None)
        if item is None:
            raise NotFoundError(f"Cart item {item_id} not found")
        return item

    def _check_quantity(self, variant: ProductVariant, quantity: int, cart: Cart, ignore: CartItem | None) -> None:
        if not 1 <= quantity <= MAX_PER_LINE:
            raise BadRequestError(f"You can order 1 to {MAX_PER_LINE} of an item at a time")
        # The same size can be in the cart twice (e.g. with different names printed); stock covers both.
        elsewhere = sum(i.quantity for i in cart.items if i.variant_id == variant.id and i is not ignore)
        available = variant.stock - elsewhere
        if quantity > available:
            if available <= 0:
                raise ConflictError(f"{variant.product.name} in size {variant.size} is sold out")
            raise ConflictError(f"Only {available} left of {variant.product.name} in size {variant.size}")


def line_price(item: CartItem) -> Decimal:
    personalized = item.personalization_name is not None or item.personalization_number is not None
    return unit_price(item.variant.product, personalized)


def cart_totals(cart: Cart | None) -> CartTotals:
    items = cart.items if cart else []
    subtotal = sum((line_price(i) * i.quantity for i in items), Decimal("0"))
    free_from = get_settings().free_shipping_from
    return CartTotals(
        item_count=sum(i.quantity for i in items),
        subtotal=subtotal,
        shipping_estimate=shipping_cost("NL", ShippingMethod.STANDARD, subtotal) if items else Decimal("0"),
        free_shipping_remaining=max(Decimal("0"), free_from - subtotal),
    )
