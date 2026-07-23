# Product Requirements Document (PRD)

**Product:** Anesthesia Intelligence (working name)
**Version:** 2.0 (weekly digest MVP, $0-marginal-cost architecture)
**User:** One private-practice anesthesiologist (the founder) who wants the product to function
as a stand-in for the intellectual perks of an academic appointment: grand-rounds currency,
journal-club-ready framing, landmark-trial context, and guideline awareness. Single-tenant by
design. The synthesis voice should be written *to an academically engaged clinician*, not a
casual reader.

---

## 1. Problem statement

More than a thousand potentially relevant papers, guidelines, and safety communications are
published every week across anesthesiology and its adjacent specialties. A practicing physician
cannot read them, and the existing tools (PubMed alerts, journal TOCs, Twitter/X, UpToDate) either
flood the user with noise or lag practice-changing evidence by months. The cost of missing a
signal is real: continuing an inferior technique, missing a safety warning, being surprised at
journal club.

## 2. Product principle

Every feature must save physician time, improve clinical reasoning, improve retention, reduce
information overload, or increase awareness of practice-changing evidence. When uncertain, choose
simplicity. (Inherited from the founding brief; treated as binding.)

## 3. The V1 promise

> Every Monday at 6:00 a.m., a single email that reliably contains everything from the past week
> that could plausibly change how I practice — and almost nothing that couldn't.

Success is defined by trust: after the 4-week calibration period, the user should feel safe *not*
monitoring the literature any other way.

## 4. Functional requirements

### FR-1: Source ingestion (daily)
- **PubMed** via NCBI E-utilities API: a curated search strategy combining (a) a journal
  allowlist (~25 journals, see `config/sources.yaml`) and (b) MeSH/keyword queries covering the
  specialty list from the founding brief. Abstracts + metadata only; no full-text scraping.
- **FDA safety communications**: MedWatch safety alerts and drug safety communication feeds.
- **Society/guideline feeds**: RSS/HTML watch on a shortlist (ASA, ASRA, SCA, ESAIC, SAMBA,
  ACC/AHA guideline pages, SCCM). Change detection only — "a new/updated guideline appeared."
- Deduplication by DOI/PMID/URL hash. Idempotent: re-running a day is safe.
- A failed source must not fail the pipeline; failures are logged and surfaced in the digest
  footer ("PubMed ingestion failed Tuesday — coverage may be incomplete").
- **Pre-filtering (free, deterministic):** journal-tier rules, standing-question keyword rules,
  and hard drops (retrospective n<30, errata, animal/bench unless topic-linked) reduce weekly
  LLM-triage volume to ~100–300 items. Dropped items are stored and auditable, never deleted.
- **Lawful full-text enrichment:** every item is checked against Unpaywall (by DOI) and PubMed
  Central (by PMID); if a legal open-access version exists, its link is stored and shown in the
  digest as "Free full text." No paywall circumvention of any kind (see Non-Goals).

### FR-2: Triage scoring (weekly, inside an interactive Claude Code session — $0)
- Monday morning, the user opens Claude Code in the repo and runs the custom `/digest` command.
- The session reads the week's pre-filtered items and scores them in batches against the
  **Practice Profile** using structured output. Fields: `relevance_tier`
  (practice_changing | worth_knowing | fyi | noise), `evidence_level`, `one_line_takeaway`,
  `reasoning`, `topics[]`, `confidence`. Scores are written to the DB with model + prompt +
  profile versions.
- Rubric lives in the Practice Profile, not in code. Prompt templates are versioned files.
- Billing: the user's Claude Pro subscription (interactive, human-initiated). No API key
  exists in the project. A documented API upgrade path exists for future full automation.

### FR-3: Synthesis + digest (same session)
- The session's second phase takes surfaced items and produces the digest: for each item, a
  2–4 sentence synthesis (what was studied, what was found, why it matters *to this user's
  practice*, key caveat, and — academic voice — how it sits against landmark trials/guidelines).
- Hard caps: ≤5 practice-changing, ≤12 worth-knowing, ≤15 FYI (title + one line). Exceeding a
  cap means demoting, not expanding. Scarcity is the feature.
- Every item links to the source and, when available, the lawful "Free full text" link, plus
  four feedback links. Maximizing lawful open-access coverage is an explicit goal (the daily
  pipeline enriches every passed item via Unpaywall + PMC; see `pipeline/enrich.py`).
- **Evidence grade (binding):** every surfaced item carries a quality-of-evidence grade
  (A–D; scale defined in `.claude/commands/digest.md`), shown inline, so the strength of
  evidence is visible at a glance — an eye-catching topic on grade-C/D evidence is labeled
  as such, and the synthesis says so (the journal-club caveat).
- **Preview before send:** the session renders the digest and shows it; the user approves (or
  edits categorizations conversationally — "demote item 4"), then it sends via Resend and the
  copy is stored. Human-in-the-loop review is a feature of this architecture, not overhead.

### FR-4: Feedback capture
- Four one-tap links per item: **Useful** / **Not relevant** / **Already knew** / **Deep-dive
  requested**. Links are HMAC-signed URLs hitting a Supabase Edge Function; clicking writes a
  feedback row and shows a plain "Recorded — you can close this tab" page. No login.
- "Deep-dive requested" queues the item; V1 fulfillment is manual-assist (the user runs a
  `make deep-dive PMID=...` command that produces a structured brief). Automated fulfillment
  is V2.

