
# CP1 – Database Schema Design

## 1. Overview

The BookMyShow database is designed as 11 PostgreSQL relations based on the supplied CSV files. The schema separates cities, venues, screens, seats, movies, shows, customers, offers, bookings, booking-seat allocations, and movie reviews.

The design aims to reduce unnecessary redundancy, preserve referential integrity, prevent invalid seat allocations, and support the specified transactional and analytical SQL workload.

Performance-tuning indexes beyond those automatically created by PRIMARY KEY and UNIQUE constraints will be considered in later optimization phases.

**Implementation status:** The schema definitions, constraints, and triggers described in this document are proposed design decisions. They will be considered implemented only after the PostgreSQL DDL has been executed and tested successfully.

## 2. Relations, Attributes, and Keys

The following attributes are taken from the supplied CSV headers.

| Relation | Attributes | Primary Key |
|---|---|---|
| cities | city_id, city_name, state | city_id |
| venues | venue_id, venue_name, city_id, chain, address | venue_id |
| screens | screen_id, venue_id, screen_name, screen_type, total_seats | screen_id |
| seats | seat_id, screen_id, row_label, seat_number, seat_class | seat_id |
| movies | movie_id, title, language, certificate, duration_min, release_date | movie_id |
| shows | show_id, movie_id, screen_id, starts_at, ends_at, format, base_price | show_id |
| customers | customer_id, full_name, email, phone, city_id, created_at | customer_id |
| offers | offer_code, description, discount_pct, max_discount, valid_from, valid_to | offer_code |
| bookings | booking_id, booking_code, customer_id, show_id, booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code, discount, total_amount, payment_method, status | booking_id |
| booking_seats | booking_id, show_id, seat_id, price | (show_id, seat_id) |
| movie_reviews | review_id, movie_id, customer_id, rating, review_text, created_at | review_id |

The `booking_seats` relation also has the alternate candidate key `(booking_id, seat_id)`.

The supplied CSV files contain blank values in `bookings.offer_code` and `movie_reviews.review_text`. These columns will therefore permit NULL. The remaining columns are proposed as required, subject to PostgreSQL loading and validation.

## 3. Candidate Keys and Functional Dependencies

A functional dependency (FD) X → Y means that a value of X determines exactly one value of Y within a relation.

The principal functional dependencies are:

| Relation | Functional Dependencies |
|---|---|
| cities | city_id → city_name, state |
| venues | venue_id → venue_name, city_id, chain, address |
| screens | screen_id → venue_id, screen_name, screen_type, total_seats |
| seats | seat_id → screen_id, row_label, seat_number, seat_class |
| seats | (screen_id, row_label, seat_number) → seat_id, seat_class |
| movies | movie_id → title, language, certificate, duration_min, release_date |
| shows | show_id → movie_id, screen_id, starts_at, ends_at, format, base_price |
| customers | customer_id → full_name, email, phone, city_id, created_at |
| customers | email → customer_id, full_name, phone, city_id, created_at |
| customers | phone → customer_id, full_name, email, city_id, created_at |
| offers | offer_code → description, discount_pct, max_discount, valid_from, valid_to |
| bookings | booking_id → booking_code, customer_id, show_id, booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code, discount, total_amount, payment_method, status |
| bookings | booking_code → booking_id and all remaining booking attributes |
| movie_reviews | review_id → movie_id, customer_id, rating, review_text, created_at |

The candidate keys implied by the proposed uniqueness rules include:

- `cities`: city_id
- `venues`: venue_id
- `screens`: screen_id
- `seats`: seat_id; (screen_id, row_label, seat_number)
- `movies`: movie_id
- `shows`: show_id
- `customers`: customer_id; email; phone
- `offers`: offer_code
- `bookings`: booking_id; booking_code
- `booking_seats`: (show_id, seat_id); (booking_id, seat_id)
- `movie_reviews`: review_id

These alternate keys are proposed based on the supplied data and intended business rules. They must be enforced only after the corresponding constraints have been tested against the dataset.

### 3.1 booking_seats: Functional Dependencies and Key Selection

The `booking_seats` CSV contains four attributes:

`(booking_id, show_id, seat_id, price)`

