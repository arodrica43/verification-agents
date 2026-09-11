"""Content-addressed blob storage (filesystem + S3/MinIO)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from formal_shared.hashing import sha256_hex


@dataclass(frozen=True)
class StoredBlob:
    content_hash: str
    uri: str
    size_bytes: int
    content_type: str


@runtime_checkable
class BlobStore(Protocol):
    async def put(
        self,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        prefix: str = "artifacts",
    ) -> StoredBlob: ...

    async def get(self, content_hash: str, *, prefix: str = "artifacts") -> bytes: ...

    async def exists(self, content_hash: str, *, prefix: str = "artifacts") -> bool: ...


class LocalFilesystemBlobStore:
    """Dev/test blob store under a local directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, content_hash: str, prefix: str) -> Path:
        return self.root / prefix / content_hash[:2] / content_hash

    async def put(
        self,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        prefix: str = "artifacts",
    ) -> StoredBlob:
        digest = sha256_hex(data)
        path = self._path(digest, prefix)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        meta = path.with_suffix(".meta")
        meta.write_text(content_type, encoding="utf-8")
        uri = f"file://{path.resolve().as_posix()}"
        return StoredBlob(
            content_hash=digest,
            uri=uri,
            size_bytes=len(data),
            content_type=content_type,
        )

    async def get(self, content_hash: str, *, prefix: str = "artifacts") -> bytes:
        path = self._path(content_hash, prefix)
        if not path.exists():
            raise FileNotFoundError(content_hash)
        return path.read_bytes()

    async def exists(self, content_hash: str, *, prefix: str = "artifacts") -> bool:
        return self._path(content_hash, prefix).exists()


class S3BlobStore:
    """S3-compatible object store (MinIO / AWS)."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        import boto3

        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _key(self, content_hash: str, prefix: str) -> str:
        return f"{prefix}/{content_hash[:2]}/{content_hash}"

    async def put(
        self,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        prefix: str = "artifacts",
    ) -> StoredBlob:
        import asyncio

        digest = sha256_hex(data)
        key = self._key(digest, prefix)

        def _upload() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata={"sha256": digest},
            )

        await asyncio.to_thread(_upload)
        endpoint = self._client.meta.endpoint_url or "s3"
        uri = f"s3://{self.bucket}/{key}"
        if endpoint and not str(endpoint).startswith("https://s3."):
            uri = f"{endpoint.rstrip('/')}/{self.bucket}/{key}"
        return StoredBlob(
            content_hash=digest,
            uri=uri,
            size_bytes=len(data),
            content_type=content_type,
        )

    async def get(self, content_hash: str, *, prefix: str = "artifacts") -> bytes:
        import asyncio

        key = self._key(content_hash, prefix)

        def _download() -> bytes:
            obj = self._client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read()

        return await asyncio.to_thread(_download)

    async def exists(self, content_hash: str, *, prefix: str = "artifacts") -> bool:
        import asyncio

        from botocore.exceptions import ClientError

        key = self._key(content_hash, prefix)

        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)


def create_blob_store_from_env() -> BlobStore:
    """Choose S3 when endpoint is set; otherwise local filesystem under BLOB_ROOT."""
    endpoint = os.environ.get("S3_ENDPOINT_URL")
    if endpoint:
        return S3BlobStore(
            bucket=os.environ.get("S3_BUCKET", "formal-artifacts"),
            endpoint_url=endpoint,
            access_key=os.environ.get("S3_ACCESS_KEY"),
            secret_key=os.environ.get("S3_SECRET_KEY"),
            region=os.environ.get("S3_REGION", "us-east-1"),
        )
    root = os.environ.get("BLOB_ROOT", ".data/blobs")
    return LocalFilesystemBlobStore(root)
