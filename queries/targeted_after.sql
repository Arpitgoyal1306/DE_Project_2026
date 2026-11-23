-- @R06
-- Search: movies whose title contains "kalki"
-- Efficient on small movies relation (300 rows).
SELECT movie_id, title, language, release_date
FROM movies
WHERE title ILIKE '%kalki%'
ORDER BY release_date DESC;

-- @R13
-- Partnerships: offers that have never been redeemed
-- Optimization & Bug Fix: Original query used `NOT IN (SELECT b.offer_code FROM bookings b)`.
-- Because bookings.offer_code contains NULLs, SQL three-valued logic evaluated `x NOT IN (..., NULL)`
-- to UNKNOWN, returning 0 rows. Rewritten to NOT EXISTS to correctly handle NULLs and produce
-- the correct 7 unredeemed offers via an Anti Join.
SELECT o.offer_code, o.description, o.discount_pct
FROM offers o
WHERE NOT EXISTS (SELECT 1 FROM bookings b WHERE b.offer_code = o.offer_code);

-- @R21
-- Loyalty: 20 customers with the most confirmed bookings in 2026
-- Aggregates 89% of bookings; optimal via parallel sequential scan.
SELECT customer_id, count(*) AS bookings, sum(total_amount) AS spend
FROM bookings
WHERE status = 'CONFIRMED' AND booked_at >= '2026-01-01'
GROUP BY customer_id
ORDER BY bookings DESC, spend DESC
LIMIT 20;

-- @R22
-- Support console: all bookings, newest first, page 4,001 (25 per page)
-- Optimization: Accelerated by idx_bookings_booked_at; eliminates full table sort.
SELECT booking_id, booking_code, customer_id, show_id, status, booked_at
FROM bookings
ORDER BY booked_at DESC
OFFSET 100000
LIMIT 25;

-- @W02
-- Seat lock: the oldest PENDING booking adds 2 more seats (the unsold seats with the lowest ids in its show)
-- Optimization: Subquery `SELECT min(booking_id) FROM bookings WHERE status = 'PENDING'` accelerated by idx_bookings_pending.
INSERT INTO booking_seats (booking_id, show_id, seat_id, price)
SELECT b.booking_id, b.show_id, se.seat_id, 250.00
FROM bookings b
JOIN shows s  ON s.show_id = b.show_id
JOIN seats se ON se.screen_id = s.screen_id
WHERE b.booking_id = (SELECT min(booking_id) FROM bookings WHERE status = 'PENDING')
  AND NOT EXISTS (SELECT 1 FROM booking_seats bs WHERE bs.show_id = b.show_id AND bs.seat_id = se.seat_id)
ORDER BY se.seat_id
LIMIT 2
ON CONFLICT (show_id, seat_id) DO NOTHING;

