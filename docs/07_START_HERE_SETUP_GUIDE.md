# START HERE — Mobile-First Setup Guide (iPhone + Claude app + web only)

Everything in this project can be set up and operated from your phone. No laptop, no
terminal, no installs. Your phone is the remote control; three free cloud services do the
work; Claude Code runs in Anthropic's cloud, not on any device you own.

## Document map (what to open when)
| Doc | Use it when… |
|---|---|
| 00 Executive Summary | you want the why / to explain the project to someone |
| 01 PRD | deciding whether a feature idea is in scope |
| 02 Technical Design | checking how something works; Claude Code proposes a change |
| 03 Roadmap | starting any build session — "which milestone are we on?" |
| 04 Repo & Claude Code | repo layout; the CLAUDE.md master copy is in its §4 |
| 05 Practice Profile | the digest miscategorized something → edit this file |
| 06 Prompts | §A claude.ai fallback digest · §B kickoff prompt · §C session ritual |
| 07 (this file) | setup, accounts, keys, weekly workflow — all phone-based |

## How the pieces fit (30-second mental model)
- **GitHub** holds the code and runs the free daily robot (ingestion — no LLM, no cost).
- **Supabase** is the free database the robot fills all week.
- **Resend** sends the email.
- **Claude Code on the web** (claude.ai/code, also inside the Claude iOS app) spins up a
  temporary cloud computer, connects to your GitHub repo, and is where both (a) the entire
  build happens and (b) your weekly `/digest` runs. It bills your existing Pro subscription.
- **Your phone** starts sessions, reads previews, taps "merge" — that's all.

---

## THE WEEKLY RITUAL (what Monday looks like on your iPhone, ~10–15 min)

1. Open the **Claude app** → go to the **Code** area (Claude Code) → start a **new cloud
   session** on the `anesthesia-intel` repository. (Same thing in any browser at
   **claude.ai/code** — identical.)
2. Type: `/digest`
3. Put the phone down; it triages and synthesizes for ~5–10 minutes. Cloud sessions keep
   running even if you close the app — check back between cases if you're in the OR.
4. It posts a preview of the digest in the session. Skim it. Optionally: "demote item 4,"
   "expand item 2," "why did item 6 make practice-changing?"
5. Reply **"send."** The email arrives in your inbox within a minute. Done.

**Forgot? Ran it Wednesday instead?** Nothing breaks, nothing is lost. Ingestion runs
automatically every day regardless, and `/digest` covers *everything since the last digest
you sent* — not "the last 7 days." Skip a week and the next digest simply covers two weeks;
the caps ensure only the best items survive.

**Automation options:**
- Now (free + compliant): automate the *reminder*, not the run — a recurring Monday iPhone
  reminder. The run stays interactive on your Pro plan (that's also what keeps it $0 and
  gives you preview-before-send).
- Later (~$6–16/mo): an API key stored as a GitHub secret turns the weekly step into a fully
  unattended scheduled job — the code is pre-structured for this flip (docs/02 §7, §9).
  Adopt it the day the ritual starts feeling like a chore.

---

## SETUP PART 1 — Accounts, from your phone's browser (~45 min, one time)

Use Safari/Chrome on the phone. Have iCloud Keychain or a password manager ready — you'll
save one password and four keys. If any site's menu differs, use its settings search with
the term given. Tip: some dashboards behave better with Safari's **AA menu → Request
Desktop Website**.

### Step 1 — GitHub
1. github.com → sign up (or log in).
2. Tap **+** (or Menu → New repository) → name `anesthesia-intel` → **Private** → do NOT
   add a README → **Create repository**.
3. Also install the **GitHub iOS app** from the App Store and log in — you'll use it to
   merge Claude Code's pull requests with one tap and to view the daily robot's logs
   (repo → Actions tab).

### Step 2 — Supabase (database)
1. supabase.com → Sign up (choosing "Continue with GitHub" is easiest).
2. **New project** → name `anesthesia-intel` → set a **Database Password** → SAVE IT to
   your password manager → nearest region → Create. Wait ~2 min.
3. Collect two things (gear icon → Project Settings):
   - **Database** → Connection string → **URI** → copy → replace `[YOUR-PASSWORD]` inside
     it with your saved password. Save as `DATABASE_URL`. Also note the host part (looks
     like `db.abcdefgh.supabase.co` or `...pooler.supabase.com`) — you'll allowlist it in
     Part 3. (Settings search term: "Connection string".)
   - **API** → copy the **Project URL** and the **service_role** key (for the feedback
     function later). (Search term: "API keys".)

