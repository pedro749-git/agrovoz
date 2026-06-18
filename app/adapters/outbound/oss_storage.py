"""Alibaba Cloud OSS adapter implementing the Storage port.

``oss2`` is a SYNCHRONOUS SDK, so every network call runs in a worker thread
(``asyncio.to_thread``) to avoid blocking the event loop. OSS errors are
translated into the port-level ``StorageError`` at this boundary.

The bucket is private: downloads go through short-lived presigned URLs, never
public object URLs (these are Spanish legal documents).
"""

import asyncio

import oss2

from app.config.settings import settings
from app.core.domain.errors import StorageError
from app.core.ports.storage import Storage


class OssStorage(Storage):
    def __init__(self) -> None:
        auth = oss2.Auth(
            settings.oss_access_key_id,
            settings.oss_access_key_secret.get_secret_value(),
        )
        # The Bucket object is a lightweight, thread-safe client; build it once.
        self._bucket = oss2.Bucket(
            auth, settings.oss_endpoint, settings.oss_bucket_name
        )

    async def upload(self, *, data: bytes, key: str, content_type: str) -> None:
        try:
            await asyncio.to_thread(
                self._bucket.put_object,
                key,
                data,
                headers={"Content-Type": content_type},
            )
        except oss2.exceptions.OssError as exc:
            raise StorageError(f"OSS upload failed for «{key}»") from exc

    async def presigned_url(self, key: str, *, expires_seconds: int = 3600) -> str:
        # sign_url is local crypto (no network), so no to_thread needed.
        try:
            return self._bucket.sign_url("GET", key, expires_seconds)
        except oss2.exceptions.OssError as exc:
            raise StorageError(f"OSS sign_url failed for «{key}»") from exc
