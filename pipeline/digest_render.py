"""M3 deterministic render layer: turns triaged + synthesized items into the weekly
digest HTML.

DB-optional — this module reads the interim JSONL files (compressed items, scores,
synthesis) directly, the same way the rest of the interim pipeline does while
DATABASE_URL is unresolved (ADR 0001). No LLM call happens here: triage
(llm/scores.py) and synthesis (prompts/synthesis-v1.md, run inside a Claude Code
/digest session) have already produced their JSON by the time this module runs.
This module only merges, caps/demotes, and renders — pure logic, thin I/O edges,
mirroring the split in pipeline/enrich.py.
"""

import argparse
import datetime
import json
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from llm.scores import load_current_scores

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"
DATA_DIR = REPO_ROOT / "data"

PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
_MONTHS_FULL = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

TIER_LABELS = {
    "practice_changing": "Practice-changing",
    "worth_knowing": "Worth knowing",
    "fyi": "FYI",
}
TIER_ORDER = ("practice_changing", "worth_knowing", "fyi")

_GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


# ---- pure: formatting ----------------------------------------------------------

def format_date(iso_or_none):
    """"2026-07-06" -> "Jul 6". None -> "". Unparseable input passes through as-is."""
    if iso_or_none is None:
        return ""
    parts = iso_or_none.split("-")
    if len(parts) != 3:
        return iso_or_none
    year, month, day = parts
    try:
        month_i = int(month)
        day_i = int(day)
        int(year)
    except ValueError:
        return iso_or_none
    if not (1 <= month_i <= 12):
        return iso_or_none
    return f"{_MONTHS[month_i - 1]} {day_i}"


def _design_line_fallback(item):
    design = item.get("design")
    n = item.get("n")
    if design and n is not None:
        return f"{design.upper() if len(design) <= 3 else design.capitalize()}, n={n}"
    if design:
        return design.upper() if len(design) <= 3 else design.capitalize()
    return ""


# ---- pure: merge -----------------------------------------------------------------

def merge_item(item, score, synth):
    """Merge one compressed item + its triage score + its (optional) synthesis into
    the flat record the template/caps logic works with. Does NOT set full_writeup —
    that's decided per-tier by apply_caps once caps/demotion are known.
    """
    pmid = item.get("pmid")
    synth = synth or {}
    return {
        "pmid": pmid,
        "title": item.get("title"),
        "journal": item.get("journal"),
        "url": PUBMED_URL.format(pmid=pmid) if pmid else item.get("url"),
        "oa_url": item.get("oa_url") or None,
        "date": format_date(item.get("date")),
        # Kept alongside the display "date" so apply_caps can order by recency
        # without re-parsing the "Mon D" display string (which has no year and
        # doesn't sort chronologically as text). Not part of the template contract.
        "_date_iso": item.get("date") or "",
        "tier": score["relevance_tier"],
        "evidence_level": score["evidence_level"],
        "grade_label": synth.get("grade_label", ""),
        "design_line": synth.get("design_line") or _design_line_fallback(item),
        "one_line_takeaway": score.get("one_line_takeaway"),
        "summary": synth.get("summary"),
        "conclusion": synth.get("conclusion"),
        "practice_impact": synth.get("practice_impact"),
        "field_impact": synth.get("field_impact"),
        "future_considerations": synth.get("future_considerations"),
    }


# ---- pure: caps / demotion -------------------------------------------------------

def _sort_by_strength(records):
    """Sort strongest-first: primary key = evidence grade (A>B>C>D), secondary =
    the record's ORIGINAL triage tier weight (practice_changing=0, worth_knowing=1,
    fyi=2) — so, at a tied grade, an item the triage step originally judged
    practice-changing outranks one it originally judged only worth-knowing, even
    after the first item gets demoted into the same pool — tertiary = date desc
    (newer first). `record["tier"]` always holds the ORIGINAL triage tier (merge_item
    sets it once and apply_caps never mutates it, even across demotions), so this
    reads that directly rather than needing a separate parameter.

    Implemented as three stable passes, least-significant key first — the simplest
    way to get mixed ascending/descending multi-key ordering out of Python's stable
    sort without a hand-rolled comparator.
    """
    by_date_desc = sorted(records, key=lambda r: r.get("_date_iso", ""), reverse=True)
    by_tier_weight = sorted(by_date_desc, key=lambda r: TIER_ORDER.index(r["tier"]))
    return sorted(by_tier_weight, key=lambda r: _GRADE_RANK.get(r["evidence_level"], 4))


