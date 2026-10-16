# Deploying so you can use it on your phone

The app needs a server that runs Docker (the API, database and web app). A phone cannot run it,
but any phone can open it once it is hosted with HTTPS. HTTPS is also required for "Add to Home Screen" (PWA install).

## Option A: a small VPS (about $5/month: Hetzner, DigitalOcean, Lightsail, Oracle free tier)
1. Install Docker on the server and clone this repo.
2. Create a DNS `A` record for a domain or subdomain pointing at the server's IP.
3. `cp .env.example .env` and set: `SECRET_KEY` (long random string), `POSTGRES_PASSWORD`, `DOMAIN`,
   `CORS_ORIGINS=https://your-domain`, and optionally the `SMTP_*` values for email reminders.
4. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
5. Open `https://your-domain` on your phone. Caddy gets the HTTPS certificate automatically.

## Automatic builds and deploys (GitHub Actions)
- **CI** (`ci.yml`) runs on every pull request and push to `main`: lint and tests on SQLite, migrations and the full test
  suite on PostgreSQL 16, the frontend build, and a Docker build check.
- **Publish Docker images** (`docker-publish.yml`) pushes `ghcr.io/<owner>/<repo>-api` and `-web` (amd64 + arm64) on
  every push to `main` (`:main`, `:latest`, `:sha-…`) and on tags like `v1.2.3` (`:1.2.3`, `:1.2`).
- **Security** (`security.yml`) runs CodeQL and `pip-audit` / `npm audit` weekly and on pull requests.
- **Deploy** (`deploy.yml`) is manual: Actions tab, "Deploy", enter an image tag (`main`, `1.2.3`, `sha-abc1234`).
  It SSHes to your server, pulls those images and restarts the stack. It never runs by itself.

One-time setup for **Deploy**:
1. On the server, clone the repo (default path `~/Moneytracker`) and create `.env` as in option A above.
2. Create a deploy key: `ssh-keygen -t ed25519 -f deploy_key -N ""`. Append `deploy_key.pub` to the server user's
   `~/.ssh/authorized_keys`.
3. In the repo go to Settings, Secrets and variables, Actions, and add these secrets:
   `SSH_HOST`, `SSH_USER`, `SSH_KEY` (contents of `deploy_key`), `SSH_KNOWN_HOSTS`
   (output of `ssh-keyscan -t ed25519 your.server.ip`), and optionally `DEPLOY_PATH` if not `~/Moneytracker`.
4. Settings, Environments, create `production` and add yourself as a required reviewer, so each deploy needs a click.
5. The server needs Docker Compose v2. Images are private by default; the workflow logs in with a short-lived token.

Optional: in Settings, Branches, protect `main` and require the CI checks to pass before merging.

## Install on your phone
- **Android (Chrome):** menu, then "Install app" (or the "Install app" button in the header).
- **iPhone (Safari):** Share, then "Add to Home Screen".

## Backups
- Database: `docker compose exec db pg_dump -U money moneytracker > backup.sql`
- Receipts: the `uploads` Docker volume.

## Email reminders
Use any SMTP provider (Gmail app password, Brevo, Mailgun, SES). Set the `SMTP_*` variables, then each
user turns on "Also email me reminders" in Settings. Without SMTP, in-app reminders still work.
