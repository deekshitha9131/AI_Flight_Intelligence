# Google Cloud Configuration — OAuth Login Setup

This is a one-time setup step in Google Cloud Console, required before
`make up` will produce a working "Sign in with Google" flow. Nothing in
the application code needs to change based on these steps — only the
three values you copy into `backend/.env` at the end.

---

## 1. Create (or select) a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/).
2. Create a new project (or reuse an existing one) — top-left project
   selector → **New Project**. Name it something like
   `ai-email-assistant-dev`.

---

## 2. Enable the Gmail API

1. In the left sidebar: **APIs & Services → Library**.
2. Search for **Gmail API** and click **Enable**.

This phase (login) doesn't call the Gmail API itself, but the OAuth
consent screen and scopes below are meaningless without it enabled —
Google will reject a request for `gmail.readonly`/`gmail.send` scopes
against a project that hasn't enabled the API those scopes belong to.

---

## 3. Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. **User Type**: choose **External** (this is what allows any Google
   account to log in during development — "Internal" is restricted to
   Google Workspace accounts on your own domain, which doesn't apply
   here).
3. Fill in the required fields: app name, user support email, developer
   contact email. Everything else on this screen can be left default
   for now.
4. **Scopes** step: click **Add or Remove Scopes** and add exactly
   these (matching `GOOGLE_OAUTH_SCOPES` in
   `backend/app/core/constants.py` — if you ever change the scopes in
   code, update them here too, and vice versa):
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
   - `.../auth/gmail.readonly`
   - `.../auth/gmail.send`
5. **Test users** step: while the app is in "Testing" publishing status
   (the default, and fine for development), only email addresses added
   here can complete the login flow. Add your own Google account.

   Publishing the app to "Production" removes this restriction but
   requires Google's verification review for the sensitive Gmail scopes
   above — not needed for local development or a portfolio
   demonstration, only for a public production launch.

---

## 4. Create an OAuth 2.0 Client ID

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. **Application type**: **Web application**.
3. **Name**: anything recognizable, e.g. `ai-email-assistant-backend`.
4. **Authorized redirect URIs** — add exactly the URI the callback
   endpoint is served at. For local development via `docker compose`:

   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```

   This must match `GOOGLE_REDIRECT_URI` in `backend/.env` **exactly**
   — including the scheme, port, and path. A mismatch here is the most
   common cause of a `redirect_uri_mismatch` error from Google, and
   Google will not tell you which part mismatched.

5. Click **Create**. Google shows a **Client ID** and **Client Secret**
   — copy both.

---

## 5. Populate `backend/.env`

```bash
GOOGLE_CLIENT_ID=<the client ID from step 4>
GOOGLE_CLIENT_SECRET=<the client secret from step 4>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

`FRONTEND_BASE_URL` (also in `backend/.env`) controls where the browser
is redirected *after* a successful login — defaults to
`http://localhost:5173`, matching the frontend's dev server port. Only
change this if your frontend runs somewhere else.

---

## 6. Verify it works

```bash
make up
```

Then visit `http://localhost:8000/api/v1/auth/google/login` directly in
a browser (not via `curl` — this flow requires a real browser to
complete Google's consent screen). You should be redirected to Google,
prompted to sign in and consent, and then redirected back to
`FRONTEND_BASE_URL` with a `session_id` cookie set.

Confirm the session actually took by visiting:

```
http://localhost:8000/api/v1/auth/session
```

which should return your profile (email, full name, status) — a 401
here after completing consent means something in this setup doesn't
match; re-check the redirect URI first, since that's the most common
point of failure.

---

## Common failure modes

| Symptom | Likely cause |
|---|---|
| `redirect_uri_mismatch` from Google | `GOOGLE_REDIRECT_URI` doesn't exactly match an Authorized redirect URI in the Cloud Console credential |
| `access_denied` from Google, immediately | Your Google account isn't in the consent screen's **Test users** list (while in Testing status) |
| Login succeeds but a *second* login for the same account never returns a refresh token in the database | Should not happen in this codebase — `prompt=consent` is set on every authorization request specifically to force a fresh refresh_token every time (see `GoogleOAuthClient.build_authorization_url`). If it does happen, check that this parameter wasn't removed. |
| `/api/v1/auth/session` returns 401 right after a successful-looking redirect | Check that `backend/.env`'s `FRONTEND_BASE_URL`, cookie `secure` flag, and browser origin are consistent — a `secure` cookie will silently not be sent back over plain `http://localhost` in some browser configurations if `APP_ENV=production` was accidentally set locally |
