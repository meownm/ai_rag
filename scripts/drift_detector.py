from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "docs/architecture/architecture-freeze.md"
RAG_OPENAPI = ROOT / "openapi/rag.yaml"
EMB_OPENAPI = ROOT / "openapi/embeddings.yaml"
RAG_ROUTES = ROOT / "services/corporate-rag-service/app/api/routes.py"
EMB_ROUTES = ROOT / "services/embeddings-service/app/api/routes.py"
MODELS = ROOT / "services/corporate-rag-service/app/models/models.py"
RAG_CONFIG = ROOT / "services/corporate-rag-service/app/core/config.py"
EMB_CONFIG = ROOT / "services/embeddings-service/app/core/config.py"
ALEMBIC_DIR = ROOT / "services/corporate-rag-service/alembic/versions"


@dataclass
class DriftSection:
    name: str
    missing_in_code: list[str]
    extra_in_code: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_in_code and not self.extra_in_code


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_freeze_list(text: str, marker: str) -> list[str]:
    pattern = rf"{re.escape(marker)}:\n(.*?)(?:\n\n[A-Z_]+:|\nARCHITECTURE FROZEN|$)"
    m = re.search(pattern, text, re.S)
    if not m:
        return []
    out: list[str] = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if s.startswith("- "):
            out.append(s[2:].strip())
    return out


def _extract_freeze_enums(text: str) -> dict[str, list[str]]:
    marker = "LIST_ENUMS:"
    block_pattern = rf"{re.escape(marker)}\n(.*?)(?:\n\nLIST_TABLES:|\nARCHITECTURE FROZEN|$)"
    m = re.search(block_pattern, text, re.S)
    if not m:
        return {}
    enums: dict[str, list[str]] = {}
    current: str | None = None
    for line in m.group(1).splitlines():
        s = line.strip()
        if s.startswith("- ") and s.endswith(":"):
            current = s[2:-1]
            enums[current] = []
            continue
        if current and s.startswith("- "):
            enums[current].append(s[2:].strip())
    return enums


def _extract_openapi_endpoints(path: Path) -> set[str]:
    text = _read(path)
    return set(re.findall(r"\n\s{2}(/v1/[^:]+):", text))


def _extract_route_endpoints(path: Path) -> set[str]:
    text = _read(path)
    return set(re.findall(r'@router\.(?:get|post|put|delete|patch)\("([^"]+)"', text))


def _extract_model_enums(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(_read(path))
    enums: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name.isupper() and isinstance(node.value, (ast.Tuple, ast.List)):
                values: list[str] = []
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        values.append(elt.value)
                if values:
                    enums[name.lower()] = values
    return enums


def _extract_settings_env_vars(path: Path) -> set[str]:
    tree = ast.parse(_read(path))
    fields: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if re.match(r"^[A-Z][A-Z0-9_]+$", name):
                        fields.add(name)
    return fields


def _extract_job_status_from_models(path: Path) -> list[str]:
    enums = _extract_model_enums(path)
    return enums.get("job_status", [])


def _extract_job_status_from_migrations(path: Path) -> set[str]:
    statuses: set[str] = set()
    for mig in path.glob("*.py"):
        text = _read(mig)
        for m in re.finditer(r'job_status\s*=\s*sa\.Enum\((.*?)name="job_status"', text, re.S):
            values = re.findall(r'"([^"]+)"', m.group(1))
            statuses.update(values)
    return statuses


def _compare(name: str, frozen: set[str], code: set[str]) -> DriftSection:
    return DriftSection(name=name, missing_in_code=sorted(frozen - code), extra_in_code=sorted(code - frozen))


def build_report() -> dict[str, Any]:
    freeze_text = _read(FREEZE_PATH)

    # Endpoints
    frozen_endpoints = _extract_openapi_endpoints(RAG_OPENAPI) | _extract_openapi_endpoints(EMB_OPENAPI)
    code_endpoints = _extract_route_endpoints(RAG_ROUTES) | _extract_route_endpoints(EMB_ROUTES)

    # Enums
    freeze_enums = _extract_freeze_enums(freeze_text)
    model_enums = _extract_model_enums(MODELS)
    enum_sections: list[dict[str, Any]] = []
    for enum_name, frozen_values in freeze_enums.items():
        code_values = set(model_enums.get(enum_name, []))
        section = _compare(f"enum:{enum_name}", set(frozen_values), code_values)
        enum_sections.append({"name": section.name, "missing_in_code": section.missing_in_code, "extra_in_code": section.extra_in_code, "ok": section.ok})

    # Env vars
    frozen_env = set(_extract_freeze_list(freeze_text, "LIST_ENV_VARS"))
    code_env = _extract_settings_env_vars(RAG_CONFIG) | _extract_settings_env_vars(EMB_CONFIG)

    # Job status
    frozen_job_status = set(_extract_freeze_list(freeze_text, "LIST_JOB_STATUS"))
    model_job_status = set(_extract_job_status_from_models(MODELS))
    migration_job_status = _extract_job_status_from_migrations(ALEMBIC_DIR)

    endpoint_section = _compare("endpoints", frozen_endpoints, code_endpoints)
    env_section = _compare("env_vars", frozen_env, code_env)
    job_model_section = _compare("job_status:model", frozen_job_status, model_job_status)
    job_migration_section = _compare("job_status:migrations", frozen_job_status, migration_job_status)

    overall_ok = endpoint_section.ok and env_section.ok and job_model_section.ok and job_migration_section.ok and all(s["ok"] for s in enum_sections)

    return {
        "overall_ok": overall_ok,
        "sections": [
            {"name": endpoint_section.name, "missing_in_code": endpoint_section.missing_in_code, "extra_in_code": endpoint_section.extra_in_code, "ok": endpoint_section.ok},
            {"name": env_section.name, "missing_in_code": env_section.missing_in_code, "extra_in_code": env_section.extra_in_code, "ok": env_section.ok},
            {"name": job_model_section.name, "missing_in_code": job_model_section.missing_in_code, "extra_in_code": job_model_section.extra_in_code, "ok": job_model_section.ok},
            {"name": job_migration_section.name, "missing_in_code": job_migration_section.missing_in_code, "extra_in_code": job_migration_section.extra_in_code, "ok": job_migration_section.ok},
            *enum_sections,
        ],
    }


def main() -> int:
    report = build_report()
    print("DRIFT REPORT")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
