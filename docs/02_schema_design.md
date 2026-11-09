# CP1 – Database Schema Design

## 1. Overview

The BookMyShow database is modelled as 11 PostgreSQL relations based on the supplied CSV files. The design separates customers, movies, theatres, shows, bookings, offers, and reviews to reduce redundancy and preserve referential integrity.

The schema is intended to support the specified transactional and analytical workload. Performance indexes beyond those automatically created for primary-key and unique constraints will be considered in later optimization phases.

## 2. Relations, Attributes, and Keys

The following attributes are taken from the CSV headers. PK means primary key; FK means foreign key.

| Relation | Attributes and keys |
|---|---|
| cities | city_id (PK), city_name, state |
| venues | venue_id (PK), venue_name, city_id (FK), chain, address |
| screens | screen_id (PK), venue_id (FK), screen_name, screen_type, total_seats |
| seats | seat_id (PK), screen_id (FK), row_label, seat_number, seat_class |
| movies | movie_id (PK), title, language, certificate, duration_min, release_date |
| shows | show_id (PK), movie_id (FK), screen_id (FK), starts_at, ends_at, format, base_price |
| customers | customer_id (PK), full_name, email, phone, city_id (FK), created_at |
| offers | offer_code (PK), description, discount_pct, max_discount, valid_from, valid_to |
| bookings | booking_id (PK), booking_code, customer_id (FK), show_id (FK), booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code (nullable FK), discount, total_amount, payment_method, status |
| booking_seats | show_id, seat_id, booking_id, price; proposed PK: (show_id, seat_id); alternate candidate key: (booking_id, seat_id) |
| movie_reviews | review_id (PK), movie_id (FK), customer_id (FK), rating, review_text (nullable), created_at |

The supplied data contains no blank values in the columns except `bookings.offer_code` and `movie_reviews.review_text`. These two columns are therefore designed to permit NULL. This observation will be checked again during loading.

## 3. Candidate Keys and Functional Dependencies

A functional dependency X → Y means that a value of X determines exactly one value of Y in a relation.

The principal dependencies are:

- cities: city_id → city_name, state
- venues: venue_id → venue_name, city_id, chain, address
- screens: screen_id → venue_id, screen_name, screen_type, total_seats
- seats: seat_id → screen_id, row_label, seat_number, seat_class
- seats: (screen_id, row_label, seat_number) → seat_id, seat_class
- movies: movie_id → title, language, certificate, duration_min, release_date
- shows: show_id → movie_id, screen_id, starts_at, ends_at, format, base_price
- customers: customer_id → full_name, email, phone, city_id, created_at
- customers: email → customer_id, full_name, phone, city_id, created_at
- customers: phone → customer_id, full_name, email, city_id, created_at
- offers: offer_code → description, discount_pct, max_discount, valid_from, valid_to
- bookings: booking_id → booking_code, customer_id, show_id, booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code, discount, total_amount, payment_method, status
- bookings: booking_code → booking_id and the remaining booking attributes
- movie_reviews: review_id → movie_id, customer_id, rating, review_text, created_at

### booking_seats: key and dependency reasoning

The CSV relation contains `(booking_id, show_id, seat_id, price)`. A booking belongs to exactly one show, so the `bookings` relation establishes:

`booking_id → show_id`

The inspected data also supports both of these candidate keys in `booking_seats`:

- `(show_id, seat_id)`: a seat can occur at most once for a particular show.
- `(booking_id, seat_id)`: a seat occurs at most once within a particular booking.

The corresponding dependencies are:

- `(show_id, seat_id) → booking_id, price`
- `(booking_id, seat_id) → show_id, price`

The second dependency is consistent with `booking_id → show_id` in `bookings`. Thus, `show_id` is repeated in `booking_seats` even though it can be obtained by joining `bookings`.

We retain `show_id` because the database must enforce the important uniqueness rule `(show_id, seat_id)` directly. The composite foreign key `(booking_id, show_id)` will reference a corresponding unique key in `bookings`, ensuring that the repeated show ID agrees with the booking.

For this relation, `(show_id, seat_id)` is the selected primary key and `(booking_id, seat_id)` is an alternate candidate key. Because `show_id` is a prime attribute (part of a candidate key), the dependency `booking_id → show_id` does not violate 3NF. However, `booking_id` is not a superkey of this relation, so this dependency means the relation does not satisfy BCNF. This trade-off is documented rather than hidden.

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
| offers | bookings | 1:N; offer is optional for a booking |
| movies | movie_reviews | 1:N |
| customers | movie_reviews | 1:N |

Bookings and seats form a many-to-many relationship resolved by `booking_seats`.

