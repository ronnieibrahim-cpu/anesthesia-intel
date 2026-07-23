# ADR 0003 — Tier-B keyword pre-filter (pulled forward from Step 4)

**Date:** 2026-07-13
**Status:** Accepted (with one open decision — see "Unresolved")

## Context
Auditing the 21-day corpus (ADR 0002), the founder found 1436/1814 (79%) of items
passing the pre-filter — far above the ~100-300/week docs/02 §3 targets. The Tier-B
standing-question keyword gate, the load-bearing precision filter, was still a Step 4
stub, so every item that matched a broad PubMed topic query passed. The founder
directed: build Tier-B keyword filtering first, before fda.py/rss.py/enrichment.

## Decision
1. **Reliable journal identity.** Added `journal_abbrev` (PubMed's `ISOAbbreviation`)
   through RawItem → normalize → canonical row. Tier A/B classification now matches on
   this stable NLM abbreviation, not the free-form full title (which varies:
   "Lancet (London, England)") — that formatting drift caused false zeros in the audit.
2. **Two-stage pre-filter** (pipeline/prefilter.py): hard-drops first, then a Tier A/B
   gate. Tier A journal (journal_abbrev in config) always passes; Tier B passes only if
   title+abstract matches a config/filters.yaml `tier_b_keyword` — word-boundary,
   case-insensitive regex (not naive substring: "mina" must not match "elimination").
3. **Keyword list** drawn 1:1 from PRACTICE_PROFILE.md §4-5 (standing questions +
   controversies), grouped by topic in config/filters.yaml for auditability.

Measured impact on the 21-day corpus: 79% → 62% pass rate (1436 → 817). 32 tests pass.

## Unresolved (founder decision, deliberately not made unilaterally)
817 is still above target. Diagnosis: **527 of the 817 passing items are from the eight
*general* medical journals** (JAMA alone: 186/21d), whose content is mostly non-
anesthesia — but PRACTICE_PROFILE.md §8 explicitly says Tier A "auto-pass … never
auto-noise," which includes those generals. Bringing volume to target means keyword-
gating the general journals too, which **contradicts §8 as written** and therefore
requires the founder to edit the profile. Options recorded for that decision:
(a) split Tier A — specialty journals auto-pass, general journals keyword-gated;
(b) keep §8 literal, rely on triage + digest caps;
(c) narrow the general-journal allowlist.
Not resolved here; the code supports (b) today and (a)/(c) with a config edit.

## Alternatives rejected
- **Naive substring keyword match** — false positives on short tokens (mina, txa,
  dasi). Word-boundary regex instead.
- **Match on full journal title** — formatting drift breaks it; ISOAbbreviation is stable.
