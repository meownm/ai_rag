#!/usr/bin/env sh
set -eu

escape_sql() {
  # Escape single quotes for SQL literals.
  printf "%s" "$1" | sed "s/'/''/g"
}

until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; do
  sleep 1
done

APP_USER="$(escape_sql "${POSTGRES_APP_USER:-}")"
APP_PASS="$(escape_sql "${POSTGRES_APP_PASS:-}")"
RO_USER="$(escape_sql "${POSTGRES_READONLY_USER:-}")"
RO_PASS="$(escape_sql "${POSTGRES_READONLY_PASS:-}")"
SCHEMA_APP="$(escape_sql "${POSTGRES_SCHEMA_APP:-app}")"
SCHEMA_LOGS="$(escape_sql "${POSTGRES_SCHEMA_LOGS:-logs}")"

# 1) Ensure migrations registry exists.
psql -v ON_ERROR_STOP=1 -f /migrations/000_schema_migrations.sql

# 2) Create/rotate roles and grant CONNECT (idempotent).
# Passwords live in .env (closed test contour). Avoid quotes/newlines in passwords.
psql -v ON_ERROR_STOP=1   -v app_user="$APP_USER" -v app_pass="$APP_PASS"   -v ro_user="$RO_USER"  -v ro_pass="$RO_PASS"   -v schema_app="$SCHEMA_APP" -v schema_logs="$SCHEMA_LOGS"   <<'SQL'
DO $body$
BEGIN
  IF :'app_user' <> '' THEN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') THEN
      EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_pass');
    ELSE
      EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_user', :'app_pass');
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user');
  END IF;

  IF :'ro_user' <> '' THEN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'ro_user') THEN
      EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', :'ro_user', :'ro_pass');
    ELSE
      EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'ro_user', :'ro_pass');
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'ro_user');
  END IF;
END
$body$ LANGUAGE plpgsql;
SQL

# 3) Apply versioned migrations (idempotent by schema_migrations table).
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

# 4) Grants on schemas/tables (idempotent).
psql -v ON_ERROR_STOP=1   -v app_user="$APP_USER" -v ro_user="$RO_USER"   -v schema_app="$SCHEMA_APP" -v schema_logs="$SCHEMA_LOGS"   <<'SQL'
DO $body$
BEGIN
  IF :'app_user' <> '' THEN
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', :'schema_app', :'app_user');
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', :'schema_logs', :'app_user');

    EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA %I TO %I', :'schema_app', :'app_user');
    EXECUTE format('GRANT USAGE,SELECT,UPDATE ON ALL SEQUENCES IN SCHEMA %I TO %I', :'schema_app', :'app_user');

    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO %I', :'schema_app', :'app_user');
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE,SELECT,UPDATE ON SEQUENCES TO %I', :'schema_app', :'app_user');
  END IF;

  IF :'ro_user' <> '' THEN
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', :'schema_app', :'ro_user');
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', :'schema_logs', :'ro_user');

    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', :'schema_app', :'ro_user');
    EXECUTE format('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', :'schema_app', :'ro_user');

    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT ON TABLES TO %I', :'schema_app', :'ro_user');
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE,SELECT ON SEQUENCES TO %I', :'schema_app', :'ro_user');
  END IF;
END
$body$ LANGUAGE plpgsql;
SQL

echo "[INFO] DB migrations and grants done."
