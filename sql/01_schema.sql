
-- ============================================================
-- BOOKMYSHOW DATABASE
-- CP1: Database Schema Definition
-- PostgreSQL 15+
-- ============================================================

-- Create the project schema
CREATE SCHEMA IF NOT EXISTS bms;

SET search_path TO bms;

-- Required for the show-time exclusion constraint
CREATE EXTENSION IF NOT EXISTS btree_gist;


-- ============================================================
-- 1. CITIES
-- ============================================================

CREATE TABLE cities (
    city_id SMALLINT PRIMARY KEY,
    city_name VARCHAR(30) NOT NULL,
    state VARCHAR(30) NOT NULL
);


-- ============================================================
-- 2. VENUES
-- ============================================================

CREATE TABLE venues (
    venue_id SMALLINT PRIMARY KEY,
    venue_name VARCHAR(60) NOT NULL,
    city_id SMALLINT NOT NULL,
    chain VARCHAR(30) NOT NULL,
    address VARCHAR(100) NOT NULL,

    CONSTRAINT fk_venues_city
        FOREIGN KEY (city_id)
        REFERENCES cities(city_id)
        ON DELETE RESTRICT
);


-- ============================================================
-- 3. SCREENS
-- ============================================================

CREATE TABLE screens (
    screen_id SMALLINT PRIMARY KEY,
    venue_id SMALLINT NOT NULL,
    screen_name VARCHAR(20) NOT NULL,
    screen_type VARCHAR(20) NOT NULL,
    total_seats SMALLINT NOT NULL,

    CONSTRAINT fk_screens_venue
        FOREIGN KEY (venue_id)
        REFERENCES venues(venue_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_screens_total_seats
        CHECK (total_seats > 0)
);


-- ============================================================
-- 4. SEATS
-- ============================================================

CREATE TABLE seats (
    seat_id INTEGER PRIMARY KEY,
    screen_id SMALLINT NOT NULL,
    row_label VARCHAR(5) NOT NULL,
    seat_number SMALLINT NOT NULL,
    seat_class VARCHAR(20) NOT NULL,

    CONSTRAINT fk_seats_screen
        FOREIGN KEY (screen_id)
        REFERENCES screens(screen_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_seats_screen_position
        UNIQUE (screen_id, row_label, seat_number),

    CONSTRAINT chk_seats_seat_number
        CHECK (seat_number > 0)
);


-- ============================================================
-- 5. MOVIES
-- ============================================================

CREATE TABLE movies (
    movie_id SMALLINT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    language VARCHAR(30) NOT NULL,
    certificate VARCHAR(10) NOT NULL,
    duration_min SMALLINT NOT NULL,
    release_date DATE NOT NULL,

    CONSTRAINT chk_movies_duration
        CHECK (duration_min > 0)
);


-- ============================================================
-- 6. SHOWS
-- ============================================================

CREATE TABLE shows (
    show_id INTEGER PRIMARY KEY,
    movie_id SMALLINT NOT NULL,
    screen_id SMALLINT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    format VARCHAR(10) NOT NULL,
    base_price NUMERIC(10,2) NOT NULL,

    CONSTRAINT fk_shows_movie
        FOREIGN KEY (movie_id)
        REFERENCES movies(movie_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_shows_screen
        FOREIGN KEY (screen_id)
        REFERENCES screens(screen_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_shows_time_order
        CHECK (ends_at > starts_at),

    CONSTRAINT chk_shows_base_price
        CHECK (base_price >= 0),

    -- Prevent overlapping shows on the same screen.
    -- The [) range allows one show to start exactly
    -- when the previous show ends.
    CONSTRAINT ex_shows_no_overlap
        EXCLUDE USING GIST (
            screen_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
);


-- ============================================================
-- 7. CUSTOMERS
-- ============================================================

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    city_id SMALLINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_customers_email
        UNIQUE (email),

    CONSTRAINT uq_customers_phone
        UNIQUE (phone),

    CONSTRAINT fk_customers_city
        FOREIGN KEY (city_id)
        REFERENCES cities(city_id)
        ON DELETE RESTRICT
);


-- ============================================================
-- 8. OFFERS
-- ============================================================

CREATE TABLE offers (
    offer_code VARCHAR(20) PRIMARY KEY,
    description VARCHAR(100) NOT NULL,
    discount_pct NUMERIC(5,2) NOT NULL,
    max_discount NUMERIC(10,2) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,

    CONSTRAINT chk_offers_discount_pct
        CHECK (discount_pct BETWEEN 0 AND 100),

    CONSTRAINT chk_offers_max_discount
        CHECK (max_discount >= 0),

    CONSTRAINT chk_offers_valid_dates
        CHECK (valid_to >= valid_from)
);


-- ============================================================
-- 9. BOOKINGS
-- ============================================================

CREATE TABLE bookings (
    booking_id INTEGER PRIMARY KEY,
    booking_code VARCHAR(20) NOT NULL,
    customer_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL,
    booked_at TIMESTAMPTZ NOT NULL,
    num_tickets SMALLINT NOT NULL,
    ticket_amount NUMERIC(10,2) NOT NULL,
    convenience_fee NUMERIC(10,2) NOT NULL,
    fnb_amount NUMERIC(10,2) NOT NULL,
    offer_code VARCHAR(20),
    discount NUMERIC(10,2) NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,

    CONSTRAINT uq_bookings_booking_code
        UNIQUE (booking_code),

    -- Required as the referenced key for the composite FK
    -- in booking_seats.
    CONSTRAINT uq_bookings_id_show
        UNIQUE (booking_id, show_id),

    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_bookings_show
        FOREIGN KEY (show_id)
        REFERENCES shows(show_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_bookings_offer
        FOREIGN KEY (offer_code)
        REFERENCES offers(offer_code)
        ON DELETE RESTRICT,

    CONSTRAINT chk_bookings_num_tickets
        CHECK (num_tickets > 0),

    CONSTRAINT chk_bookings_ticket_amount
        CHECK (ticket_amount >= 0),

    CONSTRAINT chk_bookings_convenience_fee
        CHECK (convenience_fee >= 0),

    CONSTRAINT chk_bookings_fnb_amount
        CHECK (fnb_amount >= 0),

    CONSTRAINT chk_bookings_discount
        CHECK (discount >= 0),

    CONSTRAINT chk_bookings_total_amount
        CHECK (total_amount >= 0),

    CONSTRAINT chk_bookings_discount_limit
        CHECK (
            discount <= ticket_amount
                      + convenience_fee
                      + fnb_amount
        ),

    CONSTRAINT chk_bookings_total_calculation
        CHECK (
            total_amount = ticket_amount
                         + convenience_fee
                         + fnb_amount
                         - discount
        )
);


-- ============================================================
-- 10. BOOKING_SEATS
-- ============================================================

CREATE TABLE booking_seats (
    booking_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL,
    seat_id INTEGER NOT NULL,
    price NUMERIC(10,2) NOT NULL,

    -- A seat can only be allocated once per show.
    CONSTRAINT pk_booking_seats
        PRIMARY KEY (show_id, seat_id),

    CONSTRAINT uq_booking_seats_booking_seat
        UNIQUE (booking_id, seat_id),

    -- Ensures the booking belongs to the same show.
    CONSTRAINT fk_booking_seats_booking_show
        FOREIGN KEY (booking_id, show_id)
        REFERENCES bookings(booking_id, show_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_booking_seats_show
        FOREIGN KEY (show_id)
        REFERENCES shows(show_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_booking_seats_seat
        FOREIGN KEY (seat_id)
        REFERENCES seats(seat_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_booking_seats_price
        CHECK (price >= 0)
);


-- ============================================================
-- 11. MOVIE_REVIEWS
-- ============================================================

CREATE TABLE movie_reviews (
    review_id INTEGER PRIMARY KEY,
    movie_id SMALLINT NOT NULL,
    customer_id INTEGER NOT NULL,
    rating SMALLINT NOT NULL,
    review_text TEXT,
    created_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_movie_reviews_movie
        FOREIGN KEY (movie_id)
        REFERENCES movies(movie_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_movie_reviews_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_movie_reviews_rating
        CHECK (rating BETWEEN 1 AND 10)
);


-- ============================================================
-- END OF SCHEMA DEFINITION
-- 11 TABLES
-- No custom triggers or functions.
-- No additional performance indexes.
-- ============================================================
