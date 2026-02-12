from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.db.repositories import TenantRepository
from app.services.query_pipeline import estimate_tokens


@dataclass(frozen=True)
class ExpansionDebugInfo:
    base_topk_count: int
    base_candidates_doc_diversity: int
    expanded_chunks_count: int
    expanded_from_neighbors_count: int
    expanded_from_links_count: int
    redundancy_filtered_count: int
    final_context_token_estimate: int
    context_selection_steps: list[str]


class ContextExpansionEngine:
    def __init__(self, repo: TenantRepository):
        self.repo = repo

    @staticmethod
    def _cosine(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = sum(a * a for a in v1) ** 0.5
        n2 = sum(b * b for b in v2) ** 0.5
        if n1 == 0.0 or n2 == 0.0:
            return 0.0
        return dot / (n1 * n2)

    def expand(
        self,
        *,
        final_query: str,
        base_candidates: list[dict],
        token_budget: int,
        mode: str,
        query_embedding: list[float],
    ) -> tuple[list[dict], ExpansionDebugInfo]:
        _ = final_query
        topk_base = min(settings.CONTEXT_EXPANSION_TOPK_HARD_CAP, max(1, settings.CONTEXT_EXPANSION_TOPK_BASE))
        base = list(base_candidates[:topk_base])
        doc_ids = {str(c.get("document_id")) for c in base if c.get("document_id") is not None}
        steps = [f"base:{len(base)}", f"doc_diversity:{len(doc_ids)}", f"mode:{mode}"]

        if mode == "off":
            selected, debug = self._budget_select(base, token_budget, steps=steps)
            return selected, debug

        if mode == "neighbor":
            expanded_neighbor = list(base)
            extra_added = 0
            for anchor in base:
                neighbors = self.repo.fetch_document_neighbors(
                    str(anchor.get("document_id")),
                    str(anchor.get("chunk_id")),
                    window=max(0, settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW),
                )
                for n in neighbors:
                    if extra_added >= settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS:
                        break
                    if self._contains_chunk(expanded_neighbor, str(n.get("chunk_id"))):
                        continue
                    n["final_score"] = float(anchor.get("final_score", 0.0)) * 0.92
                    n["added_by_neighbor"] = True
                    expanded_neighbor.append(n)
                    extra_added += 1
            deduped = self._dedup(expanded_neighbor)
            filtered, redundancy_filtered = self._redundancy_filter(deduped)
            steps.extend([
                f"expanded:{len(expanded_neighbor)}",
                f"deduped:{len(deduped)}",
                f"redundancy_filtered:{redundancy_filtered}",
            ])
            selected, debug = self._budget_select(filtered, token_budget, steps=steps)
            return selected, ExpansionDebugInfo(
                base_topk_count=len(base),
                base_candidates_doc_diversity=len(doc_ids),
                expanded_chunks_count=len(selected),
                expanded_from_neighbors_count=extra_added,
                expanded_from_links_count=0,
                redundancy_filtered_count=redundancy_filtered,
                final_context_token_estimate=debug.final_context_token_estimate,
                context_selection_steps=debug.context_selection_steps,
            )

        expanded: list[dict] = list(base)
        extra_added = 0
        neighbors_added = 0
        links_added = 0

        docs_ranked = sorted(
            self._group_docs(base).items(),
            key=lambda item: (-item[1][0].get("final_score", 0.0), str(item[0])),
        )
        chosen_docs = docs_ranked[: max(1, settings.CONTEXT_EXPANSION_MAX_DOCS)]
        chosen_doc_ids = [str(doc_id) for doc_id, _ in chosen_docs]
        for doc_id, items in chosen_docs:
            anchors = sorted(items, key=lambda c: (-float(c.get("final_score", 0.0)), int(c.get("ordinal", 0)), str(c.get("chunk_id"))))[:1]
            for anchor in anchors:
                neighbors = self.repo.fetch_document_neighbors(
                    str(doc_id),
                    str(anchor["chunk_id"]),
                    window=max(0, settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW),
                )
                for n in neighbors:
                    if extra_added >= settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS:
                        break
                    if self._contains_chunk(expanded, str(n["chunk_id"])):
                        continue
                    n["final_score"] = float(anchor.get("final_score", 0.0)) * 0.92
                    n["added_by_neighbor"] = True
                    expanded.append(n)
                    extra_added += 1
                    neighbors_added += 1

        if mode == "doc_neighbor_plus_links" and extra_added < settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS:
            should_expand_links = self._should_expand_links(base, chosen_docs)
            steps.append(f"links_enabled:{int(should_expand_links)}")
            linked_docs = self.repo.fetch_outgoing_linked_documents(chosen_doc_ids, settings.CONTEXT_EXPANSION_MAX_LINK_DOCS) if should_expand_links else []
            for linked_doc in linked_docs:
                if extra_added >= settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS:
                    break
                linked_chunks = self.repo.fetch_top_chunks_for_document(linked_doc, query_embedding, limit_n=2)
                for chunk in linked_chunks:
                    if extra_added >= settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS:
                        break
                    if self._contains_chunk(expanded, str(chunk["chunk_id"])):
                        continue
                    chunk["added_by_link"] = True
                    expanded.append(chunk)
                    extra_added += 1
                    links_added += 1

        deduped = self._dedup(expanded)
        filtered, redundancy_filtered = self._redundancy_filter(deduped)
        steps.append(f"expanded:{len(expanded)}")
        steps.append(f"deduped:{len(deduped)}")
        steps.append(f"redundancy_filtered:{redundancy_filtered}")

        selected, debug = self._budget_select(filtered, token_budget, steps=steps, doc_rank=chosen_doc_ids)
        info = ExpansionDebugInfo(
            base_topk_count=len(base),
            base_candidates_doc_diversity=len(doc_ids),
            expanded_chunks_count=len(selected),
            expanded_from_neighbors_count=neighbors_added,
            expanded_from_links_count=links_added,
            redundancy_filtered_count=redundancy_filtered,
            final_context_token_estimate=debug.final_context_token_estimate,
            context_selection_steps=debug.context_selection_steps,
        )
        return selected, info

    @staticmethod
    def _group_docs(candidates: list[dict]) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for c in candidates:
            key = str(c.get("document_id"))
            grouped.setdefault(key, []).append(c)
        return grouped

    @staticmethod
    def _contains_chunk(items: list[dict], chunk_id: str) -> bool:
        return any(str(x.get("chunk_id")) == chunk_id for x in items)

    @staticmethod
    def _dedup(candidates: list[dict]) -> list[dict]:
        out: list[dict] = []
        seen: set[str] = set()
        for c in sorted(candidates, key=lambda x: (-float(x.get("final_score", 0.0)), str(x.get("chunk_id")))):
            cid = str(c.get("chunk_id"))
            if cid in seen:
                continue
            seen.add(cid)
            out.append(c)
        return out

    def _redundancy_filter(self, candidates: list[dict]) -> tuple[list[dict], int]:
        kept: list[dict] = []
        filtered = 0
        threshold = float(settings.CONTEXT_EXPANSION_REDUNDANCY_SIM_THRESHOLD)
        for c in candidates:
            embedding = list(c.get("embedding", []))
            path = "/".join(c.get("heading_path", []))
            redundant = False
            for k in kept:
                k_emb = list(k.get("embedding", []))
                if self._cosine(embedding, k_emb) >= threshold and "/".join(k.get("heading_path", [])) == path:
                    redundant = True
                    break
            if redundant:
                filtered += 1
                continue
            kept.append(c)
        return kept, filtered

    def _budget_select(
        self,
        candidates: list[dict],
        token_budget: int,
        *,
        steps: list[str],
        doc_rank: list[str] | None = None,
    ) -> tuple[list[dict], ExpansionDebugInfo]:
        selected: list[dict] = []
        used_tokens = 0
        min_gain = float(settings.CONTEXT_EXPANSION_MIN_GAIN)
        for candidate in sorted(
            candidates,
            key=lambda x: (
                -float(x.get("final_score", 0.0)),
                str(x.get("document_id")),
                int(x.get("ordinal", 0)),
                str(x.get("chunk_id")),
            ),
        ):
            chunk_tokens = int(candidate.get("token_count") or estimate_tokens(str(candidate.get("chunk_text", ""))))
            redundancy_penalty = self._redundancy_penalty(candidate, selected)
            gain = float(candidate.get("final_score", 0.0)) - redundancy_penalty
            if gain < min_gain:
                steps.append(f"stop:min_gain:{gain:.4f}")
                break
            if used_tokens + chunk_tokens > token_budget:
                steps.append(f"stop:budget:{used_tokens}+{chunk_tokens}>{token_budget}")
                break
            selected.append(candidate)
            used_tokens += chunk_tokens

        doc_rank_index = {doc_id: idx for idx, doc_id in enumerate(doc_rank or [])}
        ordered = sorted(
            selected,
            key=lambda x: (
                doc_rank_index.get(str(x.get("document_id")), len(doc_rank_index) + 1),
                str(x.get("document_id")),
                int(x.get("ordinal", 0)),
                str(x.get("chunk_id")),
            ),
        )
        debug = ExpansionDebugInfo(
            base_topk_count=0,
            base_candidates_doc_diversity=0,
            expanded_chunks_count=len(ordered),
            expanded_from_neighbors_count=0,
            expanded_from_links_count=0,
            redundancy_filtered_count=0,
            final_context_token_estimate=used_tokens,
            context_selection_steps=steps,
        )
        return ordered, debug

    def _redundancy_penalty(self, candidate: dict[str, Any], selected: list[dict]) -> float:
        if not selected:
            return 0.0
        emb = list(candidate.get("embedding", []))
        sim = max((self._cosine(emb, list(s.get("embedding", []))) for s in selected), default=0.0)
        return max(0.0, sim - float(settings.CONTEXT_EXPANSION_REDUNDANCY_SIM_THRESHOLD))

    @staticmethod
    def _should_expand_links(base_candidates: list[dict], chosen_docs: list[tuple[str, list[dict]]]) -> bool:
        if not chosen_docs:
            return False
        diversity = len({str(c.get("document_id")) for c in base_candidates if c.get("document_id") is not None})
        depth = sum(len(chunks) for _, chunks in chosen_docs) / len(chosen_docs)
        return depth < 1.5 or diversity > len(chosen_docs)
