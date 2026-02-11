class EmbeddingsClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: int | None = None):
        if base_url is None or timeout_seconds is None:
            from app.core.config import settings

            base_url = base_url or settings.EMBEDDINGS_SERVICE_URL
            timeout_seconds = timeout_seconds or settings.EMBEDDINGS_TIMEOUT_SECONDS
        self.base_url = str(base_url).rstrip("/")
        self.timeout_seconds = float(timeout_seconds)

    def embed_texts(
        self,
        texts: list[str],
        model_id: str = "bge-m3",
        tenant_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": model_id,
            "input": texts,
            "encoding_format": "float",
        }
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
        import httpx

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/v1/embeddings", json=payload)
            response.raise_for_status()
            body = response.json()
        data = body["data"]
        if not data:
            raise RuntimeError("Embeddings service returned empty data")
        return [item["embedding"] for item in data]

    def embed_text(
        self,
        text: str,
        tenant_id: str | None = None,
        correlation_id: str | None = None,
        model_id: str = "bge-m3",
    ) -> list[float]:
        embeddings = self.embed_texts(
            [text],
            model_id=model_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        if not embeddings:
            raise RuntimeError("Embeddings service returned empty data")
        return embeddings[0]
