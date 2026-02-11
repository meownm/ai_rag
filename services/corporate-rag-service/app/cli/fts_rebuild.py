import argparse
from collections.abc import Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild chunk_fts rows from chunks")
    parser.add_argument("--tenant", type=str, help="Tenant UUID")
    parser.add_argument("--all", action="store_true", dest="all_tenants", help="Rebuild for all tenants")
    args = parser.parse_args(argv)
    if not args.all_tenants and not args.tenant:
        parser.error("either --tenant or --all must be provided")
    return args


def weighted_fts_expression() -> str:
    return """
    setweight(to_tsvector('simple', coalesce(d.title, '')), 'A')
    || setweight(to_tsvector('simple', coalesce(CAST(d.labels AS text), '')), 'B')
    || setweight(to_tsvector('simple', coalesce(c.chunk_path, '')), 'B')
    || setweight(to_tsvector('simple', coalesce(c.chunk_text, '')), 'C')
    """


def rebuild_fts(tenant_id: str | None = None, all_tenants: bool = False) -> int:
    from sqlalchemy import text

    from app.db.session import SessionLocal

    params: dict[str, str] = {}
    where_clause = ""
    if not all_tenants:
        where_clause = "WHERE c.tenant_id = CAST(:tenant_id AS uuid)"
        params["tenant_id"] = tenant_id or ""

    sql = text(
        f"""
        INSERT INTO chunk_fts (tenant_id, chunk_id, fts_doc, updated_at)
        SELECT c.tenant_id,
               c.chunk_id,
               ({weighted_fts_expression()}),
               now()
        FROM chunks c
        JOIN documents d ON d.document_id = c.document_id
        {where_clause}
        ON CONFLICT (tenant_id, chunk_id)
        DO UPDATE
          SET fts_doc = EXCLUDED.fts_doc,
              updated_at = now()
        """
    )

    with SessionLocal() as session:
        result = session.execute(sql, params)
        session.commit()
        return int(result.rowcount or 0)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    count = rebuild_fts(tenant_id=args.tenant, all_tenants=args.all_tenants)
    print(f"chunk_fts rebuild completed; affected_rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
