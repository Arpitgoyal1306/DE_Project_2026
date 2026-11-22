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
