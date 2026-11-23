# Query optimization on the seed dataset

The sum of the 30 statement averages fell from **1100.236 ms to 447.500 ms** (2.46×). 27 of the 30 averages decreased. The totals include the intentional R13 correctness correction. They describe serial SQL execution on the seed dataset.

PostgreSQL 18.6 on Apple M4 with 16 GiB RAM, 256 MiB shared buffers and the Asia/Kolkata session timezone. Freshly loaded databases were vacuumed and analyzed before timing. The runner opened a connection for each execution, ran each statement three times serially with EXPLAIN (ANALYZE, BUFFERS), and rolled back every write. Values are PostgreSQL execution milliseconds. Cache state was allowed to carry across runs.

## Plans and timings

| Query | Baseline ms | Plan problem or access pattern | Change | Optimized ms | Speedup | Time saved | Result |
|---|---|---|---|---|---|---|---|
| R01 | 8.136 | Non-sargable `DATE(s.starts_at)` prevented index use | Sargable range + `idx_shows_screen_starts` | 0.392 | 20.76× | +95.2% | Matched |
| R02 | 4.817 | Seq scan on 160k shows to filter movie 2 | Composite index `idx_shows_movie_starts` | 0.116 | 41.53× | +97.6% | Matched |
| R03 | 0.651 | Already efficient (uses PKs and unique index) | Kept unchanged | 0.234 | 2.78× | +64.1% | Matched |
| R04 | 0.177 | Already efficient (uses `uq_bookings_booking_code`) | Kept unchanged | 0.020 | 8.85× | +88.7% | Matched |
| R05 | 11.552 | Seq scan on 150k bookings for customer 1331 | Foreign key index `idx_bookings_customer_id` | 0.102 | 113.25× | +99.1% | Matched |
| R06 | 0.086 | Leading-wildcard title filter | GIN title trigrams | 0.078 | 1.10× | +9.3% | Matched |
| R07 | 1.057 | Non-sargable `starts_at::date` | Sargable range + `idx_shows_screen_starts` | 0.117 | 9.03× | +88.9% | Matched |
| R08 | 14.546 | Seq scan on bookings; redundant distinct | Remove redundant DISTINCT; movie/time index filters shows | 16.671 | 0.87× | -14.6% | Matched |
| R09 | 6.475 | Seq scan on 150k bookings for 10 pending rows | Partial index `idx_bookings_pending_time` | 0.040 | 161.88× | +99.4% | Matched |
| R10 | 231.279 | Non-sargable gap tested 8.1M pairs in hash join | Sargable range + `idx_shows_screen_starts` | 35.962 | 6.43× | +84.5% | Matched |
| R11 | 58.166 | Full 300k booking_seats aggregation | Aggregation over a broad input | 54.820 | 1.06× | +5.8% | Matched |
| R12 | 81.903 | Hash aggregation over 133k confirmed bookings | Planner retained bulk scans | 58.318 | 1.40× | +28.8% | Matched |
| R13 | 13.570 | NULLs invalidate NOT IN | NULL-safe anti join; partial offer-code index | 0.088 | 154.20× | +99.4% | Corrected |
| R14 | 5.072 | Aggregate reviews for eligible movies | Kept unchanged | 5.078 | 1.00× | -0.1% | Matched |
| R15 | 41.020 | Full table temporal grouping of bookings | Broad temporal aggregation | 40.551 | 1.01× | +1.1% | Matched |
| R16 | 20.260 | Full scan joining June shows to bookings | Planner retained bulk scans | 19.915 | 1.02× | +1.7% | Matched |
| R17 | 39.775 | Subquery joined all shows across all screens | Added `s.screen_id = 101` + `idx_shows_screen_starts` | 1.387 | 28.68× | +96.5% | Matched |
| R18 | 67.456 | Non-sargable `EXTRACT(YEAR)` on `starts_at` | Sargable range + `idx_bookings_show_id` | 41.347 | 1.63× | +38.7% | Matched |
| R19 | 246.678 | Correlated subquery executed 207 times | Rewrote to `LEFT JOIN` + composite index | 0.740 | 333.35× | +99.7% | Matched |
| R20 | 15.347 | Non-sargable `booked_at::date BETWEEN` | Sargable range + booking-time index | 14.020 | 1.09× | +8.6% | Matched |
| R21 | 40.821 | Reads 89% of bookings table | Aggregation over a broad input | 39.771 | 1.03× | +2.6% | Matched |
| R22 | 39.837 | Deep sorted offset | Order ties by booking ID; covering time index | 6.535 | 6.10× | +83.6% | Matched |
| R23 | 0.183 | Already optimal (unique index on phone) | Kept unchanged | 0.022 | 8.32× | +88.0% | Matched |
| R24 | 81.659 | Join ticket prices to shows starting in 2026 | Aggregate qualifying seats by city and seat class | 84.773 | 0.96× | -3.8% | Matched |
| R25 | 26.502 | Filters late-night shows in June | Accelerated via `idx_shows_movie_starts` | 23.606 | 1.12× | +10.9% | Matched |
| W01 | 1.003 | Single-row insert | Maintain secondary indexes | 0.648 | 1.55× | +35.4% | Matched |
| W02 | 18.806 | Seat-ID scan can cross unrelated screens | Oldest pending index; per-screen ordered lookup and occupied-seat probes | 0.305 | 61.66× | +98.4% | Matched |
| W03 | 8.546 | Find earliest pending timestamp | Partial index ordered by time and ID | 0.202 | 42.31× | +97.6% | Matched |
| W04 | 8.619 | Seq scan on bookings to delete expired locks | Partial index `idx_bookings_pending_time` | 0.099 | 87.06× | +98.9% | Matched |
| W05 | 6.237 | Filter shows of movie 2 by local July weekends | Movie/time range index; Kolkata calendar | 1.543 | 4.04× | +75.3% | Matched |

