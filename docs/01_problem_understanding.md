# CP1 – Problem Understanding

## 1. Business Background

BookMyShow connects movie-goers with cinemas for movie discovery, showtime search, seat selection, and ticket booking. Its database must maintain accurate relationships among venues, screens, seats, movies, shows, customers, bookings, offers, and reviews. It must support reliable real-time transactions as well as business reporting.

## 2. Business Problems, Stakeholders, and Workload Classification

- **P1 – Movie discovery and showtime search:** Find currently showing movies, cinemas, and showtimes. **Stakeholders:** movie-goers; customer app team. **Type:** customer-facing / real-time.
- **P2 – Seat availability and booking:** Display seat layouts and availability while preventing concurrent duplicate seat allocation. **Stakeholders:** movie-goers; booking engine team. **Type:** customer-facing / real-time.
- **P3 – Pending payments and seat expiry:** Track pending payments, confirm bookings, and release expired seat reservations. **Stakeholders:** payments team; seat-lock service. **Type:** operational / real-time.
- **P4 – Customer bookings and account access:** Retrieve customer details, booking history, and individual bookings. **Stakeholders:** customers; customer support. **Type:** customer-facing / real-time.
- **P5 – Theatre occupancy and operations:** Calculate occupancy, identify never-sold seats, and find gaps between shows. **Stakeholders:** cinema managers; programming team. **Type:** operational and analytical.
- **P6 – Unused offers:** Identify promotional offers that have not been redeemed. **Stakeholder:** partnerships team. **Type:** reporting / analytics.
- **P7 – Box-office reporting:** Produce show-wise and movie-wise ticket-sales and collection reports. **Stakeholders:** distributors; business teams. **Type:** reporting / analytics.
- **P8 – Business analytics:** Analyze revenue, regional collections, ratings, loyalty, booking patterns, and cancellations. **Stakeholders:** finance; insights and management teams. **Type:** reporting / analytics.

P1–P4 are latency-sensitive operational workloads requiring timely responses and transactional consistency. P5 combines operational queries with analysis. P6–P8 primarily aggregate historical data for business decisions.

## 3. Assumptions and Scope

- Each venue belongs to one city and contains one or more screens.
- Each screen contains multiple seats.
- Each show is for one movie on one screen.
- Each booking belongs to one customer and one show and may contain multiple seats.
- A seat can be allocated at most once per show.
- An offer is optional for a booking.
- Customers may submit movie reviews.

The project covers PostgreSQL schema design, keys and integrity constraints, loading and validating the supplied CSV data, and evaluating the specified SQL workloads. Building the customer-facing application is outside scope.
