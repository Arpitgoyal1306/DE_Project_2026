import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
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
    "screens": [
        "screen_id", "venue_id", "screen_name", "screen_type", "total_seats"
    ],
    "seats": ["seat_id", "screen_id", "row_label", "seat_number", "seat_class"],
    "movies": [
        "movie_id", "title", "language", "certificate",
        "duration_min", "release_date"
    ],
    "shows": [
        "show_id", "movie_id", "screen_id", "starts_at",
        "ends_at", "format", "base_price"
    ],
    "customers": [
        "customer_id", "full_name", "email", "phone", "city_id", "created_at"
    ],
    "offers": [
        "offer_code", "description", "discount_pct",
        "max_discount", "valid_from", "valid_to"
    ],
    "bookings": [
        "booking_id", "booking_code", "customer_id", "show_id",
        "booked_at", "num_tickets", "ticket_amount", "convenience_fee",
        "fnb_amount", "offer_code", "discount", "total_amount",
        "payment_method", "status"
    ],
    "booking_seats": ["booking_id", "show_id", "seat_id", "price"],
    "movie_reviews": [
        "review_id", "movie_id", "customer_id",
        "rating", "review_text", "created_at"
    ],
}

EXPECTED_ROW_COUNTS = {
    "cities": 10,
    "venues": 140,
    "screens": 490,
    "seats": 94056,
    "movies": 300,
    "shows": 160034,
    "customers": 40000,
    "offers": 25,
    "bookings": 150094,
    "booking_seats": 300389,
    "movie_reviews": 32510,
}

# Primary keys and alternate candidate keys.
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
    # Required to support the composite foreign key.
    ("bookings", ("booking_id", "show_id"), "UNIQUE"),
]

# child table, child column, parent table, parent column
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
    ("booking_seats", "booking_id", "bookings", "booking_id"),
    ("booking_seats", "show_id", "shows", "show_id"),
    ("booking_seats", "seat_id", "seats", "seat_id"),
    ("movie_reviews", "movie_id", "movies", "movie_id"),
    ("movie_reviews", "customer_id", "customers", "customer_id"),
]


# ============================================================
# REPORTING HELPERS
# ============================================================

ISSUES = []
ROW_COUNTS = {}


def add_issue(table, row_identifier, rule, values, message):
    """Add one reproducible validation issue."""
    ISSUES.append({
        "table": table,
        "row_identifier": row_identifier,
        "rule": rule,
        "offending_values": values,
        "message": message,
    })


def get_row_identifier(table, row):
    """Return a useful identifier for an offending CSV row."""
    preferred = {
        "cities": ["city_id"],
        "venues": ["venue_id"],
        "screens": ["screen_id"],
        "seats": ["seat_id"],
        "movies": ["movie_id"],
        "shows": ["show_id"],
        "customers": ["customer_id"],
        "offers": ["offer_code"],
        "bookings": ["booking_id"],
        "booking_seats": ["booking_id", "show_id", "seat_id"],
        "movie_reviews": ["review_id"],
    }

    return {
        column: row.get(column)
        for column in preferred.get(table, [])
    }


# ============================================================
# CSV STRUCTURE AND LOADING
# ============================================================