### FR-5: Archive & query
- All items, scores, digests, and feedback persist in Postgres indefinitely.
- V1 query interface: SQL / Claude Code against the database. A read-only web archive is V2.

### FR-6: Evaluation harness
- `eval_labels` table holds ~100+ hand-labeled items (the user's ground-truth tier).
- `make eval` runs the current prompt + model against the labeled set and reports: tier
  agreement, practice-changing recall (the metric that matters most — missing a signal is worse
  than including noise), and confusion matrix. Run before every prompt or model change.

## 5. User flows

### Flow A — Monday morning (the core loop, ~15 minutes)
1. User opens terminal in the repo, runs `claude`, types `/digest`. Makes coffee while it
   triages (~5–10 min, unattended but supervised).
2. Reviews the preview; optionally adjusts ("demote 4," "expand on 2"); says "send."
3. Opens the email: reads "week in brief," the 0–5 practice-changing items, taps feedback,
   taps deep-dive on ≤1 — or just asks the still-open session to deep-dive on the spot, free.
4. Skims worth-knowing, glances at FYI titles. Done, feeling *covered*.

### Flow B — Deep-dive (as needed)
1. User tapped "deep-dive" Monday.
2. That evening, runs `make deep-dive` (or asks Claude Code); receives a structured brief:
   study design, population, intervention, results with effect sizes, limitations, how it relates
   to current guidelines, and "questions to bring to journal club."
3. Reads the full paper via institutional access using the PubMed link.

### Flow C — Calibration (weekly, first month; monthly thereafter)
1. User notices a miscategorized item (e.g., a pediatric paper ranked practice-changing though
   they rarely do peds).
2. Edits `PRACTICE_PROFILE.md` (adds "pediatric-only studies are FYI unless airway-related").
3. Runs `make eval` to confirm the change helps and doesn't regress recall. Commits.

### Flow D — Model upgrade (a few times per year)
1. A new model ships. User changes one line in `config/models.yaml`.
2. Runs `make eval`; compares agreement vs. current model on the labeled set.
3. If better: commit, optionally `make rescore` on the recent backlog.

## 6. Wireframe descriptions (email — V1's only UI)

```
┌─────────────────────────────────────────────────┐
│  ANESTHESIA INTELLIGENCE          Jun 29, 2026  │
│  Week in brief: one short paragraph.            │
├─────────────────────────────────────────────────┤
│  ■ PRACTICE-CHANGING (3)                        │
│                                                 │
│  1. [Title, links to PubMed]                    │
│     Journal · RCT, n=1,204 · Jun 24             │
│     2–4 sentence synthesis written against      │
│     YOUR practice profile. Key caveat in the    │
│     last sentence.                              │
│     Useful · Not relevant · Knew it · Deep-dive │
│  ...                                            │
├─────────────────────────────────────────────────┤
│  ■ WORTH KNOWING (9)   — same layout, tighter   │
├─────────────────────────────────────────────────┤
│  ■ FYI (14) — title + one line each             │
├─────────────────────────────────────────────────┤
│  Pipeline health: all sources OK · 312 items    │
│  screened · 26 surfaced (8.3%)                  │
└─────────────────────────────────────────────────┘
```

Design rules: single column, no images, no hero banners, renders perfectly in plain-text-ish
HTML, dark-mode safe. The "items screened → surfaced" ratio is displayed every week because it
is the product's honesty metric.

## 7. Non-goals for V1 (binding)

1. Web dashboard or any web UI beyond the feedback-received page
2. Multi-user support, authentication, sharing
3. Personalization ML / recommender systems (the Practice Profile *is* personalization)
4. Chat interface of any kind
5. Conference monitoring (revisit as manual-assist in V2/V3)
6. Guideline *comparison* engine (ingestion/change-detection only)
7. Board review, spaced repetition, journal-club generation, tutoring
8. Full-text acquisition or paywall circumvention of any kind
9. Real-time/streaming anything
10. Mobile app
11. Any feature that touches patient data (permanent prohibition, not just V1)

## 8. Success metrics

- **Trust metric (primary):** after week 8, user self-reports they no longer feel the need to
  run manual PubMed checks. Binary.
- **Recall on eval set:** ≥90% of hand-labeled practice-changing items surfaced in the top two
  tiers; ≥80% tier agreement overall.
- **Noise metric:** <20% of surfaced items marked "not relevant" over a rolling month.
- **Engagement:** digest opened and ≥3 feedback taps per week (proxy for habit formation).
- **Cost:** $0/month incremental beyond the existing Claude Pro subscription.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Triage misses a true signal | Recall-weighted eval; inclusive triage (demote at synthesis, never silently drop); Tier-A journals never auto-noise |
| Weekly session strains Pro usage limits | Free deterministic pre-filters cap LLM volume at ~100–300 items; batching; mid-tier model for triage; knobs in config; documented API upgrade path |
| Anthropic changes subscription/Claude Code terms | Architecture note: the session and a future API job call identical Python entry points; switching is a config change |
| Abstract-only triage misjudges nuance | Acceptable for triage; deep-dive available live in the same session; lawful OA links for full text |
| PubMed indexing lag (days–weeks) | Accepted for V1; journal RSS fast-path is a V2 candidate |
| Prompt drift / silent regressions | Versioned prompts + mandatory `make eval` before merge |
| Founder skips Mondays → product dies | The 15-min ritual is the product's heartbeat; if it's ever resented, that's the trigger to adopt the API path |
| Supabase/Resend free-tier changes | Vanilla Postgres + SMTP-replaceable email — no lock-in |
