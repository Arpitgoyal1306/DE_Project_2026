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
| customers | email → customer_id and remaining customer attributes (proposed) |
| customers | phone → customer_id and remaining customer attributes (proposed) |
| offers | offer_code → description, discount_pct, max_discount, valid_from, valid_to |
| bookings | booking_id → booking_code and all remaining booking attributes |
| bookings | booking_code → booking_id and all remaining booking attributes (proposed) |
| movie_reviews | review_id → movie_id, customer_id, rating, review_text, created_at |

### 3.1 Candidate-key evidence and rationale

The validator checked the following alternate unique combinations in the supplied dataset. Each had zero duplicate combinations:

| Relation | Proposed alternate key | Dataset evidence | Business-rule rationale |
|---|---|---|---|
| seats | (screen_id, row_label, seat_number) | 94,056 seat rows; zero duplicate combinations | A physical seat position should identify one seat within a screen |
| customers | email | 40,000 customer rows; zero duplicate values | An email address is proposed as a unique customer contact identifier |
| customers | phone | 40,000 customer rows; zero duplicate values | A phone number is proposed as a unique customer contact identifier |
| bookings | booking_code | 150,094 booking rows; zero duplicate values | A booking code should identify one booking externally |
| booking_seats | (booking_id, seat_id) | 300,389 allocation rows; zero duplicate combinations | A seat should appear at most once within a booking |
| bookings | (booking_id, show_id) | 150,094 booking rows; zero duplicate combinations | Supports the composite foreign key from booking-seat allocations |

The observed uniqueness supports these proposed constraints for the supplied dataset. It does not, by itself, prove that every alternate key is a universal business rule. In particular, the owner should confirm whether email and phone must be unique for the application.

The candidate keys implied by the proposed uniqueness rules include:

- `cities`: city_id
- `venues`: venue_id
- `screens`: screen_id
- `seats`: seat_id; (screen_id, row_label, seat_number)
- `movies`: movie_id
- `shows`: show_id
- `customers`: customer_id; email; phone (alternate keys proposed)
- `offers`: offer_code
- `bookings`: booking_id; booking_code (alternate key proposed)
- `booking_seats`: (show_id, seat_id); (booking_id, seat_id)
- `movie_reviews`: review_id

**Review uniqueness decision pending owner confirmation:** The dataset contains 32,510 reviews and zero duplicate `(customer_id, movie_id)` pairs. We propose `UNIQUE (customer_id, movie_id)` to represent one review per customer per movie. This is not included as an enforced candidate key until the repository owner confirms that business rule.

### 3.2 booking_seats: Functional Dependencies and Key Selection

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

A composite foreign key `(booking_id, show_id)` references the corresponding UNIQUE key in `bookings`. This ensures that the repeated `show_id` agrees with the show assigned to the booking. The individual `booking_seats.booking_id → bookings.booking_id` foreign key is omitted as redundant: the composite foreign key already guarantees that the booking/show pair exists in `bookings`. The individual `booking_seats.show_id → shows.show_id` and `booking_seats.seat_id → seats.seat_id` references remain.

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

The `booking_seats` relation has the additional dependency `booking_id → show_id`. As explained in Section 3.2, `show_id` is prime, so this dependency is permitted by 3NF even though it does not satisfy BCNF.

The proposed design therefore satisfies 3NF, with the documented BCNF exception in `booking_seats`.

## 6. Intended Integrity Constraints

The final SQL schema will implement the following constraints, subject to verification against the supplied CSV data. These are proposed constraints and are not considered implemented until successfully tested in PostgreSQL.

### 6.1 PRIMARY KEY Constraints

- Primary keys on all 11 relations.
- Composite primary key `(show_id, seat_id)` on `booking_seats`.

### 6.2 FOREIGN KEY Constraints

There are **13 individual foreign-key relationships and 1 composite foreign-key relationship**, for 14 FK constraints in total.

**Individual foreign keys (13):**

