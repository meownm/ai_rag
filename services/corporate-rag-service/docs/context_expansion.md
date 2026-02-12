# Context Expansion

## Modes

- `off`: expansion disabled.
- `neighbor`: expands around each base anchor using ±`CONTEXT_EXPANSION_NEIGHBOR_WINDOW` (without doc grouping/link traversal).
- `doc_neighbor`: expands around strongest chunks in top documents using ±`CONTEXT_EXPANSION_NEIGHBOR_WINDOW`.
- `doc_neighbor_plus_links`: runs `doc_neighbor` and then adds bounded chunks from linked documents.

## Environment parameters

- `CONTEXT_EXPANSION_ENABLED` (default `false`)
- `CONTEXT_EXPANSION_MODE` (default `doc_neighbor`)
- `CONTEXT_EXPANSION_NEIGHBOR_WINDOW` (default `1`)
- `CONTEXT_EXPANSION_MAX_DOCS` (default `4`)
- `CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS` (default `12`)
- `CONTEXT_EXPANSION_MAX_LINK_DOCS` (default `1`)
- `CONTEXT_EXPANSION_REDUNDANCY_SIM_THRESHOLD` (default `0.92`)
- `CONTEXT_EXPANSION_MIN_GAIN` (default `0.01`)
- `CONTEXT_EXPANSION_TOPK_BASE` (default `8`)
- `CONTEXT_EXPANSION_TOPK_HARD_CAP` (default `20`)

## Rollout steps

1. Keep `CONTEXT_EXPANSION_ENABLED=false` and verify no change in selected chunk sets.
2. Enable `doc_neighbor` for a pilot tenant; monitor `context_expansion_*` metrics.
3. Tune redundancy threshold and min gain for precision.
4. Enable `doc_neighbor_plus_links` only after validating linked-doc precision.

## Guardrails and failure modes

- Strict token budget is enforced before prompt assembly.
- Expansion caps are hard-bounded by `MAX_EXTRA_CHUNKS` and `MAX_LINK_DOCS`.
- Near duplicates are dropped by cosine similarity threshold.
- If links are absent or low-gain, selection stops without adding noisy chunks.
- `retrieval_context_selection` log includes selection/budget timing and internal selection counters.
