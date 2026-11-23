# CP4 – Scalability Report

## 1. Introduction

This report evaluates the BookMyShow database at the large-data scale and assesses the design choices needed for a future 100× workload. It compares the **Phase 4 optimized seed benchmark** with the large-dataset benchmark. The original unoptimized baseline is not used as the growth denominator because Phase 5 starts from the optimized workload.

The large dataset contains 15,571,506 rows versus 778,048 seed rows (about 20.01×). The workload has 25 read queries (R01–R25) and 5 write queries (W01–W05).

## 2. Dataset and benchmark methodology

- Seed dataset: 778,048 rows across 11 tables.
- Large dataset: 15,571,506 rows across 11 tables.
- Large `booking_seats`: 6,016,946 rows.
- Each workload query was executed three times; the CSV average is used below.
- Plans were collected with `EXPLAIN (ANALYZE, BUFFERS)`.
- Write workloads were benchmarked in transactions rolled back after each run.
- Growth factor = large average execution time ÷ optimized-seed average execution time.

The source files are `benchmarks/results/optimized/summary.csv`, `benchmarks/results/large/summary.csv`, and their corresponding raw plan files.

## 3. Large-dataset loading and partitioning

### 3.1 Data validation

The large-data validation record reports 15,571,506 rows across the 11 tables and confirms that the loaded counts matched the CSV row counts. `booking_seats` contains 6,016,946 rows.

### 3.2 Hash partitioning of booking_seats

The implementation in `sql/08_partitioning.sql` converts `bms.booking_seats` to **HASH partitioning on `show_id`**, with 16 partitions (`booking_seats_p00` through `booking_seats_p15`), modulus 16.

The migration runs in a transaction, takes an ACCESS EXCLUSIVE lock, creates the partitioned replacement and its constraints, creates the 16 child partitions, copies the rows, checks that old and new row counts match, swaps the table, runs ANALYZE and commits. The script raises an exception if its row-count comparison fails.

A partitioned unique or primary-key constraint must include every partition-key column. PostgreSQL cannot enforce a globally unique key across partitions using a key that omits the partition key. Therefore the partitioned table uses a key containing `show_id`, for example **PRIMARY KEY (show_id, seat_id)**, rather than attempting to keep a globally unique `seat_id`-only key on the partitioned parent.

### 3.3 Evidence of pruning and non-pruning

The large R03 plan accesses `booking_seats_p00` through an index-only scan with `Index Cond: (show_id = 144446)`; the plan does not scan all 16 child tables. This is the positive example: equality on the hash partition key allows PostgreSQL to select the relevant hash partition.

By contrast, R11 and R24 scan all 16 `booking_seats` partitions because their analytical aggregation does not constrain `show_id` to a single hash value. Hash partitioning is therefore useful for targeted show lookups, but it does not remove the work from queries that need data across the full table.

## 4. Optimized-seed versus large benchmark results

The required comparison is optimized seed → large dataset. Target groups and limits follow the project README:
- Real-time / booking path: 5 ms — R02, R03, R04, R05, R06, R09, R23, W01, W02, W03.
- Interactive cinema tools: 250 ms — R01, R07, R13, R17, R22, W04, W05.
- Reports and analytics: 5,000 ms — R08, R10, R11, R12, R14, R15, R16, R18, R19, R20, R21, R24, R25.

