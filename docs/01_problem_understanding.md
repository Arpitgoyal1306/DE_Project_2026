# CP1 – Problem Understanding

## 1. Business Background and Problem Statement

BookMyShow is an online movie-ticketing platform that connects customers with cinemas and enables them to discover movies, explore theatres, view showtimes, select seats, and book tickets. Behind these activities, the platform must manage interconnected information about customers, cities, venues, screens, seats, movies, shows, bookings, offers, and reviews.

The main problem addressed in this project is designing a reliable and efficient relational database that can handle these interconnected operations while maintaining data accuracy and consistency. For example, when multiple customers attempt to book seats for the same show, the system must prevent duplicate seat allocation. Similarly, booking details, payment methods, booking statuses, and offer information must remain consistent.

Apart from supporting day-to-day transactions, the database must also provide meaningful business insights. Theatre operators and management need information about occupancy, ticket sales, revenue, unused offers, customer activity, and movie performance. Therefore, the database must support both operational transactions and analytical queries efficiently.

## 2. Identified Business Problems

The project addresses eight major business problems:

- **P1 – Movie Discovery and Showtime Search:** Customers need to quickly find currently showing movies, available theatres, and showtimes based on their preferences. The database must support efficient searching and retrieval of this information.

- **P2 – Seat Availability and Booking:** Customers must be able to view screen layouts and select available seats. The database must maintain seat allocation accurately and prevent the same seat from being booked more than once for a particular show.

- **P3 – Pending Payments and Seat Expiry:** The booking process must account for pending payments, booking confirmation, and expiry of temporary seat reservations. This requires consistent tracking of booking and payment-related statuses.

- **P4 – Customer Bookings and Account Access:** Customers and support teams need to retrieve booking details, customer information, and previous booking records quickly and accurately.

- **P5 – Theatre Occupancy and Operations:** Theatre operators need to evaluate show occupancy, identify seats that have never been sold, and understand the gaps between consecutive shows for operational planning.

- **P6 – Unused Offers:** Business and partnership teams need to identify promotional offers that have never been redeemed so they can evaluate offer effectiveness.

- **P7 – Box-Office Reporting:** Distributors and business teams need show-wise and movie-wise ticket sales and collection information to evaluate box-office performance.

- **P8 – Business Analytics:** Management needs insights into revenue distribution, regional collections, movie ratings, customer loyalty, booking patterns, and cancellations to support business decisions.

## 3. Stakeholders

- **Customers:** Need movie discovery, showtime search, seat selection, booking, and booking-history access.
- **Theatre Operators:** Need screen, seat, show-schedule, and occupancy information.
- **Booking and Payment Systems:** Need accurate booking records, payment-related statuses, and protection against duplicate seat allocation.
- **Business and Management Teams:** Need revenue, customer, offer, and performance analysis.
- **Distributors and Content Partners:** Need movie-wise and show-wise ticket collection reports.
- **Customer Support Teams:** Need access to customer and booking information to resolve booking-related issues.

## 4. Workload Classification

**Operational and Customer-facing Workloads (P1–P4):** These involve frequent transactions and information retrieval, such as movie searches, seat selection, booking creation, payment-status tracking, and customer booking lookup. They require timely responses and strong data consistency.

**Reporting and Analytical Workloads (P5–P8):** These involve aggregating and analyzing booking, show, customer, and movie data to evaluate theatre operations, unused offers, box-office collections, and overall business performance. They require efficient processing of larger datasets.

## 5. Assumptions and Project Scope

Each venue belongs to one city and can contain multiple screens. Each screen contains multiple seats, and each show is associated with one movie and one screen. A booking belongs to one customer and one show and may contain multiple seats. A seat can be allocated only once for a particular show. An offer is optional for a booking, and customers can submit movie reviews.

The project focuses on designing a normalized PostgreSQL relational database, defining entities and relationships, implementing primary keys, foreign keys and integrity constraints, loading the supplied CSV datasets, validating data, and evaluating and optimizing the specified SQL workloads. It focuses on database design and performance rather than developing a complete customer-facing application.