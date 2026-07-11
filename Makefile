# Anesthesia Intelligence — command surface (docs/04 §1).
# NOTE: triage and digest are deliberately NOT Make targets. They are LLM work and
# live in the interactive /digest Claude Code session (docs/02 §5) — keeping them
# out of Make prevents anyone from ever wiring them into unattended automation.

.PHONY: setup doctor test ingest backfill migrate eval deep-dive rescore backup

setup:  ## Install dependencies with uv
	uv sync

doctor:  ## Environment sanity check — MUST fail if an Anthropic API key is present
	@if [ -n "$$ANTHROPIC_API_KEY" ]; then \
		echo "FAIL: ANTHROPIC_API_KEY is set. This project has no API key by design"; \
		echo "      (CLAUDE.md rule 3) — its presence would silently switch Claude Code"; \
		echo "      from your Pro subscription to pay-per-token billing. Unset it."; \
		exit 1; \
	fi
	@command -v uv >/dev/null || { echo "FAIL: uv not installed (https://docs.astral.sh/uv/)"; exit 1; }
	@command -v dbmate >/dev/null || echo "note: dbmate not installed — needed from Step 2 (migrations)"
	@[ -n "$$DATABASE_URL" ] || echo "note: DATABASE_URL not set — needed from Step 2 (database access)"
	@echo "doctor: OK — no Anthropic API key present; core tooling available."

test:  ## Run the test suite
	uv run pytest

# ---- Stubs below become real in later steps; each says which one. -------------

ingest:  ## Run today's ingestion locally (supports DRY_RUN=1) — Step 5
	@echo "Not implemented until M1 Step 5 (pipeline/run_daily.py wiring)."; exit 1

backfill:  ## Backfill the last DAYS=90 days, supervised — Step 5
	@echo "Not implemented until M1 Step 5 (supervised 90-day backfill)."; exit 1

migrate:  ## Apply dbmate migrations to DATABASE_URL — Step 2
	@echo "Not implemented until M1 Step 2 (dbmate migrations)."; exit 1

eval:  ## Score the labeled eval set; report recall/agreement/confusion — M2
	@echo "Not implemented until Milestone M2 (evalset/run_eval.py)."; exit 1

deep-dive:  ## Structured brief for PMID=... (manual-assist) — M4
	@echo "Not implemented until Milestone M4 (deep-dive manual assist)."; exit 1

rescore:  ## Re-score the recent backlog after a model upgrade — M2+
	@echo "Not implemented until Milestone M2+ (rescore backlog)."; exit 1

backup:  ## pg_dump backup — Step 5 / M4
	@echo "Not implemented until M1 Step 5 (weekly pg_dump artifact)."; exit 1
