# CP1 – Database Schema Design

## 1. Overview

The BookMyShow database is designed as 11 PostgreSQL relations based on the supplied CSV files. The schema separates cities, venues, screens, seats, movies, shows, customers, offers, bookings, booking-seat allocations, and movie reviews.

The design aims to reduce unnecessary redundancy, preserve referential integrity, prevent invalid seat allocations, and support the specified transactional and analytical SQL workload.

Performance-tuning indexes beyond those automatically created by PRIMARY KEY and UNIQUE constraints will be considered in later optimization phases.

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

`booking_seats` also has the alternate candidate key `(booking_id, seat_id)`.

The supplied CSV files contain blank values in `bookings.offer_code` and `movie_reviews.review_text`. These columns will therefore permit NULL. The remaining columns will be treated as required, subject to final PostgreSQL loading and validation.

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

These alternate keys will be enforced only where the CSV data and business rules support them.

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

For `booking_seats`, the candidate keys are `(show_id, seat_id)` and `(booking_id, seat_id)`. The allocation price and associated booking information depend on the complete allocation key rather than on either component independently.

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

The final SQL schema will implement the following constraints, subject to verification against the supplied CSV data.

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

Further checks for booking status, payment method, screen type, seat class, show format, and other categorical values will be based on the complete distinct values found in the CSVs. No unsupported enum values will be assumed.

### 6.6 Show Overlap Constraint

Two shows must not overlap on the same screen.

This rule will be enforced using a PostgreSQL exclusion constraint on `screen_id` and the show time range. The half-open range `[starts_at, ends_at)` allows one show to start exactly when the preceding show ends.

The implementation will use PostgreSQL's `btree_gist` extension where available.

## 7. Seat-to-Show Screen Consistency

A foreign key on `booking_seats.seat_id` alone only proves that the seat exists. It does not prove that the seat belongs to the screen assigned to the show.

The database must enforce:

`shows.screen_id = seats.screen_id`

for every row in `booking_seats`.

The proposed implementation is a PostgreSQL trigger on `booking_seats` INSERT/UPDATE. It will retrieve the associated show and seat, compare their `screen_id` values, and reject an allocation if they do not match.

The composite foreign key `(booking_id, show_id)` separately ensures that the booking is associated with the same show as the allocation.

To keep this rule valid after allocations have been inserted, changes to `shows.screen_id` or `seats.screen_id` must also be guarded. Parent-table triggers will reject changes that would make existing allocations inconsistent. The implementation will be tested with both valid and deliberately invalid inserts and updates.

The primary key `(show_id, seat_id)` prevents duplicate allocation of the same seat for a show, including conflicting concurrent inserts.

## 8. Dataset Validation Evidence

The Python script `scripts/validate_data.py` was run against the 11 supplied CSV files.

The validation results were:

- **14 foreign-key relationship checks:** zero invalid references.
- **7 uniqueness checks:** zero duplicate combinations.
- **Booking-show consistency:** zero mismatches.
- **Seat-screen consistency:** zero mismatches.
- **Show-overlap validation:** zero overlapping show pairs on the same screen.

The seven uniqueness checks cover:

1. `cities.city_id`
2. `customers.email`
3. `customers.phone`
4. `bookings.booking_code`
5. `seats(screen_id, row_label, seat_number)`
6. `booking_seats(show_id, seat_id)`
7. `booking_seats(booking_id, seat_id)`

The script validates the CSV data before loading. These results do not replace PostgreSQL constraints. Equivalent database-level checks will be performed after loading the data.

## 9. Data Types and CSV Compatibility

The schema follows the headers of the supplied 11 CSV files.

The proposed PostgreSQL data-type mapping is:

- Identifiers and integer counts: `INTEGER` or an appropriate integer type.
- Descriptive and categorical text: `TEXT` or suitable `VARCHAR`.
- Monetary amounts and percentages: `NUMERIC`, avoiding floating-point precision errors.
- Calendar dates: `DATE`.
- Timestamps containing UTC offsets: `TIMESTAMPTZ`.
- Ratings: an integer type such as `SMALLINT`.

The CSV files contain 778,047 data rows in total:

| CSV | Expected rows |
|---|---:|
| cities | 10 |
| venues | 140 |
| screens | 490 |
| seats | 94,056 |
| movies | 300 |
| shows | 160,034 |
| customers | 40,000 |
| offers | 25 |
| bookings | 150,094 |
| booking_seats | 300,389 |
| movie_reviews | 32,510 |
| **Total** | **778,047** |

The initial inspection confirmed the supplied headers, identifier relationships, observed numeric ranges, and the two columns containing blank values. Final type compatibility, category checks, nullability, and row counts will be confirmed through PostgreSQL loading and integrity tests.

The initial schema phase will focus on constraints and data integrity. Workload-specific tuning indexes will be introduced only in the later optimization phase.