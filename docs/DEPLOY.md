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

## Email (welcome, password reset, reminders) with Gmail
1. Turn on 2-Step Verification for the Gmail account, then create an **App Password** at
   https://myaccount.google.com/apppasswords. Google shows 16 characters in groups of four; paste them **without spaces**.
2. Put these in the server's `.env` (never in git; `.env` is already ignored):
   ```
   APP_URL=https://your-domain
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.address@gmail.com
   SMTP_PASSWORD=<the app password>
   SMTP_FROM=Money Tracker <your.address@gmail.com>
   ```
3. Check it before relying on it: `docker compose exec api python -m app.send_test_email you@example.com`.
   It prints the exact reason on failure (wrong app password, blocked port, and so on).

Gmail only sends "From" the account itself, and allows about 500 messages a day, plenty for personal use. For more, use a
dedicated provider (Brevo, Mailgun, SES) with the same `SMTP_*` variables. If you revoke the app password in your Google
account, email stops and everything else keeps working. Without SMTP, in-app reminders still work.

## Sign in with Google
1. Open https://console.cloud.google.com/apis/credentials, create a project if you need one, and configure the OAuth consent
   screen (app name, your support email). Publish it to "In production" so anyone can sign in, not only test users.
2. Create credentials, **OAuth client ID**, type **Web application**. Under **Authorized JavaScript origins** add
   `https://your-domain` (and `http://localhost:5173` for local use). No redirect URI is needed.
3. Copy the Client ID into `.env` as `GOOGLE_CLIENT_ID=...` and restart the stack. The "Continue with Google" button then
   appears on the sign-in page. The Client ID is public; there is no client secret to store.

Signing in with Google creates an account on first use (and sends the welcome email). If an account with the same verified email
already exists, Google sign-in is linked to it. People who joined with Google can add a password through "Forgot password".

## Behind a proxy
The API rate-limits sign-in, sign-up and password-reset requests per client IP using `X-Forwarded-For`. The provided Caddy and
nginx configs set it. Keep the API unpublished (as `docker-compose.prod.yml` does) so clients cannot spoof that header.
