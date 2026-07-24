# Anesthesia Intelligence

A personal literature-triage pipeline that scores the week's anesthesiology-adjacent research against a physician's own practice profile and emails a three-tier digest — at $0 marginal cost beyond an existing Claude Pro subscription.

See `docs/07_START_HERE_SETUP_GUIDE.md` for setup and the weekly workflow, and `docs/06_PROMPTS_MANUAL_AND_KICKOFF.md` for the operating prompts. The four docs in `docs/` (00–04) are the project constitution; `PRACTICE_PROFILE.md` is the product's brain.

## Status

**Milestone M2 — triage layer built (gate pending founder labels):** the `/digest` triage
phase now has real parts — `prompts/triage-v1.md` (scores each pre-filtered item against
`PRACTICE_PROFILE.md` §7 into strict JSON: tier, A–D evidence grade, takeaway, reasoning,
topics, confidence), `llm/batching.make_batches()`, `llm/scores.py` (`validate()` +
append-only DB/file sinks), and `evalset/run_eval.py` wired to `make eval`
(practice-changing recall, tier agreement, confusion matrix). **The M2 gate can't run until
the founder hand-labels ~100–150 items into `evalset/labels.csv`** (a leftover-M0 task the
harness surfaces; it never fabricates labels). Synthesis + send (M3) are still to build.

**Next up — Milestone M3 (`/digest` synthesis + send):** see **`docs/08_HANDOFF_DIGEST.md`**
for the full handoff. The target output design is `templates/digest.sample.html` (a real
generated digest).

**Milestone M1, Step 3 complete:** PubMed ingester (`pipeline/ingest/pubmed.py`) driven by
`config/sources.yaml` (Tier A journal allowlist + standing-question topic queries), with
fixture-based tests and no live network calls. Plus an interim, DB-optional
`run_daily --to-file` path (`make ingest-file`) that appends pre-filtered, compressed
items to the accumulating `data/untriaged.jsonl` for `/digest` to read while
`DATABASE_URL` is unresolved (ADR 0001). Lookback window widened to 21 days by default,
with a cross-run seen-ledger so the overlap doesn't reprocess items (ADR 0002). Tier-B keyword pre-filtering (ADR 0003) and lawful open-access full-text enrichment (Unpaywall + PMC, `pipeline/enrich.py`) are implemented; the digest spec now requires a summary, an evidence grade (A-D), and a "Free full text" link per surfaced item. Next: Step 4 remainder — `fda.py`, `rss.py`, and DB-backed dedupe/persistence.

## Local development

```bash
uv sync          # install dependencies (installs Python 3.12 if needed)
make doctor      # sanity check — fails if an ANTHROPIC_API_KEY is present
make test        # run the test suite
make migrate     # apply db/migrations to $DATABASE_URL (installs dbmate if missing)
```

## Database

Schema lives in `db/migrations/` as plain, ordered dbmate SQL files; `db/schema.sql` is
the generated snapshot (do not hand-edit it — `make migrate` regenerates it). To change
the schema: add a new numbered migration file, never edit a merged one.

## Commands

| Command | What it does | Available |
|---|---|---|
| `make setup` | install dependencies | now |
| `make doctor` | environment + billing-guardrail check | now |
| `make test` | run tests | now |
| `make migrate` | apply database migrations | now |
| `make ingest-file` | ingest to `data/week-<today>.jsonl`, no DB (interim, ADR 0001) | now |
| `make ingest` | run one day's ingestion into the DB | Step 5 |
| `make backfill DAYS=90` | supervised historical backfill | Step 5 |
| `make eval` | compare triage predictions to founder labels (recall/agreement/confusion) | now (needs labels) |
| `/digest` (in Claude Code) | weekly triage → synthesis → preview → send | triage now; synthesis/send M3 |
| `make deep-dive PMID=…` | structured brief for one paper | M4 |

The weekly LLM work is deliberately **not** automated: `/digest` runs in an interactive
Claude Code session on the founder's Pro subscription, with preview-before-send. There is
no Anthropic API key anywhere in this project (CLAUDE.md rule 3).
