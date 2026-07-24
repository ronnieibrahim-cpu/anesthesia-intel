"""Tests for the M3 deterministic render layer (pipeline/digest_render.py).

Fixture-free — records are built inline as plain dicts. No network, no LLM calls
(synthesis/triage output is faked directly, per CLAUDE.md: never mock LLM prose,
just supply already-produced JSON-shaped dicts).
"""

from pipeline.digest_render import (
    apply_caps,
    build_context,
    format_date,
    merge_item,
    render_html,
)

CAPS = {"practice_changing": 5, "worth_knowing": 12, "fyi": 15}


def _score(pmid, tier="worth_knowing", grade="B", takeaway="A takeaway."):
    return {
        "pmid": pmid,
        "relevance_tier": tier,
        "evidence_level": grade,
        "one_line_takeaway": takeaway,
        "reasoning": "because reasons",
        "topics": ["regional"],
        "confidence": 0.8,
    }


def _synth(pmid, **overrides):
    base = {
        "pmid": pmid,
        "design_line": "RCT, n=90",
        "grade_label": "single RCT",
        "summary": "What was studied and found.",
        "practice_impact": "What it means for your practice.",
        "field_impact": "What it means for the field.",
        "future_considerations": "The caveat, last.",
    }
    base.update(overrides)
    return base


def _item(pmid, **overrides):
    base = {
        "pmid": pmid,
        "title": f"Title {pmid}",
        "journal": "Reg Anesth Pain Med",
        "date": "2026-07-06",
        "design": "rct",
        "n": 90,
    }
    base.update(overrides)
    return base


def _record(pmid, tier="worth_knowing", grade="B", date="2026-07-06", oa_url=None):
    """Build an already-merged record directly, for apply_caps/build_context tests."""
    item = _item(pmid, date=date, oa_url=oa_url)
    score = _score(pmid, tier=tier, grade=grade)
    synth = _synth(pmid)
    return merge_item(item, score, synth)


# ---- format_date -----------------------------------------------------------------

def test_format_date_iso_to_display():
    assert format_date("2026-07-06") == "Jul 6"


def test_format_date_none_is_empty():
    assert format_date(None) == ""


def test_format_date_garbage_passes_through():
    assert format_date("not-a-date") == "not-a-date"
    assert format_date("2026/07/06") == "2026/07/06"


# ---- merge_item -------------------------------------------------------------------

def test_merge_item_builds_pubmed_url_from_pmid():
    record = merge_item(_item("40000001"), _score("40000001"), None)
    assert record["url"] == "https://pubmed.ncbi.nlm.nih.gov/40000001/"


def test_merge_item_carries_synthesis_fields():
    record = merge_item(_item("40000001"), _score("40000001"), _synth("40000001"))
    assert record["summary"] == "What was studied and found."
    assert record["practice_impact"] == "What it means for your practice."
    assert record["field_impact"] == "What it means for the field."
    assert record["future_considerations"] == "The caveat, last."
    assert record["design_line"] == "RCT, n=90"
    assert record["grade_label"] == "single RCT"


def test_merge_item_oa_url_none_when_absent():
    record = merge_item(_item("40000001"), _score("40000001"), None)
    assert record["oa_url"] is None


def test_merge_item_oa_url_carried_when_present():
    item = _item("40000001", oa_url="https://example.org/pmc/40000001")
    record = merge_item(item, _score("40000001"), None)
    assert record["oa_url"] == "https://example.org/pmc/40000001"


def test_merge_item_design_line_fallback_when_no_synthesis():
    item = _item("40000001", design="rct", n=90)
    record = merge_item(item, _score("40000001"), None)
    assert record["design_line"] == "RCT, n=90"
    assert record["summary"] is None


def test_merge_item_design_line_fallback_no_n():
    item = _item("40000001", design="guideline", n=None)
    item.pop("n")
    record = merge_item(item, _score("40000001"), None)
    assert record["design_line"] == "Guideline"


# ---- apply_caps ---------------------------------------------------------------

def test_apply_caps_demotes_practice_changing_overflow():
    records = [_record(str(i), tier="practice_changing", grade="B") for i in range(6)]
    tiers = apply_caps(records, CAPS, "one_line")
    by_key = {t["key"]: t for t in tiers}
    assert by_key["practice_changing"]["count"] == 5
    assert by_key["worth_knowing"]["count"] == 1


