import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "seed_data"
REPORT_PATH = BASE_DIR / "validation_report.json"

NULLABLE_COLUMNS = {
    "bookings": {"offer_code"},
    "movie_reviews": {"review_text"},
}

EXPECTED_HEADERS = {
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
        "offer_code", "discount", "total_amount", "payment_method", "status"
    ],
    "booking_seats": ["booking_id", "show_id", "seat_id", "price"],
    "movie_reviews": ["review_id", "movie_id", "customer_id", "rating", "review_text", "created_at"],
}

EXPECTED_ROW_COUNTS = {
    "cities": 10, "venues": 140, "screens": 490, "seats": 94056,
    "movies": 300, "shows": 160034, "customers": 40000, "offers": 25,
    "bookings": 150094, "booking_seats": 300389, "movie_reviews": 32510,
}

# Primary keys and proposed alternate candidate keys.
UNIQUE_CHECKS = [
    ("cities", ("city_id",), "PRIMARY_KEY"),
    ("venues", ("venue_id",), "PRIMARY_KEY"),
    ("screens", ("screen_id",), "PRIMARY_KEY"),
    ("seats", ("seat_id",), "PRIMARY_KEY"),
    ("movies", ("movie_id",), "PRIMARY_KEY"),
    ("shows", ("show_id",), "PRIMARY_KEY"),
    ("customers", ("customer_id",), "PRIMARY_KEY"),
    ("offers", ("offer_code",), "PRIMARY_KEY"),
    ("bookings", ("booking_id",), "PRIMARY_KEY"),
    ("booking_seats", ("show_id", "seat_id"), "PRIMARY_KEY"),
    ("movie_reviews", ("review_id",), "PRIMARY_KEY"),
    ("seats", ("screen_id", "row_label", "seat_number"), "UNIQUE"),
    ("customers", ("email",), "UNIQUE"),
    ("customers", ("phone",), "UNIQUE"),
    ("bookings", ("booking_code",), "UNIQUE"),
    ("booking_seats", ("booking_id", "seat_id"), "UNIQUE"),
    ("bookings", ("booking_id", "show_id"), "UNIQUE"),
]

# Individual foreign keys. booking_seats.booking_id is deliberately
# represented by the composite FK below, not duplicated as a single FK.
FOREIGN_KEYS = [
    ("venues", "city_id", "cities", "city_id"),
    ("screens", "venue_id", "venues", "venue_id"),
    ("seats", "screen_id", "screens", "screen_id"),
    ("shows", "movie_id", "movies", "movie_id"),
    ("shows", "screen_id", "screens", "screen_id"),
    ("customers", "city_id", "cities", "city_id"),
    ("bookings", "customer_id", "customers", "customer_id"),
    ("bookings", "show_id", "shows", "show_id"),
    ("bookings", "offer_code", "offers", "offer_code"),
    ("booking_seats", "show_id", "shows", "show_id"),
    ("booking_seats", "seat_id", "seats", "seat_id"),
    ("movie_reviews", "movie_id", "movies", "movie_id"),
    ("movie_reviews", "customer_id", "customers", "customer_id"),
]

COMPOSITE_FOREIGN_KEYS = [
    {
        "child_table": "booking_seats",
        "child_columns": ("booking_id", "show_id"),
        "parent_table": "bookings",
        "parent_columns": ("booking_id", "show_id"),
    }
]

# Proposed bounded VARCHAR lengths. These are design limits with headroom
# above the observed maxima, not maxima inferred as universal business limits.
VARCHAR_LIMITS = {
    ("cities", "city_name"): 30,
    ("cities", "state"): 30,
    ("venues", "venue_name"): 60,
    ("venues", "chain"): 30,
    ("venues", "address"): 100,
    ("screens", "screen_name"): 20,
    ("screens", "screen_type"): 20,
    ("seats", "row_label"): 5,
    ("seats", "seat_class"): 20,
    ("movies", "title"): 100,
    ("movies", "language"): 30,
    ("movies", "certificate"): 10,
    ("shows", "format"): 10,
    ("customers", "full_name"): 100,
    ("customers", "email"): 100,
    ("customers", "phone"): 15,
    ("offers", "offer_code"): 20,
    ("offers", "description"): 100,
    ("bookings", "booking_code"): 20,
    ("bookings", "payment_method"): 20,
    ("bookings", "status"): 20,
}

