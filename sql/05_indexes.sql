-- =====================================================================
-- BookMyShow DBMS Project: CP3 Indexing Strategy
-- File: sql/05_indexes.sql
-- Description: Targeted indexes created for CP3 query optimization
--              based on workload analysis and baseline execution plans.
-- =====================================================================

BEGIN;
SET LOCAL search_path TO bms, public;

-- ---------------------------------------------------------------------
-- 1. Index on shows (screen_id, starts_at)
-- Serves: R10, R01, R07, R17, R25
-- Justification:
--   - In R10 (consecutive shows within 30 min on same screen), transforms
--     an 8.1M pair hash-join into targeted index range scans on the same
--     screen within [s1.ends_at, s1.ends_at + 30 min).
--   - In R17, allows instant lookup of June shows on screen 101, dropping
--     execution time from 46 ms to < 1 ms.
--   - In R01, R07, and R25, accelerates joining shows by screen and
--     filtering or ordering by start timestamp.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_shows_screen_starts
    ON shows (screen_id, starts_at);

-- ---------------------------------------------------------------------
-- 2. Index on shows (movie_id, starts_at)
-- Serves: R02, R19, W05
-- Justification:
--   - R02 filters by movie_id = 2 and starts_at in [2026-07-02, 2026-07-03).
--   - R19 filters by movie_id = 2 and starts_at in June 2026.
--   - W05 updates base_price for movie_id = 2 on July weekends.
--   - B-tree composite index with equality column (movie_id) first,
--     followed by range column (starts_at) eliminates sequential scans
--     across all 160,034 rows of the shows table.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_shows_movie_starts
    ON shows (movie_id, starts_at);

-- ---------------------------------------------------------------------
-- 3. Foreign key index on bookings (show_id)
-- Serves: R08, R16, R18, R19, W02
-- Justification:
--   - The schema defined fk_bookings_show referencing shows(show_id), but
--     only had a unique constraint on (booking_id, show_id) where booking_id
--     is the leading column. A lookup by show_id alone could not use that index.
--   - Accelerates all joins from shows to bookings (e.g. R08, R16, R18, and
--     the rewritten LEFT JOIN in R19).
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bookings_show_id
    ON bookings (show_id);

-- ---------------------------------------------------------------------
-- 4. Foreign key index on bookings (customer_id)
-- Serves: R05, R12, R21
-- Justification:
--   - The schema defined fk_bookings_customer referencing customers(customer_id)
--     without an index on bookings.customer_id.
--   - R05 ("My bookings" dashboard for customer 1331) previously performed
--     a full sequential scan of 150,094 bookings. This index enables an
--     index scan taking < 0.1 ms.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bookings_customer_id
    ON bookings (customer_id);

-- ---------------------------------------------------------------------
-- 5. Partial index on bookings (booked_at, booking_id) WHERE status = 'PENDING'
-- Serves: R09, W02, W03, W04
-- Justification:
--   - Pending bookings represent transient seat locks (only 10 rows out of
--     150,094 in the seed data, <0.01% of the table).
--   - R09 and W04 check for expired pending locks (status = 'PENDING' AND booked_at < ...).
--   - W02 and W03 order pending bookings by booked_at, then booking_id to break ties.
--   - A partial index stores only rows where status = 'PENDING', keeping
--     the index small. Confirming a pending booking removes its index entry.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bookings_pending_time
    ON bookings (booked_at, booking_id)
    WHERE status = 'PENDING';

-- ---------------------------------------------------------------------
-- R20 filters by booking time. R22 walks the same key in descending order.
-- Include all projected columns so PostgreSQL can serve deep pages from the index.
CREATE INDEX IF NOT EXISTS idx_bookings_support_page
    ON bookings (booked_at DESC, booking_id DESC)
    INCLUDE (booking_code, customer_id, show_id, status);

-- R06 searches inside titles. Trigrams support the leading wildcard in ILIKE.
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;
CREATE INDEX IF NOT EXISTS idx_movies_title_trgm
    ON movies USING gin (title gin_trgm_ops);

-- Only non-NULL codes can match the equality probe for R13.
CREATE INDEX IF NOT EXISTS idx_bookings_redeemed_offer
    ON bookings (offer_code) WHERE offer_code IS NOT NULL;

-- W02 reads a screen's seats in ID order and stops after finding two free seats.
CREATE INDEX IF NOT EXISTS idx_seats_screen_seat ON seats (screen_id, seat_id);

-- Retire the two superseded project indexes on databases upgraded from CP3.
DROP INDEX IF EXISTS bms.idx_bookings_booked_at;
DROP INDEX IF EXISTS bms.idx_bookings_pending;

ANALYZE movies;
ANALYZE seats;
ANALYZE shows;
ANALYZE bookings;
COMMIT;
