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

## Install on your phone
- **Android (Chrome):** menu, then "Install app" (or the "Install app" button in the header).
- **iPhone (Safari):** Share, then "Add to Home Screen".

## Backups
- Database: `docker compose exec db pg_dump -U money moneytracker > backup.sql`
- Receipts: the `uploads` Docker volume.

## Email reminders
Use any SMTP provider (Gmail app password, Brevo, Mailgun, SES). Set the `SMTP_*` variables, then each
user turns on "Also email me reminders" in Settings. Without SMTP, in-app reminders still work.
