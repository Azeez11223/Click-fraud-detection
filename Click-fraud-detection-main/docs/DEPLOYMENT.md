# Deployment status

The free-tier deployment target is Neon Postgres, Render Docker API, and Streamlit Community Cloud. Configure Render with a pooled Neon `DATABASE_URL`; the container applies Alembic migrations before starting FastAPI. Validate a staging deploy and `/readyz` before production traffic.

## Configuration

Set secrets in the hosting provider, never in Git. `JWT_SECRET` must be at least 32 characters. Set `DATABASE_URL`, `CORS_ORIGINS`, `ENV=production`, `ADMIN_EMAILS`, `MODEL_URL`, `MODEL_SHA256`, fraud thresholds, cost weights, retention, rate limits, `SENTRY_DSN`, and Streamlit `API_BASE` as needed. In Streamlit Community Cloud, select `requirements-ui.txt` in advanced settings and set `API_BASE` in app secrets.

Use UptimeRobot to request `/healthz` every five minutes. Render supports rollback to the previous deploy; restore the previous pinned `MODEL_URL` and `MODEL_SHA256` together when rolling back model artifacts.
