#!/usr/bin/env sh
set -eu

APP_ENV="${APP_ENV:-production}"
case "$APP_ENV" in
  production|staging|development)
    ;;
  *)
    echo "[entrypoint] Invalid APP_ENV='$APP_ENV'. Allowed: production|staging|development" >&2
    exit 1
    ;;
esac

require_var() {
  var_name="$1"
  var_value="$(eval "printf '%s' \"\${$var_name-}\"")"
  if [ -z "$var_value" ]; then
    echo "[entrypoint] Missing required env var: $var_name" >&2
    exit 1
  fi
}

require_var DATABASE_URL
require_var EMBEDDINGS_SERVICE_URL

exec "$@"
