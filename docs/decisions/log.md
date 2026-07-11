STATE OF THE WORLD log

## 2026-07-11 — M1 Step 1: repository scaffold
The full repo skeleton exists per docs/04 (plus config/filters.yaml, which docs/02 §3
requires but the docs/04 tree omitted): all pipeline/llm/evalset modules are documented
stubs stating which step implements them, /digest is a phase-by-phase skeleton in
.claude/commands/digest.md, and `make doctor`/`make test` are real (doctor fails if an
ANTHROPIC_API_KEY is ever set). The weekly.yml/eval.yml workflows from the docs/04 tree
were deliberately not created — docs/02 §7 says the weekly step is the interactive
/digest session and eval runs in-session; daily.yml exists with its cron commented out
until Step 5. Next: Step 2 — dbmate migrations for the docs/02 §4 schema, run against
the founder's Supabase project.

## 2026-07-11 — M1 Step 2: database schema (dbmate migrations)
7 numbered dbmate migrations in db/migrations/ create sources, items, digests, scores,
digest_items, feedback, eval_labels — reconstructed from the PRD (FR-1 through FR-6) and
docs/02 §5, since docs/02 §4 only documents three ALTER-TABLE additions (oa_url,
oa_source, prefilter) against a "v1" schema that has no standalone doc in this repo;
those three columns are folded into `items` from the start. Notable choices: items
dedupes on UNIQUE(source_id, external_id) so re-running any day is idempotent by
construction; scores is append-only with a partial UNIQUE index enforcing exactly one
is_current row per item; sources carries last_success_at/last_error for the digest's
pipeline-health footer; nothing is ever deleted, only marked (items.prefilter). Verified
by applying, rolling back, and re-applying all 7 migrations against a local Postgres 16
instance (inserted one realistic row per table; confirmed the one-current-score
constraint rejects a duplicate). `make migrate` is now real: it installs dbmate via
`go install` if missing (tested against a clean PATH) and applies db/migrations to
$DATABASE_URL. db/schema.sql is the committed, verified snapshot. Founder walked through
running `make migrate` against Supabase from a Claude Code cloud session. Next: Step 3 —
pipeline/ingest/pubmed.py against config/sources.yaml, with fixture-based pytest tests.
