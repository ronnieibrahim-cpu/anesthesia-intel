-- migrate:up

-- The founder's hand-labeled ground truth (PRD FR-6). Columns mirror
-- evalset/labels.csv exactly, which `make eval` loads into this table.
CREATE TABLE eval_labels (
    id               bigserial PRIMARY KEY,
    pmid             text,
    doi              text,
    title            text NOT NULL,
    journal          text,
    publication_date date,
    true_tier        text NOT NULL
        CHECK (true_tier IN ('practice_changing', 'worth_knowing', 'fyi', 'noise')),
    notes            text,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE eval_labels;