def apply_caps(records, caps, fyi_writeup):
    """Group records by tier and enforce caps by DEMOTION, never expansion.

    Sort each tier's items by display strength descending (grade A>B>C>D primary,
    tier weight secondary, insertion/date order tertiary) so the strongest survive.
    practice_changing overflow (beyond caps['practice_changing']) demotes into
    worth_knowing; worth_knowing overflow (after demotions) demotes into fyi; fyi
    overflow (after demotions) is trimmed out of the digest entirely — fyi is the
    floor, there is no lower tier.

    full_writeup is set per surviving record: True for practice_changing/worth_knowing
    always; for fyi, True iff fyi_writeup == "full", else False.

    Returns a list of tier dicts (practice_changing, worth_knowing, fyi order), each
    {label, key, count, items}.
    """
    by_tier = {key: [] for key in TIER_ORDER}
    for record in records:
        if record["tier"] in by_tier:
            by_tier[record["tier"]].append(record)

    pc = _sort_by_strength(by_tier["practice_changing"])
    wk = _sort_by_strength(by_tier["worth_knowing"])
    fyi = _sort_by_strength(by_tier["fyi"])

    # practice_changing -> worth_knowing demotion.
    pc_cap = caps.get("practice_changing", len(pc))
    if len(pc) > pc_cap:
        overflow = pc[pc_cap:]
        pc = pc[:pc_cap]
        wk = _sort_by_strength(wk + overflow)

    # worth_knowing -> fyi demotion.
    wk_cap = caps.get("worth_knowing", len(wk))
    if len(wk) > wk_cap:
        overflow = wk[wk_cap:]
        wk = wk[:wk_cap]
        fyi = _sort_by_strength(fyi + overflow)

    # fyi trim (floor — no lower tier to demote into).
    fyi_cap = caps.get("fyi", len(fyi))
    if len(fyi) > fyi_cap:
        fyi = fyi[:fyi_cap]

    for record in pc:
        record["full_writeup"] = True
    for record in wk:
        record["full_writeup"] = True
    for record in fyi:
        record["full_writeup"] = fyi_writeup == "full"

    grouped = {"practice_changing": pc, "worth_knowing": wk, "fyi": fyi}
    return [
        {
            "key": key,
            "label": TIER_LABELS[key],
            "count": len(grouped[key]),
            "items": grouped[key],
        }
        for key in TIER_ORDER
    ]


# ---- pure: context assembly ------------------------------------------------------

def build_context(
    records,
    caps,
    fyi_writeup,
    *,
    digest_date,
    screened_count,
    window_label="21-day window",
    practice_label="Private practice · general OR, ortho/regional",
    week_in_brief=None,
    sources_line="Sources OK: PubMed.",
    build_note=None,
):
    """Run apply_caps and assemble the full render context for digest.html.j2."""
    tiers = apply_caps(records, caps, fyi_writeup)

    surfaced_count = sum(t["count"] for t in tiers)
    oa_count = sum(1 for t in tiers for item in t["items"] if item.get("oa_url"))
    surfaced_pct = "0.0" if not screened_count else f"{surfaced_count / screened_count * 100:.1f}"

    return {
        "digest_date": digest_date,
        "window_label": window_label,
        "practice_label": practice_label,
        "week_in_brief": week_in_brief,
        "tiers": tiers,
        "screened_count": screened_count,
        "surfaced_count": surfaced_count,
        "surfaced_pct": surfaced_pct,
        "oa_count": oa_count,
        "sources_line": sources_line,
        "build_note": build_note,
    }


# ---- I/O edges --------------------------------------------------------------------

