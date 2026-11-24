# Changelog

All notable changes to Pursely are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-11-24

### Changed

- The sign-in page doubles as a landing page: a hero with Pursely's features beside a wallet-styled sign-in box, with Sign in and Create account tabs and a theme toggle.

## [1.0.0] - 2026-11-08

First stable release.

### Added

- Transactions with categories, accounts, tags, notes, CSV import and export, and receipt attachments.
- Dashboard with spending KPIs, income vs expense chart and category breakdown for any date range.
- Subscriptions with monthly and yearly cost roll-up, renewal reminders and optional auto-posting.
- Per-category and overall monthly budgets with alerts.
- Bank, cash and card accounts with live balances and transfers.
- Savings goals with deadlines and a monthly savings plan.
- Insights with month-end projection, savings rate, category trends, top merchants and a PDF report.
- AI saving tips and Ask Pursely, powered by Groq.
- Recurring transactions and reminders run by an idempotent background job.
- Email and password sign-in with JWT, Sign in with Google, password reset by email and rate limiting.
- Installable PWA with a mobile layout and light and dark themes.
- Portfolio landing page for Netlify.
- API version reported by `/health`.
- Backend Docker image published on every merge to `main`, tagged `vX.Y.Z` and `latest`.
- Weekly registry cleanup that keeps the 2 newest backend images.

### Removed

- Public demo mode (`DEMO_MODE`, `/auth/demo` and the "Try the demo" button).

[Unreleased]: https://github.com/Akshay-343/pursely/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Akshay-343/pursely/releases/tag/v1.0.0
