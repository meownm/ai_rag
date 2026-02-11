import httpx


class EmbeddingsClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def embed(self, model: str, texts: list[str], tenant_id: str, correlation_id: str) -> list[list[float]]:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f"{self.base_url}/v1/embeddings",
                json={"model": model, "input": texts, "encoding_format": "float", "tenant_id": tenant_id, "correlation_id": correlation_id},
            )
            response.raise_for_status()
            data = response.json()["data"]
            return [x["embedding"] for x in data]
