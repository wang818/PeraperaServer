from __future__ import annotations

"""
IAP (In-App Purchase) Pydantic schemas.

Request/response models for the /iap/* endpoints.
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------

class ProductResponse(BaseModel):
    """Product catalog entry returned to clients."""

    product_id: str
    name: str
    type: str
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    duration: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Transaction verification
# ---------------------------------------------------------------------------

class VerifyTransactionRequest(BaseModel):
    """Client sends this after a successful App Store purchase.

    Either transaction_id (StoreKit 2) or receipt_data (StoreKit 1) is required.
    """

    transaction_id: Optional[str] = Field(
        None,
        description="The transactionId from StoreKit 2 Transaction",
    )
    receipt_data: Optional[str] = Field(
        None,
        description="Base64-encoded receipt data (legacy StoreKit 1 path)",
    )


class VerifyTransactionResponse(BaseModel):
    """Response after server-side transaction verification."""

    is_valid: bool
    transaction_id: Optional[str] = None
    original_transaction_id: Optional[str] = None
    product_id: Optional[str] = None
    type: Optional[str] = None  # "consumable" | "non_consumable" | "auto_renewable_subscription"
    purchase_date: Optional[datetime] = None
    expires_date: Optional[datetime] = None
    environment: Optional[str] = None
    status: str = "verified"  # "verified" | "expired" | "refunded"

    # Subscription-specific
    is_subscription_active: Optional[bool] = None
    will_renew: Optional[bool] = None
    is_in_grace_period: Optional[bool] = None


# ---------------------------------------------------------------------------
# Entitlement / subscription status
# ---------------------------------------------------------------------------

class EntitlementResponse(BaseModel):
    """Current entitlement state for a specific product."""

    product_id: str
    type: str
    is_active: bool
    purchase_date: Optional[datetime] = None
    expires_date: Optional[datetime] = None
    will_renew: Optional[bool] = None
    auto_renew_status: Optional[bool] = None
    is_in_grace_period: bool = False
    is_in_billing_retry: bool = False
    grace_period_expires_date: Optional[datetime] = None
    quantity_remaining: Optional[int] = None
    environment: Optional[str] = None

    class Config:
        from_attributes = True


class RestorePurchasesResponse(BaseModel):
    """Response after restoring all purchases for a user."""

    restored_count: int
    entitlements: List[EntitlementResponse] = []


class SubscriptionStatusResponse(BaseModel):
    """Detailed subscription status for the current user."""

    is_subscribed: bool = False
    entitlements: List[EntitlementResponse] = []
    # Convenience fields for the client
    active_product_id: Optional[str] = None
    expires_date: Optional[datetime] = None
    will_renew: Optional[bool] = None
    is_in_grace_period: bool = False


# ---------------------------------------------------------------------------
# Server notification
# ---------------------------------------------------------------------------

class ServerNotificationBody(BaseModel):
    """Apple V2 server notification request body.

    Apple POSTs a responseBodyV2 containing a single signedPayload field.
    The signedPayload is a JWS (JSON Web Signature) in compact serialization format.
    """

    signedPayload: str = Field(
        ...,
        description="JWS-signed notification payload from Apple",
    )


class WebhookResponse(BaseModel):
    """Response returned to Apple after processing a notification.

    Apple expects HTTP 2xx to acknowledge receipt.
    """

    status: str = "received"
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------

class IAPErrorResponse(BaseModel):
    """Error response for IAP endpoints."""

    detail: str
    error_code: Optional[str] = None
    apple_error_code: Optional[int] = None
