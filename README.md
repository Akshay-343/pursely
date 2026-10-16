# Money Tracker

Multi-user expense tracker: FastAPI + PostgreSQL + React (Vite, Tailwind, shadcn/ui-style components).

Features: transactions (filters, CSV import/export), dashboard (KPIs, charts, date ranges), subscription tracker
(monthly/yearly cost, renewals, auto-post), budgets with warnings, recurring transactions, in-app reminders,
user-defined categories/accounts, dark mode, Google sign-in, welcome and password-reset emails (Gmail/SMTP).

## Run with Docker
```
cp .env.example .env   # set SECRET_KEY
docker compose up --build
```
App: http://localhost:5173 · API docs: http://localhost:8000/docs

## Local development
```
# backend (needs Postgres, or DATABASE_URL=sqlite:///./dev.db)
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
alembic upgrade head && uvicorn app.main:app --reload
python -m pytest            # tests run on in-memory SQLite

# frontend (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

## CI/CD
GitHub Actions run lint and tests (SQLite and PostgreSQL), build the frontend and images, scan dependencies, publish images to
ghcr.io and deploy on demand. See `docs/DEPLOY.md`.

## Notes
- Money is `NUMERIC(12,2)`. Dashboard totals include transactions in the user's default currency (no FX conversion).
- A background job (hourly, plus on notification fetch) generates recurring transactions, auto-posts subscriptions and creates reminders; it is idempotent.
- Transaction tags are stored as a JSON list on the transaction.
