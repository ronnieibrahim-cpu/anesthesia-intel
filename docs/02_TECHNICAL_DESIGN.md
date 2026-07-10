# Technical Design Document (v2)

**System:** Anesthesia Intelligence V1
**Constraints:** single user · $0/month beyond existing Claude Pro subscription · maintained by
a non-engineer using Claude Code · no servers · readable over clever · no paywall circumvention

---

## 1. Architecture overview

Two halves: a free automated data layer, and a weekly interactive intelligence layer that runs
on your Claude Pro subscription.

```
┌────────────────  GitHub Actions, DAILY 05:00 CT (free, no LLM)  ───────────────┐
│                                                                                │
│  ┌───────────┐   ┌─────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │ Ingest    │ → │ Dedupe  │ → │ Pre-filter   │ → │ Enrich: Unpaywall /  │    │
│  │ PubMed,   │   │ & store │   │ (heuristics: │   │ PubMed Central legal │    │
│  │ FDA, RSS  │   │         │   │ journals,    │   │ full-text links      │    │
│  └───────────┘   └─────────┘   │ keywords, n) │   └──────────────────────┘    │
│                                └──────────────┘                               │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       ▼
                        ┌───────────────────────────────┐
                        │ Supabase Postgres (free tier) │
                        └───────────────┬───────────────┘
                                        │
┌────────  YOUR LAPTOP, MONDAY ~06:00, interactive Claude Code session  ────────┐
│                                                                               │
│  you type: /digest                                                            │
│  Claude Code then: reads week's pre-filtered items → triages against          │
│  PRACTICE_PROFILE.md (structured JSON, batched) → writes scores to DB →       │
│  synthesizes top items → renders digest.html → shows you a preview →          │
│  on your "send", delivers via Resend and stores the copy                      │
│                                                                               │
│  Billing: your Claude Pro plan. No API key exists in this project.            │
└───────────────────────────────────────────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┴──────────────┐
              ▼                                        ▼
   ┌─────────────────────┐                 ┌───────────────────────┐
   │ Supabase Edge Fn    │ ◄── click ───   │ Weekly email in inbox │
   │ /feedback (HMAC)    │                 │ (the entire V1 UI)    │
   └─────────────────────┘                 └───────────────────────┘
```

Properties: nothing runs unattended except free non-LLM jobs; every stage idempotent; a failed
week means "no digest Monday," never corruption; everything re-runnable via `make` or `/digest`.

## 2. Technology stack and rationale

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 + `uv` | Readable, best data-pipeline ecosystem, Claude Code excels at it |
| Automation (non-LLM) | GitHub Actions scheduled workflows | $0 within private-repo free minutes; logs, retries, secrets, failure emails built in; no VPS |
| LLM runtime | **Interactive Claude Code session on Claude Pro** via a custom `/digest` slash command (`.claude/commands/digest.md`) | $0 marginal cost; within subscription terms because a human initiates and supervises; preview-before-send for free |
| LLM upgrade path | Anthropic API (documented, not wired by default) | If hands-off automation is ever wanted: ~$6–16/mo, Batch API for triage; switching = config change |
| Database | Supabase Postgres (free tier) | Real Postgres, pgvector available for V2, dashboard for inspection, Edge Functions |
| DB access | `psycopg` + plain SQL files | No ORM at this scale; SQL is more readable and Claude-Code-friendly |
| Migrations | `dbmate` | Plain, ordered SQL migrations |
| Full-text enrichment | Unpaywall REST API (by DOI) + NCBI ELink (PMC) | Lawful open-access links only; both free |
| Email | Resend free tier (100/day) | 4–5 emails/month; trivially replaced by SMTP |
| Feedback endpoint | Supabase Edge Function (~60 lines TS) | The only "server"; free tier |
| Rendering | Jinja2 template | One file in git |
| Config | YAML in `config/` | Sources, filters, caps, budget knobs — editable without code |

Deliberately excluded: Docker, queues, vector DB service, LLM frameworks, ORMs, Terraform,
API keys (V1 has none for Anthropic — this is enforced in CLAUDE.md).

## 3. Pre-filter design (the free triage that protects your subscription limits)

Weekly volume from a ~25-journal allowlist plus topic queries is roughly 300–800 items. Feeding
all of that to an LLM would strain a Pro session. Deterministic, free rules cut it first:

1. **Journal Tier A** (your trusted list) → always passes to LLM triage.
2. **Tier B** (all other journals, incl. surgical literature) → passes only if it matches a
   standing-question/topic keyword set from `config/filters.yaml`.