# Numeric parsing and PostgreSQL type/range validation.
# kind: integer or decimal; min/max are type limits or explicit domain rules.
NUMERIC_COLUMNS = {
    ("cities", "city_id"): ("integer", 1, 32767, 0),
    ("venues", "venue_id"): ("integer", 1, 32767, 0),
    ("venues", "city_id"): ("integer", 1, 32767, 0),
    ("screens", "screen_id"): ("integer", 1, 32767, 0),
    ("screens", "venue_id"): ("integer", 1, 32767, 0),
    ("screens", "total_seats"): ("integer", 1, 32767, 0),
    ("seats", "seat_id"): ("integer", 1, 2147483647, 0),
    ("seats", "screen_id"): ("integer", 1, 32767, 0),
    ("seats", "seat_number"): ("integer", 1, 32767, 0),
    ("movies", "movie_id"): ("integer", 1, 32767, 0),
    ("movies", "duration_min"): ("integer", 1, 32767, 0),
    ("shows", "show_id"): ("integer", 1, 2147483647, 0),
    ("shows", "movie_id"): ("integer", 1, 32767, 0),
    ("shows", "screen_id"): ("integer", 1, 32767, 0),
    ("shows", "base_price"): ("decimal", 0, 99999999.99, 2),
    ("customers", "customer_id"): ("integer", 1, 2147483647, 0),
    ("customers", "city_id"): ("integer", 1, 32767, 0),
    ("offers", "discount_pct"): ("decimal", 0, 100, 2),
    ("offers", "max_discount"): ("decimal", 0, 99999999.99, 2),
    ("bookings", "booking_id"): ("integer", 1, 2147483647, 0),
    ("bookings", "customer_id"): ("integer", 1, 2147483647, 0),
    ("bookings", "show_id"): ("integer", 1, 2147483647, 0),
    ("bookings", "num_tickets"): ("integer", 1, 32767, 0),
    ("bookings", "ticket_amount"): ("decimal", 0, 99999999.99, 2),
    ("bookings", "convenience_fee"): ("decimal", 0, 99999999.99, 2),
    ("bookings", "fnb_amount"): ("decimal", 0, 99999999.99, 2),
    ("bookings", "discount"): ("decimal", 0, 99999999.99, 2),
    ("bookings", "total_amount"): ("decimal", 0, 99999999.99, 2),
    ("booking_seats", "booking_id"): ("integer", 1, 2147483647, 0),
    ("booking_seats", "show_id"): ("integer", 1, 2147483647, 0),
    ("booking_seats", "seat_id"): ("integer", 1, 2147483647, 0),
    ("booking_seats", "price"): ("decimal", 0, 99999999.99, 2),
    ("movie_reviews", "review_id"): ("integer", 1, 2147483647, 0),
    ("movie_reviews", "movie_id"): ("integer", 1, 32767, 0),
    ("movie_reviews", "customer_id"): ("integer", 1, 2147483647, 0),
    ("movie_reviews", "rating"): ("integer", 1, 10, 0),
}

DATE_COLUMNS = {
    ("movies", "release_date"),
    ("offers", "valid_from"),
    ("offers", "valid_to"),
}
TIMESTAMP_COLUMNS = {
    ("shows", "starts_at"), ("shows", "ends_at"),
    ("bookings", "booked_at"), ("customers", "created_at"),
    ("movie_reviews", "created_at"),
}
MONEY_COLUMNS = {
    ("shows", "base_price"), ("offers", "max_discount"),
    ("bookings", "ticket_amount"), ("bookings", "convenience_fee"),
    ("bookings", "fnb_amount"), ("bookings", "discount"),
    ("bookings", "total_amount"), ("booking_seats", "price"),
}