def render_html(context, template_dir=REPO_ROOT / "templates"):
    """Render digest.html.j2 with `context`. The only Jinja2 touchpoint."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("digest.html.j2")
    return template.render(**context)


def write_digest(html, path):
    """Write `html` to `path`, creating parent dirs as needed. Returns the Path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _load_current_by_pmid(path):
    """Latest-line-per-pmid loader for a JSONL file keyed by "pmid" — the synthesis
    file analogue of llm.scores.load_current_scores (same append-only file shape).
    """
    path = Path(path)
    current: dict[str, dict] = {}
    if not path.exists():
        return current
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            pmid = rec.get("pmid")
            if pmid is not None:
                current[str(pmid)] = rec
    return current


def _load_items(path):
    path = Path(path)
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def build_from_files(
    items_path,
    scores_path,
    synth_path,
    *,
    out_path,
    digest_date,
    screened_count=None,
    week_in_brief=None,
):
    """Orchestrate the full render from the interim JSONL files.

    Reads compressed items (`items_path`), current scores (`scores_path`, via
    llm.scores.load_current_scores), and current synthesis (`synth_path`, latest-
    per-pmid). Only includes items with a score whose tier is not "noise". Caps and
    digest.fyi_writeup come from config/settings.yaml. Writes the rendered HTML to
    `out_path` and returns that Path.
    """
    items = _load_items(items_path)
    scores = load_current_scores(scores_path)
    synths = _load_current_by_pmid(synth_path)

    if screened_count is None:
        screened_count = len(items)

    records = []
    for item in items:
        pmid = str(item.get("pmid"))
        score = scores.get(pmid)
        if score is None or score["relevance_tier"] == "noise":
            continue
        records.append(merge_item(item, score, synths.get(pmid)))

    settings = yaml.safe_load(SETTINGS_PATH.read_text())
    digest_cfg = settings.get("digest", {})
    caps = digest_cfg.get("caps", {})
    fyi_writeup = digest_cfg.get("fyi_writeup", "full")

    context = build_context(
        records,
        caps,
        fyi_writeup,
        digest_date=digest_date,
        screened_count=screened_count,
        week_in_brief=week_in_brief,
    )
    html = render_html(context)
    return write_digest(html, out_path)


# ---- CLI ------------------------------------------------------------------------

def _default_display_date(today=None):
    """Today as a display string like 'July 24, 2026' (no leading zero on the day)."""
    today = today or datetime.date.today()
    return f"{_MONTHS_FULL[today.month - 1]} {today.day}, {today.year}"


def main(argv=None):
    """Render the weekly digest from the interim files in one command.

    The /digest session produces `data/scores.jsonl` (triage) and
    `data/synthesis.jsonl` (synthesis) from `data/untriaged.jsonl`, then calls this to
    write the HTML — the last, deterministic step. All paths default to the interim
    locations so `python -m pipeline.digest_render` just works inside a session.
    """
    parser = argparse.ArgumentParser(
        prog="pipeline.digest_render",
        description="Render the weekly digest HTML from the interim triage + synthesis files.",
    )
    parser.add_argument("--items", default=str(DATA_DIR / "untriaged.jsonl"))
    parser.add_argument("--scores", default=str(DATA_DIR / "scores.jsonl"))
    parser.add_argument("--synthesis", default=str(DATA_DIR / "synthesis.jsonl"))
    parser.add_argument("--out", default=None,
                        help="output HTML path (default: data/digest-<today>.html)")
    parser.add_argument("--date", default=None,
                        help="display date on the masthead (default: today, e.g. 'July 24, 2026')")
    parser.add_argument("--screened", type=int, default=None,
                        help="total items screened for the footer (default: lines in --items)")
    parser.add_argument("--brief", default=None, help="optional 'week in brief' masthead blurb")
    args = parser.parse_args(argv)

    out_path = args.out or str(DATA_DIR / f"digest-{datetime.date.today().isoformat()}.html")
    path = build_from_files(
        args.items, args.scores, args.synthesis,
        out_path=out_path,
        digest_date=args.date or _default_display_date(),
        screened_count=args.screened,
        week_in_brief=args.brief,
    )
    print(f"[digest_render] wrote {path}")
    return path


if __name__ == "__main__":
    main()
