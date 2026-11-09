# CP1 – Problem Understanding

## 1. Business Background and Problem Statement

BookMyShow is an online movie and event ticketing platform that connects customers with cinemas. Customers use the platform to discover movies, explore theatres, check showtimes, select seats, and book tickets.

These operations require a reliable database to manage interconnected information about cities, venues, screens, seats, movies, shows, customers, bookings, offers, and reviews. The database must maintain data accuracy, enforce relationships, and prevent issues such as the same seat being allocated to multiple customers for the same show.

The platform must also support business reporting, including theatre occupancy, ticket sales, revenue, offer usage, customer activity, and movie performance. Therefore, the database must support both transactional operations and analytical workloads.

## 2. Identified Business Problems

The project addresses eight major business problems:

- **P1 – Movie Discovery and Showtime Search:** Customers need to find currently showing movies, theatres, and showtimes efficiently.
- **P2 – Seat Availability and Booking:** Customers need accurate seat layouts and availability. The system must prevent duplicate seat allocation for a show, even when multiple customers attempt to book the same seat concurrently.
- **P3 – Pending Payments and Seat Expiry:** The booking process must track pending payments, booking confirmation, and temporary seat reservations.
- **P4 – Customer Bookings and Account Access:** Customers and support teams need reliable access to customer details and booking history.
- **P5 – Theatre Occupancy and Operations:** Theatre operators need occupancy reports, information about unsold seats, and gaps between consecutive shows.
- **P6 – Unused Offers:** Business teams need to identify promotional offers that have not been redeemed.
- **P7 – Box-Office Reporting:** Distributors and business teams need show-wise and movie-wise ticket sales and collection reports.
- **P8 – Business Analytics:** Management needs insights into revenue distribution, regional collections, movie ratings, customer loyalty, booking patterns, and cancellations.

## 3. Stakeholders

- **Customers:** Movie discovery, showtime search, seat selection, booking, and booking-history access.
- **Theatre Operators:** Screen, seat, show-schedule, and occupancy management.
- **Booking and Payment Systems:** Booking records, payment-status tracking, and duplicate-seat prevention.
- **Business and Management Teams:** Revenue, customer, offer, and performance analysis.
- **Distributors and Content Partners:** Movie-wise and show-wise ticket collection reports.
- **Customer Support Teams:** Customer and booking information for resolving booking-related issues.

## 4. Workload Classification

**Operational and Customer-facing Workloads (P1–P4):** These include movie searches, showtime lookup, seat availability, booking creation, payment-status tracking, and customer booking lookup. They require timely responses and strong transactional consistency.

**Operational and Analytical Workloads (P5):** Theatre operations include interactive tasks such as checking seat availability and planning gaps between consecutive shows, as well as analytical tasks such as calculating occupancy and identifying seats that have never been sold. The workload type depends on the query and its response-time requirements.

**Reporting and Analytical Workloads (P6–P8):** These involve aggregating booking, show, customer, and movie data to analyze unused offers, box-office collections, revenue distribution, ratings, customer loyalty, booking patterns, and cancellations.

## 5. Assumptions and Project Scope

- Each venue belongs to one city and can contain multiple screens.
- Each screen contains multiple seats.
- Each show is associated with one movie and one screen.
- Each booking belongs to one customer and one show and may contain multiple seats.
- A seat can be allocated at most once for a particular show.
- An offer is optional for a booking.
- Customers can submit movie reviews.

The project focuses on designing a normalized PostgreSQL database, defining entities and relationships, implementing primary keys, foreign keys and integrity constraints, loading and validating the supplied CSV datasets, and evaluating the specified SQL workloads. Developing a complete customer-facing application is outside the project scope.
