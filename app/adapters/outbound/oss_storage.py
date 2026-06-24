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
        self._bucket: oss2.Bucket | None = None

    def _get_bucket(self) -> oss2.Bucket:
        """Build the bucket on first use (lazy), mirroring the Supabase client.

        The ``oss2.Bucket`` constructor VALIDATES the endpoint, so building it in
        ``__init__`` would make merely importing the app require a valid OSS
        config — an empty ``OSS_ENDPOINT`` raises here. Deferring it keeps imports
        (CI, unit tests that mock storage) free of OSS config; only a real
        upload/sign touches it. The Bucket is a lightweight, thread-safe client
        cached after the first call.
        """
        if self._bucket is None:
            auth = oss2.Auth(
                settings.oss_access_key_id,
                settings.oss_access_key_secret.get_secret_value(),
            )
            self._bucket = oss2.Bucket(
                auth, settings.oss_endpoint, settings.oss_bucket_name
            )
        return self._bucket

    async def upload(self, *, data: bytes, key: str, content_type: str) -> None:
        bucket = self._get_bucket()
        try:
            await asyncio.to_thread(
                bucket.put_object,
                key,
                data,
                headers={"Content-Type": content_type},
            )
        except oss2.exceptions.OssError as exc:
            raise StorageError(f"OSS upload failed for «{key}»") from exc

    async def exists(self, key: str) -> bool:
        bucket = self._get_bucket()
        try:
            # HEAD via the SDK (network I/O -> worker thread).
            return await asyncio.to_thread(bucket.object_exists, key)
        except oss2.exceptions.OssError as exc:
            raise StorageError(f"OSS object_exists failed for «{key}»") from exc

    async def presigned_url(self, key: str, *, expires_seconds: int = 3600) -> str:
        bucket = self._get_bucket()
        # Serve the PDF as a download with a sensible filename. ``attachment``
        # works reliably on desktop AND mobile, unlike inline rendering (which a
        # browser setting like "download PDFs instead of opening them" overrides,
        # and which mobile cannot show in a JS-opened tab). Only the disposition
        # is overridden: the object already stores Content-Type application/pdf
        # (set at upload), and OSS rejects a response-content-type override. This
        # param is signed too.
        params = {
            "response-content-disposition": 'attachment; filename="prescripcion.pdf"',
        }
        # sign_url is local crypto (no network), so no to_thread needed.
        try:
            return bucket.sign_url("GET", key, expires_seconds, params=params)
        except oss2.exceptions.OssError as exc:
            raise StorageError(f"OSS sign_url failed for «{key}»") from exc
