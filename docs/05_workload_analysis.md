# Query Workload Analysis and Benchmark Evidence

**Project:** BookMyShow database  
**Repository:** `Arpitgoyal1306/DE_Project_2026`  
**Workload source:** `queries/workload_30.sql` (R01–R25 and W01–W05)  
**Schema source:** `sql/01_schema.sql`  
**Benchmark harness:** `benchmarks/run_benchmark.sh`

## 1. Scope and classification

The workload contains 25 read queries and 5 write queries. Classification below describes the dominant business purpose, not merely whether a statement is syntactically a SELECT or DML statement:

- **OLTP:** point lookups or operational actions in the customer-facing booking flow, support, payment, seat-lock, or pricing services. These are latency-sensitive and usually target a narrow set of rows.
- **OLAP:** reporting, aggregation, trend analysis, or broad scans used by cinema operations, finance, partnerships, distributors, and management.
- **Hybrid:** operationally useful reports that aggregate a bounded operational period or combine transactional data with operational monitoring.

The baseline and optimized workloads share the July pricing interval, chronological pending-booking rule and deterministic R22 page order. Performance rewrites live in `sql/06_optimized_queries.sql`.

## 2. Query-by-query workload map

| ID | Business question / purpose | Expected result | Workload class | Tables and schema columns used |
|---|---|---|---|---|
| R01 | Which movies have shows in Bengaluru on 2 July 2026, and how many shows does each have? | One row per movie with show count, ordered by popularity for that date. | Hybrid | `shows(movie_id, screen_id, starts_at)`, `movies(movie_id, title, language, certificate)`, `screens(screen_id, venue_id)`, `venues(venue_id, city_id)` |
| R02 | What are the showtimes for movie 2 in Bengaluru on 2 July 2026, grouped by cinema? | Matching venue, screen type, show ID, start time, format, and base price. | OLTP | `shows(movie_id, screen_id, starts_at, format, base_price)`, `screens(screen_id, venue_id, screen_type)`, `venues(venue_id, city_id, venue_name)` |
| R03 | Which seats are available or sold for show 144446? | Every seat on the show's screen, with a boolean sold indicator. | OLTP | `shows(show_id, screen_id)`, `seats(screen_id, row_label, seat_number, seat_class, seat_id)`, `booking_seats(show_id, seat_id)` |
| R04 | Can support locate a booking from its booking code? | At most one booking with customer, show, ticket count, amount, status, and booking timestamp. | OLTP | `bookings(booking_code, booking_id, customer_id, show_id, num_tickets, total_amount, status, booked_at)` |
| R05 | What upcoming confirmed bookings belong to customer 1331? | Booking code, movie title, show time, venue, and ticket count in chronological order. | OLTP | `bookings(customer_id, status, show_id, booking_code, num_tickets)`, `shows(show_id, movie_id, screen_id, starts_at)`, `movies(movie_id, title)`, `screens(screen_id, venue_id)`, `venues(venue_id, venue_name)` |
| R06 | Which movie titles contain “kalki”? | Matching movie IDs, titles, languages, and release dates, newest release first. | OLTP | `movies(movie_id, title, language, release_date)` |
| R07 | What is the seat occupancy of each show at venue 11 on 28 June 2026? | Per-show sold seats, screen capacity, and occupancy percentage. | Hybrid | `shows(show_id, screen_id, starts_at)`, `screens(screen_id, venue_id, screen_name, total_seats)`, `booking_seats(show_id, seat_id)` |
| R08 | Which 10 movies collected the most ticket revenue over 26–28 June 2026? | Top 10 movie titles with confirmed booking count and ticket collections. | OLAP | `bookings(show_id, status, booking_id, ticket_amount)`, `shows(show_id, movie_id, starts_at)`, `movies(movie_id, title)` |
| R09 | Which pending bookings were already older than the 10-minute seat-lock threshold at the specified cutoff? | Expired pending booking IDs, show IDs, ticket counts, and timestamps. | OLTP | `bookings(status, booked_at, booking_id, show_id, num_tickets)` |
| R10 | Which consecutive shows on the same screen leave less than 30 minutes for cleaning during June 2026? | Screen, earlier show end, next show start, and cleaning gap. | Hybrid | `shows(screen_id, show_id, starts_at, ends_at)` |
| R11 | How much ticket revenue comes from recliner seats for each screen type? | Revenue and recliner revenue percentage per screen type. | OLAP | `booking_seats(show_id, seat_id, price)`, `shows(show_id, starts_at)`, `seats(seat_id, screen_id, seat_class)`, `screens(screen_id, screen_type)` |
| R12 | Which customers booked the same movie more than once? | Customer/movie pairs and number of confirmed bookings, most frequent first. | OLAP | `bookings(customer_id, show_id, status)`, `shows(show_id, movie_id)` |
| R13 | Which offers have never been redeemed by any booking? | Offer code, description, and discount percentage for unused offers. | OLAP | `offers(offer_code, description, discount_pct)`, `bookings(offer_code)` |
| R14 | Which 2026 releases have at least 20 reviews, and what are their average ratings? | Up to 20 movies with average rating and review count, highest rated first. | OLAP | `movies(movie_id, title, release_date)`, `movie_reviews(movie_id, rating)` |
| R15 | At what weekday/hour combinations are bookings made? | Booking counts grouped by ISO weekday and hour. | OLAP | `bookings(booked_at)` |
| R16 | What is the cancellation rate per venue for June 2026 shows? | Per-venue booking totals and cancellation percentage. | OLAP | `bookings(show_id, status)`, `shows(show_id, screen_id, starts_at)`, `screens(screen_id, venue_id)`, `venues(venue_id, venue_name)` |
| R17 | Which seats on screen 101 were never sold for any June 2026 show? | Seat IDs, row labels, seat numbers, and seat classes that were never allocated. | Hybrid | `seats(screen_id, seat_id, row_label, seat_number, seat_class)`, `booking_seats(seat_id, show_id)`, `shows(show_id, starts_at)` |
| R18 | What were confirmed ticket collections by language and city during 2026? | City/language groups with total collections, ordered by city and revenue. | OLAP | `bookings(show_id, status, ticket_amount)`, `shows(show_id, movie_id, screen_id, starts_at)`, `movies(movie_id, language)`, `screens(screen_id, venue_id)`, `venues(venue_id, city_id)` |
| R19 | How many confirmed tickets were sold for each June 2026 show of movie 2? | Show ID, start time, screen ID, and tickets sold (zero when none). | OLAP | `shows(movie_id, show_id, starts_at, screen_id)`, `bookings(show_id, status, num_tickets)` |
| R20 | What were daily confirmed booking collections and the running total for June 2026? | Daily collections and cumulative collections ordered by date. | OLAP | `bookings(booked_at, status, total_amount)` |
| R21 | Which 20 customers made the most confirmed bookings in 2026, and how much did they spend? | Customer ID, booking count, and spend, ranked by count then spend. | OLAP | `bookings(customer_id, status, booked_at, total_amount)` |
| R22 | What records appear on page 4,001 of the support booking list (25 per page)? | 25 newest booking records after offset 100,000. | OLTP | `bookings(booked_at, booking_id, booking_code, customer_id, show_id, status)` |
| R23 | Which customer account matches a supplied mobile number? | Customer ID, full name, and city ID (at most one row). | OLTP | `customers(phone, customer_id, full_name, city_id)` |
| R24 | What is the average recorded booking-seat price by seat class and city for shows starting in calendar year 2026? | Average paid price and ticket count per city and seat class, using the Kolkata show date. | OLAP | `booking_seats(show_id, seat_id, price)`, `shows(show_id, starts_at)`, `seats(seat_id, screen_id, seat_class)`, `screens(screen_id, venue_id)`, `venues(venue_id, city_id)` |
| R25 | What is the occupancy of late-night shows (22:30 onward) in June 2026? | Up to 50 shows with start time, capacity, and sold-seat count. | Hybrid | `shows(show_id, starts_at, screen_id)`, `screens(screen_id, total_seats)`, `booking_seats(show_id, seat_id)` |
| W01 | Can checkout create a pending booking for two tickets on show 144446? | Insert one PENDING booking with the supplied payment and amount fields. | OLTP write | `bookings(booking_id, booking_code, customer_id, show_id, booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, discount, total_amount, payment_method, status)` |
| W02 | Can the seat-lock service allocate two lowest-ID unsold seats to the oldest pending booking? | Insert up to two booking-seat rows, avoiding already allocated show/seat pairs. | OLTP write | `bookings(booking_id, show_id, status)`, `shows(show_id, screen_id)`, `seats(screen_id, seat_id)`, `booking_seats(booking_id, show_id, seat_id, price)` |
| W03 | Can the payment callback confirm the oldest pending booking? | Update the oldest PENDING booking to CONFIRMED. | OLTP write | `bookings(booking_id, status)` |
| W04 | Can the seat-lock expiry process release seats held by expired pending bookings? | Delete booking-seat allocations whose booking remains PENDING past the cutoff. | OLTP write | `booking_seats(booking_id)`, `bookings(booking_id, status, booked_at)` |
| W05 | Can pricing increase the base price by 10% for weekend shows of movie 2 in July 2026? | Update matching Kolkata weekend shows from July 1 inclusive to August 1 exclusive; prices are rounded to whole currency units. | OLTP write / batch | `shows(movie_id, starts_at, base_price)` |

