
\set ON_ERROR_STOP on

BEGIN;

-- Load parent tables first to satisfy foreign keys.

\copy bms.cities FROM 'large_data/cities.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.movies FROM 'large_data/movies.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.offers FROM 'large_data/offers.csv' WITH (FORMAT CSV, HEADER TRUE)

-- Load dependent tables.

\copy bms.venues FROM 'large_data/venues.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.screens FROM 'large_data/screens.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.seats FROM 'large_data/seats.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.shows FROM 'large_data/shows.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.customers FROM 'large_data/customers.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.bookings FROM 'large_data/bookings.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.booking_seats FROM 'large_data/booking_seats.csv' WITH (FORMAT CSV, HEADER TRUE)
\copy bms.movie_reviews FROM 'large_data/movie_reviews.csv' WITH (FORMAT CSV, HEADER TRUE)

-- Validate the imported row counts.

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM bms.cities) <> 10 THEN
        RAISE EXCEPTION 'cities row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.movies) <> 6000 THEN
        RAISE EXCEPTION 'movies row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.offers) <> 25 THEN
        RAISE EXCEPTION 'offers row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.venues) <> 2800 THEN
        RAISE EXCEPTION 'venues row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.screens) <> 9800 THEN
        RAISE EXCEPTION 'screens row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.seats) <> 1879182 THEN
        RAISE EXCEPTION 'seats row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.shows) <> 3201268 THEN
        RAISE EXCEPTION 'shows row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.customers) <> 800000 THEN
        RAISE EXCEPTION 'customers row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.bookings) <> 3004077 THEN
        RAISE EXCEPTION 'bookings row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.booking_seats) <> 6016946 THEN
        RAISE EXCEPTION 'booking_seats row count mismatch';
    END IF;

    IF (SELECT COUNT(*) FROM bms.movie_reviews) <> 651398 THEN
        RAISE EXCEPTION 'movie_reviews row count mismatch';
    END IF;

    RAISE NOTICE 'All 11 tables passed row-count validation.';
END $$;

-- Update table statistics for query planning.
ANALYZE;

COMMIT;