ISSUES = []
WARNINGS = []
ROW_COUNTS = {}
CHECK_RESULTS = Counter()
OBSERVED = {"utc_offsets": {}, "max_string_lengths": {}, "numeric_ranges": {}}


def record_issue(table, row, rule, values, message, severity="ERROR"):
    item = {
        "table": table,
        "row_identifier": row,
        "rule": rule,
        "offending_values": values,
        "message": message,
    }
    if severity == "WARNING":
        WARNINGS.append(item)
    else:
        ISSUES.append(item)


def row_id(table, row):
    keys = {
        "cities": ["city_id"], "venues": ["venue_id"],
        "screens": ["screen_id"], "seats": ["seat_id"],
        "movies": ["movie_id"], "shows": ["show_id"],
        "customers": ["customer_id"], "offers": ["offer_code"],
        "bookings": ["booking_id"],
        "booking_seats": ["booking_id", "show_id", "seat_id"],
        "movie_reviews": ["review_id"],
    }
    return {k: row.get(k) for k in keys.get(table, [])}


def load_all_data():
    data = {}
    print("\n========== CSV STRUCTURE VALIDATION ==========")
    for table, headers in EXPECTED_HEADERS.items():
        path = DATA_DIR / f"{table}.csv"
        if not path.exists():
            record_issue(table, None, "FILE_MISSING", {}, f"Missing {path.name}")
            continue
        try:
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                actual = reader.fieldnames or []
                if actual != headers:
                    record_issue(table, None, "HEADER_MISMATCH",
                                 {"expected": headers, "actual": actual},
                                 "CSV headers or header order differ from the expected schema.")
                    continue
                rows = []
                for line, raw in enumerate(reader, start=2):
                    if None in raw:
                        record_issue(table, {"csv_row": line}, "EXTRA_FIELDS",
                                     {"extra": raw[None]}, "Row has extra fields.")
                        continue
                    missing = [h for h in headers if raw.get(h) is None]
                    if missing:
                        record_issue(table, {"csv_row": line}, "MISSING_FIELDS",
                                     {"columns": missing}, "Row has missing fields.")
                        continue
                    row = {h: raw[h].strip() for h in headers}
                    row["_csv_row"] = line
                    rows.append(row)
                data[table] = rows
                ROW_COUNTS[table] = len(rows)
                print(f"{table}.csv: {len(rows):,} rows")
        except (OSError, csv.Error, UnicodeError) as e:
            record_issue(table, None, "CSV_READ_ERROR", {}, str(e))
    print(f"Total loaded rows: {sum(ROW_COUNTS.values()):,}")
    return data


def validate_row_counts():
    print("\n========== ROW COUNT VALIDATION ==========")
    results = {}
    for table, expected in EXPECTED_ROW_COUNTS.items():
        actual = ROW_COUNTS.get(table)
        passed = actual == expected
        results[table] = {"expected": expected, "actual": actual,
                          "status": "PASSED" if passed else "FAILED"}
        CHECK_RESULTS["row_count_passed" if passed else "row_count_failed"] += 1
        print(f"{table}: expected {expected:,}, actual "
              f"{actual if actual is not None else 'MISSING'} - {'PASS' if passed else 'FAIL'}")
        if not passed:
            record_issue(table, None, "ROW_COUNT_MISMATCH",
                         {"expected": expected, "actual": actual},
                         "CSV row count differs from expected count.")
    return results


