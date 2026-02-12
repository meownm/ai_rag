from app.services.storage import ObjectStorage, StorageConfig


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self):
        return self.payload


class FakeS3Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(self.objects[(Bucket, Key)])}

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise KeyError("NotFound")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}


def test_s3_put_get_text_roundtrip(monkeypatch):
    fake_client = FakeS3Client()

    class FakeBoto3:
        @staticmethod
        def client(*_args, **_kwargs):
            return fake_client

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            return FakeBoto3
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    storage = ObjectStorage(StorageConfig(endpoint="http://localhost:9000", access_key="x", secret_key="y", region="us-east-1", secure=False))
    uri = storage.put_text("raw-bucket", "tenant/a.txt", "hello")
    content = storage.get_text("raw-bucket", "tenant/a.txt")

    assert uri == "s3://raw-bucket/tenant/a.txt"
    assert content == "hello"


def test_s3_immutable_put_rejects_overwrite(monkeypatch):
    fake_client = FakeS3Client()

    class FakeBoto3:
        @staticmethod
        def client(*_args, **_kwargs):
            return fake_client

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            return FakeBoto3
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    storage = ObjectStorage(StorageConfig(endpoint="http://localhost:9000", access_key="x", secret_key="y", region="us-east-1", secure=False))
    payload = b"immutable"
    import hashlib

    checksum = hashlib.sha256(payload).hexdigest()
    storage.put_bytes_immutable("raw-bucket", "tenant/src/ver/raw.bin", payload, checksum_hex=checksum)

    import pytest

    with pytest.raises(FileExistsError):
        storage.put_bytes_immutable("raw-bucket", "tenant/src/ver/raw.bin", payload, checksum_hex=checksum)


def test_s3_immutable_put_rejects_checksum_mismatch(monkeypatch):
    fake_client = FakeS3Client()

    class FakeBoto3:
        @staticmethod
        def client(*_args, **_kwargs):
            return fake_client

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            return FakeBoto3
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    storage = ObjectStorage(StorageConfig(endpoint="http://localhost:9000", access_key="x", secret_key="y", region="us-east-1", secure=False))

    import pytest

    with pytest.raises(ValueError):
        storage.put_bytes_immutable("raw-bucket", "tenant/src/ver/raw.bin", b"immutable", checksum_hex="deadbeef")
