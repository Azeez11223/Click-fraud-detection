# Architecture

```text
Streamlit Community Cloud -- HTTPS --> FastAPI --> SQLAlchemy adapter --> Neon Postgres
                                               \--> local SQLite for tests/dev
                                               \--> shared scoring services
Offline ml/train.py --> versioned XGBoost JSON --> MODEL_URL + SHA256 --> API cache (/tmp)
```

PostgreSQL schema changes are managed by Alembic. Local test runs can use temporary SQLite files.
