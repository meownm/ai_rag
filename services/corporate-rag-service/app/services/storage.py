from dataclasses import dataclass


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

    def put_text(self, bucket: str, key: str, text: str) -> str:
        self.client.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType="text/plain; charset=utf-8")
        return f"s3://{bucket}/{key}"

    def get_text(self, bucket: str, key: str) -> str:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