def load_all_data():
    data = {}
    structure_valid = True

    print("\n========== CSV STRUCTURE VALIDATION ==========")

    for table, expected_columns in EXPECTED_HEADERS.items():
        filename = f"{table}.csv"
        file_path = DATA_DIR / filename

        if not file_path.exists():
            add_issue(
                table, None, "FILE_MISSING", {},
                f"Required file {filename} does not exist."
            )
            structure_valid = False
            continue

        try:
            with open(
                file_path, "r", newline="", encoding="utf-8-sig"
            ) as file:
                reader = csv.DictReader(file)
                actual_headers = reader.fieldnames or []

                missing_headers = [
                    column for column in expected_columns
                    if column not in actual_headers
                ]
                unexpected_headers = [
                    column for column in actual_headers
                    if column not in expected_columns
                ]
                duplicate_headers = [
                    column for column in set(actual_headers)
                    if actual_headers.count(column) > 1
                ]

                if (
                    missing_headers
                    or unexpected_headers
                    or duplicate_headers
                ):
                    add_issue(
                        table, None, "HEADER_MISMATCH",
                        {
                            "expected": expected_columns,
                            "actual": actual_headers,
                            "missing": missing_headers,
                            "unexpected": unexpected_headers,
                            "duplicates": duplicate_headers,
                        },
                        "CSV headers do not match the expected structure."
                    )
                    structure_valid = False
                    continue

                rows = []

                for csv_row_number, raw_row in enumerate(reader, start=2):
                    # More values than the header.
                    if None in raw_row:
                        add_issue(
                            table, {"csv_row": csv_row_number},
                            "CSV_ROW_EXTRA_FIELDS",
                            {"extra_values": raw_row[None]},
                            "Row contains more fields than the header."
                        )
                        structure_valid = False
                        continue

                    # Fewer values than the header. This is different
                    # from a valid empty field in a nullable column.
                    missing_fields = [
                        column for column in expected_columns
                        if raw_row.get(column) is None
                    ]

                    if missing_fields:
                        add_issue(
                            table, {"csv_row": csv_row_number},
                            "CSV_ROW_MISSING_FIELDS",
                            {"missing_fields": missing_fields},
                            "Row contains fewer fields than the header."
                        )
                        structure_valid = False
                        continue

                    row = {
                        column: raw_row[column].strip()
                        for column in expected_columns
                    }
                    row["_csv_row"] = csv_row_number
                    rows.append(row)

                data[table] = rows
                ROW_COUNTS[table] = len(rows)
                print(f"{table}.csv: {len(rows):,} rows")

        except (OSError, csv.Error, UnicodeError) as error:
            add_issue(
                table, None, "CSV_READ_ERROR", {},
                str(error)
            )
            structure_valid = False

    print(f"\nTotal loaded rows: {sum(ROW_COUNTS.values()):,}")
    return data, structure_valid


# ============================================================
# REQUIRED VALUE VALIDATION
# ============================================================

def validate_required_values(data):
    print("\n========== REQUIRED VALUE VALIDATION ==========")
    missing_count = 0

    for table, rows in data.items():
        nullable = NULLABLE_COLUMNS.get(table, set())

        for row in rows:
            for column in EXPECTED_HEADERS[table]:
                if column in nullable:
                    continue

                if row[column] == "":
                    missing_count += 1
                    add_issue(
                        table,
                        get_row_identifier(table, row),
                        "MISSING_REQUIRED_VALUE",
                        {column: row[column]},
                        f"Required column '{column}' is blank."
                    )

    print(f"Missing required values: {missing_count}")
    return missing_count


# ============================================================
# ROW COUNT VALIDATION
# ============================================================

def validate_row_counts():
    print("\n========== ROW COUNT VALIDATION ==========")
    results = {}
    errors = 0

    for table, expected in EXPECTED_ROW_COUNTS.items():
        actual = ROW_COUNTS.get(table)
        passed = actual is not None and actual == expected

        results[table] = {
            "expected": expected,
            "actual": actual,
            "status": "PASSED" if passed else "FAILED",
        }

        if not passed:
            errors += 1

            if actual is None:
                add_issue(
                    table, None, "ROW_COUNT_UNAVAILABLE",
                    {"expected": expected, "actual": None},
                    "CSV file was not loaded, so its row count could not be verified."
                )
            else:
                add_issue(
                    table, None, "ROW_COUNT_MISMATCH",
                    {"expected": expected, "actual": actual},
                    "CSV row count differs from expected count."
                )

        actual_display = (
            f"{actual:,}" if actual is not None else "UNAVAILABLE"
        )
        print(
            f"{table}: expected {expected:,}, actual {actual_display} - "
            f"{'PASS' if passed else 'FAIL'}"
        )

    return results, errors


# ============================================================
# FOREIGN KEY VALIDATION
# ============================================================