- `venues.city_id` → `cities.city_id`
- `screens.venue_id` → `venues.venue_id`
- `seats.screen_id` → `screens.screen_id`
- `shows.movie_id` → `movies.movie_id`
- `shows.screen_id` → `screens.screen_id`
- `customers.city_id` → `cities.city_id`
- `bookings.customer_id` → `customers.customer_id`
- `bookings.show_id` → `shows.show_id`
- `bookings.offer_code` → `offers.offer_code` (nullable)
- `booking_seats.show_id` → `shows.show_id`
- `booking_seats.seat_id` → `seats.seat_id`
- `movie_reviews.movie_id` → `movies.movie_id`
- `movie_reviews.customer_id` → `customers.customer_id`

**Composite foreign key (1):**

- `booking_seats(booking_id, show_id)` → `bookings(booking_id, show_id)`

The individual `booking_seats.booking_id → bookings.booking_id` constraint is intentionally omitted because the composite FK already verifies the booking identifier together with its associated show. The composite foreign key requires a matching UNIQUE constraint on `(booking_id, show_id)` in `bookings`.

### 6.3 UNIQUE Constraints

The proposed alternate UNIQUE constraints are:

- `customers.email`
- `customers.phone`
- `bookings.booking_code`
- `seats(screen_id, row_label, seat_number)`
- `booking_seats(booking_id, seat_id)`
- `bookings(booking_id, show_id)` to support the composite foreign key.

Each combination had zero duplicates in the supplied dataset. The proposed `UNIQUE (customer_id, movie_id)` on `movie_reviews` remains pending owner confirmation and is not counted among the 17 validator primary/unique checks.

The primary keys also enforce uniqueness.

### 6.4 NOT NULL Constraints

All required columns will be declared NOT NULL, including identifiers, foreign keys, timestamps, amounts, and descriptive fields.

The two exceptions supported by the CSV data are:

- `bookings.offer_code`
- `movie_reviews.review_text`

These columns will permit NULL values.

### 6.5 CHECK Constraints

The proposed row-level checks include:

- `shows.ends_at > shows.starts_at`
- `movies.duration_min > 0`
- `screens.total_seats > 0`
- `seats.seat_number > 0`
- `bookings.num_tickets > 0`
- `shows.base_price >= 0`
- `booking_seats.price >= 0`
- `bookings.ticket_amount >= 0`
- `bookings.convenience_fee >= 0`
- `bookings.fnb_amount >= 0`
- `bookings.discount >= 0`
- `bookings.total_amount >= 0`
- `offers.discount_pct BETWEEN 0 AND 100`
- `offers.max_discount >= 0`
- `offers.valid_to >= offers.valid_from`
- `movie_reviews.rating BETWEEN 1 AND 10`

The inspected dataset also supports these booking amount consistency rules:

- `discount <= ticket_amount + convenience_fee + fnb_amount`
- `total_amount = ticket_amount + convenience_fee + fnb_amount - discount`

All 150,094 booking rows passed both checks, with zero negative monetary values and zero amount-calculation mismatches. These rules can be enforced with row-level CHECK constraints.

Further checks for booking status, payment method, screen type, seat class, show format, and other categorical values will be based on the distinct values found in the CSVs. No unsupported enum values will be assumed.

### 6.6 Show Overlap Constraint

Two shows must not overlap on the same screen.

This rule is proposed to be enforced using a PostgreSQL exclusion constraint on `screen_id` and the show time range. The half-open range `[starts_at, ends_at)` allows one show to start exactly when the preceding show ends.

The implementation will use PostgreSQL's `btree_gist` extension where available.

### 6.7 Seat-to-Screen Consistency

A seat allocated to a show must belong to the same screen on which that show is scheduled. This rule spans `booking_seats`, `shows`, and `seats`, so ordinary foreign keys on the individual IDs do not enforce it by themselves.

A trigger is proposed to validate this relationship when a row is inserted or updated in `booking_seats`. Corresponding protection is also needed when the referenced `shows.screen_id` or `seats.screen_id` is changed, so that an update cannot make an existing allocation inconsistent.

This trigger is a proposed design decision and has not yet been implemented or tested in PostgreSQL.

### 6.8 Cross-table Business Integrity Rules

The CSV inspection established the following results:

