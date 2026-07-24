# ADR 0002 — Wide lookback window + cross-run seen-ledger, not edat

**Date:** 2026-07-13
**Status:** Accepted

## Context
Auditing the Step 3 pipeline's real 7-day output, the founder noticed several Tier A
journals (PRACTICE_PROFILE.md §8) surfaced far fewer items than their 90-day weekly
average — most strikingly Anesthesiology (1 vs ~15/week) and Critical Care Medicine
(1 vs ~12/week). The founder's hypothesis: `datetype=pdat` (publication date) windows
on a monthly journal's print-issue date, missing Online First content; `edat` (date
added to PubMed) should track real-world availability better.

## Test performed
Re-ran the same 7-day window with `datetype=edat` for the flagged journals
(Anesthesiology, BJA, A&A, Anaesthesia, RAPM, CCM), then widened to 30 days to check
for a timing/batching artifact:

| Journal | pdat/7d | edat/7d | edat/30d | pdat/30d |
|---|---:|---:|---:|---:|
| Anesthesiology | 1 | 0 | 18 | 58 |
| Reg Anesth Pain Med | 18 | 3 | 24 | 39 |
| Critical Care Medicine | 1 | 1 | 22 | 58 |

Aggregate, full combined query, 7-day window: 410 (pdat) vs 401 (edat) — no material
difference. **`edat` performed the same or worse everywhere tested; the hypothesis did
not hold.** Best available explanation (not independently confirmed against NCBI docs):
`edat` appears to freeze at first entry into PubMed (often as an ahead-of-print/
in-process record), while `pdat` can be *reassigned* to the current issue date when a
citation is finalized — the reverse of the proposed mechanism.

## Decision
Keep `datetype: pdat`. Instead:
1. Widen `config/sources.yaml` `pubmed.lookback_days_default` from 3 to **21 days** —
   absorbs real per-journal weekly variance (low-frequency journals legitimately show
   0-1 items some weeks; that's not a bug) without depending on a date-field switch
   that measurably doesn't help.
2. Raise `retmax` from 500 to **3000** — true match counts at 21/30-day windows (1828/
   2347) exceed the old cap and would have silently truncated results once widened.
3. Add `pipeline/seen_store.py`: a persistent, gitignored ledger
   (`data/.seen_ids.json`) recording every item's dedupe key once considered (passed
   or dropped), so a wide, deliberately overlapping window doesn't re-emit or
   re-process the same item on every run.
4. `run_daily.py`'s default `--to-file` target changes from a per-run dated snapshot
   (`data/week-YYYY-MM-DD.jsonl`, overwritten each run) to a single accumulating
   backlog file, **`data/untriaged.jsonl`** (appended, cross-run deduped) — the correct
   shape for "everything not yet triaged," independent of how often ingestion runs.
   Passing an explicit `--to-file PATH` still does an untracked, ledger-independent
   one-off overwrite, for ad hoc exports/audits/backfills (as used in the Step 3
   audit) — only the no-argument default target is ledger-tracked.

## Alternatives rejected
- **Switch to edat** — tested directly; performs the same or worse for the flagged
  journals and is a wash in aggregate. Rejected on evidence, not theory.
- **Keep the 7-day window and accept the shortfall** — conflicts with the founder's
  explicit "cast a wider net" instruction and the recall-first posture of PRD §9
  (missing a signal is worse than surfacing noise).

## Consequences
- First run after this change re-processes the full 21-day backlog (larger than
  before); subsequent runs are incremental deltas only.
- The seen-ledger is a temporary interim substitute for the `items` table's
  `UNIQUE(source_id, external_id)` constraint (ADR 0001) and retires once
  DATABASE_URL resolves and Step 4/5 land.
- Known limitation: once an item's dedupe key is in the ledger, it is never
  reconsidered — including if `config/filters.yaml` changes later. `--reset-seen`
  is the escape hatch (forces a full re-surface of the current window).
- `.claude/commands/digest.md`'s interim item-source note, the README, and the
  Makefile's `ingest-file` help text are updated to reference `data/untriaged.jsonl`
  instead of the old dated-filename convention.
