# Hybrid score normalization notes (EPIC-07 SP4)

## Feature flag
- `HYBRID_SCORE_NORMALIZATION=false` (default): preserve current scoring behavior.
- `HYBRID_SCORE_NORMALIZATION=true`: normalize score components before weighted fusion.

## Normalization behavior
- Lexical scores use min-max normalization over current candidate set.
- Vector scores use min-max normalization over current candidate set.
- Rerank scores use min-max normalization over current candidate set.
- Safe edge case: when all values in a component are equal, normalized values are set to `1.0`.

## Scoring trace additions
When enabled, scoring trace records both raw and normalized components:
- `lex_raw`, `lex_norm`
- `vec_raw`, `vec_norm`
- `rerank_raw`, `rerank_norm`

The existing fields (`lex_score`, `vec_score`, `rerank_score`, `final_score`) remain present.