| Query | Optimized seed avg (ms) | Large avg (ms) | Growth (×) | Target (ms) | Large target |
|---|---:|---:|---:|---:|:---:|
| R01 | 0.855 | 61.507 | 71.94 | 250 | PASS |
| R02 | 0.217 | 1.475 | 6.80 | 5 | PASS |
| R03 | 0.254 | 1.028 | 4.05 | 5 | PASS |
| R04 | 0.026 | 0.364 | 14.00 | 5 | PASS |
| R05 | 0.116 | 0.750 | 6.47 | 5 | PASS |
| R06 | 0.139 | 5.076 | 36.52 | 5 | FAIL |
| R07 | 0.146 | 2.714 | 18.59 | 250 | PASS |
| R08 | 16.133 | 410.586 | 25.45 | 5,000 | PASS |
| R09 | 0.040 | 0.258 | 6.45 | 5 | PASS |
| R10 | 33.979 | 574.650 | 16.91 | 5,000 | PASS |
| R11 | 48.957 | 1,609.278 | 32.87 | 5,000 | PASS |
| R12 | 61.232 | 3,344.183 | 54.61 | 5,000 | PASS |
| R13 | 8.836 | 513.060 | 58.06 | 250 | FAIL |
| R14 | 4.860 | 109.348 | 22.50 | 5,000 | PASS |
| R15 | 36.788 | 513.223 | 13.95 | 5,000 | PASS |
| R16 | 19.962 | 773.969 | 38.77 | 5,000 | PASS |
| R17 | 0.242 | 2.952 | 12.20 | 250 | PASS |
| R18 | 41.893 | 1,352.006 | 32.27 | 5,000 | PASS |
| R19 | 0.622 | 6.846 | 11.01 | 5,000 | PASS |
| R20 | 12.392 | 235.925 | 19.04 | 5,000 | PASS |
| R21 | 40.131 | 8,609.623 | 214.54 | 5,000 | FAIL |
| R22 | 21.348 | 285.333 | 13.37 | 250 | FAIL |
| R23 | 0.023 | 0.225 | 9.78 | 5 | PASS |
| R24 | 60.600 | 1,869.174 | 30.84 | 5,000 | PASS |
| R25 | 22.211 | 623.449 | 28.07 | 5,000 | PASS |
| W01 | 0.707 | 2.311 | 3.27 | 5 | PASS |
| W02 | 9.230 | 160.828 | 17.42 | 5 | FAIL |
| W03 | 0.208 | 1.000 | 4.81 | 5 | PASS |
| W04 | 0.108 | 29.903 | 276.88 | 250 | PASS |
| W05 | 1.680 | 10.433 | 6.21 | 250 | PASS |

**Result: 25 of 30 queries meet their stated large-data target; 5 miss.** The target status is based on the average of three large-dataset runs.

### 4.1 Growth groups

For interpretation, the observed growth factors are grouped as below. These are descriptive bands, not additional project targets.

- **Below 10×:** R02, R03, R05, R09, R23, W01, W03 and W05. These queries remain relatively selective or use efficient point/range lookups.
- **10× to below 25×:** R04, R07, R10, R14, R15, R17, R19, R20, R22 and W02. Their work increases with larger input sets, but the measured increase is below 25×.
- **25× or more:** R01, R06, R08, R11, R12, R13, R16, R18, R21, R24, R25 and W04. These plans process more rows, perform broad scans/aggregations, or encounter less selective access paths at the larger scale.

The overall row count grew about 20×, but query latency did not grow uniformly. Some queries grew less than 10×, while R21 grew 214.54× and W04 276.88×. This reflects the amount and shape of work performed by each query, not just table-size growth.

## 5. Missed targets: plan evidence and next optimization steps

The historical large benchmark shows five target misses. Follow-up experiments on the local large dataset now include reproducible three-run evidence for all five queries. These local measurements are diagnostic and remain separate from §4's historical pass/fail results.

| Query | Target | Historical large average | Local finding | Next step |
|---|---:|---:|---|---|
| R06 | <5 ms | 5.076 ms | A trigram GIN index changed the plan from Seq Scan to Bitmap Index/Heap Scan; average fell from 3.072 to 0.191 ms, with 300 rows returned in both phases. | Strong local improvement; verify storage cost and include the DDL/raw plans. |
| W02 | <5 ms | 160.828 ms | The screen-first index candidate changed average time only from 78.568 to 76.905 ms; the plan continued to use the existing primary-key path. The same two seat IDs were selected before/after. | Candidate is not justified by this small change; keep the write rollback and seat-equivalence evidence. |
| R13 | <250 ms | 513.060 ms | The optimized Phase 4 `NOT EXISTS` query returned 7 rows and averaged 186.973 ms over three local runs. | This is a correctly matched optimized-query baseline, not a Phase 5 before/after improvement. |
| R22 | <250 ms | 285.333 ms | With deterministic ordering by `booked_at DESC, booking_id DESC`, a composite covering index changed the average from 147.510 to 5.990 ms. Ordered-page comparison found 0 mismatched positions on the same repeatable-read snapshot. | Strong local improvement; the test index was rolled back. |
| R21 | <5,000 ms | 8,609.623 ms | The same SELECT averaged 4,193.645 ms with the normal planner and 1,165.226 ms with session-local `enable_indexscan=off`. The latter used a sequential scan. | Treat as a planner-setting experiment, not a persistent index change; validate on production-like hardware. |

These five historical misses remain **open against the original §4 benchmark**. Local experiments show that targeted access-path changes can improve R06 and R22, but do not rewrite the historical pass/fail table or establish production performance.

