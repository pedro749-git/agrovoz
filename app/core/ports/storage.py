"""Port: object storage for the generated legal documents (today: Alibaba OSS).

Async on purpose: uploading is network I/O (unlike PdfGenerator, which is pure
CPU and therefore synchronous). The PDF is built in memory, then handed here as
bytes; this port never knows it is a PDF, only "store these bytes under a key".

Adapters translate provider errors (oss2...) into ``StorageError`` at the
boundary, so the core survives a storage-provider swap untouched.
"""

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    async def upload(self, *, data: bytes, key: str, content_type: str) -> None:
        """Store ``data`` under ``key`` (overwrites: keys are deterministic, so a
        retry re-uploads the same object). Raises ``StorageError`` on failure."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Whether an object is stored under ``key`` (a HEAD). Lets a caller
        return a clean 'no document' instead of handing out a signed URL whose
        object is missing — which would surface the provider's raw error page."""

    @abstractmethod
    async def presigned_url(self, key: str, *, expires_seconds: int = 3600) -> str:
        """A temporary signed URL to GET a private object (legal documents live
        in a private bucket). Default expiry: 1 hour."""
