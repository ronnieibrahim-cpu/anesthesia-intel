"""The eval harness: how we measure before we trust (PRD FR-6).

Implemented in Milestone M2; runnable inside a Claude Code session via `make eval`
($0, no API key). It is a pure comparator — it does NOT call a model. The triage
session scores the eval items with the current `prompts/triage-vN.md` and writes them
to `evalset/predictions.jsonl` (via `llm/scores.write_scores_to_file`); this harness
then compares those predictions against the founder's hand labels and reports, in
order of importance (docs/02 §8):

    1. practice-changing RECALL   — missing a signal is worse than including noise,
    2. overall tier agreement,
    3. a confusion matrix.

Mandatory before merging any change to prompts, filters, or PRACTICE_PROFILE.md
(CLAUDE.md rule 5); the printed report goes in the PR description.

Inputs (both file-based, so no DATABASE_URL is needed — handoff §6):
    evalset/labels.csv        founder ground truth (pmid, ..., true_tier). A header-only
                              file means the labels don't exist yet — a FOUNDER task
                              (leftover M0); this harness never fabricates them.
    evalset/predictions.jsonl session-produced scores, latest line per pmid winning.

Usage: uv run python -m evalset.run_eval [--labels PATH] [--predictions PATH]
        (or: make eval)
"""

import argparse
import csv
import sys
from pathlib import Path

from llm.scores import VALID_TIERS, load_current_scores

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = REPO_ROOT / "evalset" / "labels.csv"
DEFAULT_PREDICTIONS = REPO_ROOT / "evalset" / "predictions.jsonl"

# The M2 gate (docs/03 roadmap; handoff §4). Reported, not enforced as a hard exit —
# the founder reads the numbers and decides "fix the profile or the prompt?".
GATE_PC_RECALL = 0.90
GATE_TIER_AGREEMENT = 0.80

PRACTICE_CHANGING = "practice_changing"


def load_labels(path):
    """Read labels.csv -> {pmid: true_tier}. Rows without a pmid or true_tier are skipped."""
    path = Path(path)
    labels: dict[str, str] = {}
    if not path.exists():
        return labels
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pmid = (row.get("pmid") or "").strip()
            tier = (row.get("true_tier") or "").strip()
            if not pmid or not tier:
                continue
            if tier not in VALID_TIERS:
                raise ValueError(
                    f"labels.csv: pmid {pmid} has true_tier {tier!r}; "
                    f"must be one of {VALID_TIERS}"
                )
            labels[pmid] = tier
    return labels


def _fmt_pct(numerator, denominator):
    if denominator == 0:
        return "  n/a"
    return f"{100.0 * numerator / denominator:5.1f}%"


def compute_metrics(labels, predictions):
    """Return a metrics dict from {pmid: true_tier} and {pmid: pred_tier}.

    A labeled item with no prediction counts as a MISS for recall (honest: an item the
    session never surfaced is an item the founder never saw). Tier agreement and the
    confusion matrix are computed over items that have both a label and a prediction;
    the unscored count is reported separately so partial runs are obvious.
    """
    pc_total = sum(1 for t in labels.values() if t == PRACTICE_CHANGING)
    pc_recalled = sum(
        1 for pmid, t in labels.items()
        if t == PRACTICE_CHANGING and predictions.get(pmid) == PRACTICE_CHANGING
    )

    scored_pmids = [p for p in labels if p in predictions]
    agree = sum(1 for p in scored_pmids if predictions[p] == labels[p])

    # Confusion matrix over scored items: matrix[true][pred].
    matrix = {t: {p: 0 for p in VALID_TIERS} for t in VALID_TIERS}
    for pmid in scored_pmids:
        matrix[labels[pmid]][predictions[pmid]] += 1

    return {
        "n_labeled": len(labels),
        "n_scored": len(scored_pmids),
        "n_unscored": len(labels) - len(scored_pmids),
        "n_predictions": len(predictions),
        "n_extra_predictions": len([p for p in predictions if p not in labels]),
        "pc_total": pc_total,
        "pc_recalled": pc_recalled,
        "pc_recall": (pc_recalled / pc_total) if pc_total else None,
        "agree": agree,
        "tier_agreement": (agree / len(scored_pmids)) if scored_pmids else None,
        "matrix": matrix,
    }