def validate_required(data):
    missing = 0
    for table, rows in data.items():
        nullable = NULLABLE_COLUMNS.get(table, set())
        for row in rows:
            for col in EXPECTED_HEADERS[table]:
                if col not in nullable and row[col] == "":
                    missing += 1
                    record_issue(table, row_id(table, row), "REQUIRED_VALUE_MISSING",
                                 {col: ""}, f"{col} is required but blank.")
    CHECK_RESULTS["required_value_errors"] = missing
    print(f"\nRequired-value errors: {missing}")


def validate_numeric_and_lengths(data):
    numeric_errors = 0
    length_errors = 0
    for table, rows in data.items():
        for row in rows:
            for col in EXPECTED_HEADERS[table]:
                value = row[col]
                if value == "":
                    continue
                limit = VARCHAR_LIMITS.get((table, col))
                if limit is not None:
                    OBSERVED["max_string_lengths"][f"{table}.{col}"] = max(
                        OBSERVED["max_string_lengths"].get(f"{table}.{col}", 0),
                        len(value)
                    )
                    if len(value) > limit:
                        length_errors += 1
                        record_issue(table, row_id(table, row), "VARCHAR_LENGTH_EXCEEDED",
                                     {col: value, "length": len(value), "limit": limit},
                                     f"{col} exceeds proposed VARCHAR({limit}) length.")
            for (t, col), (kind, minimum, maximum, scale) in NUMERIC_COLUMNS.items():
                if t != table or row[col] == "":
                    continue
                try:
                    number = Decimal(row[col])
                    if not number.is_finite():
                        raise InvalidOperation
                    if kind == "integer" and number != number.to_integral_value():
                        raise ValueError("Expected an integer.")
                    actual_scale = max(0, -number.as_tuple().exponent)
                    if number < Decimal(str(minimum)) or number > Decimal(str(maximum)) or actual_scale > scale:
                        raise ValueError(
                            f"Outside configured {kind} range/precision: "
                            f"{minimum}..{maximum}, scale <= {scale}."
                        )
                    key = f"{table}.{col}"
                    current = OBSERVED["numeric_ranges"].get(key)
                    if current is None:
                        OBSERVED["numeric_ranges"][key] = {
                            "min": str(number), "max": str(number),
                            "max_decimal_places": actual_scale
                        }
                    else:
                        current["min"] = str(min(Decimal(current["min"]), number))
                        current["max"] = str(max(Decimal(current["max"]), number))
                        current["max_decimal_places"] = max(current["max_decimal_places"], actual_scale)
                except (InvalidOperation, ValueError) as e:
                    numeric_errors += 1
                    record_issue(table, row_id(table, row), "INVALID_NUMERIC_VALUE",
                                 {col: row[col]}, str(e))
    CHECK_RESULTS["numeric_errors"] = numeric_errors
    CHECK_RESULTS["string_length_errors"] = length_errors
    print(f"Numeric validation errors: {numeric_errors}")
    print(f"String length errors: {length_errors}")


def validate_dates_and_timestamps(data):
    date_errors = 0
    timestamp_errors = 0
    for table, rows in data.items():
        for row in rows:
            for t, col in DATE_COLUMNS:
                if t != table or not row[col]:
                    continue
                try:
                    date.fromisoformat(row[col])
                except ValueError:
                    date_errors += 1
                    record_issue(table, row_id(table, row), "INVALID_DATE",
                                 {col: row[col]}, "Expected a valid ISO date (YYYY-MM-DD).")
            for t, col in TIMESTAMP_COLUMNS:
                if t != table or not row[col]:
                    continue
                try:
                    parsed = datetime.fromisoformat(row[col])
                    if parsed.tzinfo is None or parsed.utcoffset() is None:
                        raise ValueError("Timestamp must include a timezone offset.")
                    offset = str(parsed.utcoffset())
                    OBSERVED["utc_offsets"].setdefault(f"{table}.{col}", set()).add(offset)
                except ValueError as e:
                    timestamp_errors += 1
                    record_issue(table, row_id(table, row), "INVALID_OR_NAIVE_TIMESTAMP",
                                 {col: row[col]}, str(e))
    for key in list(OBSERVED["utc_offsets"]):
        OBSERVED["utc_offsets"][key] = sorted(OBSERVED["utc_offsets"][key])
    CHECK_RESULTS["date_errors"] = date_errors
    CHECK_RESULTS["timestamp_errors"] = timestamp_errors
    print(f"\nDate errors: {date_errors}")
    print(f"Timestamp errors (including missing timezone): {timestamp_errors}")


