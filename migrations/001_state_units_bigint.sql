-- Upgrades a database created by the first version of the bot (January 2026).
-- Additive and safe to re-run: no rows are deleted.
--   psql -d chemistry_bot -f migrations/001_state_units_bigint.sql

BEGIN;

-- Telegram user ids no longer fit in a 32-bit integer
ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;

-- The active problem is kept in the database instead of bot memory
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_problem_id INTEGER REFERENCES problems(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS hint_index INTEGER DEFAULT 0;

-- Unit shown to students next to the answer
ALTER TABLE problems ADD COLUMN IF NOT EXISTS unit VARCHAR(30);

COMMIT;
