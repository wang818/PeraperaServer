"""
IAP (In-App Purchase) API Endpoints

Routes for purchase verification, subscription status, product catalog,
Apple server notifications webhook, and purchase restoration.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.core.dependencies import get_language
from app.core.i18n import get_translation
from app.models.user import User
from app.models.iap import Product, UserEntitlement
from app.schemas.iap import (
    VerifyTransactionRequest,
    VerifyTransactionResponse,
    EntitlementResponse,
    SubscriptionStatusResponse,
    ProductResponse,
    ServerNotificationBody,
    WebhookResponse,
    RestorePurchasesResponse,
    IAPErrorResponse,
)
from app.services.entitlement_service import EntitlementService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Verify Purchase
# ---------------------------------------------------------------------------

@router.post(
    "/verify",
    response_model=VerifyTransactionResponse,
    responses={400: {"model": IAPErrorResponse}, 422: {}},
)
async def verify_purchase(
    request: VerifyTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """Verify an IAP purchase with Apple and grant entitlement.

    The client (iOS app) calls this after completing a StoreKit purchase.
    Send either:
    - `transaction_id` (StoreKit 2 — preferred, use the Transaction.ID)
    - `receipt_data` (StoreKit 1 — legacy, base64-encoded app receipt)

    On success, the user is granted the corresponding entitlement and
    the server returns the verified transaction details.
    """
    if not request.transaction_id and not request.receipt_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either transaction_id or receipt_data is required.",
        )

    service = EntitlementService(db)

    try:
        txn_record = await service.verify_and_grant(
            user_id=current_user.id,
            transaction_id=request.transaction_id,
            receipt_data=request.receipt_data,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Verify purchase failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify purchase with Apple. Please try again.",
        )

    # Re-fetch to get the committed record with default values
    await db.refresh(txn_record)

    # Check subscription status from entitlement
    is_active = await service.check_entitlement(current_user.id, txn_record.product_id)

    return VerifyTransactionResponse(
        is_valid=True,
        transaction_id=txn_record.transaction_id,
        original_transaction_id=txn_record.original_transaction_id,
        product_id=txn_record.product_id,
        type=txn_record.type,
        purchase_date=txn_record.purchase_date,
        expires_date=txn_record.expires_date,
        environment=txn_record.environment,
        status="verified",
        is_subscription_active=is_active if txn_record.expires_date else None,
    )


# ---------------------------------------------------------------------------
# Subscription / Entitlement Status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """Get the current user's subscription/entitlement status.

    Returns all entitlements and a top-level summary for the client.
    If the user has an active subscription, subscription-specific
    fields (will_renew, is_in_grace_period, etc.) will be populated.
    """
    service = EntitlementService(db)

    # Optionally refresh from Apple (best-effort, don't fail on error)
    try:
        await service.refresh_user_subscriptions(current_user.id)
        await db.commit()
    except Exception as e:
        logger.warning(f"Background subscription refresh failed: {e}")
        # Continue with cached data

    # Get entitlements
    entitlements = await service.get_user_entitlements(current_user.id)
    entitlement_responses = [
        EntitlementResponse(
            product_id=e.product_id,
            type=e.type,
            is_active=e.is_active,
            purchase_date=e.purchase_date,
            expires_date=e.expires_date,
            will_renew=e.will_renew,
            auto_renew_status=e.auto_renew_status,
            is_in_grace_period=e.is_in_grace_period,
            is_in_billing_retry=e.is_in_billing_retry,
            grace_period_expires_date=e.grace_period_expires_date,
            quantity_remaining=e.quantity_remaining if e.type == "consumable" else None,
            environment=e.environment,
        )
        for e in entitlements
    ]

    # Build summary from active subscriptions
    is_subscribed = False
    active_product_id = None
    expires_date = None
    will_renew = None
    is_in_grace_period = False

    for e in entitlements:
        if e.is_active and e.type == "auto_renewable_subscription":
            # Check expiry
            from datetime import datetime, timezone
            if e.expires_date:
                exp = e.expires_date.replace(tzinfo=timezone.utc) if e.expires_date.tzinfo is None else e.expires_date
                if exp > datetime.now(timezone.utc) or e.is_in_grace_period:
                    is_subscribed = True
                    active_product_id = e.product_id
                    expires_date = e.expires_date
                    will_renew = e.will_renew
                    is_in_grace_period = e.is_in_grace_period
            else:
                # No expiry = lifetime / non-consumable
                is_subscribed = True
                active_product_id = e.product_id
        elif e.is_active and e.type in ("non_consumable",):
            is_subscribed = True
            active_product_id = e.product_id

    return SubscriptionStatusResponse(
        is_subscribed=is_subscribed,
        entitlements=entitlement_responses,
        active_product_id=active_product_id,
        expires_date=expires_date,
        will_renew=will_renew,
        is_in_grace_period=is_in_grace_period,
    )


# ---------------------------------------------------------------------------
# Product Catalog
# ---------------------------------------------------------------------------

@router.get(
    "/products",
    response_model=list[ProductResponse],
)
async def get_products(
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """Get the catalog of available IAP products.

    Returns all active products from the local catalog.
    The client uses this to display available purchase options.
    """
    result = await db.execute(
        select(Product).where(Product.is_active == True)  # noqa: E712
    )
    products = result.scalars().all()
    return products


# ---------------------------------------------------------------------------
# Restore Purchases
# ---------------------------------------------------------------------------

@router.post(
    "/restore",
    response_model=RestorePurchasesResponse,
)
async def restore_purchases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """Restore all previous purchases for the current user.

    Fetches transaction history from Apple for all known
    original transaction IDs and re-establishes entitlements.
    Use this when a user reinstalls the app or signs in on a new device.
    """
    service = EntitlementService(db)

    try:
        restored_count = await service.restore_purchases(current_user.id)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Restore purchases failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to restore purchases. Please try again.",
        )

    # Return current entitlements
    entitlements = await service.get_user_entitlements(current_user.id)
    entitlement_responses = [
        EntitlementResponse(
            product_id=e.product_id,
            type=e.type,
            is_active=e.is_active,
            purchase_date=e.purchase_date,
            expires_date=e.expires_date,
            will_renew=e.will_renew,
            auto_renew_status=e.auto_renew_status,
            is_in_grace_period=e.is_in_grace_period,
            is_in_billing_retry=e.is_in_billing_retry,
            grace_period_expires_date=e.grace_period_expires_date,
            quantity_remaining=e.quantity_remaining if e.type == "consumable" else None,
            environment=e.environment,
        )
        for e in entitlements
    ]

    return RestorePurchasesResponse(
        restored_count=restored_count,
        entitlements=entitlement_responses,
    )


# ---------------------------------------------------------------------------
# Apple Server Notification V2 Webhook
# ---------------------------------------------------------------------------

@router.post(
    "/notifications",
    response_model=WebhookResponse,
    responses={400: {}, 200: {}},
)
async def apple_server_notification(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Apple App Store Server Notification V2 webhook.

    Apple POSTs to this endpoint for subscription lifecycle events:
    SUBSCRIBED, DID_RENEW, DID_FAIL_TO_RENEW, REFUND, REVOKE, etc.

    The request body is a responseBodyV2 containing:
        {"signedPayload": "<JWS string>"}

    Or in some cases, the raw JWS string is sent directly.

    **Important:** This endpoint does NOT use user JWT authentication.
    Trust is established by verifying Apple's JWS signature on the payload.

    Always returns HTTP 2xx quickly — Apple may retry on 5xx.
    """
    try:
        # Read the raw body
        raw_body = await request.body()
        raw_text = raw_body.decode("utf-8")

        # Determine the signedPayload
        signed_payload: Optional[str] = None

        # Try parsing as JSON first (responseBodyV2 format)
        try:
            body_json = json.loads(raw_text)
            signed_payload = body_json.get("signedPayload", "")
        except (json.JSONDecodeError, AttributeError):
            pass

        # If not JSON, treat the entire body as the JWS string
        if not signed_payload:
            signed_payload = raw_text.strip()

        if not signed_payload:
            logger.warning("Apple notification received with empty payload")
            return WebhookResponse(status="received", message="Empty payload")

        # Process the notification
        service = EntitlementService(db)

        try:
            await service.process_notification(signed_payload)
            await db.commit()
        except ValueError as e:
            await db.rollback()
            logger.error(f"Invalid notification: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to process notification: {e}", exc_info=True)
            # Still return 200 to prevent Apple from retrying a malformed notification
            return WebhookResponse(
                status="error",
                message="Notification stored but could not be fully processed",
            )

        logger.info("Apple notification processed successfully")
        return WebhookResponse(status="received")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in notification webhook: {e}", exc_info=True)
        # Return 200 even on unexpected errors to prevent Apple retry storms
        return WebhookResponse(
            status="error",
            message="Internal error — notification logged but not processed",
        )