| Rule | Inspection result | Proposed treatment |
|---|---|---|
| Screen capacity equals the number of seat rows for that screen | 490 screens checked; 0 mismatches | Validate as a cross-table rule |
| Booking ticket count matches allocated seats | All 133,568 CONFIRMED and 10 PENDING bookings matched; all 8,910 CANCELLED and 7,606 PAYMENT_FAILED bookings had zero allocated seats | Status-aware validation |
| Applied offer is valid on booking date | 22,435 offer-using bookings checked; 0 invalid dates | Validate when an offer is applied |
| One review per customer/movie | 32,510 reviews; 0 duplicate customer/movie pairs | Proposed UNIQUE rule pending owner approval |

For booking allocation, the observed status-aware rule is:

- `CONFIRMED` and `PENDING`: allocated seat count equals `num_tickets`.
- `CANCELLED` and `PAYMENT_FAILED`: allocated seat count is zero.

These are cross-table rules and cannot be enforced by ordinary row-level CHECK constraints. They require validation queries or appropriately designed triggers if database-level enforcement is required.

The review uniqueness rule is deliberately not treated as approved. The observed absence of duplicates is dataset evidence; the decision to allow only one review per customer per movie requires owner confirmation.

## 7. CSV Dataset Validation Evidence

The supplied CSV dataset was checked using `scripts/validate_data.py`. The latest run validates CSV structure and row counts, required values, numeric ranges and precision, proposed VARCHAR limits, dates, timezone-aware timestamps, foreign-key references (including the composite FK), primary and alternate unique keys, cross-table consistency, monetary rules, offer validity, show intervals, and show overlaps.

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

### 7.2 Latest Validation Results

The latest successful run and its generated `validation_report.json` reported:

| Validation | Configured | Result |
|---|---:|---:|
| Row-count checks | 11 | 11 passed |
| Individual FK relationships | 13 | 0 invalid |
| Composite FK relationships | 1 | 0 invalid |
| Primary/unique key checks | 17 | 0 duplicates |
| Numeric columns | 36 | 0 errors |
| Proposed VARCHAR limits | 21 | 0 errors |
| Date columns | 3 | 0 errors |
| Timestamp columns | 5 | 0 errors |

Additional results:

- Required-value errors: 0.
- Foreign-key errors: 0.
- Numeric errors: 0.
- String-length errors: 0.
- Date errors: 0.
- Timestamp errors, including missing timezone: 0.
- Screen capacity mismatches: 0.
- Status-aware booking allocation mismatches: 0.
- Seat-screen mismatches: 0.
- Offer validity errors: 0.
- Negative monetary values: 0.
- Booking amount formula errors: 0.
- Show interval errors: 0.
- Overlapping show pairs: 0.
- Proposed review uniqueness warnings: 0.

The 382,672 timestamp values across shows, bookings, customers, and movie reviews were timezone-aware and parsed successfully. The observed offset in the supplied data is `+05:30`. This is informational only; the validator permits multiple valid UTC offsets.

**Overall result: PASSED — 778,048 rows, 0 errors, 0 warnings.**

### 7.3 Machine-Readable Report

The validator generates `validation_report.json` in the project root. It records expected and actual row counts, configured check counts, per-check results, observed numeric ranges, maximum string lengths, observed timestamp offsets, issue and warning counts, and detailed issue records.

These results establish that the supplied CSV files passed the implemented Python validation checks. They do not replace PostgreSQL constraints or prove that the database schema and loading process have been tested. Equivalent database-level checks will be performed after PostgreSQL implementation and data loading.

## 8. Proposed Data Types and Nullability

The following proposed data types align with the numeric range and string-length configurations in `scripts/validate_data.py`. The configured VARCHAR lengths provide headroom above the observed maximum values in the supplied CSVs. These are design limits for this project, not claims about universal business limits.

`NOT NULL` is proposed for every column except the two nullable columns identified in Section 2.

