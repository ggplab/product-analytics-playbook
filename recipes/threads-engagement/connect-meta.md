# Connect your own Meta / Threads account

The recipe runs on synthetic data out of the box. This guide gets your **real** Threads posts + insights into the same `data/threads_posts.csv`, so `analyze.py` runs unchanged on your account.

The whole point of the Threads API here is first-party analytics: it returns metrics **only for the authenticated account's own posts** — this is your data about your account, not scraping anyone else.

> **Time:** ~30–45 minutes the first time (most of it waiting on Meta's dashboard). After that, pulling fresh data is one command.
>
> **Meta's console UI shifts often.** The menu paths, permission names, and token endpoints below were verified against the official docs, which are the source of truth if a screen looks different: **[Threads API — Get Started](https://developers.facebook.com/docs/threads/get-started)**. Button labels may move; the flow does not.

---

## What you'll end up with

Two secrets in your shell environment:

```bash
export THREADS_ACCESS_TOKEN="THQVJ..."      # long-lived, 60 days
export THREADS_USER_ID="17841400000000000"  # your numeric Threads user id
```

Then:

```bash
python fetch_threads.py   # writes data/threads_posts.csv from your account
python analyze.py         # same analysis, your numbers
```

---

## Step 1 — Create a Meta app with Threads access

1. Go to **[developers.facebook.com/apps](https://developers.facebook.com/apps/)** and click **Create App** (you may need to register as a developer first — free).
2. Meta's wizard is use-case-first: when asked what you want your app to do, choose the option that grants **Threads API** access (labeled **"Access the Threads API"** or **Threads**). If your wizard instead asks for an app *type* first (Business / Consumer), pick either, create the app, then add the **Threads** use case from the app's dashboard afterward.
3. Name the app, create it, and open its dashboard.

> Threads apps carry **two** app IDs. You want the **Threads App ID** and **Threads App Secret** (not the generic Facebook ones). Find them at **App Dashboard → App settings → Basic → Threads App ID / Threads App Secret**.

## Step 2 — Configure the Threads use case

In the app dashboard, open the **Threads** use case → **Customize / Settings**:

1. **Permissions** — make sure these two are requested:
   - `threads_basic` — required for every Threads endpoint.
   - `threads_manage_insights` — required for the `/insights` metrics this recipe reads.
   (You don't need publishing or reply permissions for read-only analysis.)
2. **Redirect callback URI** — add one and note it exactly. For a solo, no-server setup use:
   ```
   https://localhost/
   ```
   It never actually loads — you'll read the auth code out of the redirected URL bar in Step 4. The URI you use in Step 4 must match what you save here **character for character** (including the trailing slash).

## Step 3 — Add yourself as a Threads Tester

Insights are only readable for a user who has authorized your app, and while the app is in development that means an approved tester:

1. **App Dashboard → App roles → Roles → Add People → Threads Tester**, and enter your own Threads username.
2. Accept the invite: log into **[threads.net](https://www.threads.net/)** → **Settings → Account → Website permissions → Invites**, and accept.

This keeps you out of Meta's full App Review — a tester can grant the permissions immediately. (App Review is only needed to analyze *other people's* accounts, which this recipe doesn't do.)

## Step 4 — Get a short-lived token (the authorization code)

Paste this into your browser, with your Threads App ID and redirect URI filled in:

```
https://threads.net/oauth/authorize
  ?client_id=<THREADS_APP_ID>
  &redirect_uri=https://localhost/
  &scope=threads_basic,threads_manage_insights
  &response_type=code
```

(Put it on one line — it's wrapped here for reading.) Log in, approve the two permissions, and Meta redirects you to `https://localhost/?code=AQB...#_`. The page won't load — that's fine. **Copy the `code` value from the address bar, and delete the trailing `#_`** (it's appended to the URL but is not part of the code). The code is valid for **1 hour, single use**.

## Step 5 — Exchange the code for a short-lived token

```bash
curl -X POST https://graph.threads.net/oauth/access_token \
  -F client_id=<THREADS_APP_ID> \
  -F client_secret=<THREADS_APP_SECRET> \
  -F grant_type=authorization_code \
  -F redirect_uri=https://localhost/ \
  -F code=<CODE_FROM_STEP_4>
```

Response:

```json
{ "access_token": "THQVJ...", "user_id": 17841400000000000 }
```

Save both. The `user_id` is your `THREADS_USER_ID`. This `access_token` is short-lived (1 hour) — exchange it now.

## Step 6 — Exchange for a long-lived token (60 days)

```bash
curl -s "https://graph.threads.net/access_token\
?grant_type=th_exchange_token\
&client_secret=<THREADS_APP_SECRET>\
&access_token=<SHORT_LIVED_TOKEN_FROM_STEP_5>"
```

Response:

```json
{ "access_token": "THQVJ...", "token_type": "bearer", "expires_in": 5183944 }
```

That `access_token` is your `THREADS_ACCESS_TOKEN` (good for ~60 days).

> **Keep the app secret server-side.** Steps 6 and the refresh call include your app secret — run them from your machine/terminal, never from client-side or committed code. Don't paste real tokens or secrets into any file you commit.

## Step 7 — Pull your data

```bash
export THREADS_ACCESS_TOKEN="THQVJ..."       # from Step 6
export THREADS_USER_ID="17841400000000000"   # from Step 5
python fetch_threads.py                       # -> data/threads_posts.csv
python analyze.py
```

`fetch_threads.py` pages through your original posts (replies to others are skipped — they aren't part of your reach funnel) and pulls `views, likes, replies, reposts, quotes` for each.

**One editorial step:** the API returns metrics, not content labels. The `track` and `theme` columns come out as `untagged`, so the per-pillar chart (Result #3) is empty until you tag your posts — by hand, with a keyword map, or an LLM pass over the post text. The baseline and the two engagement-rate charts work immediately.

## Keeping it alive

A long-lived token can be **refreshed** any time after it's 24 hours old and before it expires, which resets it to another 60 days:

```bash
curl -s "https://graph.threads.net/refresh_access_token\
?grant_type=th_refresh_token\
&access_token=<LONG_LIVED_TOKEN>"
```

Miss the 60-day window and the token is dead — you start again from Step 4. If you're automating collection, refresh on a schedule (e.g. weekly) so it never lapses.

## Gotchas (learned the hard way)

- **Silent insights loss.** If the token loses `threads_manage_insights` (permission expiry, a scope change), `/insights` doesn't error loudly — it just returns nothing, and you'd quietly log zeros. `fetch_threads.py` prints a warning per post when insights come back empty; don't ignore it. Re-authorize (Step 4) to fix.
- **The `#_` suffix.** Meta appends `#_` to the redirect URL. Leave it on the code and Step 5 fails with "code not found."
- **Redirect URI must match exactly.** The `redirect_uri` in Steps 4 and 5 must equal what you saved in Step 2, trailing slash included.
- **Everything short expires fast.** The auth code lasts 1 hour, the short-lived token 1 hour. Do Steps 4→5→6 in one sitting.
- **Own account only, public profile simplest.** Private profiles are supported now, but a public profile is the least fiddly for permission renewal.

## References

- [Threads API — Get Started](https://developers.facebook.com/docs/threads/get-started) (permissions, testers, token overview)
- [Get access tokens and permissions](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions) (authorization window, code exchange)
- [Long-lived tokens](https://developers.facebook.com/docs/threads/get-started/long-lived-tokens) (exchange + refresh endpoints)
- [Threads Insights](https://developers.facebook.com/docs/threads/insights) (the metrics `fetch_threads.py` reads)

---

© 2026 BuildnWrite. All rights reserved.
