-- migrate:up

-- One row per /digest run that reached the preview stage. sent_at stays null for
-- previews and --dry-run runs; is_dry_run distinguishes an intentional dry run from
-- a preview the founder simply hasn't confirmed yet.
CREATE TABLE digests (
    id             bigserial PRIMARY KEY,
    sent_at        timestamptz, -- set only when actually delivered via Resend
    is_dry_run     boolean NOT NULL DEFAULT false,
    week_in_brief  text,
    screened_count integer,     -- pipeline-health footer (PRD §6): items screened
    surfaced_count integer,     -- ...and surfaced
    html           text,        -- stored copy of the rendered digest (PRD FR-3)
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE digests;
