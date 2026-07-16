"""
Apple App Store Server API JWT Service

Generates ES256-signed JSON Web Tokens for authenticating with
Apple's App Store Server API.

Reference: https://developer.apple.com/documentation/appstoreserverapi/generating_json_web_tokens_for_api_requests
"""
import time
import logging
from typing import Optional
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Token cache TTL: regenerate when less than 5 minutes remain
_TOKEN_CACHE_TTL_SECONDS = 60 * 55  # 55 minutes (tokens valid for 60 min)


class AppleJWTService:
    """Generate ES256 JWTs for Apple App Store Server API authentication.

    Tokens are cached for ~55 minutes and regenerated when near expiry.

    Usage:
        service = AppleJWTService()
        token = service.generate_token()
    """

    def __init__(self):
        self._issuer_id: str = settings.APPLE_IAP_ISSUER_ID
        self._key_id: str = settings.APPLE_IAP_KEY_ID
        self._bundle_id: str = settings.APPLE_IAP_BUNDLE_ID
        self._private_key: str = self._load_private_key()

        # Token cache
        self._cached_token: Optional[str] = None
        self._token_generated_at: float = 0.0

    def _load_private_key(self) -> str:
        """Load the .p8 private key.

        Supports two modes:
        1. APPLE_IAP_PRIVATE_KEY contains the PEM key content directly
        2. APPLE_IAP_PRIVATE_KEY contains a file path (starts with / or ./)
        """
        key_or_path = settings.APPLE_IAP_PRIVATE_KEY.strip()

        if not key_or_path:
            logger.warning("Apple IAP private key is empty — API calls will fail")

        # Check if it looks like a file path
        if key_or_path and (key_or_path.startswith("/") or key_or_path.startswith("./")):
            try:
                with open(key_or_path, "r") as f:
                    return f.read().strip()
            except FileNotFoundError:
                logger.error(f"Apple private key file not found: {key_or_path}")
                return ""

        # Assume inline key content
        return key_or_path

    @property
    def is_configured(self) -> bool:
        """Check whether all required Apple credentials are present."""
        return all([self._issuer_id, self._key_id, self._bundle_id, self._private_key])

    def generate_token(self) -> str:
        """Generate (or return cached) ES256 JWT for Apple API authentication.

        The token is valid for 60 minutes. Tokens are cached and reused
        until 5 minutes before expiry.
        """
        # Return cached token if still fresh
        now = time.time()
        if (
            self._cached_token is not None
            and (now - self._token_generated_at) < _TOKEN_CACHE_TTL_SECONDS
        ):
            return self._cached_token

        if not self.is_configured:
            raise ValueError(
                "Apple IAP credentials not configured. Missing one of: "
                "ISSUER_ID, KEY_ID, BUNDLE_ID, or PRIVATE_KEY."
            )

        iat = int(now)
        exp = iat + 3600  # 1 hour from now

        payload = {
            "iss": self._issuer_id,
            "iat": iat,
            "exp": exp,
            "aud": "appstoreconnect-v1",
            "bid": self._bundle_id,
        }

        headers = {
            "kid": self._key_id,
            "typ": "JWT",
        }

        token = jwt.encode(
            payload,
            self._private_key,
            algorithm="ES256",
            headers=headers,
        )

        # Cache the new token
        self._cached_token = token
        self._token_generated_at = now

        logger.debug(f"Generated new Apple JWT (iss={self._issuer_id}, exp={exp})")
        return token

    def invalidate_cache(self) -> None:
        """Force regeneration of the token on next generate_token() call."""
        self._cached_token = None
        self._token_generated_at = 0.0


# Module-level singleton (pattern follows COSService)
apple_jwt_service = AppleJWTService()
