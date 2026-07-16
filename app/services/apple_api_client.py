"""
Apple App Store Server API Client

Async HTTP client wrapping Apple's App Store Server API endpoints.
Uses ES256 JWT authentication via AppleJWTService.

API Reference: https://developer.apple.com/documentation/appstoreserverapi
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.services.apple_jwt_service import apple_jwt_service
from app.services.apple_jws_verifier import apple_jws_verifier

logger = logging.getLogger(__name__)

# Base URLs
_PRODUCTION_API_BASE = "https://api.storekit.itunes.apple.com"
_SANDBOX_API_BASE = "https://api.storekit-sandbox.itunes.apple.com"

# Legacy receipt verification URLs (different from API base)
_PRODUCTION_RECEIPT_URL = "https://buy.itunes.apple.com/verifyReceipt"
_SANDBOX_RECEIPT_URL = "https://sandbox.itunes.apple.com/verifyReceipt"


class AppleAPIClient:
    """Async HTTP client for Apple App Store Server API.

    Handles:
    - JWT authentication (auto-generated per token)
    - Environment selection (sandbox / production)
    - JWS response decoding (transparent verification of signed payloads)

    Usage:
        client = AppleAPIClient()
        tx_info = await client.get_transaction("1234567890")
        await client.close()
    """

    def __init__(self):
        self._api_base: str = (
            _PRODUCTION_API_BASE
            if settings.APPLE_IAP_ENVIRONMENT == "production"
            else _SANDBOX_API_BASE
        )
        self._receipt_url: str = (
            _PRODUCTION_RECEIPT_URL
            if settings.APPLE_IAP_ENVIRONMENT == "production"
            else _SANDBOX_RECEIPT_URL
        )
        self._jwt_service = apple_jwt_service
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Build Authorization header with a fresh JWT."""
        token = self._jwt_service.generate_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an authenticated request to the App Store Server API."""
        client = await self._get_client()
        url = f"{self._api_base}{path}"
        headers = self._auth_headers()
        headers.update(kwargs.pop("headers", {}))

        logger.debug(f"Apple API {method} {url}")
        response = await client.request(method, url, headers=headers, **kwargs)
        return response

    async def _request_json(self, method: str, path: str, **kwargs) -> dict:
        """Make a request and parse the JSON response. Raises on error."""
        response = await self._request(method, path, **kwargs)

        if response.status_code >= 400:
            body = response.text
            logger.error(
                f"Apple API error: {response.status_code} {method} {path} — {body}"
            )
            response.raise_for_status()

        return response.json()

    # ------------------------------------------------------------------
    # Transaction API
    # ------------------------------------------------------------------

    async def get_transaction(
        self, transaction_id: str, verify: bool = False
    ) -> dict:
        """Get transaction info for a single transaction.

        GET /inApps/v1/transactions/{transactionId}

        Args:
            transaction_id: The transaction ID from StoreKit.
            verify: If True, verify JWS signature and return decoded payload.

        Returns:
            If verify=False: raw API response with 'signedTransactionInfo' key.
            If verify=True: decoded and verified transaction payload dict.
        """
        path = f"/inApps/v1/transactions/{transaction_id}"
        data = await self._request_json("GET", path)

        if verify:
            signed_info = data.get("signedTransactionInfo", "")
            if signed_info:
                decoded = await apple_jws_verifier.verify_and_decode(signed_info)
                if decoded is None:
                    logger.error("Failed to verify signedTransactionInfo JWS")
                    raise ValueError("Transaction info JWS verification failed")
                return decoded
            return {}

        return data

    async def get_transaction_history(
        self, original_transaction_id: str, revision: Optional[str] = None
    ) -> dict:
        """Get transaction history for a subscription.

        GET /inApps/v1/history/{originalTransactionId}

        Args:
            original_transaction_id: The original transaction ID.
            revision: Pagination revision token from previous response.

        Returns:
            Raw API response with 'signedTransactions' array.
        """
        path = f"/inApps/v1/history/{original_transaction_id}"
        params = {}
        if revision:
            params["revision"] = revision
        return await self._request_json("GET", path, params=params)

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    async def get_subscription_status(
        self, original_transaction_id: str
    ) -> dict:
        """Get all subscription statuses for a customer.

        GET /inApps/v1/subscriptions/{originalTransactionId}

        Returns subscription status for all auto-renewable subscriptions
        across all subscription groups for this original transaction.

        Args:
            original_transaction_id: Any transaction ID belonging to the customer.

        Returns:
            API response with 'data' array containing subscription groups,
            each with 'lastTransactions' containing status and signed info.
        """
        path = f"/inApps/v1/subscriptions/{original_transaction_id}"
        return await self._request_json("GET", path)

    async def get_subscription_status_for_group(
        self,
        original_transaction_id: str,
        product_id: str,
    ) -> Optional[dict]:
        """Get subscription status, filtering to a specific product.

        Returns the last transaction for the given product_id if found,
        with verified/decoded transaction info and renewal info.

        Returns None if no matching subscription is found.
        """
        try:
            data = await self.get_subscription_status(original_transaction_id)

            for group in data.get("data", []):
                for last_tx in group.get("lastTransactions", []):
                    # Decode signed transaction info
                    signed_info = last_tx.get("signedTransactionInfo", "")
                    signed_renewal = last_tx.get("signedRenewalInfo", "")

                    if not signed_info:
                        continue

                    tx_info = await apple_jws_verifier.verify_and_decode(signed_info)
                    if tx_info and tx_info.get("productId") == product_id:
                        renewal_info = None
                        if signed_renewal:
                            renewal_info = await apple_jws_verifier.verify_and_decode(
                                signed_renewal
                            )

                        return {
                            "status": last_tx.get("status"),
                            "original_transaction_id": last_tx.get(
                                "originalTransactionId"
                            ),
                            "transaction_info": tx_info,
                            "renewal_info": renewal_info,
                        }

            return None

        except Exception as e:
            logger.error(f"Error getting subscription status: {e}")
            return None

    # ------------------------------------------------------------------
    # Legacy Receipt Verification
    # ------------------------------------------------------------------

    async def verify_receipt(
        self,
        receipt_data: str,
        password: Optional[str] = None,
        exclude_old_transactions: bool = True,
    ) -> dict:
        """Legacy receipt verification via verifyReceipt endpoint.

        POST to buy.itunes.apple.com/verifyReceipt (or sandbox).

        Automatically retries on sandbox if production returns status 21007
        (indicating a sandbox receipt was sent to production).

        Args:
            receipt_data: Base64-encoded receipt from the app.
            password: App shared secret (uses config if not provided).
            exclude_old_transactions: Only return latest renewal info.

        Returns:
            Decoded receipt verification response from Apple.
        """
        if password is None:
            password = settings.APPLE_IAP_APP_SHARED_SECRET

        payload = {
            "receipt-data": receipt_data,
            "password": password,
            "exclude-old-transactions": exclude_old_transactions,
        }

        client = await self._get_client()

        # Try production first
        resp = await client.post(self._receipt_url, json=payload)
        data = resp.json()

        status = data.get("status", -1)

        # Status 21007 = sandbox receipt sent to production
        if status == 21007:
            logger.info(
                "Receipt is from sandbox environment, retrying with sandbox URL"
            )
            if self._receipt_url == _PRODUCTION_RECEIPT_URL:
                resp = await client.post(_SANDBOX_RECEIPT_URL, json=payload)
                data = resp.json()
                status = data.get("status", -1)

        if status != 0:
            logger.warning(f"Receipt verification returned status {status}: {data}")

        return data

    # ------------------------------------------------------------------
    # Decode helpers (convenience methods)
    # ------------------------------------------------------------------

    async def decode_signed_transaction(self, jws: str) -> Optional[dict]:
        """Verify and decode a signedTransactionInfo JWS string.

        Returns the decoded transaction payload or None if verification fails.
        """
        return await apple_jws_verifier.verify_and_decode(jws)

    async def decode_signed_renewal(self, jws: str) -> Optional[dict]:
        """Verify and decode a signedRenewalInfo JWS string.

        Returns the decoded renewal info payload or None if verification fails.
        """
        return await apple_jws_verifier.verify_and_decode(jws)


# Module-level singleton (pattern follows COSService)
apple_api_client = AppleAPIClient()