def validate_foreign_keys(data):
    print("\n========== FOREIGN KEY VALIDATION ==========")
    total_invalid = 0
    total_missing = 0

    for child_table, child_column, parent_table, parent_column in FOREIGN_KEYS:
        if child_table not in data or parent_table not in data:
            continue

        parent_values = {
            row[parent_column]
            for row in data[parent_table]
            if row[parent_column] != ""
        }

        invalid_count = 0
        missing_count = 0
        nullable = child_column in NULLABLE_COLUMNS.get(child_table, set())

        for row in data[child_table]:
            value = row[child_column]

            if value == "":
                if nullable:
                    continue

                missing_count += 1
                add_issue(
                    child_table,
                    get_row_identifier(child_table, row),
                    "MISSING_REQUIRED_FOREIGN_KEY",
                    {child_column: value},
                    f"Required reference to {parent_table}.{parent_column} is blank."
                )
                continue

            if value not in parent_values:
                invalid_count += 1
                add_issue(
                    child_table,
                    get_row_identifier(child_table, row),
                    "INVALID_FOREIGN_KEY",
                    {
                        child_column: value,
                        "parent_table": parent_table,
                        "parent_column": parent_column,
                    },
                    "Referenced parent record does not exist."
                )

        total_invalid += invalid_count
        total_missing += missing_count

        print(
            f"{child_table}.{child_column} -> "
            f"{parent_table}.{parent_column}: "
            f"{invalid_count} invalid, {missing_count} missing"
        )

    print(f"Total invalid references: {total_invalid}")
    print(f"Total missing required references: {total_missing}")
    return total_invalid + total_missing


# ============================================================
# PRIMARY KEY AND UNIQUE VALIDATION
# ============================================================

def validate_uniqueness(data):
    print("\n========== PRIMARY KEY / UNIQUE VALIDATION ==========")
    total_duplicates = 0

    for table, columns, rule_type in UNIQUE_CHECKS:
        if table not in data:
            continue

        seen = {}
        duplicate_count = 0

        for row in data[table]:
            key = tuple(row[column] for column in columns)

            # Required blank values are reported separately by
            # validate_required_values().
            if any(value == "" for value in key):
                continue

            if key in seen:
                duplicate_count += 1
                add_issue(
                    table,
                    get_row_identifier(table, row),
                    f"DUPLICATE_{rule_type}",
                    {
                        "columns": list(columns),
                        "values": list(key),
                        "first_occurrence_csv_row": seen[key],
                    },
                    f"Duplicate key for columns {columns}."
                )
            else:
                seen[key] = row["_csv_row"]

        total_duplicates += duplicate_count
        print(
            f"{table}{columns}: {duplicate_count} duplicate combinations"
        )

    print(f"Total duplicate combinations: {total_duplicates}")
    return total_duplicates


# ============================================================
# CROSS-TABLE CONSISTENCY
# ============================================================

def validate_cross_table_consistency(data):
    print("\n========== CROSS-TABLE CONSISTENCY ==========")
    errors = 0

    bookings = {
        row["booking_id"]: row
        for row in data.get("bookings", [])
        if row["booking_id"]
    }
    shows = {
        row["show_id"]: row
        for row in data.get("shows", [])
        if row["show_id"]
    }
    seats = {
        row["seat_id"]: row
        for row in data.get("seats", [])
        if row["seat_id"]
    }

    booking_show_mismatches = 0
    seat_screen_mismatches = 0

    for row in data.get("booking_seats", []):
        booking_id = row["booking_id"]
        show_id = row["show_id"]
        seat_id = row["seat_id"]

        booking = bookings.get(booking_id)
        show = shows.get(show_id)
        seat = seats.get(seat_id)

        if booking is None:
            errors += 1
            add_issue(
                "booking_seats",
                get_row_identifier("booking_seats", row),
                "MISSING_BOOKING_FOR_ALLOCATION",
                {"booking_id": booking_id},
                "Booking record does not exist."
            )

        if show is None:
            errors += 1
            add_issue(
                "booking_seats",
                get_row_identifier("booking_seats", row),
                "MISSING_SHOW_FOR_ALLOCATION",
                {"show_id": show_id},
                "Show record does not exist."
            )

        if seat is None:
            errors += 1
            add_issue(
                "booking_seats",
                get_row_identifier("booking_seats", row),
                "MISSING_SEAT_FOR_ALLOCATION",
                {"seat_id": seat_id},
                "Seat record does not exist."
            )

        if booking is not None and booking["show_id"] != show_id:
            booking_show_mismatches += 1
            errors += 1
            add_issue(
                "booking_seats",
                get_row_identifier("booking_seats", row),
                "BOOKING_SHOW_MISMATCH",
                {
                    "booking_id": booking_id,
                    "booking_show_id": booking["show_id"],
                    "allocation_show_id": show_id,
                },
                "Allocation show differs from the booking's show."
            )

        if (
            show is not None
            and seat is not None
            and show["screen_id"] != seat["screen_id"]
        ):
            seat_screen_mismatches += 1
            errors += 1
            add_issue(
                "booking_seats",
                get_row_identifier("booking_seats", row),
                "SEAT_SCREEN_MISMATCH",
                {
                    "show_id": show_id,
                    "seat_id": seat_id,
                    "show_screen_id": show["screen_id"],
                    "seat_screen_id": seat["screen_id"],
                },
                "Seat does not belong to the screen assigned to the show."
            )

    print(f"Booking-show mismatches: {booking_show_mismatches}")
    print(f"Seat-screen mismatches: {seat_screen_mismatches}")
    print(f"Cross-table errors including missing parents: {errors}")
    return errors


