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

The large benchmark shows five target misses. The available repository contains the measured large plans, but this local environment does not contain `large_data.zip` or a large-data database. Therefore **no large-data optimization rerun or measured before/after fix is claimed here**. The actions below are concrete next steps to test; they are not represented as completed fixes.

| Query | Target | Large average | Plan evidence | Next change to test |
|---|---:|---:|---|---|
| R06 | <5 ms | 5.076 ms | Sequential scan of 6,000 movies for `ILIKE '%kalki%'`; 300 rows returned. | Test a `pg_trgm` GIN index on `movies.title`; retain it only if the measured plan and timing improve enough to meet target. |
| W02 | <5 ms | 160.828 ms | Plan scans 521,522 rows from `seats` using its primary key, then removes rows by screen join/filter before inserting two rows. | Test an index beginning with `seats(screen_id, seat_id)` and rewrite candidate-seat selection to constrain the target screen before ordering/limiting. Recheck locking and seat uniqueness. |
| R13 | <250 ms | 513.060 ms | Hash anti-join scans 3,004,077 bookings to find offers not redeemed. | Test a partial index on non-NULL `bookings(offer_code)` and compare the anti-join plan; the `NOT EXISTS` rewrite fixes NULL correctness but still scans a large input. |
| R22 | <250 ms | 285.333 ms | Index scan reads 100,025 rows to satisfy `OFFSET 100000 LIMIT 25`. | Replace deep OFFSET pagination with keyset pagination using a stable, unique ordering key (for example `booked_at` plus `booking_id`); the page cursor must be defined by the preceding page's last row. |
| R21 | <5,000 ms | 8,609.623 ms | Index scan returns 2,671,876 confirmed 2026 bookings, then aggregates 771,482 customers; one run reports 1,889,536 shared-buffer reads. | Test a maintained daily/customer summary aggregate or incremental rollup. A normal index alone is unlikely to remove the cost of aggregating millions of qualifying rows. |

These five misses remain **open optimization work** until the proposed changes are implemented, checked for result equivalence, and benchmarked on the large dataset. No target is marked as met based on a proposed design alone.

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

### 6.2 Large database (not measured locally)

The large dataset validation file and all 30 large benchmark plans are present in the repository, but the large database is not present in this working copy. Consequently, its measured database size and heap/index/partition breakdown cannot be reported from this machine. The 15,571,506 row count is known, but **row count is not a substitute for measured disk size**. This measurement remains outstanding and must be collected on the machine that holds the large database (the database used for PR #10, or a team machine that loads the faculty archive). It would be misleading to extrapolate 116 MB linearly and label it as an observed size.

Run the following from a psql session connected to the loaded large database. The first query reports the database total. The second groups ordinary tables and leaf partitions by their logical parent, so the 16 booking_seats leaf partitions are summed once and the partitioned parent is not double-counted.

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

Record the database total and the grouped booking_seats total in the report; retain the third query's 16-row output as the partition-level evidence. The byte columns are included so totals can be checked without rounding.

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

The large dataset is approximately 20× the seed row count, but five of the 30 queries miss their assigned performance targets. The strongest scale-specific bottlenecks are the broad booking aggregation in R21, the large candidate-seat scan in W02, the full booking scan in R13, deep OFFSET pagination in R22 and the title search threshold miss in R06.

The partitioning implementation provides targeted pruning for R03, but R11 and R24 still scan all 16 partitions. Partitioning is therefore a useful access-path design for show-specific seat lookups, not a universal solution for analytical scans.

**Readiness verdict: partially ready, not yet fully target-compliant.** 25/30 queries meet the large-data targets. The five misses need measured fixes and result-equivalence checks. Large-database storage is also still unmeasured because the large data archive/database is not available in this local environment. A 100× production deployment would additionally require shard routing, replica-lag controls, tested archive/retention procedures, summary refresh monitoring and load tests beyond the current 20× dataset.

The next acceptance gate is to obtain the large dataset, measure its real database/table/index/partition storage, implement and benchmark the five proposed fixes, and verify all 30 target results before calling the system ready.
