"""
IAP (In-App Purchase) models for Apple App Store integration.

Tables:
- iap_products: Product catalog (local cache of App Store Connect products)
- iap_transactions: Immutable audit log of all purchase events
- user_entitlements: Current user entitlement state (mutable, upserted)
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    """Local product catalog matching App Store Connect products.

    Products are seeded manually or via admin — not fetched from Apple.
    """

    __tablename__ = "iap_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        String, unique=True, index=True, nullable=False
    )  # e.g. "com.perapera.premium.monthly"
    name = Column(String, nullable=False)  # Display name
    type = Column(
        String, nullable=False
    )  # "consumable" | "non_consumable" | "auto_renewable_subscription" | "non_renewing_subscription"
    price = Column(Numeric(10, 2), nullable=True)  # Price in USD
    currency = Column(String, default="USD")
    duration = Column(
        String, nullable=True
    )  # "monthly", "yearly", "weekly" — for subscriptions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Product(id={self.id}, product_id='{self.product_id}', type='{self.type}')>"


class TransactionRecord(Base):
    """Immutable audit log of every Apple transaction and notification event.

    Each row represents either:
    - A purchase verified via /iap/verify
    - A notification event from Apple's server notification V2
    - A status sync from the subscription status API

    Never updated — always insert-only.
    """

    __tablename__ = "iap_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )  # NULL for unlinked events
    transaction_id = Column(
        String, unique=True, index=True, nullable=False
    )  # Apple's transactionId
    original_transaction_id = Column(
        String, index=True, nullable=False
    )  # Groups subscription renewals
    product_id = Column(String, nullable=False)  # Apple product ID
    type = Column(
        String, nullable=False
    )  # "purchase" | "renewal" | "refund" | "revoke" | "expired" | "grace_period" | "billing_retry"
    environment = Column(
        String, nullable=False
    )  # "Sandbox" or "Production"
    quantity = Column(Integer, default=1)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    expires_date = Column(DateTime(timezone=True), nullable=True)
    receipt_data = Column(Text, nullable=True)  # Raw receipt (base64)
    notification_type = Column(
        String, nullable=True
    )  # Apple notification type (e.g., "SUBSCRIBED", "DID_RENEW")
    notification_subtype = Column(
        String, nullable=True
    )  # Apple notification subtype (e.g., "INITIAL_BUY", "RESUBSCRIBE")
    notification_uuid = Column(
        String, nullable=True
    )  # UUID from Apple notification (for dedup)
    raw_response = Column(JSONB, nullable=True)  # Full decoded payload from Apple
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<TransactionRecord(id={self.id}, transaction_id='{self.transaction_id}', "
            f"type='{self.type}', product_id='{self.product_id}')>"
        )


class UserEntitlement(Base):
    """Current entitlement state per user.

    This is the authoritative source for checking if a user has
    access to a given product. Updated whenever:
    - A transaction is verified
    - A server notification is processed
    - A subscription status refresh occurs

    One row per (user_id, product_id) combination.
    For consumables, quantity_remaining tracks available uses.
    """

    __tablename__ = "user_entitlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    product_id = Column(String, nullable=False)
    original_transaction_id = Column(
        String, nullable=True, index=True
    )  # Links subscription renewals
    transaction_id = Column(
        String, nullable=False
    )  # Most recent transaction ID
    type = Column(
        String, nullable=False
    )  # "consumable" | "non_consumable" | "auto_renewable_subscription"

    # Subscription state
    is_active = Column(Boolean, default=True)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    expires_date = Column(DateTime(timezone=True), nullable=True)
    auto_renew_status = Column(
        Boolean, nullable=True
    )  # True = auto-renew ON
    will_renew = Column(Boolean, nullable=True)  # True = will actually renew next cycle
    is_in_grace_period = Column(Boolean, default=False)
    grace_period_expires_date = Column(DateTime(timezone=True), nullable=True)
    is_in_billing_retry = Column(Boolean, default=False)

    # Consumable state
    quantity_remaining = Column(Integer, default=0)

    # Environment of the most recent transaction
    environment = Column(String, nullable=True)  # "Sandbox" or "Production"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Composite unique index: one entitlement per user per product
    __table_args__ = (
        Index(
            "ix_user_entitlements_user_product",
            "user_id",
            "product_id",
            unique=True,
        ),
    )

    def __repr__(self):
        return (
            f"<UserEntitlement(user_id={self.user_id}, product_id='{self.product_id}', "
            f"is_active={self.is_active}, type='{self.type}')>"
        )