A booking belongs to exactly one show. Therefore, the `bookings` relation establishes:

`booking_id → show_id`

The inspected allocation data supports two candidate keys:

1. `(show_id, seat_id)` — a particular seat can be allocated at most once for a particular show.
2. `(booking_id, seat_id)` — a particular seat can occur at most once within a booking.

The corresponding dependencies are:

- `(show_id, seat_id) → booking_id, price`
- `(booking_id, seat_id) → show_id, price`

The second dependency is consistent with `booking_id → show_id` in the parent `bookings` relation.

We select `(show_id, seat_id)` as the primary key because the most important business rule is that the same seat must not be allocated twice for the same show. The alternate key `(booking_id, seat_id)` will be enforced using a UNIQUE constraint.

Although `show_id` can be derived by joining `bookings` using `booking_id`, it is retained in `booking_seats` to enforce seat-per-show uniqueness directly.

A composite foreign key `(booking_id, show_id)` will reference the corresponding UNIQUE key in `bookings`. This ensures that the repeated `show_id` agrees with the show assigned to the booking.

**Normal-form implication:** In `booking_seats`, `booking_id → show_id` has a determinant that is not a superkey. However, `show_id` is a prime attribute because it belongs to the candidate key `(show_id, seat_id)`. Therefore, this dependency does not violate 3NF, but it does violate BCNF. This is a deliberate and documented trade-off to retain direct enforcement of seat-per-show uniqueness.

## 4. Relationships and Cardinalities

| Parent | Child | Cardinality |
|---|---|---|
| cities | venues | 1:N |
| cities | customers | 1:N |
| venues | screens | 1:N |
| screens | seats | 1:N |
| screens | shows | 1:N |
| movies | shows | 1:N |
| customers | bookings | 1:N |
| shows | bookings | 1:N |
| bookings | booking_seats | 1:N |
| offers | bookings | 1:N; booking-side reference is optional |
| movies | movie_reviews | 1:N |
| customers | movie_reviews | 1:N |

Bookings and seats form a many-to-many relationship, resolved through `booking_seats`.

## 5. Normalization Analysis

### 5.1 First Normal Form (1NF)

A relation satisfies 1NF when each attribute contains a single atomic value and there are no repeating groups.

In the supplied data, a booking does not contain repeated columns such as `seat_1`, `seat_2`, or `seat_3`. Instead, each seat allocation is represented as an individual row in `booking_seats`.

All 11 relations use individual attributes for their stored values, and each relation has a key to identify its rows.

Therefore, the proposed relations satisfy 1NF.

### 5.2 Second Normal Form (2NF)

A relation satisfies 2NF when it is in 1NF and no non-prime attribute depends on only a proper subset of a candidate key.

Most relations have single-column primary keys. Therefore, they cannot have partial dependencies on a composite primary key.

For `seats`, the alternate candidate key `(screen_id, row_label, seat_number)` determines `seat_id` and `seat_class` as a complete combination. Neither `screen_id` alone nor `row_label` alone determines the complete seat information.

For `booking_seats`, the candidate keys are `(show_id, seat_id)` and `(booking_id, seat_id)`. The allocation price depends on the complete allocation key rather than on either component independently.

Thus, the proposed relations satisfy 2NF.

### 5.3 Third Normal Form (3NF)

A relation satisfies 3NF when it is in 2NF and every non-trivial functional dependency X → A has either a superkey as X or a prime attribute as A.

The entity relations separate attributes according to the entity that determines them:

- `venues` stores `city_id`, not repeated city names and state details.
- `screens` stores `venue_id`, not repeated venue addresses.
- `seats` stores `screen_id`, not repeated screen and venue details.
- `shows` stores `movie_id` and `screen_id`, not repeated movie and screen descriptions.
- `bookings` stores `customer_id` and `show_id`, not repeated customer and movie details.
- `movie_reviews` stores references to movies and customers rather than duplicating their details.

For example, `venue_id → city_id` in `venues`, while `city_id → city_name, state` is represented in `cities`. This avoids storing city descriptions repeatedly in the venue relation.

The `booking_seats` relation has the additional dependency `booking_id → show_id`. As explained in Section 3.1, `show_id` is prime, so this dependency is permitted by 3NF even though it does not satisfy BCNF.