# ---------------------------------------------------------------------------
# Health / debug (optional)
# ---------------------------------------------------------------------------

@router.get(
    "/products/{product_id}/entitlement",
    response_model=Optional[EntitlementResponse],
)
async def get_product_entitlement(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check entitlement for a specific product.

    Returns the entitlement if found, or null if the user
    doesn't have one. Useful for feature gating.
    """
    result = await db.execute(
        select(UserEntitlement).where(
            UserEntitlement.user_id == current_user.id,
            UserEntitlement.product_id == product_id,
        )
    )
    entitlement = result.scalar_one_or_none()

    if entitlement is None:
        return None

    return EntitlementResponse(
        product_id=entitlement.product_id,
        type=entitlement.type,
        is_active=entitlement.is_active,
        purchase_date=entitlement.purchase_date,
        expires_date=entitlement.expires_date,
        will_renew=entitlement.will_renew,
        auto_renew_status=entitlement.auto_renew_status,
        is_in_grace_period=entitlement.is_in_grace_period,
        is_in_billing_retry=entitlement.is_in_billing_retry,
        grace_period_expires_date=entitlement.grace_period_expires_date,
        quantity_remaining=entitlement.quantity_remaining if entitlement.type == "consumable" else None,
        environment=entitlement.environment,
    )
