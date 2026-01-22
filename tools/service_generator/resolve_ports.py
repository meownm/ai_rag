from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTS_REGISTRY = ROOT / "docs" / "ports_registry.md"

API_MARKER = "### 54100–54199: API Services (host или docker)"
WORKER_MARKER = "### 54200–54299: Workers (host или docker)"

SERVICES_DIR = ROOT / "services"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _parse_section(md: str, marker: str) -> dict[str, int]:
    if marker not in md:
        return {}
    lines = md.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == marker:
            start = i
            break
    if start is None:
        return {}

    in_table = False
    out: dict[str, int] = {}
    for line in lines[start + 1 :]:
        s = line.strip()
        if s.startswith("### ") and s != marker:
            break
        if s.startswith("|") and "Сервис" in s and "Порт" in s:
            in_table = True
            continue
        if in_table and s.startswith("|---"):
            continue
        if in_table and s.startswith("|") and s.count("|") >= 3:
            cols = [c.strip() for c in s.strip("|").split("|")]
            if len(cols) >= 2 and re.fullmatch(r"\d{5}", cols[1]):
                out[cols[0]] = int(cols[1])
    return out


def _read_env_port(env_path: Path) -> int | None:
    if not env_path.exists():
        return None
    txt = _read(env_path)
    m = re.search(r"^APP_PORT=(\d{5})\s*$", txt, flags=re.MULTILINE)
    if not m:
        return None
    return int(m.group(1))


def main() -> int:
    md = _read(PORTS_REGISTRY)
    reg: dict[str, int] = {}
    reg.update(_parse_section(md, API_MARKER))
    reg.update(_parse_section(md, WORKER_MARKER))

    for name, reg_port in sorted(reg.items()):
        svc_dir = SERVICES_DIR / name
        env_port = _read_env_port(svc_dir / ".env")
        if env_port is None:
            port = reg_port
            source = "registry"
            warn = 0
        else:
            port = env_port
            source = "env"
            warn = 1 if env_port != reg_port else 0

        print(f"SERVICE={name} PORT={port} URL=http://localhost:{port}/docs SOURCE={source} WARN={warn}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
