# Runbook

- Cold start: `/healthz` checks process liveness. `/readyz` reports database reachability and model availability.
- Paused database: resume Neon and allow the first connection to wake it. If readiness stays degraded, check `DATABASE_URL` and database logs.
- Rollback: use Render's previous deploy rollback and restore the matching `MODEL_URL`/`MODEL_SHA256` pair.
- Key rotation: replace `JWT_SECRET` and require users to sign in again; rotate each campaign API key by adding a dedicated key rotation endpoint before production use.
- Retention: `ml/retention.py` purges event and prediction rows older than `RETENTION_DAYS`; confirm the scheduled workflow succeeds.
