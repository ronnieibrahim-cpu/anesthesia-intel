# Anesthesia Intelligence

A personal literature-triage pipeline that scores the week's anesthesiology-adjacent research against a physician's own practice profile and emails a three-tier digest — at $0 marginal cost beyond an existing Claude Pro subscription.

See `docs/07_START_HERE_SETUP_GUIDE.md` for setup and the weekly workflow, and `docs/06_PROMPTS_MANUAL_AND_KICKOFF.md` for the operating prompts. The four docs in `docs/` (00–04) are the project constitution; `PRACTICE_PROFILE.md` is the product's brain.

## Status

**Milestone M1, Step 1 complete:** repository scaffold. All modules are documented stubs; each says which step implements it. Next: Step 2 — database migrations (dbmate) against Supabase.

## Local development

```bash
uv sync          # install dependencies (installs Python 3.12 if needed)
make doctor      # sanity check — fails if an ANTHROPIC_API_KEY is present
make test        # run the test suite
```

## Commands

| Command | What it does | Available |
|---|---|---|
| `make setup` | install dependencies | now |
| `make doctor` | environment + billing-guardrail check | now |
| `make test` | run tests | now |
| `make migrate` | apply database migrations | Step 2 |
| `make ingest` | run one day's ingestion locally | Step 5 |
| `make backfill DAYS=90` | supervised historical backfill | Step 5 |
| `make eval` | score the labeled eval set (run in a Claude Code session) | M2 |
| `/digest` (in Claude Code) | weekly triage → synthesis → preview → send | M2–M3 |
| `make deep-dive PMID=…` | structured brief for one paper | M4 |

The weekly LLM work is deliberately **not** automated: `/digest` runs in an interactive
Claude Code session on the founder's Pro subscription, with preview-before-send. There is
no Anthropic API key anywhere in this project (CLAUDE.md rule 3).
