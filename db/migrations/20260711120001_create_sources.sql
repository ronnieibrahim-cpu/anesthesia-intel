-- migrate:up

-- One row per ingestion source kind. Also carries the health-check state that the
-- digest footer surfaces ("PubMed ingestion failed Tuesday — coverage may be
-- incomplete", PRD FR-1) without failing the whole daily run.
CREATE TABLE sources (
    id             bigserial PRIMARY KEY,
    kind           text NOT NULL CHECK (kind IN ('pubmed', 'fda', 'society_feed')),
    name           text NOT NULL UNIQUE, -- e.g. 'PubMed', 'FDA MedWatch', 'ASA Guidelines'
    last_success_at timestamptz,
    last_error     text,
    last_error_at  timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE sources;