# ============================================================
# TIMESTAMP AND SHOW OVERLAP VALIDATION
# ============================================================

def validate_show_times(data):
    print("\n========== SHOW TIMESTAMP VALIDATION ==========")
    valid_shows = []
    errors = 0
    observed_offsets = set()

    for row in data.get("shows", []):
        show_id = row["show_id"]

        try:
            start = datetime.fromisoformat(row["starts_at"])
            end = datetime.fromisoformat(row["ends_at"])
        except ValueError as error:
            errors += 1
            add_issue(
                "shows",
                {"show_id": show_id},
                "INVALID_TIMESTAMP",
                {
                    "starts_at": row["starts_at"],
                    "ends_at": row["ends_at"],
                },
                str(error)
            )
            continue

        if start.tzinfo is None or start.utcoffset() is None:
            errors += 1
            add_issue(
                "shows",
                {"show_id": show_id},
                "TIMEZONE_MISSING",
                {"starts_at": row["starts_at"]},
                "Show start timestamp must include a timezone offset."
            )
            continue

        if end.tzinfo is None or end.utcoffset() is None:
            errors += 1
            add_issue(
                "shows",
                {"show_id": show_id},
                "TIMEZONE_MISSING",
                {"ends_at": row["ends_at"]},
                "Show end timestamp must include a timezone offset."
            )
            continue

        start_offset = start.utcoffset()
        end_offset = end.utcoffset()
        observed_offsets.add(str(start_offset))
        observed_offsets.add(str(end_offset))

        if start_offset != end_offset:
            errors += 1
            add_issue(
                "shows",
                {"show_id": show_id},
                "INCONSISTENT_ROW_TIMEZONE",
                {
                    "starts_at": row["starts_at"],
                    "ends_at": row["ends_at"],
                },
                "Start and end timestamps use different UTC offsets."
            )
            continue

        # Python compares aware datetimes using their actual instants.
        if end <= start:
            errors += 1
            add_issue(
                "shows",
                {"show_id": show_id},
                "INVALID_SHOW_DURATION",
                {
                    "starts_at": row["starts_at"],
                    "ends_at": row["ends_at"],
                },
                "Show end must be later than show start."
            )
            continue

        valid_shows.append({
            "show_id": show_id,
            "screen_id": row["screen_id"],
            "start": start,
            "end": end,
        })

    if len(observed_offsets) > 1:
        errors += 1
        add_issue(
            "shows",
            None,
            "DATASET_TIMEZONE_INCONSISTENCY",
            {"observed_utc_offsets": sorted(observed_offsets)},
            "The dataset contains multiple UTC offsets. "
            "Confirm whether these are intentional before comparing times."
        )

    print(f"Valid show intervals: {len(valid_shows):,}")
    print(f"Observed UTC offsets: {sorted(observed_offsets)}")
    print(f"Timestamp errors: {errors}")
    return valid_shows, errors


