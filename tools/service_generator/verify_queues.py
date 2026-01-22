from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs" / "queue_registry.md"


@dataclass(frozen=True)
class Row:
    queue: str
    retry: bool
    dlq: bool


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _parse_table(md: str) -> list[Row]:
    lines = md.splitlines()
    in_table = False
    out: list[Row] = []
    for line in lines:
        s = line.strip()
        if s.startswith("| Queue |"):
            in_table = True
            continue
        if in_table and s.startswith("|---"):
            continue
        if in_table and s.startswith("|") and s.count("|") >= 6:
            cols = [c.strip() for c in s.strip("|").split("|")]
            if len(cols) >= 6 and cols[0] and cols[0] != "Queue":
                q = cols[0]
                retry = cols[4].upper() == "Y"
                dlq = cols[5].upper() == "Y"
                out.append(Row(queue=q, retry=retry, dlq=dlq))
    return out


def _is_valid_queue_name(q: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9-]+", q))


def main() -> int:
    md = _read(REGISTRY)
    if not md.strip():
        print("ERROR docs/queue_registry.md missing or empty")
        return 1

    rows = _parse_table(md)
    if not rows:
        print("ERROR No rows found in queue_registry.md")
        return 1

    errors = 0
    for r in rows:
        if not _is_valid_queue_name(r.queue):
            print(f"ERROR invalid queue name: {r.queue}")
            errors += 1

        if r.queue.endswith(".retry") or r.queue.endswith(".dlq"):
            print(f"ERROR registry row must be main queue, not suffix queue: {r.queue}")
            errors += 1
            continue

        if not r.retry:
            print(f"ERROR retry flag must be Y for: {r.queue}")
            errors += 1
        if not r.dlq:
            print(f"ERROR dlq flag must be Y for: {r.queue}")
            errors += 1

    if errors:
        return 1

    print("Queues OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
