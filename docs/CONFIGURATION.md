# Configuration

Pursely reads all settings from environment variables. Locally, put them in `.env` (copied from
[`.env.example`](../.env.example)); on a hosting platform, set them in its dashboard. Never commit real secrets.

## Demo mode

Set `DEMO_MODE=true` to show a **Try the demo** button on the sign-in page. It signs visitors into a shared account
(`demo@example.com`) with six months of sample data. The data is rebuilt when the API starts and every 24 hours,
so whatever visitors change is temporary. Real accounts are never touched.

You can also (re)build the demo data by hand: `python -m app.seed_demo`.

## Email (welcome, password reset, reminders) with Gmail
1. Turn on 2-Step Verification for the Gmail account, then create an **App Password** at
   https://myaccount.google.com/apppasswords. Google shows 16 characters in groups of four; paste them **without spaces**.
2. Set these environment variables (in `.env` locally; never in git):
   ```
   APP_URL=https://your-domain
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.address@gmail.com
   SMTP_PASSWORD=<the app password>
   SMTP_FROM=Pursely <your.address@gmail.com>
   ```
3. Check it before relying on it: `python -m app.send_test_email you@example.com` (inside `backend/`).
   It prints the exact reason on failure (wrong app password, blocked port, and so on).

Gmail only sends "From" the account itself, and allows about 500 messages a day, plenty for personal use. For more, use a
dedicated provider (Brevo, Mailgun, SES) with the same `SMTP_*` variables. If you revoke the app password in your Google
account, email stops and everything else keeps working. Without SMTP, in-app reminders still work.

## Sign in with Google
1. Open https://console.cloud.google.com/apis/credentials, create a project if you need one, and configure the OAuth consent
   screen (app name, your support email). Publish it to "In production" so anyone can sign in, not only test users.
2. Create credentials, **OAuth client ID**, type **Web application**. Under **Authorized JavaScript origins** add
   `https://your-domain` (and `http://localhost:5173` for local use). No redirect URI is needed.
3. Copy the Client ID into `.env` as `GOOGLE_CLIENT_ID=...` and restart the API. The "Continue with Google" button then
   appears on the sign-in page. The Client ID is public; there is no client secret to store.

Signing in with Google creates an account on first use (and sends the welcome email). If an account with the same verified email
already exists, Google sign-in is linked to it. People who joined with Google can add a password through "Forgot password".

## Rate limiting behind a proxy
The API rate-limits sign-in, sign-up and password-reset requests per client IP using `X-Forwarded-For`. The provided nginx config
sets it. In production, only expose the API through a proxy you control so clients cannot spoof that header.
