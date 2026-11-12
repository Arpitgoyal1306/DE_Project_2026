
import csv
from datetime import date
from decimal import Decimal
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

errors = []

def check_not_null(table, columns, nullable=()):
    for row_number, row in enumerate(tables[table], start=2):
        for column in columns:
            if column not in nullable and row[column] == "":
                errors.append((table, row_number, column, "Empty NOT NULL value"))

def check_positive(table, column, strict=True):
    for row_number, row in enumerate(tables[table], start=2):
        value = Decimal(row[column])
        invalid = value <= 0 if strict else value < 0
        if invalid:
            errors.append((table, row_number, column, f"Invalid value: {value}"))

print("=== NOT NULL CHECKS ===")

not_null_columns = {
    "cities": ["city_id", "city_name", "state"],
    "venues": ["venue_id", "venue_name", "city_id", "chain", "address"],
    "screens": ["screen_id", "venue_id", "screen_name", "screen_type", "total_seats"],
    "seats": ["seat_id", "screen_id", "row_label", "seat_number", "seat_class"],
    "movies": ["movie_id", "title", "language", "certificate", "duration_min", "release_date"],
    "shows": ["show_id", "movie_id", "screen_id", "starts_at", "ends_at", "format", "base_price"],
    "customers": ["customer_id", "full_name", "email", "phone", "city_id", "created_at"],
    "offers": ["offer_code", "description", "discount_pct", "max_discount", "valid_from", "valid_to"],
    "bookings": [
        "booking_id", "booking_code", "customer_id", "show_id", "booked_at",
        "num_tickets", "ticket_amount", "convenience_fee", "fnb_amount",
        "discount", "total_amount", "payment_method", "status"
    ],
    "booking_seats": ["booking_id", "show_id", "seat_id", "price"],
    "movie_reviews": ["review_id", "movie_id", "customer_id", "rating", "created_at"]
}

for table, columns in not_null_columns.items():
    nullable = ("offer_code",) if table == "bookings" else (
        ("review_text",) if table == "movie_reviews" else ()
    )
    check_not_null(table, columns, nullable)

print("Checked all required columns.")

print("\n=== NUMERIC CHECK CONSTRAINTS ===")

for table, column in [
    ("screens", "total_seats"),
    ("seats", "seat_number"),
    ("movies", "duration_min"),
    ("bookings", "num_tickets")
]:
    check_positive(table, column)

for table, column in [
    ("shows", "base_price"),
    ("offers", "max_discount"),
    ("bookings", "ticket_amount"),
    ("bookings", "convenience_fee"),
    ("bookings", "fnb_amount"),
    ("bookings", "discount"),
    ("booking_seats", "price")
]:
    check_positive(table, column, strict=False)

for row_number, row in enumerate(tables["offers"], start=2):
    pct = Decimal(row["discount_pct"])
    if not Decimal("0") <= pct <= Decimal("100"):
        errors.append(("offers", row_number, "discount_pct", str(pct)))

    if date.fromisoformat(row["valid_to"]) < date.fromisoformat(row["valid_from"]):
        errors.append(("offers", row_number, "valid_to", "Before valid_from"))

for row_number, row in enumerate(tables["movie_reviews"], start=2):
    rating = int(row["rating"])
    if not 1 <= rating <= 10:
        errors.append(("movie_reviews", row_number, "rating", str(rating)))

print("\n=== RESULTS ===")
print("Total violations:", len(errors))

for error in errors[:30]:
    print(error)

if errors:
    print("\nInvestigate these records before loading.")
else:
    print("\nAll tested NOT NULL and CHECK constraints passed.")