### 5.1 Local large-dataset experiments (23 November 2026)

The faculty dataset was loaded into a separate local PostgreSQL database, `bookmyshow_large`, preserving the seed database. It contains 15,571,506 rows. The following averages use three `EXPLAIN (ANALYZE, BUFFERS)` runs per phase. They are reported separately from §4 because hardware/cache conditions differ.

| Query | Before avg (ms) | Tested avg (ms) | Tested change and result |
|---|---:|---:|---|
| R06 | 3.072 | 0.191 | Added test-only GIN index `movies(title gin_trgm_ops)`; plan changed from Seq Scan to Bitmap Index Scan + Bitmap Heap Scan. Both phases returned 300 rows. About 16.1× faster. |
| R13 | 186.973 | — | Three-run baseline of the Phase 4 optimized `NOT EXISTS` query; Hash Right Anti Join; 7 rows returned. No separate Phase 5 candidate was tested. |
| R21 | 4,193.645 | 1,165.226 | Same SELECT; session-local `enable_indexscan=off` produced a Seq Scan plan. This is a planner-setting comparison, not a persistent schema change. |
| R22 | 147.510 | 5.990 | Deterministic full page query ordered by `booked_at DESC, booking_id DESC`; composite covering index enabled Index Only Scan. Ordered position comparison returned 0 mismatches. About 24.6× faster. |
| W02 | 78.568 | 76.905 | Tested `seats(screen_id, seat_id)`; the plan continued using the existing primary-key access path. Exact selected seats matched; only about 2.1% faster. |

All test-only index creation and write tests were rolled back. The R06 and R22 index results therefore describe measured experiments, not indexes currently installed in the database.

R13 correctness and baseline:
- The original Phase 3 `NOT IN` query returns 0 rows because the subquery contains NULL offer codes.
- Phase 4's optimized `NOT EXISTS` query returns 7 unredeemed offers.
- The local optimized-query runs took 190.083, 185.179 and 185.658 ms (average 186.973 ms).
- The earlier `NOT IN` versus `NOT EXISTS` timing pair is a correctness comparison, not a valid Phase 5 performance comparison.

R21 planner-setting experiment:
- Normal-planner runs averaged 4,193.645 ms and used `idx_bookings_customer_id`.
- With session-local `SET enable_indexscan = off`, the three sequential-scan runs took 1,122.273, 1,170.072 and 1,203.334 ms (average 1,165.226 ms).
- The setting was session-local; no global planner setting was changed.

R22 ordered-page equivalence and timing:
- Both variants ran in one `REPEATABLE READ` transaction using the full page query ordered by `booked_at DESC, booking_id DESC` with `OFFSET 100000 LIMIT 25`.
- The tested index was `(booked_at DESC, booking_id DESC) INCLUDE (booking_code, customer_id, show_id, status)`.
- Before plans used Incremental Sort + Index Scan (147.510 ms average); after plans used Index Only Scan with 0 heap fetches (5.990 ms average).
- The ordered `(position, booking_id)` comparison reported 25 rows in each phase and 0 mismatched positions. The transaction ended with ROLLBACK.

W02 write-safety and equivalence:
- Each INSERT execution was rolled back inside a savepoint; the outer repeatable-read transaction was also rolled back.
- Before and after selected the same two seats for booking 9079/show 3112341: seat IDs 521521 and 521522. `mismatched_seats = 0`.
- Average time changed from 78.568 to 76.905 ms, but the plan continued using the existing primary-key path. The proposed index is not justified by this small change.

R06 trigram-index experiment:
- The three before runs used Seq Scan and took 4.667, 2.350 and 2.198 ms (average 3.072 ms).
- The three after runs used Bitmap Index Scan on `idx_movies_title_trgm_test` plus Bitmap Heap Scan and took 0.199, 0.189 and 0.185 ms (average 0.191 ms).
- All runs returned 300 rows. The test transaction ended with ROLLBACK.

**Evidence packaging:** raw plans and exact SQL are being added under `benchmarks/results/local_*` and `queries/targeted_before.sql` / `queries/targeted_after.sql`. The large dataset archive is intentionally excluded from Git.

## 6. Storage measurements and measurement limitation

### 6.1 Seed database (measured)

The seed database `bookmyshow` was measured locally using PostgreSQL size functions. Its total database size is **116 MB**.

