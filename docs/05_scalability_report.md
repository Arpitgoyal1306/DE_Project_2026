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

