"""
Entitlement Service — core business logic for Apple IAP.

Handles:
- Transaction verification and entitlement granting
- Apple Server Notification V2 processing
- Legacy receipt verification
- Subscription status refresh
- User entitlement queries
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.models.iap import Product, TransactionRecord, UserEntitlement
from app.models.user import User
from app.services.apple_api_client import apple_api_client
from app.services.apple_jws_verifier import apple_jws_verifier

logger = logging.getLogger(__name__)


class EntitlementService:
    """Service for managing IAP entitlements.

    Each method receives a db session — the caller is responsible
    for committing the transaction.

    Usage:
        service = EntitlementService(db)
        result = await service.verify_and_grant(user_id, transaction_id="...")
        await db.commit()
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api = apple_api_client
        self.verifier = apple_jws_verifier

    # ------------------------------------------------------------------
    # Transaction Verification (primary flow)
    # ------------------------------------------------------------------

    async def verify_and_grant(
        self,
        user_id: int,
        transaction_id: Optional[str] = None,
        receipt_data: Optional[str] = None,
    ) -> TransactionRecord:
        """Verify a purchase with Apple and grant entitlement.

        This is the MAIN entry point called by POST /api/v1/iap/verify.

        Args:
            user_id: The authenticated user's ID.
            transaction_id: StoreKit 2 transaction ID (preferred).
            receipt_data: Base64-encoded receipt (legacy fallback).

        Returns:
            The created TransactionRecord.

        Raises:
            ValueError: If neither transaction_id nor receipt_data is provided.
        """
        if transaction_id:
            return await self._verify_transaction_id(user_id, transaction_id)
        elif receipt_data:
            return await self._verify_receipt(user_id, receipt_data)
        else:
            raise ValueError("Either transaction_id or receipt_data is required")

    async def _verify_transaction_id(
        self, user_id: int, transaction_id: str
    ) -> TransactionRecord:
        """Verify via App Store Server API (modern StoreKit 2 flow)."""

        # 1. Fetch signed transaction info from Apple
        try:
            tx_info = await self.api.get_transaction(
                transaction_id, verify=True
            )
        except Exception as e:
            logger.error(f"Failed to get transaction {transaction_id}: {e}")
            raise ValueError(f"Could not verify transaction with Apple: {e}")

        if not tx_info:
            raise ValueError(f"Transaction {transaction_id} not found or verification failed")

        # 2. Extract key fields from decoded transaction info
        apple_tx_id = tx_info.get("transactionId", transaction_id)
        original_tx_id = tx_info.get("originalTransactionId", apple_tx_id)
        product_id = tx_info.get("productId", "")
        tx_type = tx_info.get("type", "")  # "Auto-Renewable Subscription", "Consumable", etc.
        environment = tx_info.get("environment", settings.APPLE_IAP_ENVIRONMENT.capitalize())
        purchase_date_ms = tx_info.get("purchaseDate")
        expires_date_ms = tx_info.get("expiresDate")

        purchase_date = self._ms_to_datetime(purchase_date_ms)
        expires_date = self._ms_to_datetime(expires_date_ms)

        # 3. Map Apple product type to our type
        our_type = self._map_apple_type(tx_type)

        # 4. Check/seed product record
        await self._ensure_product_exists(product_id, our_type)

        # 5. Determine transaction event type
        event_type = self._determine_event_type(tx_info, our_type)

        # 6. Create transaction record (audit log)
        txn_record = TransactionRecord(
            user_id=user_id,
            transaction_id=apple_tx_id,
            original_transaction_id=original_tx_id,
            product_id=product_id,
            type=event_type,
            environment=environment,
            purchase_date=purchase_date,
            expires_date=expires_date,
            raw_response=tx_info,
        )
        self.db.add(txn_record)

        # 7. Upsert user entitlement
        await self._upsert_entitlement(
            user_id=user_id,
            product_id=product_id,
            original_transaction_id=original_tx_id,
            transaction_id=apple_tx_id,
            product_type=our_type,
            purchase_date=purchase_date,
            expires_date=expires_date,
            environment=environment,
            tx_info=tx_info,
        )

        logger.info(
            f"Transaction verified: user={user_id}, product={product_id}, "
            f"tx_id={apple_tx_id}, type={event_type}"
        )
        return txn_record

    # ------------------------------------------------------------------
    # Legacy Receipt Verification
    # ------------------------------------------------------------------

    async def _verify_receipt(
        self, user_id: int, receipt_data: str
    ) -> TransactionRecord:
        """Verify via legacy /verifyReceipt endpoint."""

        data = await self.api.verify_receipt(receipt_data)

        status = data.get("status", -1)
        if status != 0:
            logger.warning(f"Receipt verification status={status}: {data}")
            raise ValueError(
                f"Receipt verification failed (status={status}). "
                "The receipt may be invalid or from a different environment."
            )

        receipt = data.get("receipt", {})
        latest_receipt_info = data.get("latest_receipt_info", [])
        pending_renewal_info = data.get("pending_renewal_info", [])

        environment = data.get("environment", "Production")

        if not latest_receipt_info:
            # For consumables, check the in_app field in the receipt
            in_app_list = receipt.get("in_app", [])
            if in_app_list:
                latest_transaction = in_app_list[-1]
            else:
                raise ValueError("No transactions found in receipt")
        else:
            latest_transaction = latest_receipt_info[-1]

        # Extract fields
        apple_tx_id = latest_transaction.get("transaction_id", "")
        original_tx_id = latest_transaction.get("original_transaction_id", apple_tx_id)
        product_id = latest_transaction.get("product_id", "")
        purchase_date_ms = latest_transaction.get("purchase_date_ms")
        expires_date_ms = latest_transaction.get("expires_date_ms")

        purchase_date = self._ms_to_datetime(
            int(purchase_date_ms) if purchase_date_ms else None
        )
        expires_date = self._ms_to_datetime(
            int(expires_date_ms) if expires_date_ms else None
        )

        # Determine product type from receipt
        our_type = "auto_renewable_subscription" if expires_date else "consumable"

        # Ensure product record exists
        await self._ensure_product_exists(product_id, our_type)

        # Determine event type
        event_type = "renewal" if latest_receipt_info and len(latest_receipt_info) > 1 else "purchase"

        # Look up renewal info
        renewal_info = {}
        if pending_renewal_info:
            renewal_info = pending_renewal_info[0]

        # Create transaction record
        txn_record = TransactionRecord(
            user_id=user_id,
            transaction_id=apple_tx_id,
            original_transaction_id=original_tx_id,
            product_id=product_id,
            type=event_type,
            environment=environment,
            purchase_date=purchase_date,
            expires_date=expires_date,
            receipt_data=receipt_data,
            raw_response=data,
        )
        self.db.add(txn_record)

        # Upsert entitlement
        await self._upsert_entitlement(
            user_id=user_id,
            product_id=product_id,
            original_transaction_id=original_tx_id,
            transaction_id=apple_tx_id,
            product_type=our_type,
            purchase_date=purchase_date,
            expires_date=expires_date,
            environment=environment,
            tx_info=None,
            renewal_info=renewal_info,
        )

        logger.info(
            f"Receipt verified: user={user_id}, product={product_id}, "
            f"tx_id={apple_tx_id}"
        )
        return txn_record

    # ------------------------------------------------------------------
    # Server Notification Processing
    # ------------------------------------------------------------------

    async def process_notification(self, signed_payload: str) -> Optional[TransactionRecord]:
        """Process an Apple App Store Server Notification V2.

        This is called by the webhook endpoint POST /api/v1/iap/notifications.

        Args:
            signed_payload: The raw JWS string from the request body.

        Returns:
            The created TransactionRecord, or None if processing was skipped
            (e.g., duplicate notification).
        """
        # 1. Verify and decode the notification JWS
        payload = await self.verifier.verify_and_decode(signed_payload)
        if payload is None:
            logger.error("Notification JWS verification failed")
            raise ValueError("Invalid notification signature")

        # 2. Extract notification metadata
        notification_type = payload.get("notificationType", "")
        subtype = payload.get("subtype", "")
        notification_uuid = payload.get("notificationUUID", "")
        signed_date = payload.get("signedDate")

        # 3. Check for duplicate notification
        is_duplicate = await self._is_duplicate_notification(notification_uuid)
        if is_duplicate:
            logger.info(f"Duplicate notification {notification_uuid}, skipping")
            return None

        # 4. Extract and verify signed transaction info from the data object
        data = payload.get("data") or {}
        signed_tx_info = data.get("signedTransactionInfo", "")
        signed_renewal_info = data.get("signedRenewalInfo", "")

        if not signed_tx_info:
            logger.error(f"Notification {notification_type} has no signedTransactionInfo")
            # Still create a record for audit
            txn_record = TransactionRecord(
                user_id=None,
                transaction_id=notification_uuid or f"notif_{signed_date}",
                original_transaction_id="",
                product_id="",
                type=notification_type.lower(),
                environment=settings.APPLE_IAP_ENVIRONMENT.capitalize(),
                notification_type=notification_type,
                notification_subtype=subtype,
                notification_uuid=notification_uuid,
                raw_response=payload,
            )
            self.db.add(txn_record)
            return txn_record

        # Decode transaction info
        tx_info = await self.verifier.verify_and_decode(signed_tx_info)
        if tx_info is None:
            logger.error("Failed to verify signedTransactionInfo in notification")
            raise ValueError("Invalid transaction info in notification")

        renewal_info = None
        if signed_renewal_info:
            renewal_info = await self.verifier.verify_and_decode(signed_renewal_info)

        # 5. Extract transaction fields
        apple_tx_id = tx_info.get("transactionId", "")
        original_tx_id = tx_info.get("originalTransactionId", apple_tx_id)
        product_id = tx_info.get("productId", "")
        environment = tx_info.get("environment", "Production")
        purchase_date = self._ms_to_datetime(tx_info.get("purchaseDate"))
        expires_date = self._ms_to_datetime(tx_info.get("expiresDate"))

        # 6. Find the associated user
        user_id = await self._find_user_by_original_tx(original_tx_id)

        # 7. Ensure product record
        our_type = self._map_apple_type(tx_info.get("type", ""))
        if product_id:
            await self._ensure_product_exists(product_id, our_type)

        # 8. Create transaction record
        txn_record = TransactionRecord(
            user_id=user_id,
            transaction_id=apple_tx_id or notification_uuid,
            original_transaction_id=original_tx_id,
            product_id=product_id,
            type=self._map_notification_to_event_type(notification_type, subtype),
            environment=environment,
            purchase_date=purchase_date,
            expires_date=expires_date,
            notification_type=notification_type,
            notification_subtype=subtype,
            notification_uuid=notification_uuid,
            raw_response=payload,
        )
        self.db.add(txn_record)

        # 9. Update entitlement based on notification type
        if user_id:
            await self._handle_notification_entitlement_update(
                user_id=user_id,
                notification_type=notification_type,
                subtype=subtype,
                product_id=product_id,
                original_transaction_id=original_tx_id,
                transaction_id=apple_tx_id,
                expires_date=expires_date,
                environment=environment,
                tx_info=tx_info,
                renewal_info=renewal_info,
            )

        logger.info(
            f"Notification processed: type={notification_type}, subtype={subtype}, "
            f"user={user_id}, product={product_id}"
        )
        return txn_record

    async def _handle_notification_entitlement_update(
        self,
        user_id: int,
        notification_type: str,
        subtype: str,
        product_id: str,
        original_transaction_id: str,
        transaction_id: str,
        expires_date: Optional[datetime],
        environment: str,
        tx_info: dict,
        renewal_info: Optional[dict],
    ):
        """Update UserEntitlement based on the notification type."""

        if notification_type == "SUBSCRIBED":
            # New subscription — grant entitlement
            await self._upsert_entitlement(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                transaction_id=transaction_id,
                product_type="auto_renewable_subscription",
                purchase_date=self._ms_to_datetime(tx_info.get("purchaseDate")),
                expires_date=expires_date,
                environment=environment,
                tx_info=tx_info,
                renewal_info=renewal_info,
            )

        elif notification_type == "DID_RENEW":
            # Renewal succeeded — update expires date, ensure active
            await self._update_entitlement_dates(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                transaction_id=transaction_id,
                expires_date=expires_date,
                is_active=True,
                is_in_billing_retry=False,
                is_in_grace_period=False,
            )

        elif notification_type == "DID_CHANGE_RENEWAL_PREF":
            # User changed product (upgrade/downgrade) — handled in the next renewal
            if tx_info:
                new_product_id = tx_info.get("productId") or tx_info.get(
                    "autoRenewProductId", product_id
                )
                if new_product_id != product_id:
                    await self._update_entitlement_product(
                        user_id=user_id,
                        old_product_id=product_id,
                        new_product_id=new_product_id,
                        original_transaction_id=original_transaction_id,
                        transaction_id=transaction_id,
                        expires_date=expires_date,
                    )

        elif notification_type == "DID_CHANGE_RENEWAL_STATUS":
            # Auto-renew toggled on/off
            auto_renew_on = subtype == "AUTO_RENEW_ENABLED"
            await self._update_entitlement_renewal_status(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                auto_renew_status=auto_renew_on,
            )

        elif notification_type == "DID_FAIL_TO_RENEW":
            # Renewal failed — billing issue
            if subtype == "GRACE_PERIOD":
                grace_period_expires = self._ms_to_datetime(
                    tx_info.get("gracePeriodExpiresDate") if tx_info else None
                )
                await self._update_entitlement_dates(
                    user_id=user_id,
                    product_id=product_id,
                    original_transaction_id=original_transaction_id,
                    transaction_id=transaction_id,
                    is_in_billing_retry=True,
                    is_in_grace_period=True,
                    grace_period_expires_date=grace_period_expires,
                )
            else:
                await self._update_entitlement_dates(
                    user_id=user_id,
                    product_id=product_id,
                    original_transaction_id=original_transaction_id,
                    transaction_id=transaction_id,
                    is_in_billing_retry=True,
                )

        elif notification_type == "EXPIRED":
            # Subscription expired
            await self._update_entitlement_dates(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                transaction_id=transaction_id,
                is_active=False,
                is_in_billing_retry=False,
                is_in_grace_period=False,
            )

        elif notification_type == "GRACE_PERIOD_EXPIRED":
            # Grace period ended without recovery
            await self._update_entitlement_dates(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                transaction_id=transaction_id,
                is_active=False,
                is_in_grace_period=False,
            )

        elif notification_type in ("REFUND", "REVOKE"):
            # Refunded or revoked — immediately deactivate
            await self._update_entitlement_dates(
                user_id=user_id,
                product_id=product_id,
                original_transaction_id=original_transaction_id,
                transaction_id=transaction_id,
                is_active=False,
            )

        elif notification_type == "OFFER_REDEEMED":
            # Promotional offer redeemed — refresh from Apple to get new dates
            if original_transaction_id:
                await self.refresh_subscription(user_id, original_transaction_id)

        else:
            logger.debug(
                f"Unhandled notification type: {notification_type} (subtype: {subtype}) — "
                "stored for audit but no entitlement change"
            )

    # ------------------------------------------------------------------
    # Entitlement queries
    # ------------------------------------------------------------------

    async def get_user_entitlements(self, user_id: int) -> List[UserEntitlement]:
        """Get all entitlements for a user."""
        result = await self.db.execute(
            select(UserEntitlement).where(UserEntitlement.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_active_entitlements(self, user_id: int) -> List[UserEntitlement]:
        """Get only active (non-expired) entitlements for a user."""
        result = await self.db.execute(
            select(UserEntitlement).where(
                and_(
                    UserEntitlement.user_id == user_id,
                    UserEntitlement.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def check_entitlement(self, user_id: int, product_id: str) -> bool:
        """Check if a user has an active entitlement for a specific product."""
        result = await self.db.execute(
            select(UserEntitlement).where(
                and_(
                    UserEntitlement.user_id == user_id,
                    UserEntitlement.product_id == product_id,
                    UserEntitlement.is_active == True,  # noqa: E712
                )
            )
        )
        entitlement = result.scalar_one_or_none()

        if entitlement is None:
            return False

        # For subscriptions, also check expiry
        if entitlement.type == "auto_renewable_subscription":
            if entitlement.expires_date:
                now = datetime.now(timezone.utc)
                if entitlement.expires_date.replace(tzinfo=timezone.utc) < now:
                    # Check grace period
                    if (
                        entitlement.is_in_grace_period
                        and entitlement.grace_period_expires_date
                    ):
                        gp_expires = entitlement.grace_period_expires_date.replace(
                            tzinfo=timezone.utc
                        )
                        return gp_expires > now
                    return False

        return True

    # ------------------------------------------------------------------
    # Subscription refresh
    # ------------------------------------------------------------------

    async def refresh_subscription(
        self, user_id: int, original_transaction_id: str
    ) -> Optional[dict]:
        """Refresh a subscription's status from Apple API.

        Args:
            user_id: The user ID.
            original_transaction_id: The subscription's original transaction ID.

        Returns:
            Dict with updated status info, or None if the call fails.
        """
        try:
            status_data = await self.api.get_subscription_status(
                original_transaction_id
            )

            for group in status_data.get("data", []):
                for last_tx in group.get("lastTransactions", []):
                    signed_info = last_tx.get("signedTransactionInfo", "")
                    signed_renewal = last_tx.get("signedRenewalInfo", "")

                    if not signed_info:
                        continue

                    tx_info = await self.verifier.verify_and_decode(signed_info)
                    if tx_info is None:
                        continue

                    renewal_info = None
                    if signed_renewal:
                        renewal_info = await self.verifier.verify_and_decode(
                            signed_renewal
                        )

                    status = last_tx.get("status", 0)
                    product_id = tx_info.get("productId", "")
                    expires_date = self._ms_to_datetime(tx_info.get("expiresDate"))

                    is_active = status == 1  # 1 = Active
                    will_renew = (
                        renewal_info.get("autoRenewStatus") == 1
                        if renewal_info
                        else None
                    )

                    # Update entitlement
                    await self._upsert_entitlement(
                        user_id=user_id,
                        product_id=product_id,
                        original_transaction_id=original_transaction_id,
                        transaction_id=tx_info.get("transactionId", ""),
                        product_type="auto_renewable_subscription",
                        purchase_date=self._ms_to_datetime(
                            tx_info.get("purchaseDate")
                        ),
                        expires_date=expires_date,
                        environment=tx_info.get(
                            "environment",
                            settings.APPLE_IAP_ENVIRONMENT.capitalize(),
                        ),
                        tx_info=tx_info,
                        renewal_info=renewal_info,
                    )

                    return {
                        "product_id": product_id,
                        "status": status,
                        "is_active": is_active,
                        "will_renew": will_renew,
                        "expires_date": expires_date,
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to refresh subscription {original_transaction_id}: {e}")
            return None

    async def refresh_user_subscriptions(self, user_id: int) -> List[dict]:
        """Refresh all subscription entitlements for a user."""
        entitlements = await self.get_user_entitlements(user_id)
        results = []

        for ent in entitlements:
            if ent.type == "auto_renewable_subscription" and ent.original_transaction_id:
                result = await self.refresh_subscription(
                    user_id, ent.original_transaction_id
                )
                if result:
                    results.append(result)

        return results

    # ------------------------------------------------------------------
    # Restore purchases
    # ------------------------------------------------------------------

    async def restore_purchases(self, user_id: int) -> int:
        """Restore all purchases for a user by querying transaction history.

        For each known original_transaction_id, fetches the latest transaction
        info from Apple and re-creates entitlements.

        Returns the count of restored entitlements.
        """
        # Find all distinct original_transaction_ids for this user
        result = await self.db.execute(
            select(TransactionRecord.original_transaction_id)
            .where(TransactionRecord.user_id == user_id)
            .distinct()
        )
        original_tx_ids = [row[0] for row in result.all() if row[0]]

        restored_count = 0
        for orig_tx_id in original_tx_ids:
            try:
                # Get transaction history
                history = await self.api.get_transaction_history(orig_tx_id)
                signed_txs = history.get("signedTransactions", [])

                if signed_txs:
                    # Verify and process the most recent transaction
                    latest_jws = signed_txs[-1]
                    tx_info = await self.verifier.verify_and_decode(latest_jws)
                    if tx_info:
                        product_id = tx_info.get("productId", "")
                        expires_date = self._ms_to_datetime(
                            tx_info.get("expiresDate")
                        )
                        await self._upsert_entitlement(
                            user_id=user_id,
                            product_id=product_id,
                            original_transaction_id=orig_tx_id,
                            transaction_id=tx_info.get("transactionId", ""),
                            product_type="auto_renewable_subscription",
                            purchase_date=self._ms_to_datetime(
                                tx_info.get("purchaseDate")
                            ),
                            expires_date=expires_date,
                            environment=tx_info.get(
                                "environment",
                                settings.APPLE_IAP_ENVIRONMENT.capitalize(),
                            ),
                            tx_info=tx_info,
                        )
                        restored_count += 1
            except Exception as e:
                logger.error(f"Failed to restore purchase {orig_tx_id}: {e}")

        return restored_count

    # ------------------------------------------------------------------
    # Entitlement upsert / update helpers
    # ------------------------------------------------------------------

    async def _upsert_entitlement(
        self,
        user_id: int,
        product_id: str,
        original_transaction_id: str,
        transaction_id: str,
        product_type: str,
        purchase_date: Optional[datetime],
        expires_date: Optional[datetime],
        environment: str,
        tx_info: Optional[dict] = None,
        renewal_info: Optional[dict] = None,
    ):
        """Insert or update a UserEntitlement record.

        Uses PostgreSQL ON CONFLICT ... DO UPDATE for atomic upsert.
        """
        # Determine auto-renew and will-renew from renewal info
        auto_renew_status = None
        will_renew = None

        if renewal_info:
            auto_renew_int = renewal_info.get("autoRenewStatus")
            if auto_renew_int is not None:
                auto_renew_status = auto_renew_int == 1
            will_renew_int = renewal_info.get("renewalPrice") or renewal_info.get("expirationIntent")
            # "will renew" is based on auto_renew_status == 1 and no expiration intent
            if auto_renew_status is True:
                expiration_intent = renewal_info.get("expirationIntent")
                will_renew = expiration_intent != 1  # 1 = customer intends to let expire

        now = datetime.now(timezone.utc)

        # Check if already expired
        is_active = True
        if expires_date:
            exp = expires_date.replace(tzinfo=timezone.utc) if expires_date.tzinfo is None else expires_date
            if exp < now:
                is_active = False

        values = {
            "user_id": user_id,
            "product_id": product_id,
            "original_transaction_id": original_transaction_id,
            "transaction_id": transaction_id,
            "type": product_type,
            "is_active": is_active,
            "purchase_date": purchase_date,
            "expires_date": expires_date,
            "auto_renew_status": auto_renew_status,
            "will_renew": will_renew,
            "environment": environment,
            "updated_at": now,
        }

        # Use PostgreSQL upsert
        stmt = pg_insert(UserEntitlement).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "product_id"],
            set_={
                "original_transaction_id": stmt.excluded.original_transaction_id,
                "transaction_id": stmt.excluded.transaction_id,
                "is_active": stmt.excluded.is_active,
                "purchase_date": stmt.excluded.purchase_date,
                "expires_date": stmt.excluded.expires_date,
                "auto_renew_status": stmt.excluded.auto_renew_status,
                "will_renew": stmt.excluded.will_renew,
                "environment": stmt.excluded.environment,
                "is_in_grace_period": False,
                "is_in_billing_retry": False,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await self.db.execute(stmt)

    async def _update_entitlement_dates(
        self,
        user_id: int,
        product_id: str,
        original_transaction_id: str,
        transaction_id: str = "",
        expires_date: Optional[datetime] = None,
        is_active: Optional[bool] = None,
        is_in_billing_retry: Optional[bool] = None,
        is_in_grace_period: Optional[bool] = None,
        grace_period_expires_date: Optional[datetime] = None,
    ):
        """Update specific fields on an existing entitlement."""
        result = await self.db.execute(
            select(UserEntitlement).where(
                and_(
                    UserEntitlement.user_id == user_id,
                    UserEntitlement.product_id == product_id,
                    UserEntitlement.original_transaction_id == original_transaction_id,
                )
            )
        )
        entitlement = result.scalar_one_or_none()

        if entitlement is None:
            logger.warning(
                f"No entitlement found for user={user_id}, product={product_id}, "
                f"orig_tx={original_transaction_id} — cannot update"
            )
            return

        if transaction_id:
            entitlement.transaction_id = transaction_id
        if expires_date is not None:
            entitlement.expires_date = expires_date
        if is_active is not None:
            entitlement.is_active = is_active
        if is_in_billing_retry is not None:
            entitlement.is_in_billing_retry = is_in_billing_retry
        if is_in_grace_period is not None:
            entitlement.is_in_grace_period = is_in_grace_period
        if grace_period_expires_date is not None:
            entitlement.grace_period_expires_date = grace_period_expires_date

        entitlement.updated_at = datetime.now(timezone.utc)

        logger.info(
            f"Updated entitlement: user={user_id}, product={product_id}, "
            f"is_active={is_active}, expires={expires_date}"
        )

    async def _update_entitlement_renewal_status(
        self,
        user_id: int,
        product_id: str,
        original_transaction_id: str,
        auto_renew_status: bool,
    ):
        """Update auto-renew status on an entitlement."""
        result = await self.db.execute(
            select(UserEntitlement).where(
                and_(
                    UserEntitlement.user_id == user_id,
                    UserEntitlement.product_id == product_id,
                    UserEntitlement.original_transaction_id == original_transaction_id,
                )
            )
        )
        entitlement = result.scalar_one_or_none()

        if entitlement:
            entitlement.auto_renew_status = auto_renew_status
            entitlement.will_renew = auto_renew_status
            entitlement.updated_at = datetime.now(timezone.utc)

    async def _update_entitlement_product(
        self,
        user_id: int,
        old_product_id: str,
        new_product_id: str,
        original_transaction_id: str,
        transaction_id: str,
        expires_date: Optional[datetime],
    ):
        """Handle product change (upgrade/downgrade)."""
        result = await self.db.execute(
            select(UserEntitlement).where(
                and_(
                    UserEntitlement.user_id == user_id,
                    UserEntitlement.product_id == old_product_id,
                    UserEntitlement.original_transaction_id == original_transaction_id,
                )
            )
        )
        entitlement = result.scalar_one_or_none()

        if entitlement:
            entitlement.product_id = new_product_id
            entitlement.transaction_id = transaction_id
            if expires_date:
                entitlement.expires_date = expires_date
            entitlement.updated_at = datetime.now(timezone.utc)
            logger.info(
                f"Product changed: user={user_id}, {old_product_id} → {new_product_id}"
            )

    # ------------------------------------------------------------------
    # Product helpers
    # ------------------------------------------------------------------

    async def _ensure_product_exists(self, product_id: str, product_type: str) -> Product:
        """Get or create a Product record for the given product ID."""
        result = await self.db.execute(
            select(Product).where(Product.product_id == product_id)
        )
        product = result.scalar_one_or_none()

        if product is None:
            product = Product(
                product_id=product_id,
                name=product_id,  # Can be updated later in admin
                type=product_type,
                is_active=True,
            )
            self.db.add(product)
            logger.info(f"Auto-created product record: {product_id} ({product_type})")

        return product

    # ------------------------------------------------------------------
    # User lookup (for notifications)
    # ------------------------------------------------------------------

    async def _find_user_by_original_tx(
        self, original_transaction_id: str
    ) -> Optional[int]:
        """Find a user by their original transaction ID.

        Searches both UserEntitlement and TransactionRecord tables.
        """
        # Try UserEntitlement first (faster)
        result = await self.db.execute(
            select(UserEntitlement.user_id).where(
                UserEntitlement.original_transaction_id == original_transaction_id
            )
        )
        user_id = result.scalar_one_or_none()

        if user_id:
            return user_id

        # Fall back to TransactionRecord
        result = await self.db.execute(
            select(TransactionRecord.user_id).where(
                and_(
                    TransactionRecord.original_transaction_id == original_transaction_id,
                    TransactionRecord.user_id.isnot(None),
                )
            )
        )
        tx_record = result.first()

        return tx_record[0] if tx_record else None

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    async def _is_duplicate_notification(self, notification_uuid: str) -> bool:
        """Check if a notification has already been processed."""
        if not notification_uuid:
            return False

        result = await self.db.execute(
            select(TransactionRecord.id).where(
                TransactionRecord.notification_uuid == notification_uuid
            )
        )
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ms_to_datetime(ms: Optional[int]) -> Optional[datetime]:
        """Convert Apple's millisecond timestamp to a datetime."""
        if ms is None:
            return None
        try:
            return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            return None

    @staticmethod
    def _map_apple_type(apple_type: str) -> str:
        """Map Apple's transaction type string to our type."""
        type_lower = apple_type.lower()
        if "subscription" in type_lower:
            return "auto_renewable_subscription"
        elif "consumable" in type_lower:
            return "consumable"
        elif "non-consumable" in type_lower or "non_consumable" in type_lower:
            return "non_consumable"
        return "consumable"

    @staticmethod
    def _determine_event_type(tx_info: dict, product_type: str) -> str:
        """Determine the event type from transaction info."""
        # For subscriptions, check if this is an initial purchase or renewal
        if product_type == "auto_renewable_subscription":
            original_tx_id = tx_info.get("originalTransactionId", "")
            transaction_id = tx_info.get("transactionId", "")
            if original_tx_id != transaction_id:
                return "renewal"
            return "purchase"
        return "purchase"

    @staticmethod
    def _map_notification_to_event_type(
        notification_type: str, subtype: str
    ) -> str:
        """Map Apple notification type to our internal event type."""
        mapping = {
            "SUBSCRIBED": "purchase",
            "DID_RENEW": "renewal",
            "DID_CHANGE_RENEWAL_PREF": "renewal_pref_change",
            "DID_CHANGE_RENEWAL_STATUS": "renewal_status_change",
            "DID_FAIL_TO_RENEW": "billing_retry",
            "EXPIRED": "expired",
            "GRACE_PERIOD_EXPIRED": "expired",
            "REFUND": "refund",
            "REVOKE": "revoke",
            "OFFER_REDEEMED": "purchase",
            "REFUND_DECLINED": "refund_declined",
            "REFUND_REVERSED": "refund_reversed",
            "RENEWAL_EXTENDED": "renewal",
            "RENEWAL_EXTENSION": "renewal_extension",
            "PRICE_INCREASE": "price_increase",
            "CONSUMPTION_REQUEST": "consumption_request",
            "TEST": "test",
        }
        return mapping.get(notification_type, notification_type.lower())
