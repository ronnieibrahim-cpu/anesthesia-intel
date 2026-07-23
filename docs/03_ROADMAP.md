# Milestone Roadmap

Rule inherited from the founding brief, applied at every milestone boundary:
**"Is this the highest-leverage feature we could build next?"** Each milestone below ends with an
explicit go/no-go question. Estimates assume part-time work with Claude Code doing implementation.

---

## M0 — Ground truth before code (Week 1–2, mostly founder time)

**Deliverables**
- `PRACTICE_PROFILE.md` v1: case mix, techniques, institutional context, standing clinical
  questions, controversies followed, explicit tier rubric, known exclusions.
- `config/sources.yaml` v1: journal allowlist (~25), PubMed search strategy, FDA feeds,
  society feed shortlist.
- Labeled eval set: founder hand-labels 100–150 recent items (one evening + one coffee).
  Pull candidates with a throwaway PubMed script; labels go straight into a CSV for now.

**Acceptance:** a colleague could read the Practice Profile and correctly predict which of 10
sample papers you'd call practice-changing.
**Gate question:** does the rubric feel honest, or aspirational? Fix now — it's the product.

## M1 — Ingestion (Week 2–3)

**Deliverables:** repo scaffolding, migrations, `ingest/` modules for all three source kinds,
dedupe, `daily.yml` workflow running unattended, backfill of the last 90 days.

**Acceptance:** 5 consecutive unattended daily runs; spot-check shows expected top-journal papers
present; zero duplicate `external_id`s; a killed mid-run job re-runs cleanly.
**Gate question:** is coverage right? (Missing sources are cheaper to add now than to backfill trust later.)

## M2 — Triage that agrees with you (Week 3–5)

> **Implementers:** `docs/08_HANDOFF_DIGEST.md` is the step-by-step handoff for M2/M3
> (what's built vs stub, the Opus-overseer + Sonnet-subagent workflow, open decisions).

**Deliverables:** the `/digest` slash command (triage phase), `triage-v1.md` prompt, structured
scoring (including the A–D evidence grade) written from within the session, `make eval`
runnable in-session, eval report checked into the repo, pre-filter tuning in
`config/filters.yaml`. Scores persist to the DB when reachable; today they operate off
`data/untriaged.jsonl` (DATABASE_URL unresolved in cloud sessions — see the handoff §6).

**Acceptance:** ≥90% practice-changing recall and ≥80% overall tier agreement on the eval set;
one full week's pre-filtered volume triaged comfortably within a single Pro session.
**Gate question:** where does the model disagree with you, and is the fix in the prompt or in the
Practice Profile? (Usually the profile.) Iterate here — this milestone is allowed to take longer;
everything downstream depends on it.

## M3 — First real digest (Week 5–6)

**Deliverables:** `/digest` synthesis phase, Jinja2 template (reproducing the design of
`templates/digest.sample.html` — per-item summary, evidence grade, "Free full text" link),
caps enforcement, preview-then-confirm send via Resend, `--dry-run` mode, digest copy stored
(DB when reachable, else to disk).

**Acceptance:** a real Monday digest generated end-to-end in one interactive session (ingest ran
automatically all week; you typed one command and one "send"), and your honest reaction is
"I would miss this if it stopped."
**Gate question:** would you show this email to a skeptical colleague? If not, what one change
would fix that — do only that.

## M4 — Feedback loop + calibration (Week 6–10)

**Deliverables:** Supabase Edge Function feedback endpoint, HMAC-signed links in the template,
`make deep-dive` manual-assist command, pipeline-health footer, monthly token budget guardrail.

**Process:** four consecutive weeks of live digests. Each week: tap feedback honestly, note
miscategorizations, adjust `PRACTICE_PROFILE.md`, run `make eval`, commit.

**Acceptance (V1 done):** trust metric hit — you stop manually checking PubMed; <20% "not
relevant" rate over the month; ≥3 feedback taps/week without forcing it.
**Gate question:** what did feedback data reveal that the plan didn't predict? That answer sets
the V2 priority — do not decide V2 before seeing it.

## V2 candidates (choose ONE first, informed by M4 data)

- Automated deep-dive fulfillment (reply-email brief when you tap deep-dive)
- Minimal read-only web archive (Next.js + Vercel free tier) with search
- pgvector semantic layer: dedup near-duplicates, "related prior work" in briefs
- Journal RSS fast-path to beat PubMed indexing lag
- Conference manual-assist (upload abstracts → scored like any item)

## V3+ horizon (unchanged from the founding vision, unlocked by the same engine)

Journal club generator · guideline comparison · controversy tracker · board review companion ·
multi-user for colleagues. Each is a rendering layer over the corpus + scores + feedback data
V1 is quietly accumulating from week one.