| Table | Heap/table size | Index size | Total relation size |
|---|---:|---:|---:|
| booking_seats | 15 MB | 16 MB | 32 MB |
| bookings | 17 MB | 13 MB | 30 MB |
| shows | 10,112 kB | 16 MB | 26 MB |
| seats | 4,552 kB | 4,152 kB | 8,736 kB |
| customers | 3,736 kB | 4,496 kB | 8,264 kB |
| movie_reviews | 2,048 kB | 728 kB | 2,816 kB |
| screens | 32 kB | 32 kB | 88 kB |
| movies | 24 kB | 16 kB | 64 kB |
| venues | 16 kB | 16 kB | 56 kB |
| offers | 8 kB | 16 kB | 24 kB |
| cities | 8 kB | 16 kB | 24 kB |

Values are PostgreSQL's displayed rounded sizes, so displayed per-table totals may not sum exactly to the database-level size.

### 6.2 Large database (measured locally)

The faculty large dataset was loaded into the separate local database `bookmyshow_large`. PostgreSQL reports a total database size of **2,580 MB** (approximately 2.52 GiB).

| Table | Heap size | Index size | Total relation size |
|---|---:|---:|---:|
| booking_seats (16 leaf partitions summed) | 299 MB | 506 MB | 806 MB |
| bookings | 338 MB | 358 MB | 696 MB |
| shows | 188 MB | 477 MB | 664 MB |
| customers | 75 MB | 105 MB | 180 MB |
| seats | 89 MB | 81 MB | 170 MB |
| movie_reviews | 40 MB | 14 MB | 54 MB |
| screens | 504 kB | 232 kB | 768 kB |
| movies | 424 kB | 152 kB | 608 kB |
| venues | 248 kB | 80 kB | 360 kB |
| cities | 8 kB | 16 kB | 24 kB |
| offers | 8 kB | 16 kB | 24 kB |

The table sizes are PostgreSQL's rounded display values; their sum may differ slightly from the database-level total because database size also includes catalog, TOAST and other relation/overhead storage. The `booking_seats` total is calculated by summing its 16 leaf partitions and their indexes, not by reading the partitioned parent's relation size.

The exact summed `booking_seats` partition sizes were:
- Heap: 314,032,128 bytes.
- Indexes: 530,874,368 bytes.
- Total: 844,906,496 bytes (about 806 MiB).

The local test-only R22 covering index (193 MB) was created after the above storage measurement and is therefore **not included** in the reported 2,580 MB database total or the table/index breakdown above.

Run the following SQL on the loaded database to reproduce the database and logical-table measurements. Leaf partitions are grouped under their parent so the 16 `booking_seats` partitions are counted once and the partitioned parent is not double-counted.

```sql
-- 1. Whole database size
SELECT current_database() AS database_name,
       pg_size_pretty(pg_database_size(current_database())) AS database_size;

-- 2. Heap, index and total relation size.
-- Leaf partitions are grouped under their parent table.
SELECT
    COALESCE(parent.relname, c.relname) AS table_name,
    pg_size_pretty(SUM(pg_relation_size(c.oid))) AS heap_size,
    pg_size_pretty(SUM(pg_indexes_size(c.oid))) AS indexes_size,
    pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS total_size,
    SUM(pg_relation_size(c.oid)) AS heap_bytes,
    SUM(pg_indexes_size(c.oid)) AS index_bytes,
    SUM(pg_total_relation_size(c.oid)) AS total_bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_inherits i ON i.inhrelid = c.oid
LEFT JOIN pg_class parent ON parent.oid = i.inhparent
WHERE n.nspname = 'bms'
  AND c.relkind = 'r'
GROUP BY COALESCE(parent.relname, c.relname)
ORDER BY SUM(pg_total_relation_size(c.oid)) DESC;

-- 3. Explicit child-partition detail for booking_seats
SELECT
    c.relname AS partition_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS heap_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_total_relation_size(c.oid) AS total_bytes
FROM pg_inherits i
JOIN pg_class p ON p.oid = i.inhparent
JOIN pg_class c ON c.oid = i.inhrelid
JOIN pg_namespace n ON n.oid = p.relnamespace
WHERE n.nspname = 'bms'
  AND p.relname = 'booking_seats'
ORDER BY c.relname;
```

## 7. 100× architecture design

The following is a proposed design, not a claim that a distributed deployment has already been implemented or benchmarked.

### 7.1 Sharding