def format_report(m):
    """Render the metrics dict as the plain-text report that goes in the PR."""
    lines = []
    lines.append("=" * 66)
    lines.append("  EVAL REPORT — triage vs. founder hand labels (make eval)")
    lines.append("=" * 66)
    lines.append(f"  Labeled items:        {m['n_labeled']}")
    lines.append(f"  Scored (predicted):   {m['n_scored']}")
    if m["n_unscored"]:
        lines.append(f"  Unscored labels:      {m['n_unscored']}  "
                     "(counted as recall misses — score these in-session)")
    if m["n_extra_predictions"]:
        lines.append(f"  Predictions not in label set (ignored): {m['n_extra_predictions']}")
    lines.append("")

    lines.append("  1. Practice-changing RECALL (primary — do not miss signals)")
    if m["pc_total"] == 0:
        lines.append("       n/a — no practice_changing items in the label set")
    else:
        pass_recall = m["pc_recall"] >= GATE_PC_RECALL
        lines.append(f"       {_fmt_pct(m['pc_recalled'], m['pc_total'])}  "
                     f"({m['pc_recalled']}/{m['pc_total']})   "
                     f"gate ≥{GATE_PC_RECALL:.0%}  ->  "
                     f"{'PASS' if pass_recall else 'BELOW GATE'}")
    lines.append("")

    lines.append("  2. Overall tier agreement (of scored items)")
    if m["n_scored"] == 0:
        lines.append("       n/a — nothing scored yet")
    else:
        pass_agree = m["tier_agreement"] >= GATE_TIER_AGREEMENT
        lines.append(f"       {_fmt_pct(m['agree'], m['n_scored'])}  "
                     f"({m['agree']}/{m['n_scored']})   "
                     f"gate ≥{GATE_TIER_AGREEMENT:.0%}  ->  "
                     f"{'PASS' if pass_agree else 'BELOW GATE'}")
    lines.append("")

    lines.append("  3. Confusion matrix (rows = true, cols = predicted)")
    if m["n_scored"] == 0:
        lines.append("       n/a — nothing scored yet")
    else:
        abbr = {"practice_changing": "PC", "worth_knowing": "WK", "fyi": "FYI", "noise": "NOI"}
        header = "        " + "".join(f"{abbr[p]:>6}" for p in VALID_TIERS)
        lines.append(header + "   (pred)")
        for t in VALID_TIERS:
            cells = "".join(f"{m['matrix'][t][p]:>6}" for p in VALID_TIERS)
            lines.append(f"   {abbr[t]:>4} {cells}")
    lines.append("=" * 66)
    return "\n".join(lines)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="evalset.run_eval")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS))
    parser.add_argument("--predictions", default=str(DEFAULT_PREDICTIONS))
    args = parser.parse_args(argv)

    labels = load_labels(args.labels)
    if not labels:
        print(
            "No eval labels yet.\n"
            f"  {args.labels} is empty (header only).\n"
            "  This is a FOUNDER task (leftover M0): hand-label ~100-150 recent items\n"
            "  with a true_tier of practice_changing | worth_knowing | fyi | noise.\n"
            "  The harness never fabricates labels — the eval gate is blocked until\n"
            "  these exist (handoff §4.3).",
            file=sys.stderr,
        )
        return

    predictions_raw = load_current_scores(args.predictions)
    predictions = {pmid: rec.get("relevance_tier") for pmid, rec in predictions_raw.items()}
    if not predictions:
        print(
            "Labels present, but no predictions to score against.\n"
            f"  {args.predictions} is empty or missing.\n"
            "  Run the /digest triage phase over the eval items in an interactive\n"
            "  session first; it writes predictions there "
            "(llm.scores.write_scores_to_file).",
            file=sys.stderr,
        )
        return

    print(format_report(compute_metrics(labels, predictions)))


if __name__ == "__main__":
    main()