def validate_foreign_keys(data):
    errors = 0
    print("\n========== FOREIGN KEY VALIDATION ==========")
    for child, child_col, parent, parent_col in FOREIGN_KEYS:
        if child not in data or parent not in data:
            continue
        parent_values = {r[parent_col] for r in data[parent] if r[parent_col]}
        count = 0
        for row in data[child]:
            value = row[child_col]
            if value == "" and child_col in NULLABLE_COLUMNS.get(child, set()):
                continue
            if value not in parent_values:
                count += 1
                record_issue(child, row_id(child, row), "INVALID_FOREIGN_KEY",
                             {child_col: value, "parent": f"{parent}.{parent_col}"},
                             "Referenced parent record does not exist.")
        errors += count
        print(f"{child}.{child_col} -> {parent}.{parent_col}: {count} invalid")
    # Composite FK: booking_seats(booking_id, show_id) -> bookings(booking_id, show_id)
    if "bookings" in data and "booking_seats" in data:
        parent_pairs = {(r["booking_id"], r["show_id"]) for r in data["bookings"]}
        count = 0
        for row in data["booking_seats"]:
            pair = (row["booking_id"], row["show_id"])
            if pair not in parent_pairs:
                count += 1
                record_issue("booking_seats", row_id("booking_seats", row),
                             "INVALID_COMPOSITE_FOREIGN_KEY",
                             {"booking_id": pair[0], "show_id": pair[1]},
                             "Booking/show pair does not exist in bookings.")
        errors += count
        print(f"booking_seats(booking_id, show_id) -> bookings(booking_id, show_id): {count} invalid")
    CHECK_RESULTS["foreign_key_errors"] = errors
    print(f"Total FK errors: {errors}")


def validate_uniqueness(data):
    duplicates = 0
    print("\n========== PRIMARY KEY / UNIQUE VALIDATION ==========")
    for table, columns, rule in UNIQUE_CHECKS:
        if table not in data:
            continue
        seen = set()
        count = 0
        for row in data[table]:
            key = tuple(row[c] for c in columns)
            if any(v == "" for v in key):
                continue
            if key in seen:
                count += 1
                record_issue(table, row_id(table, row), f"DUPLICATE_{rule}",
                             {"columns": columns, "values": key},
                             f"Duplicate key for {columns}.")
            else:
                seen.add(key)
        duplicates += count
        print(f"{table}{columns}: {count} duplicates")
    CHECK_RESULTS["duplicate_key_errors"] = duplicates
    # Proposed rule awaiting owner approval: one review per customer/movie.
    if "movie_reviews" in data:
        seen = set()
        review_dups = 0
        for row in data["movie_reviews"]:
            key = (row["customer_id"], row["movie_id"])
            if key in seen:
                review_dups += 1
                record_issue("movie_reviews", row_id("movie_reviews", row),
                             "PROPOSED_ONE_REVIEW_PER_CUSTOMER_MOVIE",
                             {"customer_id": key[0], "movie_id": key[1]},
                             "Duplicate customer/movie review pair; UNIQUE constraint is proposed pending owner approval.",
                             severity="WARNING")
            seen.add(key)
        CHECK_RESULTS["proposed_review_duplicate_warnings"] = review_dups
        print(f"Proposed review uniqueness warnings: {review_dups}")


