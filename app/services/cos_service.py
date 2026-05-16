import os
import asyncio
import hashlib
import logging
import re
import time
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


def hash_filename(name: str, fallback: str = "file") -> str:
    """Return an ASCII-safe filename derived from ``name`` via MD5.

    Useful for sanitizing names that may contain non-ASCII characters
    (e.g. Chinese) before using them as part of a COS object key.
    """
    if not name:
        return fallback
    return hashlib.md5(name.encode("utf-8")).hexdigest()


class COSService:
    """Tencent Cloud COS upload service."""

    def __init__(self):
        self.secret_id = settings.COS_SECRET_ID
        self.secret_key = settings.COS_SECRET_KEY
        self.bucket = settings.COS_BUCKET
        self.region = settings.COS_REGION
        self.upload_prefix = settings.COS_UPLOAD_PREFIX

    def _get_client(self):
        from qcloud_cos import CosConfig, CosS3Client

        config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
        )
        return CosS3Client(config)

    @staticmethod
    def generate_object_key(file_name: str, prefix: str = "audios/") -> str:
        """Generate a unique object key for COS upload.

        The base name is hashed (MD5) so non-ASCII characters (e.g. Chinese)
        are normalized into a URL-safe object key.

        Format: audios/<md5>_timestamp_uuid.ext
        """
        file_ext = os.path.splitext(file_name)[1]
        base_name = os.path.splitext(file_name)[0]
        hashed_base = hash_filename(base_name, fallback="file")
        # Keep the extension only if it is ASCII; otherwise drop it.
        if file_ext and not re.fullmatch(r"\.[A-Za-z0-9]+", file_ext):
            file_ext = ""
        timestamp = int(time.time())
        short_uuid = uuid.uuid4().hex[:8]
        return f"{prefix}{hashed_base}_{timestamp}_{short_uuid}{file_ext}"

    async def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: str = "audio/mpeg",
    ) -> str:
        """Upload a local file to COS and return the access URL."""
        client = self._get_client()

        def _upload():
            client.put_object_from_local_file(
                Bucket=self.bucket,
                LocalFilePath=file_path,
                Key=object_key,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)

        url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{object_key}"
        logger.info(f"Uploaded to COS: {object_key} -> {url}")
        return url


# Singleton
cos_service = COSService()