The proposed design therefore satisfies 3NF, with the documented BCNF exception in `booking_seats`.

## 6. Intended Integrity Constraints

The final SQL schema will implement the following constraints, subject to verification against the supplied CSV data. These are proposed constraints and are not considered implemented until successfully tested in PostgreSQL.

### 6.1 PRIMARY KEY Constraints

- Primary keys on all 11 relations.
- Composite primary key `(show_id, seat_id)` on `booking_seats`.

### 6.2 FOREIGN KEY Constraints

- `venues.city_id` → `cities.city_id`
- `screens.venue_id` → `venues.venue_id`
- `seats.screen_id` → `screens.screen_id`
- `shows.movie_id` → `movies.movie_id`
- `shows.screen_id` → `screens.screen_id`
- `customers.city_id` → `cities.city_id`
- `bookings.customer_id` → `customers.customer_id`
- `bookings.show_id` → `shows.show_id`
- `bookings.offer_code` → `offers.offer_code`
- `booking_seats.booking_id` → `bookings.booking_id`
- `booking_seats.show_id` → `shows.show_id`
- `booking_seats.seat_id` → `seats.seat_id`
- `booking_seats(booking_id, show_id)` → `bookings(booking_id, show_id)`
- `movie_reviews.movie_id` → `movies.movie_id`
- `movie_reviews.customer_id` → `customers.customer_id`

The composite foreign key on `booking_seats` requires a matching UNIQUE constraint on `(booking_id, show_id)` in `bookings`.

### 6.3 UNIQUE Constraints

- `customers.email`
- `customers.phone`
- `bookings.booking_code`
- `seats(screen_id, row_label, seat_number)`
- `booking_seats(booking_id, seat_id)`
- `bookings(booking_id, show_id)` to support the composite foreign key.

The primary keys also enforce uniqueness.

### 6.4 NOT NULL Constraints

All required columns will be declared NOT NULL, including identifiers, foreign keys, timestamps, amounts, and descriptive fields.

The two exceptions supported by the CSV data are:

- `bookings.offer_code`
- `movie_reviews.review_text`

These columns will permit NULL values.

### 6.5 CHECK Constraints

The initial schema will implement appropriate checks, including:

- `shows.ends_at > shows.starts_at`
- `movies.duration_min > 0`
- `screens.total_seats > 0`
- `seats.seat_number > 0`
- `bookings.num_tickets > 0`
- Monetary amounts must be non-negative.
- `movie_reviews.rating BETWEEN 1 AND 10`
- `offers.discount_pct BETWEEN 0 AND 100`
- `offers.max_discount >= 0`
- `offers.valid_to >= offers.valid_from`

Further checks for booking status, payment method, screen type, seat class, show format, and other categorical values will be based on the distinct values found in the CSVs. No unsupported enum values will be assumed.

### 6.6 Show Overlap Constraint

Two shows must not overlap on the same screen.

This rule is proposed to be enforced using a PostgreSQL exclusion constraint on `screen_id` and the show time range. The half-open range `[starts_at, ends_at)` allows one show to start exactly when the preceding show ends.

The implementation will use PostgreSQL's `btree_gist` extension where available.

### 6.7 Seat-to-Screen Consistency

A seat allocated to a show must belong to the same screen on which that show is scheduled. This rule spans `booking_seats`, `shows`, and `seats`, so ordinary foreign keys on the individual IDs do not enforce it by themselves.

A trigger is proposed to validate this relationship when a row is inserted or updated in `booking_seats`. Corresponding protection is also needed when the referenced `shows.screen_id` or `seats.screen_id` is changed, so that an update cannot make an existing allocation inconsistent.

This trigger is a proposed design decision and has not yet been implemented or tested in PostgreSQL.

## 7. CSV Dataset Validation Evidence

The supplied CSV dataset was checked using `scripts/validate_data.py`. The validator checks CSV headers and row structure, expected row counts, required values, foreign-key references, primary and alternate unique keys, cross-table consistency, show timestamp validity, and overlapping shows on the same screen.

### 7.1 Expected and Actual Row Counts

