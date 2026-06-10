# Setup for `--data=auto` mode (one-time)

This guide gets you the **four free API credentials** that let `pick-next-tool` pull
real keyword data *without you sitting in a browser clicking through CAPTCHAs*. Do
this **once**. After that, running the skill with `--data=auto` is hands-off.

> **You can skip this entire page if you only ever use manual or hybrid mode.**
> Manual and hybrid modes drive free tools through the browser (Ahrefs free Keyword
> Generator, Bing UI, live Google SERP, etc.) and need **NONE** of these keys. The
> keys only exist to remove the manual browser steps in `--data=auto`.

---

## What you'll end up with

By the end you'll have set **8 environment variables** (jargon: an *environment
variable* is just a named value your shell hands to any script you run — like a
sticky note the scripts can read). Five belong to one service (Google Ads), the
other three are one key each:

| Service | What the skill uses it for | Env var(s) |
|---|---|---|
| **Google Ads API** | **Search volume** — canonical monthly volume + CPC from Keyword Planner | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID` |
| **Bing Webmaster Tools** | **Exact-volume tie-break** — real Bing impression integers, used to break ties when two candidates look equal | `BING_WEBMASTER_API_KEY` |
| **OpenPageRank (DomCop)** | **DR-wall** — Domain Rating of page-1 incumbents, to judge how strong the competition's domains are | `OPENPAGERANK_API_KEY` |
| **SerpApi** | **SERP + AI-Overview** — structured search results and whether Google shows an AI Overview for a query | `SERPAPI_KEY` |

All four services have a genuinely free tier. None requires a credit card to obtain
the key (Google Ads asks for billing only when you actually *run ads*, which you
never will here).

---

## Where to put the values (do this first so you have a home for each key)

Pick **one** of these. The scripts read the variables from your environment, so any
method that ends with them set will work.

### Option A — a `.env` file (recommended, easiest to manage)
1. In the **project root** (`Online Web Apps/`), create a file named `.env`.
2. Add one `NAME=value` line per credential (examples filled in as you go below).
3. **Make sure `.env` is git-ignored** so you never commit secrets. Check your
   `.gitignore` contains a line `.env`; add it if missing.

```dotenv
# .env  (NEVER commit this file)
GOOGLE_ADS_DEVELOPER_TOKEN=your-token-here
GOOGLE_ADS_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your-secret-here
GOOGLE_ADS_REFRESH_TOKEN=1//your-refresh-token-here
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
BING_WEBMASTER_API_KEY=your-bing-key-here
OPENPAGERANK_API_KEY=your-openpagerank-key-here
SERPAPI_KEY=your-serpapi-key-here
```

### Option B — your shell profile (sets them for every terminal)
Add the same `export NAME=value` lines to `~/.zshrc` (this machine uses **zsh**),
then run `source ~/.zshrc` or open a new terminal:

```zsh
export GOOGLE_ADS_DEVELOPER_TOKEN=your-token-here
# ...one export line per variable...
```

> **The variable names must match exactly** (all capitals, underscores). The scripts
> look them up by name; a typo means the script silently can't find the value.

---

## 1. Google Ads API — gives the skill real search **volume** (5 variables)

This is the most involved one (5 values). Budget ~30 minutes of clicking spread over
**~1 business day** because of an approval wait in the middle. There is **no cost** —
you create a no-spend account and never run an ad.

> **Jargon, quickly:**
> - *Expert Mode* = the full Google Ads interface, instead of the simplified "Smart"
>   wizard that forces you to launch an ad. Expert Mode lets you create an account
>   **without a campaign**, so you never spend money.
> - *Manager account (MCC)* = a Google Ads account that can contain other accounts.
>   The developer token lives here.
> - *Developer token* = a string that authorizes your app to call the Ads API.
> - *OAuth client ID + secret* = your app's "username/password" with Google.
> - *Refresh token* = a long-lived key proving *you* approved that app to read *your*
>   Google account, so scripts can run unattended.

### 1a. Create a no-spend Expert-Mode Google Ads account
1. Go to **https://ads.google.com** and click to create an account.
2. On the first setup screen, look for the small link **"Switch to Expert Mode"**
   (sometimes phrased "Are you a professional marketer? Switch to Expert Mode") and
   click it. This escapes the wizard that would force you to build an ad.
3. Choose **"Create an account without a campaign."**
4. Confirm your business info (time zone, currency). **Do not enter a credit card** —
   you can finish account creation without billing. The account stays free as long as
   you never launch a campaign.

### 1b. Create a Manager (MCC) account — this is where the token lives
1. Go to **https://ads.google.com/home/tools/manager-accounts/** and create a
   **manager account** (also free, no billing).
2. Link the account from step 1a under this manager account (Sub-account settings →
   link). The developer-token application wants your active accounts linked here.
3. Note the manager account's **Customer ID** — the 10-digit number at the top right,
   shown like `123-456-7890`. **Strip the dashes** → `1234567890`.
   → put it in **`GOOGLE_ADS_LOGIN_CUSTOMER_ID`**.

### 1c. Apply for a developer token (Basic access)
1. While signed into the **manager** account, open the **API Center**:
   **https://ads.google.com/aw/apicenter**.
2. Make sure the **API Contact Email** field is filled with an email you actually
   read — the application can't complete without it.
3. Click **Apply for Basic Access**, describe your use case plainly (e.g. "internal
   keyword-volume research for a small website portfolio; read-only Keyword Planner
   queries"). Submit.
4. Copy the token string shown in API Center → put it in
   **`GOOGLE_ADS_DEVELOPER_TOKEN`**.

> **Approval timing (verify, June 2026):** Basic access historically targets **~1
> business day** (24–48h). As of early 2026 Google acknowledged a **backlog** that
> has stretched some approvals **longer**. The *token string itself is available
> immediately* and works against **test accounts** right away; you only need approval
> before it returns data for your real (no-spend) account. So you can finish steps 1d–1e
> while you wait.

### 1d. Create the OAuth client ID + secret (in Google Cloud)
1. Go to **https://console.cloud.google.com** and create a **project** (any name).
2. In the project, open **APIs & Services → Library**, search **"Google Ads API"**,
   and click **Enable**.
3. Open **APIs & Services → OAuth consent screen**. Configure it (User Type
   **External** is fine), add yourself as a **Test user**, and — **important** — set
   the **Publishing status to "In production."** If you leave it in *Testing*, your
   refresh token (step 1e) silently **expires after 7 days**.
4. Open **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   Choose application type **Desktop app**. Create it.
5. Copy the two values shown:
   - **Client ID** (ends in `.apps.googleusercontent.com`) → **`GOOGLE_ADS_CLIENT_ID`**
   - **Client secret** → **`GOOGLE_ADS_CLIENT_SECRET`**
   - Also click the download icon to save the `client_secret_*.json` file — you'll
     point the next script at it.

### 1e. Generate the refresh token (a short one-time script run)
1. Install the helper library (one line):
   ```zsh
   pip install google-ads
   ```
2. Download Google's generator script:
   **https://developers.google.com/google-ads/api/docs/first-call/refresh-token**
   has the current `generate_user_credentials.py` (or use the one bundled with the
   `google-ads` library). Run it pointing at the JSON you downloaded in 1d:
   ```zsh
   python generate_user_credentials.py --client_secrets_path=/path/to/client_secret_XXX.json
   ```
3. It prints a URL. Open it **in a browser**, sign in with the **same Google account**
   that owns your Ads/manager account, and click **Continue / Allow** on the consent
   screen.
4. The script prints your **refresh token** (a long string usually starting `1//`).
   Copy it → put it in **`GOOGLE_ADS_REFRESH_TOKEN`**.

