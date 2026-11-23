# Targeted follow-up experiments for PR #11

Run against the local large PostgreSQL database `bookmyshow_large` with schema `bms`. These experiments are diagnostics, separate from the historical §4 benchmark. Each timing phase uses three `EXPLAIN (ANALYZE, BUFFERS)` runs. Test-only indexes and writes are rolled back; do not describe them as deployed schema changes.

## R06: trigram index — successful local candidate

SQL tested: the R06 title search from `sql/06_optimized_queries.sql`, using `WHERE title ILIKE '%kalki%'` and ordering by `release_date DESC`.

DDL:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_movies_title_trgm_test
    ON bms.movies USING gin (title gin_trgm_ops);
ANALYZE bms.movies;
```

Three-run averages: 3.072 ms before, 0.191 ms after (about 16.1× faster). The plan changed from Seq Scan to Bitmap Index Scan + Bitmap Heap Scan; both phases returned 300 rows. Raw plans: `benchmarks/results/local_r06_verified/R06.txt`. The test transaction ended with ROLLBACK. Validate index storage and write overhead before adopting it permanently.

## W02: screen-first seat lookup — no meaningful improvement

Candidate DDL:
```sql
CREATE INDEX idx_seats_screen_seat_test
    ON bms.seats (screen_id, seat_id);
ANALYZE bms.seats;
```

The exact INSERT was run three times per phase using savepoints inside one repeatable-read transaction; each write was rolled back. Average changed from 78.568 to 76.905 ms (about 2.1% faster), and the plan continued to use the existing primary-key path. Before and after selected the same seats for booking 9079/show 3112341: 521521 and 521522; `mismatched_seats = 0`. The outer transaction ended with ROLLBACK. Raw evidence: `benchmarks/results/local_w02_verified/W02_corrected.txt`. Do not claim the candidate index as an effective optimization.

## R13: optimized-query baseline — no Phase 5 candidate comparison

Phase 4 already uses:
```sql
SELECT o.offer_code, o.description, o.discount_pct
FROM bms.offers o
WHERE NOT EXISTS (
    SELECT 1 FROM bms.bookings b
    WHERE b.offer_code = o.offer_code
);
```

Three-run optimized baseline: 190.083, 185.179 and 185.658 ms; average 186.973 ms. The Hash Right Anti Join returned 7 rows. Raw evidence: `benchmarks/results/local_r13_verified/R13.txt`.

The Phase 3 `NOT IN` query returns 0 rows due to NULL offer codes, while the Phase 4 `NOT EXISTS` query returns 7. That is a correctness correction, not a valid Phase 5 performance before/after comparison. No separate R13 index/query candidate was established in this experiment.

## R22: deterministic page and covering index — successful local candidate

Both variants used the full page query with a deterministic unique ordering:
```sql
SELECT booking_id, booking_code, customer_id, show_id, status, booked_at
FROM bms.bookings
ORDER BY booked_at DESC, booking_id DESC
OFFSET 100000 LIMIT 25;
```

Test index:
```sql
CREATE INDEX idx_bookings_page_order_test
ON bms.bookings (booked_at DESC, booking_id DESC)
INCLUDE (booking_code, customer_id, show_id, status);
```

Both phases ran in the same repeatable-read snapshot. Before plans used Incremental Sort + Index Scan (147.510 ms average); after plans used Index Only Scan (5.990 ms average; 0 heap fetches). The ordered `(position, booking_id)` comparison returned 25 rows in each phase and 0 mismatched positions. The test index was rolled back with the transaction. Raw evidence: `benchmarks/results/local_r22_verified/R22.txt`.

This local result is not a deployed index and does not rewrite the historical §4 timing.

## R21: planner-setting comparison

The same SELECT was run with the normal planner and with session-local:
```sql
SET enable_indexscan = off;
```

Normal planner average: 4,193.645 ms. Sequential-scan runs: 1,122.273, 1,170.072 and 1,203.334 ms (average 1,165.226 ms). The setting was session-local and was not made global. Raw evidence with the setting and plans: `benchmarks/results/local_seqscan_verified/R21.txt`.

Treat this as a planner-setting experiment, not a persistent index or production recommendation. Validate on production-like hardware and workload before adopting.

## Evidence to commit

Include the three-run raw plans and SQL artifacts for the five targeted queries. Keep the older control runs when they help explain the original comparisons, and use the verified R06/R13/R21/R22/W02 files for the final measured results. Do not include the faculty CSV archive or database files in Git.
