# ADR 0001 — JSONL file as interim triage input (DB-optional ingestion)

**Date:** 2026-07-13
**Status:** Accepted (interim; revisit when DATABASE_URL works in cloud sessions)

## Context
The Supabase schema is live, but `DATABASE_URL` does not yet resolve inside Claude Code
cloud sessions (network/allowlist; see docs/decisions/log.md), so the pipeline cannot
write to or read from Postgres there. The weekly `/digest` needs *some* source of
pre-filtered items to triage in the meantime.

## Decision
`pipeline/run_daily.py` gains a `--to-file` store target that writes the normalized,
pre-filtered, compressed items to `data/week-YYYY-MM-DD.jsonl`. The DB write is a separate
`--to-db` target and is **not required** — `--to-file` alone runs the full
ingest → normalize/dedupe → pre-filter chain with no database. The interim `/digest` reads
the JSONL directly. The file holds the same compressed shape the triage model will see
(pmid, title, journal, date, design, n, abstract, oa_url, doi — null fields omitted for
token efficiency); `llm/batching.compress()` is the single source of that shape.

To ship this now, the core of `normalize.py` and `prefilter.py` (both Step 4 modules) was
implemented ahead of schedule. This is additive, not throwaway — Step 4 completes them
(FDA/RSS ingesters, Unpaywall/PMC enrichment, DB-backed dedupe).

## Alternatives rejected
- **Block on fixing DATABASE_URL first** — couples progress to an unresolved
  infra/allowlist issue; the file path is useful regardless and de-risks Step 5.
- **Write full uncompressed rows to the file** — wastes triage-session tokens; the
  compressed shape is what triage consumes anyway.
- **Hard-drop retrospective n<floor at the pre-filter** — rejected on recall grounds:
  PRACTICE_PROFILE.md §6 makes that a *demotion to FYI at triage*, not a silent drop
  (missing a signal is worse than surfacing noise, PRD §9).

## Consequences
- `data/` is git-ignored (derived, regenerated daily).
- `oa_url` is present-but-null until enrichment lands in Step 4.
- Tier B standing-question keyword matching is still Step 4; the interim passed-set is
  legitimately pre-filtered because items already arrive via the Tier A allowlist or a
  topic query, plus hard-drops. Volume runs slightly above the ~100–300 target until that
  precision pass exists (observed: ~324 for a 7-day window).
- When the DB works: `--to-db` is wired (Step 5) and `/digest` switches back to reading
  Postgres; the file path remains as an offline/backfill convenience. Identical entry
  point either way (docs/02 §9).