That's all five Google Ads variables set.

---

## 2. Bing Webmaster Tools API key — exact-volume **tie-break** (1 variable)

Bing reports real **impression** integers (no ad spend needed), which the skill uses
to break ties when two candidates score the same on volume.

1. Go to **https://www.bing.com/webmasters** and sign in (Microsoft / Google / Facebook
   login all work).
2. **Add and verify at least one site.** You need one verified property before the API
   section unlocks. (If you have no site yet, verifying any domain you control — even a
   placeholder — is enough; verification options include a meta tag, XML file, or DNS
   record.)
3. Click the **Settings** (gear) icon, top-right → open the **API Access** section.
4. Accept the Terms & Conditions (first time only), then click **Generate API Key**.
5. Copy the key → put it in **`BING_WEBMASTER_API_KEY`**.

> Note: Bing issues **one key per user**, and it works for **all** your verified sites
> — you don't need a separate key per site. If it's ever compromised, delete and
> regenerate it on the same API Access page.

---

## 3. OpenPageRank (DomCop) API key — the **DR-wall** check (1 variable)

OpenPageRank returns a free **Domain Rating (0–10)** for any domain, which the skill
uses to gauge how strong page-1 incumbents' domains are (the "DR wall").

1. Go to **https://www.domcop.com/openpagerank/** and click to sign up, or go straight
   to **https://www.domcop.com/openpagerank/auth/signup**.
