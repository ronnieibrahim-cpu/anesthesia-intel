-- migrate:up

-- Append-only triage scores (docs/02 §5): every row is traceable to the exact
-- model, prompt version, and Practice Profile version that produced it, so the
-- backlog can be re-scored when a better model ships without losing history.
CREATE TABLE scores (
    id             bigserial PRIMARY KEY,
    item_id        bigint NOT NULL REFERENCES items(id),

    relevance_tier text NOT NULL
        CHECK (relevance_tier IN ('practice_changing', 'worth_knowing', 'fyi', 'noise')),
    evidence_level text,
    one_line_takeaway text,
    reasoning      text,
    topics         text[] NOT NULL DEFAULT '{}',
    confidence     numeric(3, 2), -- 0.00-1.00

    model          text NOT NULL, -- e.g. 'claude-code-session/sonnet'
    prompt_version text NOT NULL, -- e.g. 'triage-v1'
    profile_version text NOT NULL, -- PRACTICE_PROFILE.md version/date this score used

    is_current     boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX scores_item_id_idx ON scores (item_id);

-- Exactly one current score per item at a time.
CREATE UNIQUE INDEX scores_one_current_per_item ON scores (item_id) WHERE is_current;

-- migrate:down
DROP TABLE scores;
