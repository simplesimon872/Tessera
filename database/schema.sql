-- Tessera — Supabase schema
-- Run this in the Supabase SQL editor.
-- Safe to re-run: all statements use IF NOT EXISTS / OR REPLACE.

-- ── users ────────────────────────────────────────────────────────────────────
-- One row per claimed handle. Created when @bannerusmaximus claim is processed.

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT UNIQUE NOT NULL,
    arena_user_id   TEXT NOT NULL,
    claimed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_epoch_id   UUID,               -- FK added after epochs table exists
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── epochs ───────────────────────────────────────────────────────────────────
-- One row per scoring window per handle.
-- status: computed → sealed (happy path) | seal_failed (retry on next cron)

CREATE TABLE IF NOT EXISTS epochs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT NOT NULL,
    epoch_start     TIMESTAMPTZ NOT NULL,
    epoch_end       TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'computed'
                        CHECK (status IN ('computed', 'sealed', 'seal_failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (handle, epoch_start)        -- never duplicate a window
);

CREATE INDEX IF NOT EXISTS epochs_handle_idx    ON epochs (handle);
CREATE INDEX IF NOT EXISTS epochs_status_idx    ON epochs (status);

-- ── scores ───────────────────────────────────────────────────────────────────
-- Pillar scores + full canonical snapshot for each epoch.

CREATE TABLE IF NOT EXISTS scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    epoch_id            UUID NOT NULL REFERENCES epochs (id) ON DELETE CASCADE,
    originality         NUMERIC(5, 2),
    focus               NUMERIC(5, 2),
    consistency         NUMERIC(5, 2),
    depth               NUMERIC(5, 2),
    composite           NUMERIC(5, 2),
    methodology         TEXT NOT NULL DEFAULT 'v1.0',
    snapshot_hash       TEXT NOT NULL,
    collection_hash     TEXT,
    prompt_hash         TEXT,
    model               TEXT,
    consistency_mode    TEXT,           -- 'frequency_variance' | 'thirds_entropy'
    other_cap_applied   BOOLEAN DEFAULT FALSE,
    post_total          INTEGER,
    post_classified     INTEGER,
    post_greeting       INTEGER,
    post_null           INTEGER,
    snapshot_json       JSONB,          -- full canonical snapshot
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scores_epoch_id_idx ON scores (epoch_id);

-- ── anchors ──────────────────────────────────────────────────────────────────
-- Onchain seal receipts. One row per sealed epoch.

CREATE TABLE IF NOT EXISTS anchors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    epoch_id        UUID NOT NULL REFERENCES epochs (id) ON DELETE CASCADE,
    tx_hash         TEXT NOT NULL UNIQUE,
    block_number    BIGINT NOT NULL,
    snapshot_hash   TEXT NOT NULL,      -- must match scores.snapshot_hash
    anchored_at     TIMESTAMPTZ NOT NULL,
    snowtrace_url   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS anchors_epoch_id_idx ON anchors (epoch_id);

-- ── bot_state ─────────────────────────────────────────────────────────────────
-- Key-value store for bot polling state and cron state.
-- Keys: 'last_processed_notification_id', 'last_seal_run'

CREATE TABLE IF NOT EXISTS bot_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── command_log ───────────────────────────────────────────────────────────────
-- Every bot command logged here for rate limiting and abuse detection.

CREATE TABLE IF NOT EXISTS command_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle      TEXT NOT NULL,
    command     TEXT NOT NULL,
    target      TEXT,                   -- for inspect @handle, stores target
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS command_log_handle_time_idx ON command_log (handle, issued_at);

-- ── FK: users.last_epoch_id ───────────────────────────────────────────────────
-- Added after epochs table exists.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'users_last_epoch_id_fkey'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_last_epoch_id_fkey
            FOREIGN KEY (last_epoch_id) REFERENCES epochs (id);
    END IF;
END $$;

-- ── updated_at trigger ────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS bot_state_updated_at ON bot_state;
CREATE TRIGGER bot_state_updated_at
    BEFORE UPDATE ON bot_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
