
-- ============================================================
-- BOOKMYSHOW DATABASE
-- CP1: CSV Data Loading Script
-- PostgreSQL 15+
-- Dataset: 778,048 records across 11 CSV files
-- ============================================================

\set ON_ERROR_STOP on

SET search_path TO bms;

-- Run all loads as one transaction.
BEGIN;

-- 1. CITIES
\echo 'Loading cities...'
\copy cities FROM 'seed_data/seed_data/cities.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 2. VENUES
\echo 'Loading venues...'
\copy venues FROM 'seed_data/seed_data/venues.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 3. SCREENS
\echo 'Loading screens...'
\copy screens FROM 'seed_data/seed_data/screens.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 4. SEATS
\echo 'Loading seats...'
\copy seats FROM 'seed_data/seed_data/seats.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 5. MOVIES
\echo 'Loading movies...'
\copy movies FROM 'seed_data/seed_data/movies.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 6. SHOWS
\echo 'Loading shows...'
\copy shows FROM 'seed_data/seed_data/shows.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 7. CUSTOMERS
\echo 'Loading customers...'
\copy customers FROM 'seed_data/seed_data/customers.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 8. OFFERS
\echo 'Loading offers...'
\copy offers FROM 'seed_data/seed_data/offers.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 9. BOOKINGS
\echo 'Loading bookings...'
\copy bookings FROM 'seed_data/seed_data/bookings.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 10. BOOKING_SEATS
\echo 'Loading booking seats...'
\copy booking_seats FROM 'seed_data/seed_data/booking_seats.csv' WITH (FORMAT CSV, HEADER TRUE)

-- 11. MOVIE_REVIEWS
\echo 'Loading movie reviews...'
\copy movie_reviews FROM 'seed_data/seed_data/movie_reviews.csv' WITH (FORMAT CSV, HEADER TRUE)

-- ============================================================
-- VERIFY EXPECTED ROW COUNTS
-- ============================================================

\echo 'Verifying loaded row counts...'

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM cities) <> 10 THEN
        RAISE EXCEPTION 'cities row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM venues) <> 140 THEN
        RAISE EXCEPTION 'venues row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM screens) <> 490 THEN
        RAISE EXCEPTION 'screens row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM seats) <> 94056 THEN
        RAISE EXCEPTION 'seats row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM movies) <> 300 THEN
        RAISE EXCEPTION 'movies row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM shows) <> 160034 THEN
        RAISE EXCEPTION 'shows row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM customers) <> 40000 THEN
        RAISE EXCEPTION 'customers row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM offers) <> 25 THEN
        RAISE EXCEPTION 'offers row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bookings) <> 150094 THEN
        RAISE EXCEPTION 'bookings row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM booking_seats) <> 300389 THEN
        RAISE EXCEPTION 'booking_seats row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM movie_reviews) <> 32510 THEN
        RAISE EXCEPTION 'movie_reviews row count mismatch';
    END IF;

    IF (
        (SELECT COUNT(*) FROM cities) +
        (SELECT COUNT(*) FROM venues) +
        (SELECT COUNT(*) FROM screens) +
        (SELECT COUNT(*) FROM seats) +
        (SELECT COUNT(*) FROM movies) +
        (SELECT COUNT(*) FROM shows) +
        (SELECT COUNT(*) FROM customers) +
        (SELECT COUNT(*) FROM offers) +
        (SELECT COUNT(*) FROM bookings) +
        (SELECT COUNT(*) FROM booking_seats) +
        (SELECT COUNT(*) FROM movie_reviews)
    ) <> 778048 THEN
        RAISE EXCEPTION 'Total dataset row count mismatch';
    END IF;

    RAISE NOTICE 'All 11 table row counts verified successfully.';
END $$;

-- Update planner statistics after loading.
ANALYZE;

COMMIT;

\echo '============================================================'
\echo 'DATA LOADING COMPLETED SUCCESSFULLY'
\echo 'Expected total rows: 778048'
\echo '============================================================'
