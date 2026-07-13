"""The single daily entry point: ingest -> normalize/dedupe -> pre-filter -> (store).

The --to-file store target is implemented in M1 Step 3, ahead of the DB path, because
DATABASE_URL is not yet resolvable inside Claude Code cloud sessions (see
docs/decisions/log.md). --to-file writes the pre-filtered, compressed items to a JSONL
file that the interim /digest can read directly, so a working database is NOT required.

Store targets (choose any combination; --to-file alone is sufficient):
  --to-file [PATH]   write JSONL (default data/week-YYYY-MM-DD.jsonl). Default target
                     when no target is given, since the DB path isn't wired yet.
  --to-db            upsert into Postgres. Wired in M1 Step 5; raises until then.

Other flags:
  --days N           lookback window (default 7). --since YYYY-MM-DD overrides it.
  --dry-run          fetch + filter, report counts, write nothing.

This is the ONE orchestrator that GitHub Actions, local runs, backfill, and the future
API path all call, so the upgrade path stays a config change, not a rewrite (docs/02 §9).
Enrichment (oa_url) lands in Step 4; until then that field is present-but-null.

Usage: uv run python -m pipeline.run_daily --to-file [--days 7] [--dry-run]
"""

import argparse
import datetime
import json
from pathlib import Path

import yaml

from llm.batching import compress
from pipeline import normalize, prefilter
from pipeline.ingest import pubmed

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
FILTERS_PATH = REPO_ROOT / "config" / "filters.yaml"


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="pipeline.run_daily")
    p.add_argument("--to-file", nargs="?", const="__default__", metavar="PATH",
                   help="write pre-filtered items as JSONL (default data/week-<today>.jsonl)")
    p.add_argument("--to-db", action="store_true", help="upsert into Postgres (Step 5)")
    p.add_argument("--days", type=int, default=7, help="lookback window in days (default 7)")
    p.add_argument("--since", help="explicit start date YYYY-MM-DD (overrides --days)")
    p.add_argument("--dry-run", action="store_true", help="fetch + filter, write nothing")
    return p.parse_args(argv)


def _since_date(args) -> datetime.date:
    if args.since:
        return datetime.date.fromisoformat(args.since)
    return datetime.date.today() - datetime.timedelta(days=args.days)


def _default_file_path() -> Path:
    return DEFAULT_DATA_DIR / f"week-{datetime.date.today().isoformat()}.jsonl"


def _write_jsonl(path: Path, compressed_items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in compressed_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def run(args) -> dict:
    """Execute the pipeline; return a summary dict. Pure of argument parsing."""
    since = _since_date(args)
    raw_items = pubmed.fetch(since)                         # network (not run in tests)
    rows = normalize.normalize(raw_items)                  # canonical + dedupe
    filters_cfg = yaml.safe_load(FILTERS_PATH.read_text())
    rows = prefilter.apply(rows, filters_cfg)              # mark passed / drop:<rule>

    passed = [r for r in rows if r["prefilter"] == "passed"]
    dropped = len(rows) - len(passed)
    compressed = [compress(r) for r in passed]

    summary = {
        "since": since.isoformat(),
        "fetched": len(raw_items),
        "deduped": len(rows),
        "dropped": dropped,
        "passed": len(passed),
        "wrote_file": None,
    }

    # Default target: file (the DB path isn't wired, and must not be required).
    want_file = args.to_file is not None or not args.to_db
    if args.dry_run:
        return summary
    if want_file:
        path = (_default_file_path() if args.to_file in (None, "__default__")
                else Path(args.to_file))
        _write_jsonl(path, compressed)
        summary["wrote_file"] = str(path)
    if args.to_db:
        raise NotImplementedError("--to-db is wired in M1 Step 5 (DB upsert).")
    return summary


def main(argv=None) -> None:
    args = _parse_args(argv)
    summary = run(args)
    verb = "would surface" if args.dry_run else "surfaced"
    print(
        f"[run_daily] since {summary['since']}: fetched {summary['fetched']}, "
        f"deduped {summary['deduped']}, dropped {summary['dropped']}, "
        f"{verb} {summary['passed']}."
    )
    if summary["wrote_file"]:
        print(f"[run_daily] wrote {summary['passed']} items -> {summary['wrote_file']}")


if __name__ == "__main__":
    main()
