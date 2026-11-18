-- =====================================================================
-- BookMyShow DBMS Project: CP3 Indexing Strategy
-- File: sql/05_indexes.sql
-- Description: Targeted indexes created for CP3 query optimization
--              based on workload analysis and baseline execution plans.
-- =====================================================================

SET search_path TO bms;

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
-- 5. Partial index on bookings (booking_id, booked_at) WHERE status = 'PENDING'
-- Serves: R09, W02, W03, W04
-- Justification:
--   - Pending bookings represent transient seat locks (only 10 rows out of
--     150,094 in the seed data, <0.01% of the table).
--   - R09 and W04 check for expired pending locks (status = 'PENDING' AND booked_at < ...).
--   - W02 and W03 search for the oldest pending booking (SELECT min(booking_id) WHERE status = 'PENDING').
--   - A partial index stores only rows where status = 'PENDING', requiring
--     only 16 kB of storage and incurring zero write overhead on confirmed bookings.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bookings_pending
    ON bookings (booking_id, booked_at)
    WHERE status = 'PENDING';

-- ---------------------------------------------------------------------
-- 6. Index on bookings (booked_at DESC)
-- Serves: R20, R22
-- Justification:
--   - R22 implements support console pagination (ORDER BY booked_at DESC OFFSET 100000 LIMIT 25).
--     Without an index, PostgreSQL must sort 150,094 records. With this index,
--     it scans pre-sorted index tuples.
--   - R20 aggregates daily collections filtered on booked_at range.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bookings_booked_at
    ON bookings (booked_at DESC);

-- Analyze updated table statistics
ANALYZE shows;
ANALYZE bookings;