| CSV file | Expected rows | Actual rows | Result |
|---|---:|---:|---|
| cities.csv | 10 | 10 | PASS |
| venues.csv | 140 | 140 | PASS |
| screens.csv | 490 | 490 | PASS |
| seats.csv | 94,056 | 94,056 | PASS |
| movies.csv | 300 | 300 | PASS |
| shows.csv | 160,034 | 160,034 | PASS |
| customers.csv | 40,000 | 40,000 | PASS |
| offers.csv | 25 | 25 | PASS |
| bookings.csv | 150,094 | 150,094 | PASS |
| booking_seats.csv | 300,389 | 300,389 | PASS |
| movie_reviews.csv | 32,510 | 32,510 | PASS |
| **Total** | **778,048** | **778,048** | **PASS** |

### 7.2 Integrity Validation Results

The latest successful validator run reported:

- Required-value checks: 0 missing required values.
- Foreign-key relationships: 14 checked; 0 invalid and 0 missing references.
- Primary-key and UNIQUE checks: 17 checked; 0 duplicate combinations.
- Cross-table consistency: 0 booking-show mismatches, 0 seat-screen mismatches, and 0 missing parent records.
- Show timestamps: 160,034 valid show intervals; every start and end timestamp was timezone-aware, and every show ended after it started. The supplied dataset currently uses UTC offset `+05:30`; this is an observation, not a rule enforced by the validator. Multiple valid UTC offsets are allowed.
- Show overlaps: 0 overlapping show pairs on the same screen.

### 7.3 Machine-Readable Report

The validator generates `validation_report.json` in the project root. It records the expected and actual row counts for all 11 CSV files, individual row-count check results, total expected and actual rows, configured foreign-key and primary/unique checks, overall validation status, issue count, and reported validation issues.

The latest successful run reported:

- Expected total rows: 778,048
- Actual total rows: 778,048
- Row-count checks: 11 passed, 0 failed
- Foreign-key relationship checks: 14
- Primary and unique key checks: 17
- Validation issues: 0
- Overall result: PASSED

These results establish that the supplied CSV files passed the implemented Python validation checks. They do not replace PostgreSQL constraints or prove that the database schema and loading process have been tested. Equivalent database-level checks will be performed after PostgreSQL implementation and data loading.

## 8. Proposed Data Types and Nullability

The following data types are proposed based on the CSV headers and inspected values. They are design choices and must be confirmed during PostgreSQL table creation and data loading. `NOT NULL` is proposed for every column except the two nullable columns identified in Section 2.

