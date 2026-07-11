"""The single daily entry point: ingest → normalize/dedupe → pre-filter → enrich.

STUB — wired for real in M1 Step 5 (daily.yml). Modules it calls land in Steps 3–4.

Design decided now:
- This is the ONE orchestrator that GitHub Actions, local dry-runs (`make ingest`),
  the 90-day backfill (`make backfill DAYS=90`), and any future API-billed automation
  all call — so the upgrade path stays a config change, not a rewrite (docs/02 §9).
- Per-source error isolation: one failed source is logged and recorded for the digest
  health footer; the rest of the pipeline continues (PRD FR-1).
- Supports --dry-run (fetch and report counts, write nothing) and --since YYYY-MM-DD
  (backfill window).

Usage (from Step 5): uv run python -m pipeline.run_daily [--dry-run] [--since DATE]
"""


def main() -> None:
    raise NotImplementedError("Wired in M1 Step 5 (daily workflow + backfill).")


if __name__ == "__main__":
    main()
