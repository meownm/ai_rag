import logging
import re

from app.services.retrieval import lexical_score, vector_score

LOGGER = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def verify_answer(answer: str, chunks: list[str], min_similarity: float, min_lexical_overlap: float) -> tuple[bool, dict]:
    sentences = split_sentences(answer)
    unsupported = 0
    chunk_tokens = [set(chunk.lower().split()) for chunk in chunks]
    for sentence in sentences:
        s_tokens = set(sentence.lower().split())
        lex_ok = any((len(s_tokens & c_tokens) / max(1, len(s_tokens))) >= min_lexical_overlap for c_tokens in chunk_tokens)
        sem_ok = any(vector_score([1.0 if w in c_tokens else 0.0 for w in s_tokens], [1.0 for _ in s_tokens]) >= min_similarity for c_tokens in chunk_tokens)
        if not (lex_ok or sem_ok):
            unsupported += 1
    refusal = unsupported > 0
    payload = {
        "total_sentences": len(sentences),
        "unsupported_sentences": unsupported,
        "refusal_triggered": refusal,
    }
    LOGGER.info("anti_hallucination_check", extra=payload)
    return not refusal, payload