## Five largest relative improvements

| Query | Baseline → optimized ms | Plan change | Before / after |
|---|---|---|---|
| R19 | 246.678 → 0.740 | Rewrote to `LEFT JOIN` + composite index | [plan](../benchmarks/results/baseline/R19.txt) / [plan](../benchmarks/results/optimized/R19.txt) |
| R09 | 6.475 → 0.040 | Partial index `idx_bookings_pending_time` | [plan](../benchmarks/results/baseline/R09.txt) / [plan](../benchmarks/results/optimized/R09.txt) |
| R13 | 13.570 → 0.088 | NULL-safe anti join; partial offer-code index | [plan](../benchmarks/results/baseline/R13.txt) / [plan](../benchmarks/results/optimized/R13.txt) |
| R05 | 11.552 → 0.102 | Foreign key index `idx_bookings_customer_id` | [plan](../benchmarks/results/baseline/R05.txt) / [plan](../benchmarks/results/optimized/R05.txt) |
| W04 | 8.619 → 0.099 | Partial index `idx_bookings_pending_time` | [plan](../benchmarks/results/baseline/W04.txt) / [plan](../benchmarks/results/optimized/W04.txt) |

## Correctness

The comparison script checks full row values and duplicate counts in both directions using EXCEPT ALL on a repeatable-read snapshot. It checks the ordered R22 page against an independently ranked list of 25 booking IDs. W01–W05 compare every returned affected row from the same starting state using savepoints. The R24 fixture verifies the local show year at both New Year boundaries, including advance bookings. Boundary fixtures cover earliest-booking ties, occupied seats, local midnight, wrong movies, weekdays and August exclusion.

R13 is an intentional correction. A NULL offer code in the original NOT IN subquery causes unmatched candidates to evaluate to UNKNOWN. The original returned zero rows. NOT EXISTS returned seven unused offers and matched an independent NULL-filtered reference on both datasets.

[Seed comparison](evidence/final_seed_results.csv) · [Large comparison](evidence/final_large_results.csv) · [Runnable checks](../benchmarks/check_results.py)

## Index costs and write impact

| Index | Seed KiB | % of table heap | Large MiB |
|---|---|---|---|
| `idx_bookings_customer_id` | 1,960 | 11.2% | 38.03 |
| `idx_bookings_pending_time` | 16 | 0.1% | 0.02 |
| `idx_bookings_redeemed_offer` | 176 | 1.0% | 3.05 |
| `idx_bookings_show_id` | 2,912 | 16.7% | 56.48 |
| `idx_bookings_support_page` | 9,912 | 56.7% | 193.33 |
| `idx_movies_title_trgm` | 48 | 200.0% | 0.34 |
| `idx_seats_screen_seat` | 2,072 | 45.5% | 40.28 |
| `idx_shows_movie_starts` | 3,000 | 29.7% | 55.88 |
| `idx_shows_screen_starts` | 4,960 | 49.1% | 96.32 |

See [index definitions](../sql/05_indexes.sql) for query IDs, column order and access methods. The R22 covering index trades storage and maintenance on booking writes for an index-only page scan; the partial booking indexes restrict maintenance to qualifying rows. GIN maintenance applies to movie title writes, which are outside this workload.

| Write | Baseline ms | Optimized ms | Delta ms (positive = slower) |
|---|---|---|---|
| W01 | 1.003 | 0.648 | -0.355 |
| W02 | 18.806 | 0.305 | -18.501 |
| W03 | 8.546 | 0.202 | -8.344 |
| W04 | 8.619 | 0.099 | -8.520 |
| W05 | 6.237 | 1.543 | -4.694 |

All five seed writes were faster in this sample. R08 remained slower (14.546 to 16.671 ms) and still scanned bookings for the weekend aggregation. R24 also ran slower on the optimized seed and uses the same annual aggregation in both versions. R14 differed by 0.006 ms on a largely unchanged review aggregation.

These deltas include lookup savings, index maintenance and run variability. Three runs cannot isolate the cost of maintaining one index. Broad revenue and seat-class aggregations still need input from many rows; their raw plans show the scans and aggregation costs.

## Reproduce the measurements

From the repository root, set the libpq connection variables and use fresh databases named seed and large. The loaders expect seed_data/ and large_data/ respectively. Use Asia/Kolkata for both sessions.

```sh
export PGOPTIONS="-c timezone=Asia/Kolkata"
for db in seed large; do
  createdb "$db"
  psql -X -v ON_ERROR_STOP=1 -d "$db" -f sql/01_schema.sql
done
psql -X -v ON_ERROR_STOP=1 -d seed -f sql/02_load_data.sql
psql -X -v ON_ERROR_STOP=1 -d large -f sql/07_load_large_data.sql
psql -X -v ON_ERROR_STOP=1 -d large -f sql/08_partitioning.sql
vacuumdb -z seed
vacuumdb -z large
./benchmarks/run_benchmark.sh seed baseline 3 queries/workload_30.sql
for db in seed large; do
  psql -X -v ON_ERROR_STOP=1 -d "$db" -f sql/05_indexes.sql
done
./benchmarks/run_benchmark.sh seed optimized 3 sql/06_optimized_queries.sql
./benchmarks/run_benchmark.sh large large 3 sql/06_optimized_queries.sql
python3 benchmarks/check_results.py seed
python3 benchmarks/check_results.py large
```
