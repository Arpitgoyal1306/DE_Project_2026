# CP4 – Scalability Report

## 1. Introduction

The objective of this phase is to evaluate how the BookMyShow database performs when the dataset grows significantly in size.

The report compares the original baseline benchmark with the large-dataset benchmark after implementing partitioning on the `booking_seats` table.

The analysis focuses on query execution time, execution plans, partition pruning, and the performance impact of increased data volume.

## 2. Dataset Overview

The project uses two dataset sizes:

| Dataset | Total Records |
|---|---:|
| Baseline dataset | 778,048 |
| Large dataset | Approximately 15.57 million |

The large dataset provides a way to evaluate database scalability under a substantially higher data volume.

## 3. Benchmark Methodology

The same 30-query workload was used for both benchmark phases:

- 25 read queries (R01–R25).
- 5 write queries (W01–W05).
- Each query was executed 3 times.
- Query performance was measured using `EXPLAIN (ANALYZE, BUFFERS)`.
- Average execution time was used for the primary comparison.
- Raw execution plans were retained for further analysis.

Write queries were executed inside transactions using `BEGIN` and `ROLLBACK` so that benchmark modifications did not persist in the database.

## 4. Partitioning Strategy

Details of the partitioning implementation and validation will be documented in this section.

## 5. Large-Scale Benchmark Results

The large-dataset benchmark results and comparison with the baseline will be documented in this section.

## 6. Query Performance Analysis

The execution plans and major performance bottlenecks will be analyzed in this section.

## 7. Findings and Conclusion

The scalability findings, limitations, and recommendations will be documented in this section.

## 4. Partitioning Strategy and Validation

### 4.1 Large Dataset Loading

The large dataset was imported using `sql/07_load_large_data.sql` into the `bms` schema.

All 11 tables were loaded in foreign-key dependency order. The import process included row-count validation and an `ANALYZE` operation.

The total imported dataset contains **15,571,506 rows**.

The `booking_seats` table contains **6,016,946 rows**, making it the largest table in the dataset.

### 4.2 Hash Partitioning

The `booking_seats` table was selected for partitioning because it stores booking-to-seat allocations and contains a large number of records.

The implementation in `sql/08_partitioning.sql` uses **hash partitioning on `show_id`**.

Sixteen partitions were created:

- `booking_seats_p00`
- `booking_seats_p01`
- `booking_seats_p02`
- `booking_seats_p03`
- `booking_seats_p04`
- `booking_seats_p05`
- `booking_seats_p06`
- `booking_seats_p07`
- `booking_seats_p08`
- `booking_seats_p09`
- `booking_seats_p10`
- `booking_seats_p11`
- `booking_seats_p12`
- `booking_seats_p13`
- `booking_seats_p14`
- `booking_seats_p15`

Each partition is assigned a different hash remainder using a modulus of 16.

### 4.3 Migration and Data Integrity

The partition migration was performed inside a transaction.

The script follows these steps:

1. Starts a transaction.
2. Acquires an `ACCESS EXCLUSIVE` lock on the original `booking_seats` table.
3. Creates a new partitioned table with the required constraints and foreign keys.
4. Creates all 16 hash partitions.
5. Adds an index on `(booking_id, seat_id)` for booking-based lookups.
6. Copies the original records into the partitioned table.
7. Compares the original and partitioned row counts.
8. Replaces the original table with the validated partitioned table.
9. Runs `ANALYZE` and commits the transaction.

The migration raises an exception if the original and partitioned row counts do not match. This prevents the migration from committing with a detected row-count mismatch.

### 4.4 Validation Results

The large dataset validation confirmed that all 11 table counts matched their corresponding CSV row counts.

The partition migration script includes a row-count validation step that compares the original and partitioned tables before replacing the original. The large benchmark execution plans also confirm that queries access the created child partitions.

These checks provide evidence that the migration preserves the existing records and maintains the expected table structure.


## 5. Baseline vs Large Benchmark Comparison

The following table compares average execution times from the baseline and large-dataset benchmarks.

Percentage change is calculated as:

`((Large Average - Baseline Average) / Baseline Average) × 100`

A positive percentage indicates increased execution time, while a negative percentage indicates reduced execution time.

| Query | Type | Baseline Avg (ms) | Large Avg (ms) | Change (%) |
|---|---|---:|---:|---:|
| R01 | READ | 7.104 | 61.507 | +765.81% |
| R02 | READ | 4.709 | 1.475 | -68.68% |
| R03 | READ | 0.296 | 1.028 | +247.30% |
| R04 | READ | 0.034 | 0.364 | +970.59% |
| R05 | READ | 7.969 | 0.750 | -90.59% |
| R06 | READ | 0.130 | 5.076 | +3804.62% |
| R07 | READ | 0.844 | 2.714 | +221.56% |
| R08 | READ | 14.189 | 410.586 | +2793.69% |
| R09 | READ | 5.637 | 0.258 | -95.42% |
| R10 | READ | 249.938 | 574.650 | +129.92% |
| R11 | READ | 48.135 | 1609.278 | +3243.26% |
| R12 | READ | 63.162 | 3344.183 | +5194.61% |
| R13 | READ | 13.155 | 513.060 | +3800.11% |
| R14 | READ | 4.758 | 109.348 | +2198.19% |
| R15 | READ | 35.007 | 513.223 | +1366.06% |
| R16 | READ | 18.579 | 773.969 | +4065.83% |
| R17 | READ | 29.848 | 2.952 | -90.11% |
| R18 | READ | 63.621 | 1352.006 | +2025.09% |
| R19 | READ | 235.055 | 6.846 | -97.09% |
| R20 | READ | 15.366 | 235.925 | +1435.37% |
| R21 | READ | 39.017 | 8609.623 | +21966.34% |
| R22 | READ | 38.495 | 285.333 | +641.22% |
| R23 | READ | 0.026 | 0.225 | +765.38% |
| R24 | READ | 58.542 | 1869.174 | +3092.88% |
| R25 | READ | 23.649 | 623.449 | +2536.26% |
| W01 | WRITE | 0.584 | 2.311 | +295.72% |
| W02 | WRITE | 9.598 | 160.828 | +1575.64% |
| W03 | WRITE | 0.569 | 1.000 | +75.75% |
| W04 | WRITE | 7.625 | 29.903 | +292.17% |
| W05 | WRITE | 4.987 | 10.433 | +109.20% |

