import logging
import time

LOGGER = logging.getLogger(__name__)


class RerankerService:
    def __init__(self, model_id: str, model=None):
        self.model_id = model_id
        if model is not None:
            self.model = model
        else:
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(model_id)

    def rerank(self, query: str, candidates: list[dict]) -> tuple[list[dict], int]:
        if len(candidates) < 2:
            return candidates, 0
        start = time.perf_counter()
        pairs = [[query, c["chunk_text"]] for c in candidates]
        scores = self.model.predict(pairs)
        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)
        sorted_candidates = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        duration_ms = int((time.perf_counter() - start) * 1000)
        LOGGER.info(
            "reranker_applied",
            extra={"model_id": self.model_id, "candidate_count": len(candidates), "duration_ms": duration_ms},
        )
        return sorted_candidates, duration_ms