## 3. Schema compatibility check

The query references above were checked against `sql/01_schema.sql`, which defines the 11 tables used by the workload:

`cities`, `venues`, `screens`, `seats`, `movies`, `shows`, `customers`, `offers`, `bookings`, `booking_seats`, and `movie_reviews`.

All table and column names in the 30 supplied statements are present in that schema. The following schema details affect the workload:

- `booking_seats` is keyed by `(show_id, seat_id)`, which supports the seat-allocation conflict check in W02.
- `bookings.booking_code` and `customers.phone` are unique lookup keys used by R04 and R23.
- The supplied baseline R13 uses `NOT IN` against nullable `bookings.offer_code`. Because NULL values can make `NOT IN` evaluate to UNKNOWN, the original query can return no offers even when some are unused. The optimized `NOT EXISTS` rewrite is a correctness fix, not a like-for-like timing-only rewrite; the optimization report documents the 7-row corrected result.
- The supplied write workload is designed to run in a transaction and roll back. The benchmark harness wraps each W query in `BEGIN ... ROLLBACK`; do not commit these test writes.
- R24 assigns each ticket to the calendar year of its show in Asia/Kolkata. A December booking for a January show counts in January’s reporting year.
- W05 uses the Kolkata calendar for both the month boundary and weekend selection.

