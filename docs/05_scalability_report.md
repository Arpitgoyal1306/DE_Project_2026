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

The partition migration was also tested on a separate disposable database. Validation confirmed that all **300,389 seed `booking_seats` records** were preserved and that all 16 partitions were created.

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
