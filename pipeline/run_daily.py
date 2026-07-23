"""The single daily entry point: ingest -> normalize/dedupe -> pre-filter -> (store).

The --to-file store target is implemented in M1 Step 3, ahead of the DB path, because
DATABASE_URL is not yet resolvable inside Claude Code cloud sessions (see
docs/decisions/log.md). --to-file writes to the accumulating data/untriaged.jsonl file
that the interim /digest reads directly, so a working database is NOT required.

Lookback window (docs/decisions/0002): default is wide (config/sources.yaml
pubmed.lookback_days_default) to absorb real per-journal weekly publication variance
and PubMed pdat/edat quirks discovered auditing Step 3 — rather than assume a narrow
calendar window, cast a wide net and rely on the persistent seen-ledger
(pipeline/seen_store.py) to avoid re-processing the same item on every run.

Store targets:
  --to-file           default target: APPEND newly-seen, pre-filtered items to the
                      tracked data/untriaged.jsonl. Cross-run dedupe via
                      pipeline/seen_store.py — safe to run daily with an overlapping
                      window; only genuinely new items get appended.
  --to-file PATH      untracked one-off: OVERWRITE PATH with a fresh snapshot of
                      everything in the window, bypassing the seen-ledger entirely.
                      For ad hoc exports/audits/backfills, not routine ingestion.
  --to-db             upsert into Postgres. Wired in M1 Step 5; raises until then.

Other flags:
  --days N            lookback window (overrides the config default).
  --since YYYY-MM-DD  explicit start date (overrides --days).
  --dry-run           fetch + filter, report counts, mutate nothing (no file, no ledger).
  --reset-seen        forget all previously-seen items before running (forces a full
                      re-surface of the current window) — an escape hatch for e.g.
                      after materially changing config/filters.yaml.

This is the ONE orchestrator that GitHub Actions, local runs, backfill, and the future
API path all call, so the upgrade path stays a config change, not a rewrite (docs/02 §9).
Enrichment (oa_url/oa_source via pipeline/enrich.py, Step 4) runs on passed items only,
right before compress(); it's skipped on --dry-run (see run(), below) to avoid spending
Unpaywall/NCBI lookups on a preview that writes nothing.

Usage: uv run python -m pipeline.run_daily [--to-file [PATH]] [--days N] [--dry-run]
"""

import argparse
import datetime
import json
from pathlib import Path

import yaml

from llm.batching import compress
from pipeline import enrich, normalize, prefilter, seen_store
from pipeline.ingest import pubmed

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
FILTERS_PATH = REPO_ROOT / "config" / "filters.yaml"

UNTRIAGED_PATH = DEFAULT_DATA_DIR / "untriaged.jsonl"
SEEN_PATH = DEFAULT_DATA_DIR / ".seen_ids.json"


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="pipeline.run_daily")
    p.add_argument(
        "--to-file", nargs="?", const="__default__", metavar="PATH",
        help="no PATH: append new-since-last-run items to the tracked "
             "data/untriaged.jsonl (default target). With PATH: write a fresh, "
             "untracked one-off snapshot instead.",
    )
    p.add_argument("--to-db", action="store_true", help="upsert into Postgres (Step 5)")
    p.add_argument("--days", type=int, help="lookback window in days (default: "
                   "config/sources.yaml pubmed.lookback_days_default)")
    p.add_argument("--since", help="explicit start date YYYY-MM-DD (overrides --days)")
    p.add_argument("--dry-run", action="store_true", help="fetch + filter, mutate nothing")
    p.add_argument("--reset-seen", action="store_true",
                   help="forget all previously-seen items before running")
    return p.parse_args(argv)


def _since_date(args, pubmed_cfg) -> datetime.date:
    if args.since:
        return datetime.date.fromisoformat(args.since)
    days = args.days if args.days is not None else pubmed_cfg.get("lookback_days_default", 7)
    return datetime.date.today() - datetime.timedelta(days=days)


def _write_jsonl(path: Path, compressed_items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in compressed_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, compressed_items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for item in compressed_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def run(args) -> dict:
    """Execute the pipeline; return a summary dict. Pure of argument parsing."""
    pubmed_cfg = pubmed.load_sources_config()["pubmed"]
    since = _since_date(args, pubmed_cfg)
    raw_items = pubmed.fetch(since)                          # network (not run in tests)
    rows = normalize.normalize(raw_items)                    # canonical + in-run dedupe
    filters_cfg = yaml.safe_load(FILTERS_PATH.read_text())

    is_default_target = args.to_file in (None, "__default__")

    updated_seen = None
    if is_default_target:
        seen = {} if args.reset_seen else seen_store.load(SEEN_PATH)
        rows_to_classify, updated_seen = seen_store.filter_unseen(
            rows, seen, datetime.date.today().isoformat()
        )
    else:
        rows_to_classify = rows

    rows_to_classify = prefilter.apply(rows_to_classify, filters_cfg)
    passed = [r for r in rows_to_classify if r["prefilter"] == "passed"]
    dropped = len(rows_to_classify) - len(passed)
    # Enrich only passed items (saves API calls) with lawful OA links, before
    # compress() so oa_url is available to include. Skipped on --dry-run: a dry
    # run is for previewing counts, not for spending Unpaywall/NCBI rate-limit
    # budget on items that won't be written anywhere.
    if not args.dry_run:
        enrich.enrich(passed)
    compressed = [compress(r) for r in passed]

    summary = {
        "since": since.isoformat(),
        "fetched": len(raw_items),
        "deduped": len(rows),
        "new_since_last_run": len(rows_to_classify) if is_default_target else None,
        "dropped": dropped,
        "passed": len(passed),
        "wrote_file": None,
    }

    want_file = args.to_file is not None or not args.to_db
    if args.dry_run:
        return summary
    if want_file:
        if is_default_target:
            _append_jsonl(UNTRIAGED_PATH, compressed)
            seen_store.save(SEEN_PATH, updated_seen)
            summary["wrote_file"] = str(UNTRIAGED_PATH)
        else:
            path = Path(args.to_file)
            _write_jsonl(path, compressed)
            summary["wrote_file"] = str(path)
    if args.to_db:
        raise NotImplementedError("--to-db is wired in M1 Step 5 (DB upsert).")
    return summary


def main(argv=None) -> None:
    args = _parse_args(argv)
    summary = run(args)
    verb = "would surface" if args.dry_run else "surfaced"
    new_note = (f", {summary['new_since_last_run']} new-since-last-run"
                if summary["new_since_last_run"] is not None else "")
    print(
        f"[run_daily] since {summary['since']}: fetched {summary['fetched']}, "
        f"deduped {summary['deduped']}{new_note}, dropped {summary['dropped']}, "
        f"{verb} {summary['passed']}."
    )
    if summary["wrote_file"]:
        mode = "appended to" if args.to_file in (None, "__default__") else "wrote"
        print(f"[run_daily] {mode} {summary['passed']} items -> {summary['wrote_file']}")


if __name__ == "__main__":
    main()
