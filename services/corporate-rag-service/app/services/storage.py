from dataclasses import dataclass
import hashlib


class VersionOverwriteError(FileExistsError):
    """Raised when a versioned immutable object key already exists."""


@dataclass
class StorageConfig:
    endpoint: str
    access_key: str
    secret_key: str
    region: str
    secure: bool


class ObjectStorage:
    def __init__(self, config: StorageConfig):
        self.config = config
        import boto3

        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )

    def _object_exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    def _validate_checksum(self, payload: bytes, expected_checksum: str) -> None:
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected_checksum:
            raise ValueError("S-STORAGE-CHECKSUM-MISMATCH")

    @staticmethod
    def _is_versioned_raw_key(key: str) -> bool:
        parts = [part for part in key.split("/") if part]
        return len(parts) == 4 and parts[-1] == "raw.bin"

    def _guard_versioned_raw_overwrite(self, bucket: str, key: str) -> None:
        if self._is_versioned_raw_key(key) and self._object_exists(bucket, key):
            raise VersionOverwriteError("S-STORAGE-VERSION-EXISTS")

    def put_text(self, bucket: str, key: str, text: str) -> str:
        self.client.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType="text/plain; charset=utf-8")
        return f"s3://{bucket}/{key}"

    def get_text(self, bucket: str, key: str) -> str:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")

    def put_text_immutable(self, bucket: str, key: str, text: str, checksum_hex: str) -> str:
        payload = text.encode("utf-8")
        self._validate_checksum(payload, checksum_hex)
        if self._object_exists(bucket, key):
            raise VersionOverwriteError("S-STORAGE-VERSION-EXISTS")
        self.client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain; charset=utf-8")
        return f"s3://{bucket}/{key}"

    def put_bytes(self, bucket: str, key: str, payload: bytes, content_type: str = "application/octet-stream") -> str:
        self._guard_versioned_raw_overwrite(bucket, key)
        self.client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType=content_type)
        return f"s3://{bucket}/{key}"

    def put_bytes_immutable(self, bucket: str, key: str, payload: bytes, checksum_hex: str, content_type: str = "application/octet-stream") -> str:
        self._validate_checksum(payload, checksum_hex)
        if self._object_exists(bucket, key):
            raise VersionOverwriteError("S-STORAGE-VERSION-EXISTS")
        self.client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType=content_type)
        return f"s3://{bucket}/{key}"
