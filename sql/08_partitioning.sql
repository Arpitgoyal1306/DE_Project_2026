\set ON_ERROR_STOP on

BEGIN;

-- Prevent concurrent reads/writes during the table migration.
-- The lock is held until COMMIT.
LOCK TABLE bms.booking_seats IN ACCESS EXCLUSIVE MODE;

-- ============================================================
-- PARTITION BOOKING_SEATS BY HASH(show_id)
-- ============================================================

-- Create a new partitioned table first so the original data
-- remains available until the migration has been validated.

CREATE TABLE bms.booking_seats_partitioned (
    booking_id INTEGER NOT NULL,
    show_id INTEGER NOT NULL,
    seat_id INTEGER NOT NULL,
    price NUMERIC(10,2) NOT NULL,

    CONSTRAINT pk_booking_seats_partitioned
        PRIMARY KEY (show_id, seat_id),

    -- The partition key must be included in unique constraints.
    CONSTRAINT uq_booking_seats_booking_show_seat
        UNIQUE (booking_id, show_id, seat_id),

    CONSTRAINT fk_booking_seats_booking_show_partitioned
        FOREIGN KEY (booking_id, show_id)
        REFERENCES bms.bookings(booking_id, show_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_booking_seats_show_partitioned
        FOREIGN KEY (show_id)
        REFERENCES bms.shows(show_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_booking_seats_seat_partitioned
        FOREIGN KEY (seat_id)
        REFERENCES bms.seats(seat_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_booking_seats_price_partitioned
        CHECK (price >= 0)
)
PARTITION BY HASH (show_id);

-- Create 16 hash partitions.

CREATE TABLE bms.booking_seats_p00
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);

CREATE TABLE bms.booking_seats_p01
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);

CREATE TABLE bms.booking_seats_p02
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 2);

CREATE TABLE bms.booking_seats_p03
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 3);

CREATE TABLE bms.booking_seats_p04
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 4);

CREATE TABLE bms.booking_seats_p05
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 5);

CREATE TABLE bms.booking_seats_p06
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 6);

CREATE TABLE bms.booking_seats_p07
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 7);

CREATE TABLE bms.booking_seats_p08
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 8);

CREATE TABLE bms.booking_seats_p09
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 9);

CREATE TABLE bms.booking_seats_p10
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 10);

CREATE TABLE bms.booking_seats_p11
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 11);

CREATE TABLE bms.booking_seats_p12
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 12);

CREATE TABLE bms.booking_seats_p13
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 13);

CREATE TABLE bms.booking_seats_p14
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 14);

CREATE TABLE bms.booking_seats_p15
    PARTITION OF bms.booking_seats_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 15);

-- Preserve efficient lookups by booking_id.
CREATE INDEX idx_booking_seats_booking_id_seat_id
    ON bms.booking_seats_partitioned (booking_id, seat_id);

-- Copy existing data into the new partitioned table.
INSERT INTO bms.booking_seats_partitioned
    (booking_id, show_id, seat_id, price)
SELECT booking_id, show_id, seat_id, price
FROM bms.booking_seats;

-- Validate that every original row was copied.
DO $$
DECLARE
    original_count BIGINT;
    partitioned_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO original_count
    FROM bms.booking_seats;

    SELECT COUNT(*) INTO partitioned_count
    FROM bms.booking_seats_partitioned;

    IF original_count <> partitioned_count THEN
        RAISE EXCEPTION
            'Partition migration failed: original %, partitioned %',
            original_count, partitioned_count;
    END IF;

    RAISE NOTICE 'Migration validated: % rows copied.',
        partitioned_count;
END $$;

-- No tables reference booking_seats through an inbound FK.
-- Replace the original table only after successful validation.
DROP TABLE bms.booking_seats;

ALTER TABLE bms.booking_seats_partitioned
    RENAME TO booking_seats;

-- Restore familiar constraint names where their definitions
-- remain equivalent.
ALTER TABLE bms.booking_seats
    RENAME CONSTRAINT pk_booking_seats_partitioned
    TO pk_booking_seats;

ALTER TABLE bms.booking_seats
    RENAME CONSTRAINT fk_booking_seats_booking_show_partitioned
    TO fk_booking_seats_booking_show;

ALTER TABLE bms.booking_seats
    RENAME CONSTRAINT fk_booking_seats_show_partitioned
    TO fk_booking_seats_show;

ALTER TABLE bms.booking_seats
    RENAME CONSTRAINT fk_booking_seats_seat_partitioned
    TO fk_booking_seats_seat;

ALTER TABLE bms.booking_seats
    RENAME CONSTRAINT chk_booking_seats_price_partitioned
    TO chk_booking_seats_price;

ANALYZE bms.booking_seats;

COMMIT;
