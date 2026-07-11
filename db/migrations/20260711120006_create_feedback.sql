-- migrate:up

-- One row per one-tap feedback click (PRD FR-4): Useful / Not relevant / Already
-- knew / Deep-dive requested. Written by the Supabase Edge Function after HMAC
-- verification — no login, no other identifying data.
CREATE TABLE feedback (
    id          bigserial PRIMARY KEY,
    item_id     bigint NOT NULL REFERENCES items(id),
    digest_id   bigint REFERENCES digests(id), -- which digest the tap came from
    verdict     text NOT NULL
        CHECK (verdict IN ('useful', 'not_relevant', 'knew_it', 'deep_dive')),
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX feedback_item_id_idx ON feedback (item_id);

-- migrate:down
DROP TABLE feedback;
