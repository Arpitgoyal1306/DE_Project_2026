# CP1 – Database Schema Design

## 1. Overview

The BookMyShow database is designed as a relational database using PostgreSQL. It contains 11 entities representing geographical locations, theatres, movies, shows, customers, bookings, offers, and reviews.

The schema is designed to maintain referential integrity, minimize unnecessary data redundancy, and support both transactional and analytical workloads.

## 2. Entities and Attributes

| Entity | Attributes |
|---|---|
| Cities | city_id (PK), city_name, state |
| Venues | venue_id (PK), venue_name, city_id (FK), chain, address |
| Screens | screen_id (PK), venue_id (FK), screen_name, screen_type, total_seats |
| Seats | seat_id (PK), screen_id (FK), row_label, seat_number, seat_class |
| Movies | movie_id (PK), title, language, certificate, duration_min, release_date |
| Shows | show_id (PK), movie_id (FK), screen_id (FK), starts_at, ends_at, format, base_price |
| Customers | customer_id (PK), full_name, email, phone, city_id (FK), created_at |
| Offers | offer_code (PK), description, discount_pct, max_discount, valid_from, valid_to |
| Bookings | booking_id (PK), booking_code, customer_id (FK), show_id (FK), booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code (FK, nullable), discount, total_amount, payment_method, status |
| Booking_Seats | booking_id (PK, FK), show_id (FK), seat_id (PK, FK), price |
| Movie_Reviews | review_id (PK), movie_id (FK), customer_id (FK), rating, review_text, created_at |

## 3. Primary Keys and Constraints

Primary keys uniquely identify records in their respective tables. Foreign keys establish relationships and prevent references to nonexistent records.

Important constraints include:

- Every entity has a primary key.
- Customer email and phone numbers must be unique.
- Booking codes must be unique.
- A seat's row label and seat number must be unique within its screen.
- A booking must reference an existing customer and show.
- An offer reference is optional for a booking.
- A seat must not be allocated more than once for the same show.
- Numeric values such as ticket amounts, prices, discounts, and ratings must satisfy appropriate business rules.
- A show's ending time must be later than its starting time.

The proposed composite primary key for `booking_seats` is `(booking_id, seat_id)`. An additional unique constraint on `(show_id, seat_id)` prevents the same seat from being allocated twice for one show.

## 4. Relationships and Cardinalities

| Relationship | Cardinality |
|---|---|
| Cities – Venues | One-to-Many |
| Cities – Customers | One-to-Many |
| Venues – Screens | One-to-Many |
| Screens – Seats | One-to-Many |
| Screens – Shows | One-to-Many |
| Movies – Shows | One-to-Many |
| Customers – Bookings | One-to-Many |
| Shows – Bookings | One-to-Many |
| Bookings – Booking_Seats | One-to-Many |
| Offers – Bookings | One-to-Many (optional on the booking side) |
| Movies – Movie_Reviews | One-to-Many |
| Customers – Movie_Reviews | One-to-Many |

A booking and a seat have a many-to-many relationship, resolved through the `booking_seats` junction table.

## 5. Functional Dependencies

The following functional dependencies form the basis of the relational design:

- `city_id → city_name, state`
- `venue_id → venue_name, city_id, chain, address`
- `screen_id → venue_id, screen_name, screen_type, total_seats`
- `seat_id → screen_id, row_label, seat_number, seat_class`
- `movie_id → title, language, certificate, duration_min, release_date`
- `show_id → movie_id, screen_id, starts_at, ends_at, format, base_price`
- `customer_id → full_name, email, phone, city_id, created_at`
- `offer_code → description, discount_pct, max_discount, valid_from, valid_to`
- `booking_id → booking_code, customer_id, show_id, booked_at, num_tickets, ticket_amount, convenience_fee, fnb_amount, offer_code, discount, total_amount, payment_method, status`
- `review_id → movie_id, customer_id, rating, review_text, created_at`

For `booking_seats`, the composite key `(booking_id, seat_id)` identifies each booking-seat allocation and determines `show_id` and `price`.

## 6. Normalization

**First Normal Form (1NF):** All tables contain atomic attributes, and each record is uniquely identifiable through a primary key. Repeating groups are avoided.

**Second Normal Form (2NF):** Non-key attributes depend on the complete primary key. In the `booking_seats` table, the composite key identifies the booking-seat allocation, and its attributes describe that allocation rather than depending on only part of the key.

**Third Normal Form (3NF):** Non-key attributes depend on the key, the whole key, and nothing but the key. For example, city information is stored in the `cities` table rather than being repeatedly stored in every venue and customer record. Similarly, movie, screen, customer, and offer details are maintained in their respective tables.

The design separates independent entities to reduce insertion, update, and deletion anomalies.

## 7. Data Integrity Validation

The supplied CSV datasets were examined before finalizing the schema. The validation results showed:

- All 14 tested foreign-key relationships had zero invalid references.
- All six tested unique-key combinations had zero duplicates.
- No booking-seat show mismatches were found.
- No seat-screen mismatches were found.
- No overlapping show schedules were detected on the same screen.

The supplied data therefore passed the tested referential-integrity and consistency checks. These validations will be repeated after loading the data into PostgreSQL.

## 8. Design Considerations

The database will use appropriate PostgreSQL data types, including integer identifiers, numeric monetary values, dates, and timezone-aware timestamps. Nullable fields will be preserved where the supplied data allows missing values.

The design also accounts for the business rule that a seat can be allocated only once for a particular show. Additional database-level enforcement will be considered for cross-table seat-screen consistency.

The schema is intended to support the specified 30-query workload. Performance indexes and query optimization will be considered in subsequent project phases rather than added during the initial schema-design phase.