-- migrate:up

-- Which items appeared in which digest, at which tier, in what order — denormalized
-- at send time (docs/02 §5), because a later re-score must never rewrite history of
-- what a past digest actually said.
CREATE TABLE digest_items (
    id          bigserial PRIMARY KEY,
    digest_id   bigint NOT NULL REFERENCES digests(id),
    item_id     bigint NOT NULL REFERENCES items(id),
    tier        text NOT NULL CHECK (tier IN ('practice_changing', 'worth_knowing', 'fyi')),
    position    integer NOT NULL, -- display order within the tier
    synthesis   text,             -- the 2-4 sentence synthesis shown (null for FYI titles)

    UNIQUE (digest_id, item_id)
);

CREATE INDEX digest_items_digest_id_idx ON digest_items (digest_id);

-- migrate:down
DROP TABLE digest_items;
