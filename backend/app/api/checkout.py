"""Checkout and the simulated payment provider ("TestPay"). Everything is fictional: no money moves."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import PaymentMethod, ShippingMethod, User
from app.schemas.checkout import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentDecision,
    PaymentRead,
    RetryPaymentRequest,
    ShippingOption,
    ShopInfo,
)
from app.schemas.order import OrderRead
from app.services.checkout_service import Address, CheckoutService
from app.services.order_service import OrderService
from app.services.pricing import EXPRESS_COUNTRIES, SHIPPING_COUNTRIES

router = APIRouter(tags=["checkout"])


@router.get("/shop/info", response_model=ShopInfo)
def shop_info() -> ShopInfo:
    """Countries, shipping costs and payment methods, for the checkout page."""
    s = get_settings()
    return ShopInfo(
        countries=SHIPPING_COUNTRIES,
        free_shipping_from=s.free_shipping_from,
        personalization_price=s.personalization_price,
        shipping=[
            ShippingOption(method=ShippingMethod.STANDARD, cost=s.shipping_benelux, countries=list(SHIPPING_COUNTRIES)),
            ShippingOption(
                method=ShippingMethod.EXPRESS, cost=s.shipping_benelux + s.express_surcharge, countries=sorted(EXPRESS_COUNTRIES)
            ),
        ],
        payment_methods=list(PaymentMethod),
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Empty cart or invalid address"}, 409: {"description": "Not enough stock"}},
)
def checkout(body: CheckoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CheckoutResponse:
    """Turn your cart into an order. Prices, shipping and the total are calculated by the server.
    The order waits for payment: approve or decline it with POST /payments/{id}/complete."""
    address = Address(body.name, body.street, body.postcode, body.city, body.country)
    order, payment = CheckoutService(db).checkout(user, address, body.shipping_method, body.payment_method)
    return CheckoutResponse(order=OrderRead.from_order(order), payment=PaymentRead.model_validate(payment))


@router.get("/payments/{payment_id}", response_model=PaymentRead, tags=["payments"])
def get_payment(payment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PaymentRead:
    return PaymentRead.model_validate(CheckoutService(db).get_payment(user, payment_id))


@router.post("/payments/{payment_id}/complete", response_model=PaymentRead, tags=["payments"])
def complete_payment(
    payment_id: int, body: PaymentDecision, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PaymentRead:
    """TestPay: approve or decline the payment, like a bank would. Approved orders go to "processing"."""
    payment = CheckoutService(db).complete_payment(user, payment_id, approve=body.outcome == "approve")
    return PaymentRead.model_validate(payment)


@router.post("/orders/{order_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, tags=["payments"])
def retry_payment(
    order_id: int, body: RetryPaymentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PaymentRead:
    """Pay again for a pending order whose payment failed or was abandoned."""
    return PaymentRead.model_validate(CheckoutService(db).retry_payment(user, order_id, body.payment_method))


@router.post("/orders/{order_id}/cancel", response_model=OrderRead, tags=["orders"], responses={409: {"description": "Already shipped"}})
def cancel_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderRead:
    """Cancel an order that hasn't shipped yet. Stock goes back; a paid order is refunded (fictionally)."""
    CheckoutService(db).cancel(user, order_id)
    return OrderRead.from_order(OrderService(db).get_order(user, order_id))
