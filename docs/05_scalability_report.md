# Scalability on the faculty dataset

**30 of 30 queries met their large-data targets** using the final optimized SQL and submitted indexes. The seed contains 778,048 rows and the large dataset contains 15,571,506 across the same 11 logical tables (20.01×). The large database includes 6,016,946 booked seats across 16 hash partitions.

PostgreSQL 18.6 on Apple M4 with 16 GiB RAM, 256 MiB shared buffers and the Asia/Kolkata session timezone. Freshly loaded databases were vacuumed and analyzed before timing. The runner opened a connection for each execution, ran each statement three times serially with EXPLAIN (ANALYZE, BUFFERS), and rolled back every write. Values are PostgreSQL execution milliseconds. Cache state was allowed to carry across runs. [Reproduction commands](04_optimization_report.md#reproduce-the-measurements).

## Optimized seed versus large

| Query | Seed ms | Large ms | Growth | Target ms | Result |
|---|---|---|---|---|---|
| R01 | 0.392 | 7.822 | 19.95× | 250 | Pass |
| R02 | 0.116 | 0.361 | 3.11× | 5 | Pass |
| R03 | 0.234 | 0.424 | 1.81× | 5 | Pass |
| R04 | 0.020 | 0.177 | 8.85× | 5 | Pass |
| R05 | 0.102 | 0.399 | 3.91× | 5 | Pass |
| R06 | 0.078 | 0.223 | 2.86× | 5 | Pass |
| R07 | 0.117 | 1.769 | 15.12× | 250 | Pass |
| R08 | 16.671 | 148.011 | 8.88× | 5000 | Pass |
| R09 | 0.040 | 0.217 | 5.42× | 5 | Pass |
| R10 | 35.962 | 305.145 | 8.49× | 5000 | Pass |
| R11 | 54.820 | 981.340 | 17.90× | 5000 | Pass |
| R12 | 58.318 | 1548.669 | 26.56× | 5000 | Pass |
| R13 | 0.088 | 0.139 | 1.58× | 250 | Pass |
| R14 | 5.078 | 47.495 | 9.35× | 5000 | Pass |
| R15 | 40.551 | 290.150 | 7.16× | 5000 | Pass |
| R16 | 19.915 | 372.439 | 18.70× | 5000 | Pass |
| R17 | 1.387 | 4.181 | 3.01× | 250 | Pass |
| R18 | 41.347 | 688.696 | 16.66× | 5000 | Pass |
| R19 | 0.740 | 2.670 | 3.61× | 5000 | Pass |
| R20 | 14.020 | 93.260 | 6.65× | 5000 | Pass |
| R21 | 39.771 | 2518.155 | 63.32× | 5000 | Pass |
| R22 | 6.535 | 7.398 | 1.13× | 250 | Pass |
| R23 | 0.022 | 0.222 | 10.09× | 5 | Pass |
| R24 | 84.773 | 1678.624 | 19.80× | 5000 | Pass |
| R25 | 23.606 | 320.355 | 13.57× | 5000 | Pass |
| W01 | 0.648 | 1.526 | 2.35× | 5 | Pass |
| W02 | 0.305 | 0.453 | 1.49× | 5 | Pass |
| W03 | 0.202 | 0.521 | 2.58× | 5 | Pass |
| W04 | 0.099 | 39.972 | 403.76× | 250 | Pass |
| W05 | 1.543 | 5.695 | 3.69× | 250 | Pass |

## Growth and access paths

- **Below 10×** — R02, R03, R04, R05, R06, R08, R09, R10, R13, R14, R15, R17, R19, R20, R22, W01, W02, W03, W05.
- **10× to below 25×** — R01, R07, R11, R16, R18, R23, R24, R25.
- **At least 25×** — R12, R21, W04.

Point lookups, ordered limits and targeted seat probes can stop after a few index entries. Reports that join or aggregate a fixed share of bookings and seats process substantially more rows at 20× scale. Growth ratios on sub-millisecond queries are sensitive to small absolute changes. Compare the buffer counts, actual rows, sort methods and loop counts in the [large plans](../benchmarks/results/large/) with the [seed plans](../benchmarks/results/optimized/).

## Large-data changes measured on the same database

The before phase used the preceding six-index design on the same partitioned large database. Both phases used the corrected oldest-booking definition for W02 and the same deterministic page order for R22. The R13 before query already used the correct NOT EXISTS predicate. R21 used default planner settings throughout. Each value averages three runs; earlier experiments remain in the local_* plan directories.

| Query | Before ms | Final ms | Finding | Before / final plans |
|---|---|---|---|---|
| R06 | 1.145 | 0.223 | GIN trigrams support substring search. | [plan](../benchmarks/results/prior_large/R06.txt) / [plan](../benchmarks/results/large/R06.txt) |
| R13 | 172.911 | 0.139 | The partial offer-code index supports a fast existence check for each offer. | [plan](../benchmarks/results/prior_large/R13.txt) / [plan](../benchmarks/results/large/R13.txt) |
| R21 | 2873.439 | 2518.155 | The customer ranking groups confirmed bookings; it still processes a large share of the table. | [plan](../benchmarks/results/prior_large/R21.txt) / [plan](../benchmarks/results/large/R21.txt) |
| R22 | 114.334 | 7.398 | The covering time/ID index reads the ordered page without sorting the entire input. OFFSET still visits the skipped entries. | [plan](../benchmarks/results/prior_large/R22.txt) / [plan](../benchmarks/results/large/R22.txt) |
| W02 | 196.344 | 0.453 | The outer query selects one booking. Its lateral subquery probes seats in screen/ID order, skips occupied seats and stops at two. | [plan](../benchmarks/results/prior_large/W02.txt) / [plan](../benchmarks/results/large/W02.txt) |

In the preceding plan W02 rejected 1,254,820 rows at the join filter. The final plan restricted the seat index to one screen, inserted two rows in each run, and averaged 0.453 ms. An independent rolled-back execution returned booking 25026, show 3092426 and seats 1254821 and 1254822.

To reproduce the before phase, use the six indexes in revision `2438c7a` on the partitioned large database. Execute R06, R13, R21 and R22 from the final optimized workload and W02 from the corrected baseline. Then apply the final index script and benchmark the optimized workload.

The workload fixes the R22 page order when timestamps tie, selects the earliest pending timestamp in W02/W03, and uses the July half-open interval and Kolkata weekend in W05. These definitions apply in both benchmark workloads.

## Storage and partitioning

Heap and index measurements use pg_relation_size and pg_indexes_size per ordinary relation, summed across child partitions. Database totals include catalogs and other overhead. Measurements were taken after benchmarking.

| Dataset | pg_database_size (MiB) |
|---|---|
| seed | 140.22 |
| large | 2,794.27 |

| Table | Seed heap MiB | Seed indexes MiB | Large heap MiB | Large indexes MiB |
|---|---|---|---|---|
| booking_seats | 15.38 | 16.16 | 299.48 | 506.28 |
| bookings | 17.06 | 27.36 | 338.06 | 531.63 |
| cities | 0.01 | 0.02 | 0.01 | 0.02 |
| customers | 3.65 | 4.39 | 74.75 | 104.96 |
| movie_reviews | 1.95 | 0.71 | 39.02 | 13.97 |
| movies | 0.02 | 0.06 | 0.41 | 0.49 |
| offers | 0.01 | 0.02 | 0.01 | 0.02 |
| screens | 0.03 | 0.03 | 0.49 | 0.23 |
| seats | 4.45 | 6.08 | 88.88 | 120.87 |
| shows | 9.88 | 23.98 | 187.88 | 476.50 |
| venues | 0.02 | 0.02 | 0.24 | 0.08 |

The implementation in `sql/08_partitioning.sql` converts `bms.booking_seats` to **HASH partitioning on `show_id`**, with 16 partitions (`booking_seats_p00` through `booking_seats_p15`), modulus 16.

The migration runs in a transaction, takes an ACCESS EXCLUSIVE lock, creates the partitioned replacement and its constraints, creates the 16 child partitions, copies the rows, checks that old and new row counts match, swaps the table, runs ANALYZE and commits. The script raises an exception if its row-count comparison fails.

A partitioned unique or primary-key constraint must include every partition-key column. PostgreSQL cannot enforce a globally unique key across partitions using a key that omits the partition key. Therefore the partitioned table uses a key containing `show_id`, for example **PRIMARY KEY (show_id, seat_id)**, rather than attempting to keep a globally unique `seat_id`-only key on the partitioned parent.

### Evidence of pruning and non-pruning

The large R03 plan accesses `booking_seats_p00` through an index-only scan with `Index Cond: (show_id = 144446)`; the plan does not scan all 16 child tables. This is the positive example: equality on the hash partition key allows PostgreSQL to select the relevant hash partition.

By contrast, R11 and R24 scan all 16 `booking_seats` partitions because their analytical aggregation does not constrain `show_id` to a single hash value. Hash partitioning is therefore useful for targeted show lookups, but it does not remove the work from queries that need data across the full table.

## Architecture at 100×

The following is a proposed design, not a claim that a distributed deployment has already been implemented or benchmarked.

### Sharding

At 20×, R03 already prunes to one seat partition and averages 0.424 ms. R21 averages 2,518.155 ms while processing 2,671,876 confirmed bookings. At 100×, the former supports routing by show and the latter motivates aggregating customer rankings away from the booking primary.

A practical initial shard key is **`show_id`** for the booking transaction domain. A booking and its seat allocations belong to one show, and the partitioned `booking_seats` table already uses `show_id` as its hash key. Co-locating a show, its bookings and its booking-seat rows by show/shard key keeps seat locking, booking writes and show-level ticket lookups local to one shard.

The trade-off is that customer-centric and city-wide queries become cross-shard:
- R05 (customer's bookings) and R21 (top customers) can touch multiple show shards.
- R08, R11–R16, R18, R20, R24 and R25 are broad reporting queries and may aggregate across many shards.
- R01/R02 city showtime queries require a city-to-show routing map or fan-out to relevant shards.

For cross-shard reporting, stream shard-local aggregates into a reporting store or summary layer and combine partial aggregates. Avoid making interactive booking transactions wait for global analytics. A production design would need a routing directory mapping `show_id` to shard and a resharding/rebalancing plan for hot shows.

### Primary, read replicas and caching

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

### Maintenance, archiving and summary refresh

- Keep autovacuum enabled on the high-churn booking tables. For a large `booking_seats` parent/children, monitor dead tuples, vacuum duration, analyze freshness and replication lag; tune per-table autovacuum thresholds/scale factors from observed churn rather than applying one aggressive global setting.
- Run ANALYZE after bulk loads and after major distribution changes. Monitor each child partition independently as well as the parent.
- Define a retention policy with the business before archiving. Move only completed, sufficiently old shows/bookings and their dependent booking-seat rows after verifying foreign-key dependencies and audit/legal retention requirements. Keep recent and upcoming shows online. Use date-based archive partitions or a separate archive store for aged transactional history; do not drop records simply to improve benchmark results.
- Maintain summary tables for expensive customer, revenue and occupancy analytics (notably R11/R12/R18/R20/R21/R24/R25). Refresh incrementally from booking/payment changes where possible; otherwise refresh on a defined schedule (for example every 5–15 minutes for operational dashboards and nightly for historical reports). Publish the refresh timestamp and keep transactional reads on the primary.

## Readiness for next year

The database meets all 30 SQL timing targets on the faculty dataset at the projected 20× volume. This supports using the current design for the measured workload. Production readiness still depends on seat allocation under concurrent checkouts and the impact of large reports on booking traffic. The runs measured one statement at a time. The proposed 100× design also needs measurements of replica lag and cross-shard aggregation cost.