2. Register with an email + password (free, no card).
3. After signing in, your **API key** is shown in your OpenPageRank dashboard / account
   page.
4. Copy it → put it in **`OPENPAGERANK_API_KEY`**.

> Free tier is generous — up to **10,000 API calls per hour** — far more than this
> skill needs.

---

## 4. SerpApi key — **SERP + AI-Overview** detection (1 variable)

SerpApi returns Google results as clean JSON, including whether an **AI Overview**
fired for a query (a core input to the skill's AI-Resistance score).

1. Go to **https://serpapi.com/users/sign_up** and create a free account (no card for
   the free tier).
2. After signing in, open your **dashboard / "Your Account"** page; the **Private API
   Key** (a long hex string) is displayed there.
3. Copy it → put it in **`SERPAPI_KEY`**.

> **Free tier (verify, June 2026):** SerpApi's free plan is **250 searches/month** (it
> was raised from 100/month in July 2025) and is described as a **forever-free** plan.
> The skill's `references/free-tools.md` still says "~100/mo" — treat **250** as
> current and update that line if you touch it. 250/month is enough for a few skill
> runs per month, not high-frequency batch use.

---

## Verify it all worked

Open a **new** terminal (so it picks up exports / your `.env` loader) and check the
names are populated. Each line should print a non-empty value:

```zsh
for v in GOOGLE_ADS_DEVELOPER_TOKEN GOOGLE_ADS_CLIENT_ID GOOGLE_ADS_CLIENT_SECRET \
         GOOGLE_ADS_REFRESH_TOKEN GOOGLE_ADS_LOGIN_CUSTOMER_ID \
         BING_WEBMASTER_API_KEY OPENPAGERANK_API_KEY SERPAPI_KEY; do
  printf '%-32s %s\n' "$v" "${(P)v:+SET}"
done
```

(That prints `SET` next to each variable that has a value, without revealing the
secret. If a line is blank, that variable isn't set — re-check the name and your
`.env`/profile.)

Once all eight say `SET` (and the Google Ads developer token has been **approved**),
`--data=auto` can pull real data unattended.

---

## Quick reference

| Env var | Service | Skill data role | Where to get it |
|---|---|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API | volume | API Center of the manager account (Basic access) |
| `GOOGLE_ADS_CLIENT_ID` | Google Ads API | volume | Google Cloud → OAuth client (Desktop app) |
| `GOOGLE_ADS_CLIENT_SECRET` | Google Ads API | volume | Google Cloud → OAuth client (Desktop app) |
| `GOOGLE_ADS_REFRESH_TOKEN` | Google Ads API | volume | `generate_user_credentials.py` output |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Google Ads API | volume | Manager account Customer ID, dashes removed |
| `BING_WEBMASTER_API_KEY` | Bing Webmaster Tools | exact-volume tie-break | Settings → API Access → Generate API Key |
| `OPENPAGERANK_API_KEY` | OpenPageRank (DomCop) | DR-wall | DomCop OpenPageRank dashboard |
| `SERPAPI_KEY` | SerpApi | SERP + AI-Overview | SerpApi dashboard (Private API Key) |

**Reminder: manual and hybrid modes need none of the above.** This page is only for
`--data=auto`.

---

### Could not be fully confirmed (verify when you reach that step)

- **Exact Google Ads Basic-access wait time today.** Target is ~1 business day, but a
  Feb 2026 Google notice confirmed a backlog stretching some approvals longer. Plan for
  more than a day to be safe.
- **Exact label/placement of buttons inside each console** (e.g. the precise wording of
  "Switch to Expert Mode," the API Center "Apply for Basic Access" link, the Bing
  "Generate API Key" button) can shift between UI revisions. The flow and section names
  above match June 2026 sources, but follow the on-screen labels if they differ slightly.
- **SerpApi free count = 250/month** is the latest figure (raised from 100 in Jul 2025);
  re-check https://serpapi.com/pricing if exactness matters for your usage budget.
- **OpenPageRank key location** is in the post-signup dashboard; DomCop's exact dashboard
  layout wasn't independently re-verified screen-by-screen.
