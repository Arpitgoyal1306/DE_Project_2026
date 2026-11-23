# Baseline query timings

PostgreSQL 18.6 on Apple M4 with 16 GiB RAM, 256 MiB shared buffers and the Asia/Kolkata session timezone. Freshly loaded databases were vacuumed and analyzed before timing. The runner opened a connection for each execution, ran each statement three times serially with EXPLAIN (ANALYZE, BUFFERS), and rolled back every write. Values are PostgreSQL execution milliseconds. Cache state was allowed to carry across runs. The seed contains 778,048 rows across 11 tables. Only schema constraints and their indexes were present.

| Query | Run 1 | Run 2 | Run 3 | Mean (ms) | Scan nodes, final run | Reason |
|---|---|---|---|---|---|---|
| R01 | 12.110 | 6.076 | 6.221 | 8.136 | Index Scan using movies_pkey on movies; Seq Scan on screens; Seq Scan on venues; Index Scan using ex_shows_no_overlap on shows | Non-sargable `DATE(s.starts_at)` prevented index use |
| R02 | 4.869 | 4.497 | 5.084 | 4.817 | Seq Scan on screens; Seq Scan on venues; Index Scan using ex_shows_no_overlap on shows | Seq scan on 160k shows to filter movie 2 |
| R03 | 1.432 | 0.259 | 0.261 | 0.651 | Index Scan using shows_pkey on shows; Index Scan using uq_seats_screen_position on seats; Index Only Scan using pk_booking_seats on booking_seats | Already efficient (uses PKs and unique index) |
| R04 | 0.483 | 0.025 | 0.023 | 0.177 | Index Scan using uq_bookings_booking_code on bookings | Already efficient (uses `uq_bookings_booking_code`) |
| R05 | 17.940 | 8.443 | 8.273 | 11.552 | Seq Scan on bookings; Index Scan using shows_pkey on shows; Seq Scan on movies; Seq Scan on screens; Seq Scan on venues | Seq scan on 150k bookings for customer 1331 |
| R06 | 0.080 | 0.089 | 0.088 | 0.086 | Seq Scan on movies | Leading-wildcard title filter |
| R07 | 1.185 | 1.003 | 0.982 | 1.057 | Seq Scan on screens; Bitmap Heap Scan on shows; Bitmap Index Scan on ex_shows_no_overlap; Index Only Scan using pk_booking_seats on booking_seats | Non-sargable `starts_at::date` |
| R08 | 15.030 | 14.816 | 13.792 | 14.546 | Seq Scan on bookings; Seq Scan on shows; Seq Scan on movies | Seq scan on bookings; redundant distinct |
| R09 | 5.908 | 7.142 | 6.374 | 6.475 | Seq Scan on bookings | Seq scan on 150k bookings for 10 pending rows |
| R10 | 245.090 | 224.330 | 224.417 | 231.279 | Seq Scan on shows | Non-sargable gap tested 8.1M pairs in hash join |
| R11 | 59.137 | 55.136 | 60.225 | 58.166 | Seq Scan on booking_seats; Seq Scan on seats; Seq Scan on screens | Full 300k booking_seats aggregation |
| R12 | 92.121 | 84.005 | 69.584 | 81.903 | Seq Scan on bookings; Seq Scan on shows | Hash aggregation over 133k confirmed bookings |
| R13 | 13.680 | 13.497 | 13.534 | 13.570 | Seq Scan on offers; Seq Scan on bookings | NULLs invalidate NOT IN |
| R14 | 5.115 | 5.024 | 5.076 | 5.072 | Seq Scan on movie_reviews; Seq Scan on movies | Aggregate reviews for eligible movies |
| R15 | 40.785 | 40.538 | 41.736 | 41.020 | Seq Scan on bookings | Full table temporal grouping of bookings |
| R16 | 20.574 | 20.033 | 20.174 | 20.260 | Seq Scan on bookings; Seq Scan on shows; Seq Scan on screens; Seq Scan on venues | Full scan joining June shows to bookings |
| R17 | 35.475 | 34.080 | 49.770 | 39.775 | Seq Scan on booking_seats; Seq Scan on shows; Index Scan using uq_seats_screen_position on seats | Subquery joined all shows across all screens |
| R18 | 69.851 | 66.888 | 65.630 | 67.456 | Seq Scan on bookings; Seq Scan on shows; Seq Scan on movies; Seq Scan on screens; Seq Scan on venues | Non-sargable `EXTRACT(YEAR)` on `starts_at` |
| R19 | 248.711 | 236.962 | 254.362 | 246.678 | Seq Scan on shows; Index Scan using uq_bookings_id_show on bookings | Correlated subquery executed 207 times |
| R20 | 15.296 | 15.479 | 15.267 | 15.347 | Seq Scan on bookings | Non-sargable `booked_at::date BETWEEN` |
| R21 | 39.791 | 41.769 | 40.902 | 40.821 | Seq Scan on bookings | Reads 89% of bookings table |
| R22 | 39.596 | 39.840 | 40.074 | 39.837 | Seq Scan on bookings | Deep sorted offset |
| R23 | 0.506 | 0.022 | 0.021 | 0.183 | Index Scan using uq_customers_phone on customers | Already optimal (unique index on phone) |
| R24 | 80.752 | 81.979 | 82.246 | 81.659 | Seq Scan on booking_seats; Seq Scan on shows; Seq Scan on seats; Seq Scan on screens; Seq Scan on venues | Join ticket prices to shows starting in 2026 and aggregate by city and seat class. |
| R25 | 26.939 | 26.421 | 26.146 | 26.502 | Seq Scan on booking_seats; Seq Scan on shows; Seq Scan on screens | Filters late-night shows in June |
| W01 | 1.665 | 0.612 | 0.732 | 1.003 | (no scan) | Single-row insert |
| W02 | 19.792 | 18.272 | 18.354 | 18.806 | Seq Scan on bookings; Index Scan using seats_pkey on seats; Index Only Scan using uq_bookings_id_show on bookings; Index Scan using shows_pkey on shows; Index Only Scan using pk_booking_seats on booking_seats | Seat-ID scan can cross unrelated screens |
| W03 | 8.917 | 8.286 | 8.434 | 8.546 | Seq Scan on bookings; Index Scan using uq_bookings_id_show on bookings | Find earliest pending timestamp |
| W04 | 9.405 | 8.252 | 8.200 | 8.619 | Seq Scan on bookings; Index Scan using uq_booking_seats_booking_seat on booking_seats | Seq scan on bookings to delete expired locks |
| W05 | 6.587 | 6.144 | 5.981 | 6.237 | Seq Scan on shows | Filter shows of movie 2 by local July weekends |