A practical initial shard key is **`show_id`** for the booking transaction domain. A booking and its seat allocations belong to one show, and the partitioned `booking_seats` table already uses `show_id` as its hash key. Co-locating a show, its bookings and its booking-seat rows by show/shard key keeps seat locking, booking writes and show-level ticket lookups local to one shard.

The trade-off is that customer-centric and city-wide queries become cross-shard:
- R05 (customer's bookings) and R21 (top customers) can touch multiple show shards.
- R08, R11–R16, R18, R20, R24 and R25 are broad reporting queries and may aggregate across many shards.
- R01/R02 city showtime queries require a city-to-show routing map or fan-out to relevant shards.

For cross-shard reporting, stream shard-local aggregates into a reporting store or summary layer and combine partial aggregates. Avoid making interactive booking transactions wait for global analytics. A production design would need a routing directory mapping `show_id` to shard and a resharding/rebalancing plan for hot shows.

### 7.2 Primary, read replicas and caching

All writes and correctness-sensitive seat/booking reads must go to the primary:
- W01–W05.
- R03 seat availability/seat-lock view, R04 current booking status, R05 immediately updated customer bookings and R09 pending-lock queue.

Read replicas can serve read-heavy or slightly stale-tolerant queries:
- R01/R02 show discovery and showtimes.
- R06 movie search.
- R23 phone-number sign-in lookup may use a replica only when the application can tolerate replication lag; for immediate read-after-write sign-in/profile changes, route to the primary.
- R07/R17 cinema operational summaries when a small replication delay is acceptable.
- R08, R10–R16, R18–R22 and R24–R25 analytical/reporting reads.

Cache relatively stable movie metadata and popular showtime/search responses (for example R06 and parts of R01/R02) with short TTLs and explicit invalidation when show schedules or prices change. Do not cache seat availability, pending locks, payment status or other data where stale results could allow double-selling or mislead payment handling. Replica lag must be monitored; route read-after-write requests to the primary.

### 7.3 Maintenance, archiving and summary refresh

- Keep autovacuum enabled on the high-churn booking tables. For a large `booking_seats` parent/children, monitor dead tuples, vacuum duration, analyze freshness and replication lag; tune per-table autovacuum thresholds/scale factors from observed churn rather than applying one aggressive global setting.
- Run ANALYZE after bulk loads and after major distribution changes. Monitor each child partition independently as well as the parent.
- Define a retention policy with the business before archiving. Move only completed, sufficiently old shows/bookings and their dependent booking-seat rows after verifying foreign-key dependencies and audit/legal retention requirements. Keep recent and upcoming shows online. Use date-based archive partitions or a separate archive store for aged transactional history; do not drop records simply to improve benchmark results.
- Maintain summary tables for expensive customer, revenue and occupancy analytics (notably R11/R12/R18/R20/R21/R24/R25). Refresh incrementally from booking/payment changes where possible; otherwise refresh on a defined schedule (for example every 5–15 minutes for operational dashboards and nightly for historical reports). Publish the refresh timestamp and keep transactional reads on the primary.

## 8. Limitations and readiness conclusion

The large dataset is approximately 20× the seed row count. The historical benchmark in §4 has 25/30 queries meeting target and five misses. Local experiments now provide reproducible evidence for all five: R06's trigram-index test and R22's deterministic covering-index test show substantial local improvements; R21's sequential-scan planner-setting test is faster; W02's candidate index gives only a small improvement without changing the plan; and R13 has a correctly matched Phase 4 optimized-query baseline but no separate Phase 5 candidate comparison.

The partitioning implementation provides targeted pruning for R03, but R11 and R24 still scan all 16 partitions. Partitioning is therefore a useful access-path design for show-specific seat lookups, not a universal solution for analytical scans.

**Readiness verdict: partially ready, not yet fully target-compliant.** The historical benchmark remains 25/30 against target; §4 is unchanged. Local R06 and R22 experiments are promising but their test-only indexes were rolled back and their results must not be represented as deployed improvements. R21's faster plan depends on a session-local planner setting and requires production-like validation. W02 remains far above its 5 ms target, and R13 still lacks a separate Phase 5 optimization candidate. Raw plans and exact SQL/settings are included as experimental evidence, not as proof that the five historical misses are now resolved. A 100× production deployment would additionally require shard routing, replica-lag controls, tested archive/retention procedures, summary refresh monitoring and load tests beyond the current 20× dataset.

The next acceptance gate is to validate R06/R22 index trade-offs on production-like hardware, investigate a stronger W02 candidate and R13 plan, and reassess all five historical misses without changing §4's historical measurements.
