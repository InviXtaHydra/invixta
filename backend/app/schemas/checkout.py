from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import PaymentMethod, PaymentStatus, ShippingMethod
from app.schemas.order import OrderRead
from app.services.pricing import SHIPPING_COUNTRIES


class CheckoutRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    street: str = Field(min_length=3, max_length=200, description="Street and house number")
    postcode: str = Field(min_length=3, max_length=16)
    city: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=2, description="ISO code, e.g. NL or BE")
    shipping_method: ShippingMethod = ShippingMethod.STANDARD
    payment_method: PaymentMethod

    @field_validator("name", "street", "postcode", "city")
    @classmethod
    def strip(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("country")
    @classmethod
    def known_country(cls, value: str) -> str:
        code = value.upper()
        if code not in SHIPPING_COUNTRIES:
            raise ValueError(f"We ship to: {', '.join(SHIPPING_COUNTRIES)}")
        return code


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus
    created_at: datetime
    decided_at: datetime | None


class CheckoutResponse(BaseModel):
    order: OrderRead
    payment: PaymentRead = Field(description="Open the payment page for this payment")


class PaymentDecision(BaseModel):
    outcome: Literal["approve", "decline"]


class RetryPaymentRequest(BaseModel):
    payment_method: PaymentMethod | None = None


class ShippingOption(BaseModel):
    method: ShippingMethod
    cost: Decimal
    countries: list[str]


class ShopInfo(BaseModel):
    countries: dict[str, str]
    free_shipping_from: Decimal
    personalization_price: Decimal
    shipping: list[ShippingOption]
    payment_methods: list[PaymentMethod]