def validate_cross_table(data):
    errors = 0
    screens = {r["screen_id"]: r for r in data.get("screens", [])}
    shows = {r["show_id"]: r for r in data.get("shows", [])}
    seats = {r["seat_id"]: r for r in data.get("seats", [])}
    bookings = {r["booking_id"]: r for r in data.get("bookings", [])}

    actual_capacity = Counter(r["screen_id"] for r in data.get("seats", []))
    capacity_errors = 0
    for sid, screen in screens.items():
        actual = actual_capacity[sid]
        expected = int(screen["total_seats"])
        if actual != expected:
            capacity_errors += 1
            record_issue("screens", {"screen_id": sid}, "SCREEN_CAPACITY_MISMATCH",
                         {"declared": expected, "actual_seats": actual},
                         "Declared screen capacity differs from seat records.")

    allocated = Counter(r["booking_id"] for r in data.get("booking_seats", []))
    allocation_errors = 0
    for bid, booking in bookings.items():
        expected = int(booking["num_tickets"])
        actual = allocated[bid]
        status = booking["status"]
        valid = (
            status in {"CONFIRMED", "PENDING"} and actual == expected
        ) or (
            status in {"CANCELLED", "PAYMENT_FAILED"} and actual == 0
        )
        if not valid:
            allocation_errors += 1
            record_issue("bookings", {"booking_id": bid}, "BOOKING_SEAT_ALLOCATION_MISMATCH",
                         {"status": status, "num_tickets": expected, "allocated_seats": actual},
                         "Seat allocation does not match the status-aware booking rule.")

    seat_screen_errors = 0
    for row in data.get("booking_seats", []):
        show = shows.get(row["show_id"])
        seat = seats.get(row["seat_id"])
        if show and seat and show["screen_id"] != seat["screen_id"]:
            seat_screen_errors += 1
            record_issue("booking_seats", row_id("booking_seats", row),
                         "SEAT_SCREEN_MISMATCH",
                         {"show_screen_id": show["screen_id"], "seat_screen_id": seat["screen_id"]},
                         "Allocated seat does not belong to the show's screen.")

    CHECK_RESULTS["screen_capacity_errors"] = capacity_errors
    CHECK_RESULTS["booking_allocation_errors"] = allocation_errors
    CHECK_RESULTS["seat_screen_errors"] = seat_screen_errors
    print(f"\nScreen capacity mismatches: {capacity_errors}")
    print(f"Status-aware booking allocation mismatches: {allocation_errors}")
    print(f"Seat-screen mismatches: {seat_screen_errors}")