def test_apply_caps_trims_fyi_overflow():
    records = [_record(str(i), tier="fyi", grade="C") for i in range(18)]
    tiers = apply_caps(records, CAPS, "one_line")
    by_key = {t["key"]: t for t in tiers}
    assert by_key["fyi"]["count"] == 15


def test_apply_caps_full_writeup_flags():
    records = [
        _record("1", tier="practice_changing", grade="A"),
        _record("2", tier="worth_knowing", grade="B"),
        _record("3", tier="fyi", grade="C"),
    ]
    tiers_full = {t["key"]: t for t in apply_caps(records, CAPS, "full")}
    assert all(item["full_writeup"] for tier in tiers_full.values() for item in tier["items"])

    tiers_one_line = {t["key"]: t for t in apply_caps(records, CAPS, "one_line")}
    assert tiers_one_line["practice_changing"]["items"][0]["full_writeup"] is True
    assert tiers_one_line["worth_knowing"]["items"][0]["full_writeup"] is True
    assert tiers_one_line["fyi"]["items"][0]["full_writeup"] is False


def test_apply_caps_display_order_grade_a_before_d():
    records = [
        _record("low", tier="worth_knowing", grade="D"),
        _record("high", tier="worth_knowing", grade="A"),
    ]
    tiers = {t["key"]: t for t in apply_caps(records, CAPS, "full")}
    items = tiers["worth_knowing"]["items"]
    assert [item["pmid"] for item in items] == ["high", "low"]


# ---- build_context ---------------------------------------------------------------

def test_build_context_counts_and_tier_order():
    records = [
        _record("1", tier="practice_changing", grade="A", oa_url="https://example.org/1"),
        _record("2", tier="worth_knowing", grade="B"),
        _record("3", tier="worth_knowing", grade="C"),
    ]
    ctx = build_context(records, CAPS, "full", digest_date="July 24, 2026", screened_count=100)
    assert ctx["surfaced_count"] == 3
    assert ctx["surfaced_pct"] == "3.0"
    assert ctx["oa_count"] == 1
    assert [t["key"] for t in ctx["tiers"]] == ["practice_changing", "worth_knowing", "fyi"]


def test_build_context_zero_screened_count_is_safe():
    ctx = build_context([], CAPS, "full", digest_date="July 24, 2026", screened_count=0)
    assert ctx["surfaced_pct"] == "0.0"


def test_build_context_empty_tier_still_present_with_zero_count():
    records = [_record("1", tier="practice_changing", grade="A")]
    ctx = build_context(records, CAPS, "full", digest_date="July 24, 2026", screened_count=10)
    fyi = next(t for t in ctx["tiers"] if t["key"] == "fyi")
    assert fyi["count"] == 0
    assert fyi["items"] == []


# ---- render_html ------------------------------------------------------------------

def _small_context(**overrides):
    records = [
        _record("40000001", tier="practice_changing", grade="A",
                 oa_url="https://example.org/pmc/40000001"),
        _record("40000002", tier="worth_knowing", grade="C"),
    ]
    ctx = build_context(
        records, CAPS, "full",
        digest_date="July 24, 2026", screened_count=100,
        week_in_brief="A quiet week.",
    )
    ctx.update(overrides)
    return ctx


def test_render_html_contains_masthead_and_tier_labels():
    html = render_html(_small_context())
    assert "July 24, 2026" in html
    assert "Practice-changing" in html
    assert "Worth knowing" in html
    # FYI has zero items in this fixture, so its section is skipped entirely.
    assert "<h2>FYI</h2>" not in html


def test_render_html_grade_chip_and_four_labels_and_ft_link():
    html = render_html(_small_context())
    assert 'g-A' in html
    assert "Summary" in html
    assert "Your practice" in html
    assert "Anesthesia broadly" in html
    assert "Looking ahead" in html
    assert "Free full text" in html
    assert 'href="https://example.org/pmc/40000001"' in html


def test_render_html_no_ft_link_when_oa_url_absent():
    records = [_record("40000009", tier="practice_changing", grade="B", oa_url=None)]
    ctx = build_context(records, CAPS, "full", digest_date="July 24, 2026", screened_count=10)
    html = render_html(ctx)
    assert "Free full text" not in html


def test_render_html_footer_ratio_string():
    html = render_html(_small_context())
    assert "100 items screened" in html
    assert "2 surfaced (2.0%)" in html


def test_render_html_dark_theme_css_present():
    html = render_html(_small_context())
    assert "prefers-color-scheme: dark" in html