def validate_show_overlaps(valid_shows):
    print("\n========== SHOW OVERLAP VALIDATION ==========")
    shows_by_screen = defaultdict(list)

    for show in valid_shows:
        shows_by_screen[show["screen_id"]].append(show)

    overlap_count = 0

    for screen_id, screen_shows in shows_by_screen.items():
        screen_shows.sort(key=lambda item: item["start"])
        active_shows = []

        for current in screen_shows:
            active_shows = [
                previous
                for previous in active_shows
                if previous["end"] > current["start"]
            ]

            for previous in active_shows:
                overlap_count += 1
                add_issue(
                    "shows",
                    {"show_id": current["show_id"]},
                    "OVERLAPPING_SHOWS",
                    {
                        "screen_id": screen_id,
                        "first_show_id": previous["show_id"],
                        "first_starts_at": previous["start"].isoformat(),
                        "first_ends_at": previous["end"].isoformat(),
                        "second_show_id": current["show_id"],
                        "second_starts_at": current["start"].isoformat(),
                        "second_ends_at": current["end"].isoformat(),
                    },
                    "Two shows overlap on the same screen."
                )

            active_shows.append(current)

    print(f"Overlapping show pairs: {overlap_count}")
    return overlap_count


# ============================================================
# JSON REPORT
# ============================================================

def write_report(row_count_results=None):
    if row_count_results is None:
        row_count_results = {}

        # Produce a result for every expected table, even if loading
        # stopped early because of a malformed or missing CSV file.
        for table, expected in EXPECTED_ROW_COUNTS.items():
            actual = ROW_COUNTS.get(table)
            passed = actual is not None and actual == expected
            row_count_results[table] = {
                "expected": expected,
                "actual": actual,
                "status": "PASSED" if passed else "FAILED",
            }

    checks_passed = sum(
        1 for result in row_count_results.values()
        if result["status"] == "PASSED"
    )
    checks_failed = len(EXPECTED_ROW_COUNTS) - checks_passed

    expected_total_rows = sum(EXPECTED_ROW_COUNTS.values())
    actual_total_rows = sum(ROW_COUNTS.values())

    failed = len(ISSUES) > 0 or checks_failed > 0

    report = {
        "dataset_directory": DATA_DIR.relative_to(BASE_DIR).as_posix(),
        "expected_row_counts": EXPECTED_ROW_COUNTS,
        "row_counts": ROW_COUNTS,
        "row_count_results": row_count_results,
        "row_count_summary": {
            "checks_configured": len(EXPECTED_ROW_COUNTS),
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "expected_total_rows": expected_total_rows,
            "actual_total_rows": actual_total_rows,
        },
        "total_rows": actual_total_rows,
        "checks_configured": {
            "row_count_checks": len(EXPECTED_ROW_COUNTS),
            "foreign_key_relationships": len(FOREIGN_KEYS),
            "primary_and_unique_key_checks": len(UNIQUE_CHECKS),
        },
        "issue_count": len(ISSUES),
        "status": "FAILED" if failed else "PASSED",
        "issues": ISSUES,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print(f"\nMachine-readable report: {REPORT_PATH}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("==============================================")
    print("       BOOKMYSHOW CSV DATA VALIDATOR")
    print("==============================================")

    data, structure_valid = load_all_data()

    # Always run row-count validation so missing/unreadable files
    # appear as FAILED in the JSON report.
    row_count_results, _ = validate_row_counts()

    # Do not run relational checks against malformed or incomplete
    # CSV structures.
    if not structure_valid:
        print("\nCSV structure validation failed.")
        write_report(row_count_results)
        return 1

    validate_required_values(data)
    validate_foreign_keys(data)
    validate_uniqueness(data)
    validate_cross_table_consistency(data)

    valid_shows, _ = validate_show_times(data)
    validate_show_overlaps(valid_shows)

    print("\n========== FINAL VALIDATION SUMMARY ==========")
    print(f"Files loaded: {len(data)}")
    print(f"Total CSV rows: {sum(ROW_COUNTS.values()):,}")
    print(f"Validation issues: {len(ISSUES)}")

    write_report(row_count_results)

    if ISSUES:
        print("\nRESULT: VALIDATION FAILED")
        print(f"{len(ISSUES)} issue(s) require attention.")
        return 1

    print("\nRESULT: ALL VALIDATIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
