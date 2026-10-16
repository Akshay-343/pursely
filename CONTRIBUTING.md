# Contributing to Pursely

Thanks for taking the time to contribute.

## Setup

Follow [Getting started](README.md#getting-started) to run the backend and frontend locally.
`python -m app.seed_demo` fills the database with sample data (login `demo@example.com` / `demo1234`).

## Before opening a pull request

```bash
cd backend && ruff check . && python -m pytest
cd frontend && npm run build      # type-checks and builds
```

- Keep pull requests focused on one change and describe what and why.
- Add or update tests for backend behaviour changes.
- Schema changes need an Alembic migration: `alembic revision --autogenerate -m "describe change"`.
  CI fails if models and migrations drift.
- Money values are `Decimal`, never `float`.
- Every query that reads user data must filter by the current user.

## Commit messages

Use the imperative mood ("Add budget alerts", not "Added budget alerts") and keep the first line under 72 characters.

## Reporting bugs and ideas

Open an issue using the bug report or feature request template.
For security problems, see [SECURITY.md](SECURITY.md) instead of opening a public issue.
