# Targeted follow-up experiments for PR #11

Run against `bookmyshow_large` with the `bms` schema. Capture each phase with the existing runner and retain all generated raw plan files.

## R06: trigram candidate

Control SQL is the R06 statement in `sql/06_optimized_queries.sql`. Record its three-run plan first. Then:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_movies_title_trgm_test
    ON bms.movies USING gin (title gin_trgm_ops);
ANALYZE bms.movies;
```

Run the same R06 statement three times again. Keep the index only if the plan uses it and the measured latency justifies its storage/write overhead. The table has only 6,000 rows, so a sequential scan may remain cheaper.

## W02: screen-first seat lookup candidate

Capture the current optimized W02 plan three times first. Then:

```sql
CREATE INDEX idx_seats_screen_seat_test
    ON bms.seats (screen_id, seat_id);
ANALYZE bms.seats;
```

Run the exact same W02 statement three times. Every execution must be inside `BEGIN; EXPLAIN (ANALYZE, BUFFERS) INSERT ...; ROLLBACK;` (the benchmark runner does this for W* statements). Compare the two selected seat IDs before and after the index using a read-only preview of the oldest PENDING booking's show and its two lowest unsold seat IDs. Do not retain the index unless the selected seat IDs are identical and latency improves.

Preview query:

```sql
SET search_path TO bms;
WITH target AS (
  SELECT b.booking_id, b.show_id, s.screen_id
  FROM bookings b
  JOIN shows s ON s.show_id = b.show_id
  WHERE b.booking_id = (
    SELECT min(booking_id) FROM bookings WHERE status = 'PENDING'
  )
)
SELECT t.booking_id, t.show_id, se.seat_id
FROM target t
JOIN seats se ON se.screen_id = t.screen_id
WHERE NOT EXISTS (
  SELECT 1 FROM booking_seats bs
  WHERE bs.show_id = t.show_id AND bs.seat_id = se.seat_id
)
ORDER BY se.seat_id
LIMIT 2;
```

## R13: correct optimized baseline

Phase 4 already rewrites R13 to `NOT EXISTS`. Do not compare Phase 3 `NOT IN` against Phase 4 `NOT EXISTS` as an optimization. Run the exact R13 statement from `sql/06_optimized_queries.sql` three times as the Phase 4 optimized baseline on the large database, save its plans, and compare the same statement against any proposed index only if one is tested. Confirm the returned offer rows are identical.

## R22: deterministic page and equivalence

Use a stable ordering in both variants:

```sql
SELECT booking_id
FROM bms.bookings
ORDER BY booked_at DESC, booking_id DESC
OFFSET 100000 LIMIT 25;
```

Capture the ordered 25 IDs before and after the covering index. Compare with EXCEPT in both directions (or compare ordered arrays). If using a covering index, its leading keys must match the ordering:

```sql
CREATE INDEX idx_bookings_page_cover_test
ON bms.bookings (booked_at DESC, booking_id DESC)
INCLUDE (booking_code, customer_id, show_id, status);
```

Run the same full R22 SELECT three times before and after this index. Do not compare the old non-deterministic `ORDER BY booked_at DESC` page against the new tie-broken page.

## R21

The current evidence compares the same top-20 SELECT with normal planner settings and with session-local `SET enable_indexscan = off`. Preserve the two plan sets and the bidirectional EXCEPT result. Do not change global planner settings.

## Evidence to commit

Commit the complete raw plan files for all five queries and all three runs in each applicable phase, plus the exact SQL/DDL/session settings. Do not include the faculty CSV archive or database files in Git.
