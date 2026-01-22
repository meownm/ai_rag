CREATE TABLE IF NOT EXISTS logs.api_requests (
  log_id bigserial PRIMARY KEY,
  request_id uuid NOT NULL,
  service_name text NOT NULL,
  plane text NOT NULL DEFAULT 'data',
  http_method text NOT NULL,
  http_path text NOT NULL,
  http_status int NOT NULL,
  client_ip text,
  user_agent text,
  request_ts_start timestamptz NOT NULL,
  request_ts_end timestamptz NOT NULL,
  duration_ms double precision NOT NULL,
  is_success boolean NOT NULL,
  error_text text,
  payload_in jsonb,
  payload_out jsonb
);