3. **Hard drops:** item types (errata, letters unless linked to a flagged trial), retrospective
   n<30 (per your rubric), animal/bench unless keyword-tied to a standing question.
4. Everything dropped is still stored and marked `prefiltered_out` — recoverable, auditable,
   and re-scorable later.

Expected LLM-triage volume after pre-filter: ~100–300 items/week, scored in batches of ~25 per
call with compressed metadata. Comfortably one Pro session; if limits ever pinch, the knobs are
in config (tighter keywords, smaller Tier B), not in code.

## 4. Database schema

Same as v1 with three additions (full schema in `db/migrations/`):

```sql
-- items: add lawful open-access link + pre-filter audit
ALTER TABLE items ADD COLUMN oa_url text;            -- Unpaywall/PMC link if one exists
ALTER TABLE items ADD COLUMN oa_source text;         -- 'unpaywall' | 'pmc' | null
ALTER TABLE items ADD COLUMN prefilter text;         -- 'passed' | rule that dropped it

-- scores.model now records e.g. 'claude-code-session/<model>' vs API model strings
```

Core tables unchanged: `sources`, `items`, `scores` (append-only, `is_current` flag,
model+prompt+profile versions on every row), `digests`, `digest_items`, `feedback`,
`eval_labels`.

## 5. AI architecture (subscription edition)

**One session, two phases, same principles as before:**

- **Phase 1 — Triage** (`prompts/triage-vN.md`): batches of pre-filtered items → strict JSON
  tiers. Instructed to be *inclusive* (torn between noise and FYI → FYI); nothing recovers a
  false noise. Within the session, triage should run on a mid-tier model to conserve limits.
- **Phase 2 — Synthesis** (`prompts/synthesis-vN.md`): the ~20–40 surviving items → per-item
  2–4 sentence synthesis written against your Practice Profile with an *academic-appointment
  voice*: how it relates to landmark trials, what a journal club would ask, guideline context.
  Use the strongest available model here (Opus-class or Fable when offered in Claude Code);
  this is where reasoning quality shows.

**Five-year rules (unchanged and still the point):** model names only in `config/models.yaml`
(here: which model the session should select per phase); prompts as versioned files with
changelog headers; every score row traceable; `make eval` mandatory before merging prompt/
profile changes; re-score backlog when a better model ships. The eval harness runs inside a
Claude Code session too — also $0.

## 6. Cost model

| Component | Monthly |
|---|---|
| GitHub Actions, Supabase, Resend, Unpaywall/NCBI | $0 (free tiers / public APIs) |
| LLM triage + synthesis + eval | $0 marginal (Claude Pro subscription, interactive sessions) |
| **Total incremental** | **$0** |

Real cost: ~15 min of your Monday and a slice of your weekly Pro usage allowance (shared with
your claude.ai chatting). If a Monday session ever hits limits, options in order: run later in
the day, tighten pre-filters, or adopt the API upgrade path.

## 7. Deployment & operations

- Private GitHub repo. Secrets (Supabase, Resend, HMAC) in Actions secrets. **No
  ANTHROPIC_API_KEY anywhere** — its presence would silently divert Claude Code to paid API
  billing, so CLAUDE.md forbids it and `make doctor` checks for it.
- Workflows: `daily.yml` (ingest→prefilter→enrich), `eval-fixtures.yml` (manual), `ci.yml`
  (tests). The weekly LLM step is *not* a workflow — it's your `/digest` session.
- Local setup: `uv sync`, `.env`, `make ingest --dry-run`, `claude` → `/digest --dry-run`
  (renders HTML locally, sends nothing).
- Backups: weekly `pg_dump` as an Actions artifact.

## 8. Testing strategy

1. **pytest** on deterministic logic: parsers, dedupe, pre-filter rules, HMAC, template
   rendering, caps enforcement. Runs in CI on every push.
2. **`make eval`** (run inside a Claude Code session): agreement vs `eval_labels` —
   practice-changing recall (primary), tier agreement, confusion matrix. Mandatory before
   merging changes to prompts, filters, or PRACTICE_PROFILE.md; report pasted into the PR.
3. **Dry-run golden test:** `/digest --dry-run` against a fixture week; diff the rendered HTML.

## 9. Scalability path

Unchanged: multi-user = users table + Supabase Auth (schema anticipates it); V2 web archive =
read-only Next.js on Vercel free tier; V2 semantic layer = pgvector; deep-dive automation and
conference manual-assist as described in the roadmap. The API upgrade path converts the weekly
session into a scheduled job with zero code restructuring — the session and the job call the
same Python entry points.
