"""The shopping cart. Works for guests (X-Cart-Token header) and for signed-in users (JWT)."""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.exceptions import NotFoundError
from app.models import ShippingMethod, User
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartQuote, CartRead
from app.services.cart_service import CartService, cart_totals, normalize_personalization
from app.services.pricing import shipping_cost

router = APIRouter(prefix="/cart", tags=["cart"])

CartToken = Header(None, alias="X-Cart-Token", max_length=64, description="Token of a guest cart")


@router.get("", response_model=CartRead)
def get_cart(user: User | None = Depends(get_optional_user), token: str | None = CartToken, db: Session = Depends(get_db)) -> CartRead:
    """The current cart (empty if there is none yet)."""
    return CartRead.from_cart(CartService(db).find(user, token))


@router.post(
    "/items", response_model=CartRead, responses={404: {"description": "Unknown product/size"}, 409: {"description": "Not enough stock"}}
)
def add_item(
    body: CartItemAdd, user: User | None = Depends(get_optional_user), token: str | None = CartToken, db: Session = Depends(get_db)
) -> CartRead:
    """Add a size of a product. A guest without a cart gets a new one: keep the returned `token`."""
    service = CartService(db)
    cart = service.find_or_create(user, token)
    personalization = normalize_personalization(body.personalization_name, body.personalization_number)
    return CartRead.from_cart(service.add_item(cart, body.variant_id, body.quantity, personalization))


@router.patch("/items/{item_id}", response_model=CartRead)
def update_item(
    item_id: int,
    body: CartItemUpdate,
    user: User | None = Depends(get_optional_user),
    token: str | None = CartToken,
    db: Session = Depends(get_db),
) -> CartRead:
    service = CartService(db)
    cart = service.find(user, token)
    if cart is None:
        raise NotFoundError(f"Cart item {item_id} not found")
    return CartRead.from_cart(service.update_quantity(cart, item_id, body.quantity))


@router.delete("/items/{item_id}", response_model=CartRead)
def remove_item(
    item_id: int, user: User | None = Depends(get_optional_user), token: str | None = CartToken, db: Session = Depends(get_db)
) -> CartRead:
    service = CartService(db)
    cart = service.find(user, token)
    if cart is None:
        raise NotFoundError(f"Cart item {item_id} not found")
    return CartRead.from_cart(service.remove_item(cart, item_id))


@router.post("/claim", response_model=CartRead)
def claim_cart(
    token: str = Header(alias="X-Cart-Token", max_length=64), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartRead:
    """After signing in: move the guest cart's items into your own cart."""
    return CartRead.from_cart(CartService(db).claim(user, token))


@router.get("/quote", response_model=CartQuote, responses={400: {"description": "Not shipped there, or no express"}})
def quote(
    country: str = Query(min_length=2, max_length=2),
    shipping_method: ShippingMethod = ShippingMethod.STANDARD,
    user: User | None = Depends(get_optional_user),
    token: str | None = CartToken,
    db: Session = Depends(get_db),
) -> CartQuote:
    """What the order will cost with this delivery country and method: the same calculation as the checkout."""
    totals = cart_totals(CartService(db).find(user, token))
    shipping = shipping_cost(country.upper(), shipping_method, totals.subtotal)
    return CartQuote(subtotal=totals.subtotal, shipping_cost=shipping, total=totals.subtotal + shipping)
