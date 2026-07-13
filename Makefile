# Anesthesia Intelligence — command surface (docs/04 §1).
# NOTE: triage and digest are deliberately NOT Make targets. They are LLM work and
# live in the interactive /digest Claude Code session (docs/02 §5) — keeping them
# out of Make prevents anyone from ever wiring them into unattended automation.

.PHONY: setup doctor test ingest-file ingest backfill migrate eval deep-dive rescore backup

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
	@command -v dbmate >/dev/null || [ -x "$$(go env GOPATH 2>/dev/null)/bin/dbmate" ] || \
		echo "note: dbmate not found — 'make migrate' will try to install it via 'go install'"
	@[ -n "$$DATABASE_URL" ] || echo "note: DATABASE_URL not set — needed for migrate/ingest"
	@echo "doctor: OK — no Anthropic API key present; core tooling available."

test:  ## Run the test suite
	uv run pytest

# ---- Stubs below become real in later steps; each says which one. -------------

ingest-file:  ## Ingest to data/week-<today>.jsonl (no DB needed) — interim, ADR 0001
	uv run python -m pipeline.run_daily --to-file $(if $(DAYS),--days $(DAYS),)

ingest:  ## Run today's ingestion into the DB (supports DRY_RUN=1) — Step 5
	@echo "DB ingestion is wired in M1 Step 5. For now use 'make ingest-file'"; \
	echo "(writes data/week-<today>.jsonl; DATABASE_URL not required)."; exit 1

backfill:  ## Backfill the last DAYS=90 days, supervised — Step 5
	@echo "Not implemented until M1 Step 5 (supervised 90-day backfill)."; exit 1

migrate:  ## Apply db/migrations to DATABASE_URL via dbmate (installs dbmate if missing)
	@[ -n "$$DATABASE_URL" ] || { echo "FAIL: DATABASE_URL is not set."; exit 1; }
	@export PATH="$$PATH:$$(go env GOPATH 2>/dev/null)/bin"; \
	if ! command -v dbmate >/dev/null 2>&1; then \
		if command -v go >/dev/null 2>&1; then \
			echo "dbmate not found — installing via 'go install' (one-time, ~30s)..."; \
			go install github.com/amacneil/dbmate/v2@latest; \
		else \
			echo "FAIL: dbmate not found and no Go toolchain to install it."; \
			echo "      Fallback: paste the migrate:up blocks from db/migrations/*.sql, in"; \
			echo "      filename order, into the Supabase SQL Editor instead."; \
			exit 1; \
		fi; \
	fi; \
	dbmate --no-dump-schema up

eval:  ## Score the labeled eval set; report recall/agreement/confusion — M2
	@echo "Not implemented until Milestone M2 (evalset/run_eval.py)."; exit 1

deep-dive:  ## Structured brief for PMID=... (manual-assist) — M4
	@echo "Not implemented until Milestone M4 (deep-dive manual assist)."; exit 1

rescore:  ## Re-score the recent backlog after a model upgrade — M2+
	@echo "Not implemented until Milestone M2+ (rescore backlog)."; exit 1

backup:  ## pg_dump backup — Step 5 / M4
	@echo "Not implemented until M1 Step 5 (weekly pg_dump artifact)."; exit 1
