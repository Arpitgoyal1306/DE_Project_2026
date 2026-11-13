# CP1 – Problem Understanding

## 1. Business Background and Problem Statement

BookMyShow is an online movie and event ticketing platform that connects customers with cinemas. Customers use the platform to discover movies, explore theatres, check showtimes, select seats, and book tickets.

These operations require a reliable database to manage interconnected information about cities, venues, screens, seats, movies, shows, customers, bookings, offers, and reviews. The database must maintain data accuracy, enforce relationships, and prevent issues such as the same seat being allocated to multiple customers for the same show.

The platform must also support business reporting, including theatre occupancy, ticket sales, revenue, offer usage, customer activity, and movie performance. Therefore, the database must support both transactional operations and analytical workloads.

## 2. Business Problems, Stakeholders, and Workload Classification

| Problem | Business need | Primary stakeholder(s) | Workload classification |
|---|---|---|---|
| **P1 – Movie discovery and showtime search** | Find currently showing movies, cinemas, and showtimes efficiently. | Movie-goers; customer app team | Customer-facing / real-time |
| **P2 – Seat availability and booking** | Display accurate seat layouts and availability, and prevent concurrent duplicate seat allocation. | Movie-goers; booking engine team | Customer-facing / real-time |
| **P3 – Pending payments and seat expiry** | Track pending payments, booking confirmation, and temporary seat reservations; release expired holds. | Payments team; seat-lock service | Operational / real-time |
| **P4 – Customer bookings and account access** | Retrieve customer details, booking history, and individual bookings reliably. | Customers; customer support team | Customer-facing / real-time |
| **P5 – Theatre occupancy and operations** | Check occupancy, identify never-sold seats, and find gaps between consecutive shows. | Cinema / venue managers; programming team | Operational and analytical |
| **P6 – Unused offers** | Identify promotional offers that have not been redeemed. | Partnerships team | Reporting / analytics |
| **P7 – Box-office reporting** | Produce show-wise and movie-wise ticket-sales and collection reports. | Distributors; business teams | Reporting / analytics |
| **P8 – Business analytics** | Analyze revenue distribution, regional collections, ratings, customer loyalty, booking patterns, and cancellations. | Finance; insights and management teams | Reporting / analytics |

P1–P4 are latency-sensitive operational workloads that require timely responses and transactional consistency. P5 combines interactive operational queries with analytical reporting. P6–P8 primarily aggregate historical data for business decisions.

## 5. Assumptions and Project Scope

- Each venue belongs to one city and can contain multiple screens.
- Each screen contains multiple seats.
- Each show is associated with one movie and one screen.
- Each booking belongs to one customer and one show and may contain multiple seats.
- A seat can be allocated at most once for a particular show.
- An offer is optional for a booking.
- Customers can submit movie reviews.

The project focuses on designing a normalized PostgreSQL database, defining entities and relationships, implementing primary keys, foreign keys and integrity constraints, loading and validating the supplied CSV datasets, and evaluating the specified SQL workloads. Developing a complete customer-facing application is outside the project scope.
