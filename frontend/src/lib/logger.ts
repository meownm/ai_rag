export type UiEvent =
  | 'query_submitted'
  | 'query_success'
  | 'query_refusal'
  | 'query_error'
  | 'ingestion_started'
  | 'ingestion_status'
  | 'health_loaded';

export function logEvent(event: UiEvent, payload: Record<string, unknown>) {
  console.log(JSON.stringify({ event, ...payload, ts: new Date().toISOString() }));
}
