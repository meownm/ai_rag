import json
import logging
import re
from functools import lru_cache
from typing import Any

from app.core.math_utils import cosine_similarity
from app.services.retrieval import lexical_score

LOGGER = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


@lru_cache
def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _semantic_similarity(sentence: str, chunk: str) -> float:
    try:
        model = _load_sentence_transformer("sentence-transformers/all-MiniLM-L6-v2")
        from sentence_transformers import util

        emb_sentence = model.encode(sentence, convert_to_tensor=True)
        emb_chunk = model.encode(chunk, convert_to_tensor=True)
        return float(util.cos_sim(emb_sentence, emb_chunk).item())
    except Exception:  # noqa: BLE001
        # Fallback when model/runtime deps are unavailable.
        s_tokens = sentence.lower().split()
        c_tokens = chunk.lower().split()
        return cosine_similarity([1.0 if t in c_tokens else 0.0 for t in s_tokens], [1.0 for _ in s_tokens])


def verify_answer(answer: str, chunks: list[str], min_similarity: float, min_lexical_overlap: float) -> tuple[bool, dict[str, Any]]:
    sentences = split_sentences(answer)
    unsupported_sentences: list[str] = []
    chunk_tokens = [set(chunk.lower().split()) for chunk in chunks]

    for sentence in sentences:
        s_tokens = set(sentence.lower().split())
        lex_ok = any((len(s_tokens & c_tokens) / max(1, len(s_tokens))) >= min_lexical_overlap for c_tokens in chunk_tokens)
        sem_ok = any(_semantic_similarity(sentence, chunk) >= min_similarity for chunk in chunks)
        if not (lex_ok or sem_ok):
            unsupported_sentences.append(sentence)

    refusal = len(unsupported_sentences) > 0
    payload = {
        "total_sentences": len(sentences),
        "unsupported_sentences": len(unsupported_sentences),
        "unsupported_sentence_texts": unsupported_sentences,
        "refusal_triggered": refusal,
    }
    LOGGER.info("anti_hallucination_check", extra=payload)
    return not refusal, payload


def build_structured_refusal(correlation_id: str, details: dict[str, Any]) -> str:
    envelope = {
        "refusal": {
            "code": "ONLY_SOURCES_VIOLATION",
            "message": "Answer cannot be produced strictly from retrieved sources.",
            "correlation_id": correlation_id,
            "details": details,
        }
    }
    return json.dumps(envelope, ensure_ascii=False)
