class OllamaClient:
    def __init__(self, endpoint: str | None = None, model: str | None = None, timeout_seconds: int | None = None):
        if endpoint is None or model is None or timeout_seconds is None:
            from app.core.config import settings

            endpoint = endpoint or settings.LLM_ENDPOINT
            model = model or settings.LLM_MODEL
            timeout_seconds = timeout_seconds or settings.REQUEST_TIMEOUT_SECONDS
        self.endpoint = str(endpoint)
        self.model = str(model)
        self.timeout_seconds = float(timeout_seconds)

    def generate(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "top_p": 1},
        }
        import httpx

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.endpoint, json=payload)
            response.raise_for_status()
            return response.json()
