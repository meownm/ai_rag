#!/usr/bin/env sh
set -eu

# Expected env vars are provided via docker-compose service 'db-migrator'.
# We defensively default optional vars to empty strings to keep psql variable substitution valid.
: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=postgres}"
: "${POSTGRES_SUPERUSER:=postgres}"
: "${POSTGRES_SUPERPASS:=postgres}"

# Optional: roles and schemas
: "${POSTGRES_APP_USER:=}"
: "${POSTGRES_APP_PASS:=}"
: "${POSTGRES_READONLY_USER:=}"
: "${POSTGRES_READONLY_PASS:=}"
: "${POSTGRES_SCHEMA_APP:=app}"
: "${POSTGRES_SCHEMA_LOGS:=logs}"

export PGPASSWORD="${POSTGRES_SUPERPASS}"

PSQL_BASE="psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_SUPERUSER} -d ${POSTGRES_DB} -v ON_ERROR_STOP=1"
# Ensure psql variables always exist (even if empty) so SQL containing :'<var>' won't break.
PSQL_VARS=" -v app_user=${POSTGRES_APP_USER} -v app_pass=${POSTGRES_APP_PASS} -v readonly_user=${POSTGRES_READONLY_USER} -v readonly_pass=${POSTGRES_READONLY_PASS} -v schema_app=${POSTGRES_SCHEMA_APP} -v schema_logs=${POSTGRES_SCHEMA_LOGS}"

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/migrations}"

if [ ! -d "${MIGRATIONS_DIR}" ]; then
  echo "[ERROR] Migrations dir not found: ${MIGRATIONS_DIR}" >&2
  exit 1
fi

echo "[INFO] Running migrations from ${MIGRATIONS_DIR} ..."

# Run in lexical order
for f in $(ls -1 "${MIGRATIONS_DIR}"/*.sql 2>/dev/null | sort); do
  echo "[INFO] Applying $(basename "$f")"
  # shellcheck disable=SC2086
  sh -c "${PSQL_BASE} ${PSQL_VARS} -f \"$f\""
done

echo "[INFO] Migrations applied successfully."