def validate_business_rules(data):
    # --------------------------------------------------------
    # 1. Validate offer date ranges: valid_to >= valid_from
    # --------------------------------------------------------
    offer_date_range_errors = 0
    offer_map = {}

    for offer in data.get("offers", []):
        code = offer["offer_code"]

        try:
            start = date.fromisoformat(offer["valid_from"])
            end = date.fromisoformat(offer["valid_to"])

            offer_map[code] = {
                "row": offer,
                "start": start,
                "end": end
            }

            if end < start:
                offer_date_range_errors += 1
                record_issue(
                    "offers",
                    row_id("offers", offer),
                    "OFFER_DATE_RANGE_INVALID",
                    {
                        "valid_from": start.isoformat(),
                        "valid_to": end.isoformat()
                    },
                    "Offer valid_to must be greater than or equal to valid_from."
                )

        except ValueError:
            # Invalid dates are already reported by date validation.
            continue

    # --------------------------------------------------------
    # 2. Validate offer validity at booking time
    # --------------------------------------------------------
    invalid_offer_dates = 0

    for row in data.get("bookings", []):
        code = row["offer_code"]

        if not code or code not in offer_map:
            continue

        offer = offer_map[code]

        # Skip offers with an invalid date range.
        if offer["end"] < offer["start"]:
            continue

        try:
            booked = datetime.fromisoformat(row["booked_at"]).date()

            if not offer["start"] <= booked <= offer["end"]:
                invalid_offer_dates += 1

                record_issue(
                    "bookings",
                    row_id("bookings", row),
                    "OFFER_OUTSIDE_VALIDITY",
                    {
                        "offer_code": code,
                        "booked_date": booked.isoformat(),
                        "valid_from": offer["start"].isoformat(),
                        "valid_to": offer["end"].isoformat()
                    },
                    "Booking date falls outside the offer validity period."
                )

        except ValueError:
            # Invalid timestamps are already reported separately.
            continue

    # --------------------------------------------------------
    # 3. Validate monetary values are non-negative
    # --------------------------------------------------------
    money_errors = 0

    for table, col in MONEY_COLUMNS:
        for row in data.get(table, []):
            if not row[col]:
                continue

            try:
                if Decimal(row[col]) < 0:
                    money_errors += 1

                    record_issue(
                        table,
                        row_id(table, row),
                        "NEGATIVE_MONEY",
                        {col: row[col]},
                        "Monetary value must be non-negative."
                    )

            except InvalidOperation:
                # Numeric parser reports this separately.
                pass

    # --------------------------------------------------------
    # 4. Validate booking amount arithmetic
    # total = ticket + fee + fnb - discount
    # --------------------------------------------------------
    formula_errors = 0

    for row in data.get("bookings", []):
        try:
            ticket = Decimal(row["ticket_amount"])
            fee = Decimal(row["convenience_fee"])
            fnb = Decimal(row["fnb_amount"])
            discount = Decimal(row["discount"])
            total = Decimal(row["total_amount"])

            before_discount = ticket + fee + fnb
            expected_total = before_discount - discount

            if discount > before_discount or total != expected_total:
                formula_errors += 1

                record_issue(
                    "bookings",
                    row_id("bookings", row),
                    "BOOKING_AMOUNT_INCONSISTENT",
                    {
                        "ticket_amount": str(ticket),
                        "convenience_fee": str(fee),
                        "fnb_amount": str(fnb),
                        "discount": str(discount),
                        "total_amount": str(total),
                        "expected_total": str(expected_total)
                    },
                    "Discount or total amount violates the verified booking arithmetic."
                )

        except InvalidOperation:
            continue

    # --------------------------------------------------------
    # 5. Store results in validation report
    # --------------------------------------------------------
    CHECK_RESULTS["offer_date_range_errors"] = offer_date_range_errors
    CHECK_RESULTS["offer_validity_errors"] = invalid_offer_dates
    CHECK_RESULTS["negative_money_errors"] = money_errors
    CHECK_RESULTS["booking_amount_formula_errors"] = formula_errors

    print(f"\nOffer date range errors: {offer_date_range_errors}")
    print(f"Offer validity errors: {invalid_offer_dates}")
    print(f"Negative monetary values: {money_errors}")
    print(f"Booking amount formula errors: {formula_errors}")


def validate_show_times_and_overlaps(data):
    valid = []
    errors = 0
    offsets = set()
    for row in data.get("shows", []):
        try:
            start = datetime.fromisoformat(row["starts_at"])
            end = datetime.fromisoformat(row["ends_at"])
            if start.tzinfo is None or start.utcoffset() is None or end.tzinfo is None or end.utcoffset() is None:
                raise ValueError("Show timestamps must be timezone-aware.")
            if end <= start:
                raise ValueError("Show end must be later than show start.")
            offsets.add(str(start.utcoffset()))
            offsets.add(str(end.utcoffset()))
            valid.append((row["show_id"], row["screen_id"], start, end))
        except ValueError as e:
            errors += 1
            record_issue("shows", row_id("shows", row), "INVALID_SHOW_INTERVAL",
                         {"starts_at": row["starts_at"], "ends_at": row["ends_at"]}, str(e))

    by_screen = defaultdict(list)
    for item in valid:
        by_screen[item[1]].append(item)
    overlaps = 0
    for screen_id, items in by_screen.items():
        items.sort(key=lambda x: x[2])
        active = []
        for current in items:
            active = [p for p in active if p[3] > current[2]]
            for previous in active:
                overlaps += 1
                record_issue("shows", {"show_id": current[0]}, "OVERLAPPING_SHOWS",
                             {"screen_id": screen_id, "other_show_id": previous[0]},
                             "Two show intervals overlap on the same screen.")
            active.append(current)
    CHECK_RESULTS["show_interval_errors"] = errors
    CHECK_RESULTS["show_overlap_errors"] = overlaps
    OBSERVED["show_utc_offsets"] = sorted(offsets)
    print(f"\nValid show intervals: {len(valid):,}")
    print(f"Show interval errors: {errors}")
    print(f"Observed show UTC offsets (informational): {sorted(offsets)}")
    print(f"Overlapping show pairs: {overlaps}")


