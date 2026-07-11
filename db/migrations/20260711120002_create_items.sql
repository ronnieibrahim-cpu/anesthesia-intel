-- migrate:up

-- Every item ever seen, across all sources. Dropped (pre-filtered) items are kept,
-- never deleted (docs/02 §3): recoverable, auditable, re-scorable later.
--
-- oa_url / oa_source / prefilter are the three columns docs/02 §4 calls out by name
-- as the v2 additions; there is no separate v1 to ALTER in this repo, so they are
-- folded directly into the table from the start.
CREATE TABLE items (
    id             bigserial PRIMARY KEY,
    source_id      bigint NOT NULL REFERENCES sources(id),

    -- Dedupe key (PRD FR-1: dedupe by DOI/PMID/URL hash). Precedence for what goes
    -- here is decided in pipeline/normalize.py: DOI, else PMID, else a URL hash.
    external_id    text NOT NULL,

    doi            text,
    pmid           text,
    title          text NOT NULL,
    journal        text,

    -- Deterministic signals the pre-filter needs (docs/02 §3): item_type feeds the
    -- errata/letters hard-drop, sample_size + study_design feed the retrospective
    -- n-floor rule. Populated by pipeline/normalize.py from source metadata/abstract.
    item_type      text,       -- e.g. 'journal_article' | 'erratum' | 'letter' |
                                --      'safety_communication' | 'guideline_update'
    study_design   text,       -- e.g. 'rct' | 'meta_analysis' | 'retrospective' | 'animal'
    sample_size    integer,

    published_on   date,
    abstract       text,
    url            text NOT NULL,

    -- Lawful open-access enrichment (docs/02 §4; CLAUDE.md rule 2 — the ONLY
    -- full-text mechanism in this project).
    oa_url         text,
    oa_source      text CHECK (oa_source IN ('unpaywall', 'pmc')),

    -- 'pending' until pipeline/prefilter.py runs, then 'passed' or the name of the
    -- rule that dropped it (dynamic — rule names live in config/filters.yaml, so
    -- this is free text, not a fixed enum).
    prefilter      text NOT NULL DEFAULT 'pending',

    raw            jsonb NOT NULL DEFAULT '{}'::jsonb, -- full source payload, for audit
    created_at     timestamptz NOT NULL DEFAULT now(),

    UNIQUE (source_id, external_id) -- makes re-running any day idempotent (PRD FR-1)
);

-- The digest's coverage-window query and the /digest triage read ("unscored,
-- passed items") both filter on prefilter + published_on.
CREATE INDEX items_prefilter_passed_idx ON items (published_on) WHERE prefilter = 'passed';

-- migrate:down
DROP TABLE items;
