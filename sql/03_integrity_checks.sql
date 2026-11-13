
-- ============================================================
-- BOOKMYSHOW DATABASE
-- CP1: Cross-Table Integrity Validation
-- PostgreSQL 15+
-- ============================================================

\set ON_ERROR_STOP on

SET search_path TO bms;

CREATE TEMP TABLE integrity_check_results (
    check_id INTEGER PRIMARY KEY,
    check_name TEXT NOT NULL,
    violation_count BIGINT NOT NULL
);


-- ============================================================
-- CHECK 1: Seat belongs to the screen of its show
-- ============================================================

\echo 'Running Check 1: Seat-screen consistency...'

INSERT INTO integrity_check_results
VALUES (
    1,
    'Seat belongs to the screen of its show',
    (
        SELECT COUNT(*)
        FROM booking_seats bs
        JOIN shows sh ON sh.show_id = bs.show_id
        JOIN seats se ON se.seat_id = bs.seat_id
        WHERE sh.screen_id <> se.screen_id
    )
);


-- ============================================================
-- CHECK 2: Screen capacity matches actual seat count
-- ============================================================

\echo 'Running Check 2: Screen capacity...'

INSERT INTO integrity_check_results
VALUES (
    2,
    'Screen capacity matches actual seat count',
    (
        SELECT COUNT(*)
        FROM (
            SELECT sc.screen_id
            FROM screens sc
            LEFT JOIN seats se ON se.screen_id = sc.screen_id
            GROUP BY sc.screen_id, sc.total_seats
            HAVING COUNT(se.seat_id) <> sc.total_seats
        ) AS mismatches
    )
);


-- ============================================================
-- CHECK 3: Booking allocations match status and ticket count
-- ============================================================

\echo 'Running Check 3: Booking seat allocations...'

INSERT INTO integrity_check_results
VALUES (
    3,
    'Booking allocations match status and num_tickets',
    (
        SELECT COUNT(*)
        FROM bookings b
        LEFT JOIN (
            SELECT booking_id, COUNT(*) AS allocated_seats
            FROM booking_seats
            GROUP BY booking_id
        ) bs ON bs.booking_id = b.booking_id
        WHERE
            (
                b.status IN ('CONFIRMED', 'PENDING')
                AND COALESCE(bs.allocated_seats, 0) <> b.num_tickets
            )
            OR
            (
                b.status IN ('CANCELLED', 'PAYMENT_FAILED')
                AND COALESCE(bs.allocated_seats, 0) <> 0
            )
    )
);


-- ============================================================
-- CHECK 4: Applied offer is valid on booking date
-- ============================================================

\echo 'Running Check 4: Offer validity...'

INSERT INTO integrity_check_results
VALUES (
    4,
    'Applied offer is valid on booking date',
    (
        SELECT COUNT(*)
        FROM bookings b
        JOIN offers o ON o.offer_code = b.offer_code
        WHERE b.booked_at::date
              NOT BETWEEN o.valid_from AND o.valid_to
    )
);


-- ============================================================
-- CHECK 5: No overlapping shows on the same screen
-- ============================================================

\echo 'Running Check 5: Show-time overlaps...'

INSERT INTO integrity_check_results
VALUES (
    5,
    'No overlapping shows on the same screen',
    (
        SELECT COUNT(*)
        FROM shows a
        JOIN shows b
            ON a.screen_id = b.screen_id
           AND a.show_id < b.show_id
           AND tstzrange(a.starts_at, a.ends_at, '[)')
               && tstzrange(b.starts_at, b.ends_at, '[)')
    )
);


-- ============================================================
-- FINAL RESULTS
-- ============================================================

\echo ''
\echo '============================================================'
\echo 'BOOKMYSHOW INTEGRITY VALIDATION REPORT'
\echo '============================================================'

SELECT
    check_id,
    check_name,
    violation_count,
    CASE
        WHEN violation_count = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS result
FROM integrity_check_results
ORDER BY check_id;


-- ============================================================
-- SUMMARY
-- ============================================================

SELECT
    COUNT(*) AS total_checks,
    COUNT(*) FILTER (
        WHERE violation_count = 0
    ) AS passed_checks,
    COUNT(*) FILTER (
        WHERE violation_count > 0
    ) AS failed_checks,
    COALESCE(SUM(violation_count), 0) AS total_violations
FROM integrity_check_results;


-- ============================================================
-- FAIL THE SCRIPT IF ANY CHECK FAILS
-- ============================================================

DO $$
DECLARE
    failed_count BIGINT;
    total_violations BIGINT;
BEGIN
    SELECT
        COUNT(*) FILTER (WHERE violation_count > 0),
        COALESCE(SUM(violation_count), 0)
    INTO failed_count, total_violations
    FROM integrity_check_results;

    IF failed_count > 0 THEN
        RAISE EXCEPTION
            'Integrity validation failed: % checks failed, % violations.',
            failed_count,
            total_violations;
    END IF;

    RAISE NOTICE
        'SUCCESS: All five integrity checks passed.';
END;
$$;

DROP TABLE integrity_check_results;

\echo '============================================================'
\echo 'INTEGRITY VALIDATION COMPLETED SUCCESSFULLY'
\echo '============================================================'
