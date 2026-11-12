
import csv
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

DATA = Path("seed_data/seed_data")

def load(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def duplicates(rows, key):
    values = [key(row) for row in rows]
    counts = Counter(values)
    return [(value, count) for value, count in counts.items() if count > 1]

tables = {
    name: load(name)
    for name in [
        "cities", "venues", "screens", "seats", "movies",
        "shows", "customers", "offers", "bookings",
        "booking_seats", "movie_reviews"
    ]
}

print("=== UNIQUENESS CHECKS ===")

checks = [
    ("customers.email", "customers", lambda r: r["email"]),
    ("customers.phone", "customers", lambda r: r["phone"]),
    ("bookings.booking_code", "bookings", lambda r: r["booking_code"]),
    ("seats position", "seats",
     lambda r: (r["screen_id"], r["row_label"], r["seat_number"])),
    ("booking_seats booking-seat", "booking_seats",
     lambda r: (r["booking_id"], r["seat_id"])),
    ("booking_seats show-seat", "booking_seats",
     lambda r: (r["show_id"], r["seat_id"])),
    ("bookings booking-show", "bookings",
     lambda r: (r["booking_id"], r["show_id"])),
]

for label, table, key in checks:
    dup = duplicates(tables[table], key)
    print(f"{label}: {len(dup)} duplicate keys")

print("\n=== BOOKING AMOUNT CHECKS ===")

bad_total = []
bad_discount = []

for r in tables["bookings"]:
    ticket = Decimal(r["ticket_amount"])
    fee = Decimal(r["convenience_fee"])
    fnb = Decimal(r["fnb_amount"])
    discount = Decimal(r["discount"])
    total = Decimal(r["total_amount"])

    if total != ticket + fee + fnb - discount:
        bad_total.append(r["booking_id"])

    if discount > ticket + fee + fnb:
        bad_discount.append(r["booking_id"])

print("Incorrect total calculations:", len(bad_total))
print("Discount exceeds total components:", len(bad_discount))

print("\n=== SEAT-SCREEN CONSISTENCY ===")

show_screen = {
    r["show_id"]: r["screen_id"] for r in tables["shows"]
}
seat_screen = {
    r["seat_id"]: r["screen_id"] for r in tables["seats"]
}

bad_allocations = []

for r in tables["booking_seats"]:
    expected = show_screen.get(r["show_id"])
    actual = seat_screen.get(r["seat_id"])

    if expected is None or actual is None or expected != actual:
        bad_allocations.append(r)

print("Invalid seat-screen allocations:", len(bad_allocations))

print("\n=== SMALLINT RANGE CHECKS ===")

smallint_columns = {
    "cities": ["city_id"],
    "venues": ["venue_id", "city_id"],
    "screens": ["screen_id", "venue_id", "total_seats"],
    "seats": ["screen_id", "seat_number"],
    "movies": ["movie_id", "duration_min"],
    "shows": ["movie_id", "screen_id"],
    "customers": ["city_id"],
    "bookings": ["num_tickets"],
    "movie_reviews": ["movie_id", "rating"],
}

bad_ranges = []

for table, columns in smallint_columns.items():
    for r in tables[table]:
        for col in columns:
            value = int(r[col])
            if not -32768 <= value <= 32767:
                bad_ranges.append((table, col, value))

print("Values outside SMALLINT range:", len(bad_ranges))

print("\n=== SUMMARY ===")
print("Audit completed.")
