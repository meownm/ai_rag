#!/usr/bin/env sh
set -eu
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; do
  sleep 1
done
psql -v ON_ERROR_STOP=1 -f /migrations/000_schema_migrations.sql
for f in $(ls -1 /migrations/*.sql | sort); do
  ver="$(basename "$f")"
  if [ "$ver" = "000_schema_migrations.sql" ]; then
    continue
  fi
  applied="$(psql -v ON_ERROR_STOP=1 -tAc "SELECT 1 FROM public.schema_migrations WHERE version='${ver}'" | tr -d '[:space:]' || true)"
  if [ "$applied" = "1" ]; then
    echo "[SKIP] $ver"
    continue
  fi
  echo "[APPLY] $ver"
  psql -v ON_ERROR_STOP=1 -f "$f"
  psql -v ON_ERROR_STOP=1 -c "INSERT INTO public.schema_migrations(version) VALUES ('${ver}')"
done