| Relation | Column | Proposed PostgreSQL type | Nullability / key |
|---|---|---|---|
| cities | city_id | INTEGER | NOT NULL, PK |
| cities | city_name | VARCHAR(50) | NOT NULL |
| cities | state | VARCHAR(50) | NOT NULL |
| venues | venue_id | INTEGER | NOT NULL, PK |
| venues | venue_name | VARCHAR(100) | NOT NULL |
| venues | city_id | INTEGER | NOT NULL, FK |
| venues | chain | VARCHAR(30) | NOT NULL |
| venues | address | VARCHAR(100) | NOT NULL |
| screens | screen_id | INTEGER | NOT NULL, PK |
| screens | venue_id | INTEGER | NOT NULL, FK |
| screens | screen_name | VARCHAR(30) | NOT NULL |
| screens | screen_type | VARCHAR(20) | NOT NULL |
| screens | total_seats | INTEGER | NOT NULL |
| seats | seat_id | INTEGER | NOT NULL, PK |
| seats | screen_id | INTEGER | NOT NULL, FK |
| seats | row_label | VARCHAR(5) | NOT NULL |
| seats | seat_number | SMALLINT | NOT NULL |
| seats | seat_class | VARCHAR(20) | NOT NULL |
| movies | movie_id | INTEGER | NOT NULL, PK |
| movies | title | VARCHAR(150) | NOT NULL |
| movies | language | VARCHAR(30) | NOT NULL |
| movies | certificate | VARCHAR(5) | NOT NULL |
| movies | duration_min | SMALLINT | NOT NULL |
| movies | release_date | DATE | NOT NULL |
| shows | show_id | INTEGER | NOT NULL, PK |
| shows | movie_id | INTEGER | NOT NULL, FK |
| shows | screen_id | INTEGER | NOT NULL, FK |
| shows | starts_at | TIMESTAMPTZ | NOT NULL |
| shows | ends_at | TIMESTAMPTZ | NOT NULL |
| shows | format | VARCHAR(10) | NOT NULL |
| shows | base_price | NUMERIC(10,2) | NOT NULL |
| customers | customer_id | INTEGER | NOT NULL, PK |
| customers | full_name | VARCHAR(100) | NOT NULL |
| customers | email | VARCHAR(254) | NOT NULL, UNIQUE proposed |
| customers | phone | VARCHAR(15) | NOT NULL, UNIQUE proposed |
| customers | city_id | INTEGER | NOT NULL, FK |
| customers | created_at | TIMESTAMPTZ | NOT NULL |
| offers | offer_code | VARCHAR(20) | NOT NULL, PK |
| offers | description | VARCHAR(100) | NOT NULL |
| offers | discount_pct | NUMERIC(5,2) | NOT NULL |
| offers | max_discount | NUMERIC(10,2) | NOT NULL |
| offers | valid_from | DATE | NOT NULL |
| offers | valid_to | DATE | NOT NULL |
| bookings | booking_id | INTEGER | NOT NULL, PK |
| bookings | booking_code | VARCHAR(20) | NOT NULL, UNIQUE proposed |
| bookings | customer_id | INTEGER | NOT NULL, FK |
| bookings | show_id | INTEGER | NOT NULL, FK |
| bookings | booked_at | TIMESTAMPTZ | NOT NULL |
| bookings | num_tickets | SMALLINT | NOT NULL |
| bookings | ticket_amount | NUMERIC(10,2) | NOT NULL |
| bookings | convenience_fee | NUMERIC(10,2) | NOT NULL |
| bookings | fnb_amount | NUMERIC(10,2) | NOT NULL |
| bookings | offer_code | VARCHAR(20) | NULL allowed, FK |
| bookings | discount | NUMERIC(10,2) | NOT NULL |
| bookings | total_amount | NUMERIC(10,2) | NOT NULL |
| bookings | payment_method | VARCHAR(20) | NOT NULL |
| bookings | status | VARCHAR(20) | NOT NULL |
| booking_seats | booking_id | INTEGER | NOT NULL, FK |
| booking_seats | show_id | INTEGER | NOT NULL, PK component, FK |
| booking_seats | seat_id | INTEGER | NOT NULL, PK component, FK |
| booking_seats | price | NUMERIC(10,2) | NOT NULL |
| movie_reviews | review_id | INTEGER | NOT NULL, PK |
| movie_reviews | movie_id | INTEGER | NOT NULL, FK |
| movie_reviews | customer_id | INTEGER | NOT NULL, FK |
| movie_reviews | rating | SMALLINT | NOT NULL |
| movie_reviews | review_text | TEXT | NULL allowed |
| movie_reviews | created_at | TIMESTAMPTZ | NOT NULL |

### 8.1 Type Selection Notes

- Identifier columns use `INTEGER` because the supplied identifiers are whole-number values.
- `phone` uses `VARCHAR(15)` rather than a numeric type because phone numbers are identifiers, not quantities; this also avoids losing leading zeros or a possible plus sign.
- Monetary values use `NUMERIC(10,2)` to preserve decimal currency values without floating-point rounding.
- `discount_pct` uses `NUMERIC(5,2)` to store percentage values with two decimal places.
- Calendar-only values use `DATE`.
- Date-time values with timezone offsets use `TIMESTAMPTZ`. The inspected show timestamps in the supplied dataset use UTC offset `+05:30`; the validator permits multiple valid offsets and checks each timestamp for timezone awareness and each interval for a valid end-after-start order.
- `review_text` uses `TEXT` because review text does not require a fixed maximum length.
- `SMALLINT` is proposed for small whole-number attributes such as seat numbers, duration in minutes, ticket counts, and ratings. These choices will be checked against the full dataset during loading.

**Status:** The data types, nullability, and constraints in this section remain proposed until the SQL schema is created, all CSV data is loaded, and PostgreSQL integrity checks pass.
