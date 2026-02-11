import boto3


class ObjectStorage:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def put_text(self, key: str, text: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=text.encode("utf-8"))
        return f"s3://{self.bucket}/{key}"
