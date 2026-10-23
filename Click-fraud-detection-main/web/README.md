# AdShield web app

React, TypeScript, and Vite frontend. The API runs separately from this app.

## Local setup

1. Install Python and Node.js 22 or newer.
2. From the repository root, create a virtual environment and install API dependencies:

   ```bash
   python -m venv .venv
   # macOS/Linux
   . .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements-api.txt
   ```

3. Set a local JWT secret and allow the Vite origin in backend CORS, then start the API from the repository root:

   ```bash
   # macOS/Linux
   export JWT_SECRET='replace-with-a-random-secret-of-at-least-32-characters'
   export CORS_ORIGINS='http://localhost:5173'
   uvicorn backend.main:app --reload
   ```

   In PowerShell, use `$env:JWT_SECRET='...'` and `$env:CORS_ORIGINS='http://localhost:5173'` instead.

4. In a second terminal:

   ```bash
   cd web
   cp .env.example .env.local
   npm ci
   npm run dev
   ```

Open `http://localhost:5173`, create an account, and sign in. The API uses local SQLite by default. For a fresh database, its schema initializes at API startup.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `VITE_API_BASE` | Yes | `http://localhost:8000` | API origin. Set to the deployed API URL in Vercel Project Settings → Environment Variables for Preview and Production. |
| `VITE_DEMO_MODE` | No | `false` | Set `true` only in a demo environment to show bot and attack simulation controls. |
| `VITE_SENTRY_DSN` | No | empty | Frontend Sentry project DSN. Sentry stays disabled when empty. |

`VITE_*` values are embedded in the static bundle at build time. For production, copy [`.env.production.example`](./.env.production.example) as a reference and configure the same values in Vercel before deployment. Add the deployed frontend origin (the default project URL is `https://adshield.vercel.app`) to the API's comma-separated `CORS_ORIGINS`. If you use a custom domain or a differently named Vercel project, use that exact origin instead.

## Checks

```bash
npm run lint
npm run typecheck
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
npm audit
```
