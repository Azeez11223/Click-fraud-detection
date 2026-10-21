# API

Existing endpoints remain available for the Streamlit client. `/api/v1` aliases are also registered for gradual client migration. Login, signup, health checks, and campaign click ingestion are the intended unauthenticated surfaces; click ingestion requires a campaign API key. Other data endpoints require a bearer JWT.

Use `/healthz` for liveness and `/readyz` for a database/model readiness summary. Errors use `{error:{code,message,request_id}}`. Supply an optional `event_id` to prediction, campaign-click, and platform-event writes for deduplication. `/account` deletes the signed-in user's account and related rows. `/api/v1/admin/stats` is admin-only and reports process-local request and latency counts.

List endpoints accept `limit` (1–500) and `offset` (0 or greater); defaults are 100, except platform event lists default to 200. The admin-only `/api/v1/admin/audit-events` endpoint uses the same pagination and returns IP-list/dataset change records. Audit metadata deliberately omits raw IP values.
