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

    def generate(self, prompt: str, *, keep_alive: int = 0) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"temperature": 0, "top_p": 1},
        }
        import httpx

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.endpoint, json=payload)
            response.raise_for_status()
            return response.json()

    def show_model(self, model_id: str | None = None) -> dict:
        import httpx

        target_model = model_id or self.model
        base_url = self.endpoint.rsplit("/api/generate", 1)[0]
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{base_url}/api/show", json={"model": target_model})
            response.raise_for_status()
            return response.json()

    def fetch_model_num_ctx(self, model_id: str | None = None) -> int | None:
        payload = self.show_model(model_id=model_id)
        details = payload.get("details") if isinstance(payload, dict) else None
        if isinstance(details, dict):
            for key in ("num_ctx", "context_length"):
                value = details.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)

        model_info = payload.get("model_info") if isinstance(payload, dict) else None
        if isinstance(model_info, dict):
            for key in ("llama.context_length", "context_length", "num_ctx"):
                value = model_info.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
        return None