## 5. Normalization Analysis

### First Normal Form (1NF)

Each CSV field represents a single value and there are no repeating groups such as `seat_1`, `seat_2`, and `seat_3` in a booking row. Multiple seats are represented as separate rows in `booking_seats`. Each relation has a key that identifies its rows.

### Second Normal Form (2NF)

All single-column-key relations are in 2NF because their non-key attributes depend on the whole key. In `booking_seats`, `price` and booking allocation details depend on the complete seat-allocation key, not on `show_id` alone or `seat_id` alone. The alternate key `(booking_id, seat_id)` also identifies one allocation.

### Third Normal Form (3NF)

The entity relations separate attributes that depend on other entities: city details are stored in `cities`, venue details in `venues`, screen details in `screens`, movie details in `movies`, and offer details in `offers`.

For example, `venue_id` determines `city_id`, but `city_name` and `state` are stored in `cities` rather than repeated in `venues`. This avoids transitive dependencies within the venue relation.

The `booking_seats` relation has the documented dependency `booking_id → show_id`. It satisfies 3NF because `show_id` is a prime attribute (it belongs to candidate key `(show_id, seat_id)`), but it does not satisfy BCNF for this dependency. Keeping `show_id` allows a direct unique constraint on `(show_id, seat_id)`. The design therefore prioritizes enforceable seat-per-show uniqueness and explicitly records this BCNF trade-off.

## 6. Intended Integrity Constraints

The final DDL will implement constraints supported by the CSV data and business rules:

- PRIMARY KEY on each relation; `booking_seats` will use `(show_id, seat_id)`.
- FOREIGN KEY relationships shown in the entity and relationship sections.
- UNIQUE `customers(email)`, UNIQUE `customers(phone)`, UNIQUE `bookings(booking_code)`.
- UNIQUE `seats(screen_id, row_label, seat_number)`.
- UNIQUE `booking_seats(booking_id, seat_id)`, in addition to its primary key.
- NOT NULL on required columns. `bookings.offer_code` and `movie_reviews.review_text` remain nullable based on the CSV.
- CHECK `shows(ends_at > starts_at)`.
- CHECK `movies(duration_min > 0)`, `screens(total_seats > 0)`, `bookings(num_tickets > 0)`, and non-negative monetary amounts.
- CHECK `movie_reviews.rating BETWEEN 1 AND 10`; the observed data ranges from 2 to 10, and the rating scale is out of 10.
- CHECK `offers.discount_pct BETWEEN 0 AND 100`, `offers.max_discount >= 0`, and `valid_to >= valid_from`.
- Additional checks for enumerated status, payment, screen, seat, and show-format values will be added only after inspecting the complete distinct-value sets.

### Seat-to-show screen consistency

A foreign key on `booking_seats.seat_id` alone proves that the seat exists, but it does not prove that the seat belongs to the screen assigned to the show.

The schema will enforce this cross-table rule with a PostgreSQL trigger on `booking_seats` INSERT/UPDATE. The trigger will compare `shows.screen_id` with `seats.screen_id` and reject an allocation if they differ.

The `booking_seats` row will also have a composite foreign key `(booking_id, show_id)` referencing a UNIQUE `(booking_id, show_id)` key in `bookings`. This prevents a row from associating a booking with a different show.

The PRIMARY KEY `(show_id, seat_id)` prevents two bookings from allocating the same seat for the same show, including concurrent inserts.

The trigger and related key constraints will be tested with both valid and deliberately invalid inserts during schema validation.

## 7. Dataset Validation Evidence

A Python validation script was run against the 11 supplied CSV files. It reported:

- 14 tested foreign-key relationships: zero invalid references.
- Six tested unique-key combinations: zero duplicates.
- Booking-seat show mismatches: zero.
- Seat-screen mismatches: zero.
- Potential overlapping show pairs on the same screen: zero.

These are checks on the supplied dataset, not a substitute for constraints in PostgreSQL. The checks will be made reproducible by committing the validation script and rerunning equivalent SQL checks after loading the CSV files.

## 8. Data Types and CSV Compatibility

The final DDL will use INTEGER for the supplied identifiers and counts, TEXT or suitable VARCHAR for textual attributes, NUMERIC for monetary amounts and percentages, DATE for calendar dates, and TIMESTAMPTZ for timestamps containing UTC offsets. Monetary values will not use floating-point types.

The schema column list follows the headers of the supplied 11 CSV files. Exact nullability, distinct category values, numeric ranges, and successful COPY compatibility will be verified before the schema is considered final.

No workload-tuning indexes beyond indexes created by PRIMARY KEY and UNIQUE constraints will be added in this initial schema phase.