## 4. Benchmark evidence

The [baseline timings](03_baseline_timings.md) report each of three seed runs. The [optimization report](04_optimization_report.md) compares the 30 seed queries and provides the reproduction commands. The [scalability report](05_scalability_report.md) compares the optimized seed and faculty large datasets, documents the remaining limits, and links the plans used to investigate performance at scale.

## 5. Workload composition and service-level implications

The classification above produces the following mix:

| Workload group | Query IDs | Count | Share of all 30 |
|---|---|---:|---:|
| OLTP reads | R02–R06, R09, R22, R23 | 8 | 26.7% |
| OLAP reads | R08, R11–R16, R18–R21, R24 | 12 | 40.0% |
| Hybrid reads | R01, R07, R10, R17, R25 | 5 | 16.7% |
| OLTP writes | W01–W05 | 5 | 16.7% |

This is a mixed workload rather than a pure transactional benchmark: 17 of the 25 reads are analytical or hybrid (12 OLAP + 5 hybrid), while the eight OLTP reads are operational lookups/listing operations. The five OLTP writes model checkout, seat allocation, payment confirmation, lock expiry, and pricing maintenance.

The distinction matters when interpreting aggregate timing. A large reduction in a reporting query can dominate summed execution time without necessarily changing the p95 latency of a high-volume checkout endpoint. For a production service, collect request-weighted latency (p50/p95/p99), throughput, concurrency, lock waits, and error rates in addition to this fixed-query benchmark. The current three-run query benchmark is useful for plan comparison, but it is not a load or concurrency test.

## 6. Benchmark interpretation and limitations

- EXPLAIN (ANALYZE, BUFFERS) executes the statement. The W queries are real writes during each measurement, even though the harness rolls them back afterward.
- Rollback protects the logical dataset from committed changes; it does not make concurrent benchmarking harmless. Run the write workload in an isolated test database or quiet maintenance window, not concurrently with real booking traffic.
- Three repetitions provide a small comparison sample. Averages can be affected by cache state, background activity, connection setup, and PostgreSQL variance. Keep raw plans and compare individual runs as well as averages.
- EXPLAIN ANALYZE execution time is server-side statement execution time. It excludes application serialization, network transfer, connection-pool queueing, and end-to-end API latency.
- Scan-node names in the summary CSV are extracted from the final run's plan only. Use full raw plans when evaluating join order, estimated versus actual rows, buffers, loops, and sort/hash memory.
- Indexes can improve selective lookups while adding storage and maintenance work to inserts, updates, and deletes. The optimization report measures each write before and after indexing.


## 7. Reading the benchmark results responsibly

The baseline and optimized summaries should be interpreted query by query, not only through the sum of average execution times.

- **Large selective-query wins:** R05, R09, R17, and R19 show the clearest evidence that indexes and query-shape changes reduced unnecessary row visits or repeated work.
- **Broad analytical scans:** R11, R15, R21, and R24 still read a substantial fraction of their input relations. A sequential scan can be the correct plan when most rows are needed; adding an index does not automatically make such a query faster.
- **Observed regressions:** In the final seed sample R08, R14 and R24 ran slower. All five write means decreased. The before/after table records the magnitude alongside raw plans.

For a repeatable comparison, use the same PostgreSQL major version, schema, dataset snapshot, query parameters, connection route, and benchmark run count. Record whether the database was warm or cold, and avoid comparing a local database run directly with a remote Neon run as if only the SQL had changed. The committed figures are historical evidence for the environment described in the optimization report, not a guarantee of current production latency.