### Initial Observations

- Query performance varies significantly across the workload as the dataset grows.
- Some queries benefit from index-based access paths, while others still perform large sequential scans.
- Partitioning does not guarantee faster execution for every query. Its effectiveness depends on whether the query can use the partition key and eliminate irrelevant partitions.
- The detailed causes of major performance changes are discussed in the query performance analysis section.

## 6. Query Performance and Execution Plan Analysis

The large-dataset execution plans show that query performance depends on the amount of data processed, the available indexes, and whether partition pruning can eliminate unnecessary partitions.

### 6.1 R21 – Large Index Scan

R21 increased from an average of 39.017 ms to 8,609.623 ms.

The large execution plan uses `idx_bookings_customer_id`, but the index scan still returns approximately 2,671,876 rows. It also reports approximately 1,889,536 shared buffer reads in one run.

This demonstrates that using an index does not guarantee fast execution when a query must process millions of matching records.

### 6.2 R12 – Sequential Scans and Temporary I/O

R12 increased from 63.162 ms to 3,344.183 ms.

The large execution plan performs sequential scans on both `bookings` and `shows`. It also reports substantial temporary block activity, including 29,130 temporary blocks read and 40,692 written in one run.

The larger input tables and intermediate query operations contribute to the increased execution time.

### 6.3 R11 and R24 – Partition Scanning

R11 increased from 48.135 ms to 1,609.278 ms, while R24 increased from 58.542 ms to 1,869.174 ms.

Both execution plans show scans across all 16 `booking_seats` hash partitions.

This indicates that partition pruning did not eliminate partitions for these queries. Since the queries need data across the partitioned table rather than restricting access to a particular `show_id`, PostgreSQL must process data from multiple partitions.

The plans also show sequential scans on related tables such as `seats` and `screens`.

Partitioning therefore does not automatically improve queries that need to examine a large portion of the partitioned data.

### 6.4 R18 – Large Parallel Scans

R18 increased from 63.621 ms to 1,352.006 ms.

Its large execution plan uses parallel sequential scans on `bookings` and `shows`. It also processes large intermediate results and reports substantial temporary block activity.

Parallel execution helps distribute the scan work, but it does not eliminate the cost of processing millions of records.

### 6.5 Overall Execution Plan Observations

The analyzed queries demonstrate several important points:

- Index scans can still be expensive when they return millions of rows.
- Sequential scans may become costly as table sizes increase.
- Temporary disk activity can add significant overhead to complex queries.
- Hash partitioning is most useful when queries can benefit from partition pruning.
- Queries scanning all partitions may not receive a significant performance benefit from partitioning.
- Parallel scans can help with large workloads but do not remove the underlying data-processing cost.

These results show that partitioning should be considered alongside query design, indexing, filtering conditions, and execution-plan analysis.

## 7. Findings, Recommendations and Conclusion

### 7.1 Key Findings

1. **Dataset growth:** The dataset increased from 778,048 rows in the baseline environment to 15,571,506 rows in the large environment, approximately 20 times larger.
2. **Performance varies by query:** Not all queries scale equally. Some remain relatively fast, while several become significantly slower as the data volume increases.
3. **Selective index usage:** Queries such as R02, R04, R09 and R23 continue to show efficient index-based access in the large environment.
4. **Large scans are expensive:** R11, R12, R18, R21 and R24 show substantial execution times on the large dataset, with sequential scans, large result sets or temporary I/O contributing to the workload.
5. **Partitioning is query-dependent:** The `booking_seats` table is hash-partitioned on `show_id` into 16 partitions. However, R11 and R24 access all 16 partitions, showing that partitioning alone does not guarantee partition pruning or faster execution.

### 7.2 Recommendations

- Review frequently executed slow queries and their filter and join conditions.
- Evaluate suitable indexes on frequently filtered and joined columns, using execution plans to confirm whether they help.
- Where logically appropriate, include conditions on the partition key `show_id` so PostgreSQL can potentially eliminate irrelevant partitions.
- Investigate queries with high temporary I/O and large sequential scans.
- Compare alternative query plans and index designs using `EXPLAIN (ANALYZE, BUFFERS)`.
- Repeat benchmarks under consistent hardware, database configuration and cache conditions before making optimization decisions.

### 7.3 Limitations

- Benchmarks were performed in a single local database environment.
- Each query was executed three times, so timings may vary due to caching and system load.
- Results depend on PostgreSQL configuration, available resources and query-planner decisions.
- The report evaluates the recorded workload and does not represent every possible production workload.

### 7.4 Conclusion

The scalability experiment increased the dataset to approximately 15.57 million rows and evaluated all 30 workload queries. The results show that query performance is highly dependent on query structure, indexes, data volume and execution plans.

Hash partitioning provides a structured way to organize the large `booking_seats` table, but its benefits depend on whether queries can make effective use of the partition key. Several queries still scan large portions of the data and require further optimization.

Overall, the experiment demonstrates why database performance must be evaluated at realistic data volumes. Indexing, partitioning and query optimization should be guided by measured execution plans rather than assumptions.
