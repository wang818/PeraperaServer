import os
import asyncio
import logging
import time
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


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

        Format: audios/baseName_timestamp_uuid.ext
        """
        file_ext = os.path.splitext(file_name)[1]
        base_name = os.path.splitext(file_name)[0]
        timestamp = int(time.time())
        short_uuid = uuid.uuid4().hex[:8]
        return f"{prefix}{base_name}_{timestamp}_{short_uuid}{file_ext}"

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
