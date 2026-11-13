
import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

DATA = Path("seed_data/seed_data")

def load(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

tables = {
    name: load(name)
    for name in [
        "cities", "venues", "screens", "seats", "movies",
        "shows", "customers", "offers", "bookings",
        "booking_seats", "movie_reviews"
    ]
}

def ids(table, column):
    return {r[column] for r in tables[table]}

def check_fk(label, rows, column, parent_ids, nullable=False):
    invalid = [
        r[column] for r in rows
        if not (nullable and not r[column])
        and r[column] not in parent_ids
    ]
    print(f"{label}: {len(invalid)} invalid references")

print("=== FOREIGN KEY CHECKS ===")

check_fk("venues.city_id", tables["venues"], "city_id",
         ids("cities", "city_id"))

check_fk("screens.venue_id", tables["screens"], "venue_id",
         ids("venues", "venue_id"))

check_fk("seats.screen_id", tables["seats"], "screen_id",
         ids("screens", "screen_id"))

check_fk("shows.movie_id", tables["shows"], "movie_id",
         ids("movies", "movie_id"))

check_fk("shows.screen_id", tables["shows"], "screen_id",
         ids("screens", "screen_id"))

check_fk("customers.city_id", tables["customers"], "city_id",
         ids("cities", "city_id"))

check_fk("bookings.customer_id", tables["bookings"], "customer_id",
         ids("customers", "customer_id"))

check_fk("bookings.show_id", tables["bookings"], "show_id",
         ids("shows", "show_id"))

check_fk("bookings.offer_code", tables["bookings"], "offer_code",
         ids("offers", "offer_code"), nullable=True)

check_fk("movie_reviews.movie_id", tables["movie_reviews"], "movie_id",
         ids("movies", "movie_id"))

check_fk("movie_reviews.customer_id", tables["movie_reviews"],
         "customer_id", ids("customers", "customer_id"))

check_fk("booking_seats.seat_id", tables["booking_seats"],
         "seat_id", ids("seats", "seat_id"))

check_fk("booking_seats.show_id", tables["booking_seats"],
         "show_id", ids("shows", "show_id"))

print("\n=== COMPOSITE FOREIGN KEYS ===")

booking_show = {
    (r["booking_id"], r["show_id"]) for r in tables["bookings"]
}

invalid_composite = [
    r for r in tables["booking_seats"]
    if (r["booking_id"], r["show_id"]) not in booking_show
]

print("booking_seats(booking_id, show_id):",
      len(invalid_composite), "invalid references")

print("\n=== VARCHAR LENGTH CHECKS ===")

limits = {
    "cities": {"city_name": 30, "state": 30},
    "venues": {"venue_name": 60, "chain": 30, "address": 100},
    "screens": {"screen_name": 20, "screen_type": 20},
    "seats": {"row_label": 5, "seat_class": 20},
    "movies": {"title": 100, "language": 30, "certificate": 10},
    "shows": {"format": 10},
    "customers": {"full_name": 100, "email": 100, "phone": 15},
    "offers": {"offer_code": 20, "description": 100},
    "bookings": {
        "booking_code": 20, "offer_code": 20,
        "payment_method": 20, "status": 20
    },
}

length_errors = []

for table, columns in limits.items():
    for row in tables[table]:
        for column, limit in columns.items():
            if len(row[column]) > limit:
                length_errors.append(
                    (table, column, len(row[column]), limit)
                )

print("Values exceeding VARCHAR limits:", len(length_errors))

for error in length_errors[:10]:
    print(error)

print("\n=== DATE AND TIMESTAMP CHECKS ===")

date_columns = {
    "movies": ["release_date"],
    "offers": ["valid_from", "valid_to"],
}

timestamp_columns = {
    "shows": ["starts_at", "ends_at"],
    "customers": ["created_at"],
    "bookings": ["booked_at"],
    "movie_reviews": ["created_at"],
}

date_errors = []
timestamp_errors = []

for table, columns in date_columns.items():
    for row in tables[table]:
        for column in columns:
            try:
                date.fromisoformat(row[column])
            except ValueError:
                date_errors.append((table, column, row[column]))

for table, columns in timestamp_columns.items():
    for row in tables[table]:
        for column in columns:
            try:
                parsed = datetime.fromisoformat(
                    row[column].replace("Z", "+00:00")
                )
                if parsed.tzinfo is None:
                    timestamp_errors.append(
                        (table, column, "Missing timezone")
                    )
            except ValueError:
                timestamp_errors.append(
                    (table, column, row[column])
                )

print("Invalid dates:", len(date_errors))
print("Invalid or timezone-free timestamps:", len(timestamp_errors))

print("\n=== SHOW TIME VALIDITY AND OVERLAPS ===")

shows_by_screen = defaultdict(list)
invalid_intervals = []

for row in tables["shows"]:
    start = datetime.fromisoformat(
        row["starts_at"].replace("Z", "+00:00")
    )
    end = datetime.fromisoformat(
        row["ends_at"].replace("Z", "+00:00")
    )

    if end <= start:
        invalid_intervals.append(row["show_id"])

    shows_by_screen[row["screen_id"]].append(
        (start, end, row["show_id"])
    )

overlaps = []

for screen_id, shows in shows_by_screen.items():
    shows.sort(key=lambda x: x[0])

    for previous, current in zip(shows, shows[1:]):
        if current[0] < previous[1]:
            overlaps.append(
                (screen_id, previous[2], current[2])
            )

print("Invalid show intervals:", len(invalid_intervals))
print("Overlapping show pairs:", len(overlaps))

for overlap in overlaps[:10]:
    print(overlap)

print("\n=== AUDIT COMPLETE ===")