| Relation | Column | Proposed PostgreSQL type | Nullability / key |
|---|---|---|---|
| cities | city_id | SMALLINT | NOT NULL, PK |
| cities | city_name | VARCHAR(30) | NOT NULL |
| cities | state | VARCHAR(30) | NOT NULL |
| venues | venue_id | SMALLINT | NOT NULL, PK |
| venues | venue_name | VARCHAR(60) | NOT NULL |
| venues | city_id | SMALLINT | NOT NULL, FK |
| venues | chain | VARCHAR(30) | NOT NULL |
| venues | address | VARCHAR(100) | NOT NULL |
| screens | screen_id | SMALLINT | NOT NULL, PK |
| screens | venue_id | SMALLINT | NOT NULL, FK |
| screens | screen_name | VARCHAR(20) | NOT NULL |
| screens | screen_type | VARCHAR(20) | NOT NULL |
| screens | total_seats | SMALLINT | NOT NULL |
| seats | seat_id | INTEGER | NOT NULL, PK |
| seats | screen_id | SMALLINT | NOT NULL, FK |
| seats | row_label | VARCHAR(5) | NOT NULL |
| seats | seat_number | SMALLINT | NOT NULL |
| seats | seat_class | VARCHAR(20) | NOT NULL |
| movies | movie_id | SMALLINT | NOT NULL, PK |
| movies | title | VARCHAR(100) | NOT NULL |
| movies | language | VARCHAR(30) | NOT NULL |
| movies | certificate | VARCHAR(10) | NOT NULL |
| movies | duration_min | SMALLINT | NOT NULL |
| movies | release_date | DATE | NOT NULL |
| shows | show_id | INTEGER | NOT NULL, PK |
| shows | movie_id | SMALLINT | NOT NULL, FK |
| shows | screen_id | SMALLINT | NOT NULL, FK |
| shows | starts_at | TIMESTAMPTZ | NOT NULL |
| shows | ends_at | TIMESTAMPTZ | NOT NULL |
| shows | format | VARCHAR(10) | NOT NULL |
| shows | base_price | NUMERIC(10,2) | NOT NULL |
| customers | customer_id | INTEGER | NOT NULL, PK |
| customers | full_name | VARCHAR(100) | NOT NULL |
| customers | email | VARCHAR(100) | NOT NULL, UNIQUE proposed |
| customers | phone | VARCHAR(15) | NOT NULL, UNIQUE proposed |
| customers | city_id | SMALLINT | NOT NULL, FK |
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
| booking_seats | booking_id | INTEGER | NOT NULL, composite FK component |
| booking_seats | show_id | INTEGER | NOT NULL, PK component, FK |
| booking_seats | seat_id | INTEGER | NOT NULL, PK component, FK |
| booking_seats | price | NUMERIC(10,2) | NOT NULL |
| movie_reviews | review_id | INTEGER | NOT NULL, PK |
| movie_reviews | movie_id | SMALLINT | NOT NULL, FK |
| movie_reviews | customer_id | INTEGER | NOT NULL, FK |
| movie_reviews | rating | SMALLINT | NOT NULL |
| movie_reviews | review_text | TEXT | NULL allowed |
| movie_reviews | created_at | TIMESTAMPTZ | NOT NULL |

### 8.1 Type Selection Notes

- `SMALLINT` is used for identifiers and whole-number attributes whose observed values fit within PostgreSQL's signed SMALLINT range (-32,768 to 32,767). The largest observed values in these configured columns are at most 32,767.
- `INTEGER` is used for larger identifiers such as `seat_id`, `show_id`, `customer_id`, and `booking_id`.
- `phone` uses `VARCHAR(15)` rather than a numeric type because phone numbers are identifiers, not quantities; this also avoids losing leading zeros or a possible plus sign.
- Monetary values use `NUMERIC(10,2)` to preserve decimal currency values without floating-point rounding.
- `discount_pct` uses `NUMERIC(5,2)` to store percentage values with two decimal places.
- Calendar-only values use `DATE`.
- Date-time values with timezone offsets use `TIMESTAMPTZ`. The inspected data uses `+05:30`, but multiple valid offsets are supported.
- `review_text` uses `TEXT` because review text does not require a fixed maximum length.
- Configured VARCHAR lengths are larger than the observed maximum lengths: for example, `venues.venue_name` has an observed maximum of 41 characters against a proposed limit of 60, and `customers.email` has an observed maximum of 33 against a proposed limit of 100.

**Status:** The data types, nullability, and constraints in this section remain proposed until the SQL schema is created, all CSV data is loaded, and PostgreSQL integrity checks pass.