### Step 3 — Resend (email)
1. resend.com → sign up **using the email address where you want the digest delivered**.
2. Sidebar → **API Keys** → **Create API Key** → name it → **copy immediately** (shown
   once) → save as `RESEND_API_KEY`.
3. Skip domain verification: the free tier can send to your own account email without a
   domain — which is exactly this product.

### Step 4 — NCBI / PubMed key (optional, recommended, free, 5 min)
account.ncbi.nlm.nih.gov → create account → Account Settings → **API Key Management** →
generate → save as `NCBI_API_KEY`. (Raises PubMed rate limits. Unpaywall needs no key.)

### Step 5 — Put secrets into GitHub (for the daily robot)
On github.com (Request Desktop Website helps here): your repo → **Settings** → **Secrets
and variables** → **Actions** → **New repository secret**, one at a time:
`DATABASE_URL` · `RESEND_API_KEY` · `NCBI_API_KEY` · `FEEDBACK_HMAC_SECRET` (invent this
one: any random ~40-character string from your password manager's generator).
Never paste these into chat or code — CLAUDE.md forbids it and Claude Code knows.

## SETUP PART 2 — Seed the repo from your phone (~15 min)

The seven seed files are the documents from this conversation. Two phone-friendly routes:

**Route A (recommended): let Claude Code do it.** In Part 3 you'll open the first cloud
session; its first task (already written into the kickoff prompt) can create the folder
structure. You will paste in only the two files that must exist verbatim: CLAUDE.md
(copy the block from doc 04 §4) and PRACTICE_PROFILE.md (doc 05) — pasting text into a
session works fine on a phone. Then attach or paste docs 00–07 one by one when it asks, or:

**Route B: upload directly to GitHub.** Download the files from this chat to the **Files
app** → github.com in Safari → **Request Desktop Website** → your repo → **Add file →
Upload files** → select all → commit to `main`. Layout: `CLAUDE.md` and
`PRACTICE_PROFILE.md` at the repo root; everything numbered 00–07 inside a `docs/` folder.

Before moving on: read PRACTICE_PROFILE.md once more and fix anything that rings false —
it is the product's brain.

## SETUP PART 3 — Connect Claude Code on the web (~15 min, one time)

1. In a browser go to **claude.ai/code** (or the Code area of the Claude app) → log in
   with your Pro account → **connect your GitHub account** when prompted and grant access
   to the `anesthesia-intel` repository.
2. Configure the repo's **cloud environment** (the dialog where sessions are configured):
   - **Environment variables:** add the same four secrets from Part 1 Step 5
     (`DATABASE_URL`, `RESEND_API_KEY`, `NCBI_API_KEY`, `FEEDBACK_HMAC_SECRET`). These are
     what let your weekly `/digest` session reach the database and send the email. (Note:
     they're available inside the running session, which is all this project needs.)
   - **Network access:** the sandbox blocks unknown outbound domains by default. Add these
     as custom allowed domains, or `/digest` will mysteriously fail:
     your Supabase host from Part 1 Step 2 (or `*.supabase.co` and `*.pooler.supabase.com`),
     `api.resend.com`, `eutils.ncbi.nlm.nih.gov`, `api.unpaywall.org`,
     `www.ncbi.nlm.nih.gov`.
3. That's it. Every future session — build sessions and Monday digests — starts from this
   same place with two taps.

## SETUP PART 4 — First build session (from the phone)

1. claude.ai/code (or app → Code) → new session on `anesthesia-intel`.
2. Type `/model opus` (use the strongest model for architecture sessions; if a stronger
   tier like Fable is offered in the picker, use it). Routine later sessions: `/model sonnet`.
3. Paste the **kickoff prompt from doc 06 §B**. It forces a plan first: Claude Code proposes
   the full scaffold and WAITS for your approval before writing anything.
4. Claude Code works in its cloud sandbox and opens a **pull request** per step. You review
   the summary and tap **Merge** in the GitHub app. Merging to `main` is what activates the
   daily robot.
5. Follow the session ritual in doc 06 §C so every session hands off cleanly. Cloud sessions
   keep running with the app closed — start one before a case, check it after.

## Honest caveats for the all-mobile path
- Claude Code on the web is a research preview; occasional rough edges are normal. Nothing
  about this project depends on preview-only features — any desktop browser is a fallback
  that works identically, still with zero installs.
- Reviewing long diffs on a phone is the least pleasant part. Mitigation is built into the
  workflow: small PR-sized steps, plain-language summaries, and the eval harness as your
  quality gate — you're approving behavior ("eval recall 92%"), not reading every line.
- Build sessions and digests share your Pro usage limits with your regular Claude chatting.
  The pre-filters keep digest sessions light; do heavy build sessions on lighter-chat days.