def write_report(row_results):
    checks = {
        "row_count_checks": len(EXPECTED_ROW_COUNTS),
        "individual_foreign_key_relationships": len(FOREIGN_KEYS),
        "composite_foreign_key_relationships": len(COMPOSITE_FOREIGN_KEYS),
        "primary_and_unique_key_checks": len(UNIQUE_CHECKS),
        "numeric_columns_configured": len(NUMERIC_COLUMNS),
        "varchar_columns_configured": len(VARCHAR_LIMITS),
        "date_columns_configured": len(DATE_COLUMNS),
        "timestamp_columns_configured": len(TIMESTAMP_COLUMNS),
    }
    passed_rows = sum(1 for r in row_results.values() if r["status"] == "PASSED")
    report = {
        "dataset_directory": DATA_DIR.relative_to(BASE_DIR).as_posix(),
        "expected_row_counts": EXPECTED_ROW_COUNTS,
        "row_counts": ROW_COUNTS,
        "row_count_results": row_results,
        "row_count_summary": {
            "checks_configured": len(EXPECTED_ROW_COUNTS),
            "checks_passed": passed_rows,
            "checks_failed": len(EXPECTED_ROW_COUNTS) - passed_rows,
            "expected_total_rows": sum(EXPECTED_ROW_COUNTS.values()),
            "actual_total_rows": sum(ROW_COUNTS.values()),
        },
        "total_rows": sum(ROW_COUNTS.values()),
        "checks_configured": checks,
        "check_results": dict(CHECK_RESULTS),
        "observed": OBSERVED,
        "issue_count": len(ISSUES),
        "warning_count": len(WARNINGS),
        "status": "FAILED" if ISSUES else "PASSED",
        "issues": ISSUES,
        "warnings": WARNINGS,
    }
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nMachine-readable report: {REPORT_PATH}")


def main():
    print("==============================================")
    print("       BOOKMYSHOW CSV DATA VALIDATOR")
    print("==============================================")
    data = load_all_data()
    row_results = validate_row_counts()

    if len(data) != len(EXPECTED_HEADERS):
        write_report(row_results)
        print("\nRESULT: VALIDATION FAILED (CSV files/structures missing)")
        return 1

    validate_required(data)
    validate_numeric_and_lengths(data)
    validate_dates_and_timestamps(data)
    validate_foreign_keys(data)
    validate_uniqueness(data)
    validate_cross_table(data)
    validate_business_rules(data)
    validate_show_times_and_overlaps(data)

    print("\n========== FINAL VALIDATION SUMMARY ==========")
    print(f"Files loaded: {len(data)}")
    print(f"Total CSV rows: {sum(ROW_COUNTS.values()):,}")
    print(f"Errors: {len(ISSUES)}")
    print(f"Warnings: {len(WARNINGS)}")
    write_report(row_results)

    if ISSUES:
        print("\nRESULT: VALIDATION FAILED")
        return 1
    print("\nRESULT: ALL VALIDATIONS PASSED (warnings may require review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
