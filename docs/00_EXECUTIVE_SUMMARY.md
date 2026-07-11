# Anesthesia Intelligence — Executive Summary (v2, zero-marginal-cost architecture)

**One-line description:** A personal signal-extraction engine that gathers the anesthesiology-
adjacent literature automatically all week, then — in one short Monday Claude Code session on
your existing Claude Pro subscription — scores it against your written Practice Profile and
emails you a three-tier digest of what could change how you practice.

**Who it's for:** A private-practice anesthesiologist who wants the intellectual perks of an
academic appointment — grand-rounds-level currency, journal-club-ready framing, awareness of
landmark trials and guideline shifts — without the committee meetings.

## The core insight (unchanged)

Every future feature (journal club generator, board review, tutor, controversy tracker) is a
rendering layer on top of one asset: a pipeline that reliably separates practice-changing
evidence from noise, calibrated to one physician. V1 builds only that asset.

## What changed in v2: $0/month, by design

The original plan spent ~$6–16/month on Anthropic API calls. v2 eliminates that:

- **Everything that doesn't need an LLM is fully automated and free.** GitHub Actions ingests
  PubMed, FDA safety feeds, and society/guideline feeds daily into Supabase Postgres (free
  tier), applies free heuristic pre-filters (journal tiers, keyword rules, n-size floor), and
  enriches every item with a legal open-access full-text link where one exists (Unpaywall/
  PubMed Central).
- **Everything that does need an LLM happens inside your Claude Pro subscription,** as one
  interactive Claude Code session per week (~10–15 min, mostly unattended while you make
  coffee): you run `/digest`, Claude Code reads the week's pre-filtered items from the
  database, triages them against PRACTICE_PROFILE.md, writes the synthesis, shows you the
  rendered digest for a 60-second sanity check, and sends it via Resend (free tier).

Why interactive rather than a fully automated cron job: subscription plans cover human-in-the-
loop Claude Code sessions; fully autonomous/headless automation is treated differently under
Anthropic's terms and billing. Running the weekly step interactively keeps you cleanly inside
your $20/month plan — and as a bonus, you approve every digest before it sends. If you ever
want true hands-off automation, the documented upgrade path is an API key (~$6–16/month); the
code is written so that switch is a config change, not a rewrite.

**Total recurring cost: $0 beyond the Claude Pro subscription you already pay for.**

## Full-text access (revised for private practice)

No paywall bypassing — ever (see CLAUDE.md hard rules; Sci-Hub and similar are copyright-
infringing and are out). Instead the pipeline maximizes *legal* access automatically:
every item is checked against Unpaywall and PubMed Central by DOI/PMID, and the digest shows a
**"Free full text"** link whenever a lawful open-access version exists (a large share of recent
biomedical literature). For the rest: society memberships are the private-practice equivalent
of institutional access (ASA → *Anesthesiology*; IARS → *A&A*; ASRA → *RAPM*; ESAIC → *EJA*),
plus preprints and emailing corresponding authors, which works surprisingly often.

## Why this will work

1. **The digest comes to you** — email beats dashboards for retention.
2. **Relevance is defined in writing** — PRACTICE_PROFILE.md is the product's brain; when the
   digest is wrong you edit a document, not code.
3. **We measure before we trust** — a hand-labeled eval set gates every prompt/model change.
4. **Feedback from day one** — one-tap useful/not-relevant/knew-it/deep-dive links accumulate
   the training data for real personalization later.
5. **Human-in-the-loop is now a feature** — you see every digest before it sends, and the
   weekly session doubles as your deep-dive venue ("tell me more about item 3") at no cost.

## Sequence

| Milestone | Outcome | Target |
|---|---|---|
| M0 | Practice Profile + rubric + labeled eval set | Week 1–2 (founder time) |
| M1 | Automated ingestion + pre-filters + OA-link enrichment | Week 2–3 |
| M2 | `/digest` triage beating 80% agreement on eval set | Week 3–5 |
| M3 | First real Monday digest sent from a live session | Week 5–6 |
| M4 | Feedback loop + 4-week calibration | Week 6–10 |

## Regulatory posture (non-negotiable)

Education and awareness only. No patient data ever enters this system. No paywall
circumvention, no full-text scraping — metadata, abstracts, and lawful open-access links only.
