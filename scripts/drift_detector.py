from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

rag_yaml = (ROOT / "openapi/rag.yaml").read_text(encoding="utf-8")
emb_yaml = (ROOT / "openapi/embeddings.yaml").read_text(encoding="utf-8")
model_py = (ROOT / "services/corporate-rag-service/app/models/models.py").read_text(encoding="utf-8")
routes_py = (ROOT / "services/corporate-rag-service/app/api/routes.py").read_text(encoding="utf-8")
emb_routes_py = (ROOT / "services/embeddings-service/app/api/routes.py").read_text(encoding="utf-8")

endpoints_frozen = set(re.findall(r"\n\s{2}(/v1/[^:]+):", rag_yaml)) | set(re.findall(r"\n\s{2}(/v1/[^:]+):", emb_yaml))
endpoints_code = set(re.findall(r'@router\.(?:get|post)\("([^"]+)"', routes_py)) | set(re.findall(r'@router\.(?:get|post)\("([^"]+)"', emb_routes_py))

tables_frozen = {
    "tenants", "tenant_settings", "local_groups", "tenant_group_bindings", "users", "user_group_memberships",
    "sources", "source_versions", "documents", "document_links", "chunks", "chunk_fts", "chunk_vectors",
    "ingest_jobs", "search_requests", "search_candidates", "answers", "pipeline_trace", "event_logs",
}
tables_code = set(re.findall(r'__tablename__ = "([^"]+)"', model_py))

report = []
if endpoints_frozen - endpoints_code:
    report.append(f"Missing endpoints in code: {sorted(endpoints_frozen - endpoints_code)}")
if tables_frozen - tables_code:
    report.append(f"Missing tables in code: {sorted(tables_frozen - tables_code)}")

if report:
    print("DRIFT REPORT")
    print("\n".join(report))
    raise SystemExit(1)

print("DRIFT CHECK PASSED")
