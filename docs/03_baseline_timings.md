# Baseline Query Timings

## Benchmark methodology

- Database: PostgreSQL
- Dataset: 778,048 records across 11 tables
- Workload: 25 read queries and 5 write queries
- Each query was executed 3 times.
- Execution times were collected using EXPLAIN (ANALYZE, BUFFERS).
- Write queries were executed inside transactions and rolled back.
- Timings are reported in milliseconds (ms).

## Read queries

| Query | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Average (ms) |
|---|---:|---:|---:|---:|
| R01 | 8.573 | 6.677 | 6.061 | 7.104 |
| R02 | 5.320 | 4.521 | 4.285 | 4.709 |
| R03 | 0.315 | 0.289 | 0.283 | 0.296 |
| R04 | 0.038 | 0.031 | 0.032 | 0.034 |
| R05 | 8.476 | 7.897 | 7.534 | 7.969 |
| R06 | 0.135 | 0.129 | 0.126 | 0.130 |
| R07 | 0.846 | 0.839 | 0.847 | 0.844 |
| R08 | 17.236 | 12.913 | 12.419 | 14.189 |
| R09 | 5.676 | 5.576 | 5.658 | 5.637 |
| R10 | 251.074 | 244.690 | 254.051 | 249.938 |
| R11 | 47.563 | 48.052 | 48.791 | 48.135 |
| R12 | 64.259 | 63.525 | 61.701 | 63.162 |
| R13 | 13.943 | 12.832 | 12.691 | 13.155 |
| R14 | 4.860 | 4.698 | 4.716 | 4.758 |
| R15 | 34.898 | 34.890 | 35.232 | 35.007 |
| R16 | 18.574 | 18.460 | 18.702 | 18.579 |
| R17 | 29.771 | 29.527 | 30.245 | 29.848 |
| R18 | 67.091 | 61.874 | 61.897 | 63.621 |
| R19 | 231.126 | 230.350 | 243.688 | 235.055 |
| R20 | 15.599 | 15.427 | 15.072 | 15.366 |
| R21 | 39.760 | 38.797 | 38.493 | 39.017 |
| R22 | 39.029 | 38.039 | 38.418 | 38.495 |
| R23 | 0.029 | 0.026 | 0.024 | 0.026 |
| R24 | 60.220 | 58.317 | 57.089 | 58.542 |
| R25 | 24.367 | 23.126 | 23.454 | 23.649 |

## Write queries

| Query | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Average (ms) |
|---|---:|---:|---:|---:|
| W01 | 0.656 | 0.573 | 0.524 | 0.584 |
| W02 | 9.811 | 9.490 | 9.492 | 9.598 |
| W03 | 0.640 | 0.523 | 0.545 | 0.569 |
| W04 | 7.987 | 7.320 | 7.569 | 7.625 |
| W05 | 5.234 | 4.880 | 4.848 | 4.987 |

## Summary

- Read queries benchmarked: 25
- Write queries benchmarked: 5
- Total queries benchmarked: 30
- Executions per query: 3
- Total query executions: 90
