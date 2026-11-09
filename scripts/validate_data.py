
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "seed_data"


# --------------------------------------------------
# CSV LOADER
# --------------------------------------------------

def load_csv(filename):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return list(reader)


# --------------------------------------------------
# LOAD ALL DATASETS
# --------------------------------------------------

def load_all_data():
    filenames = [
        "cities.csv",
        "venues.csv",
        "screens.csv",
        "seats.csv",
        "movies.csv",
        "shows.csv",
        "customers.csv",
        "offers.csv",
        "bookings.csv",
        "booking_seats.csv",
        "movie_reviews.csv",
    ]

    data = {}

    for filename in filenames:
        table_name = filename.replace(".csv", "")
        data[table_name] = load_csv(filename)

    return data


# --------------------------------------------------
# FOREIGN KEY VALIDATION
# --------------------------------------------------

def validate_foreign_keys(data):
    print("\n========== FOREIGN KEY VALIDATION ==========")

    fk_checks = [
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

    total_errors = 0

    for child_table, child_column, parent_table, parent_column in fk_checks:

        parent_values = {
            row[parent_column]
            for row in data[parent_table]
        }

        invalid_count = 0

        for row in data[child_table]:
            value = row[child_column]

            # Empty nullable values are allowed.
            if value == "":
                continue

            if value not in parent_values:
                invalid_count += 1

        total_errors += invalid_count

        print(
            f"{child_table}.{child_column} -> "
            f"{parent_table}: {invalid_count} invalid references"
        )

    return total_errors


# --------------------------------------------------
# UNIQUENESS VALIDATION
# --------------------------------------------------

def validate_uniqueness(data):
    print("\n========== UNIQUENESS VALIDATION ==========")

    unique_checks = [
        (
            "cities.city_id",
            "cities",
            ("city_id",),
        ),
        (
            "customers.email",
            "customers",
            ("email",),
        ),
        (
            "customers.phone",
            "customers",
            ("phone",),
        ),
        (
            "bookings.booking_code",
            "bookings",
            ("booking_code",),
        ),
        (
            "seats(screen_id,row_label,seat_number)",
            "seats",
            ("screen_id", "row_label", "seat_number"),
        ),
        (
            "booking_seats(show_id,seat_id)",
            "booking_seats",
            ("show_id", "seat_id"),
        ),
        (
            "booking_seats(booking_id,seat_id)",
            "booking_seats",
            ("booking_id", "seat_id"),
        ),
    ]

    total_errors = 0

    for label, table, columns in unique_checks:

        seen = set()
        duplicate_count = 0

        for row in data[table]:
            key = tuple(row[column] for column in columns)

            if key in seen:
                duplicate_count += 1
            else:
                seen.add(key)

        total_errors += duplicate_count

        print(
            f"{label}: {duplicate_count} duplicate combinations"
        )

    return total_errors


# --------------------------------------------------
# CROSS-TABLE CONSISTENCY VALIDATION
# --------------------------------------------------

def validate_cross_table_consistency(data):
    print("\n========== CROSS-TABLE VALIDATION ==========")

    total_errors = 0

    # Create lookup dictionaries.
    bookings = {
        row["booking_id"]: row
        for row in data["bookings"]
    }

    shows = {
        row["show_id"]: row
        for row in data["shows"]
    }

    seats = {
        row["seat_id"]: row
        for row in data["seats"]
    }

    # Check whether booking_seats.show_id matches
    # bookings.show_id for the same booking.
    booking_show_mismatches = 0

    for row in data["booking_seats"]:
        booking = bookings.get(row["booking_id"])

        if booking and booking["show_id"] != row["show_id"]:
            booking_show_mismatches += 1

    print(
        f"Booking-show mismatches: {booking_show_mismatches}"
    )

    total_errors += booking_show_mismatches

    # Check whether the seat belongs to the same screen
    # on which the show is scheduled.
    seat_screen_mismatches = 0

    for row in data["booking_seats"]:
        show = shows.get(row["show_id"])
        seat = seats.get(row["seat_id"])

        if show and seat:
            if show["screen_id"] != seat["screen_id"]:
                seat_screen_mismatches += 1

    print(
        f"Seat-screen mismatches: {seat_screen_mismatches}"
    )

    total_errors += seat_screen_mismatches

    return total_errors


# --------------------------------------------------
# SHOW OVERLAP VALIDATION
# --------------------------------------------------

def validate_show_overlaps(data):
    print("\n========== SHOW OVERLAP VALIDATION ==========")

    shows_by_screen = defaultdict(list)

    for show in data["shows"]:
        screen_id = show["screen_id"]

        start_time = datetime.fromisoformat(
            show["starts_at"]
        )

        end_time = datetime.fromisoformat(
            show["ends_at"]
        )

        shows_by_screen[screen_id].append(
            (start_time, end_time, show["show_id"])
        )

    overlap_count = 0

    for screen_id, screen_shows in shows_by_screen.items():

        screen_shows.sort(key=lambda item: item[0])

        active_shows = []

        for current_start, current_end, current_id in screen_shows:

            # Remove shows that have already ended.
            active_shows = [
                show for show in active_shows
                if show[1] > current_start
            ]

            # Every remaining active show overlaps
            # with the current show.
            overlap_count += len(active_shows)

            active_shows.append(
                (current_id, current_end)
            )

    print(
        f"Overlapping show pairs: {overlap_count}"
    )

    return overlap_count


# --------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------

def main():

    data = load_all_data()

    fk_errors = validate_foreign_keys(data)

    uniqueness_errors = validate_uniqueness(data)

    consistency_errors = validate_cross_table_consistency(data)

    overlap_errors = validate_show_overlaps(data)

    print("\n========== VALIDATION SUMMARY ==========")

    print(f"Foreign-key errors: {fk_errors}")
    print(f"Uniqueness errors: {uniqueness_errors}")
    print(f"Booking-show / Seat-screen errors: {consistency_errors}")
    print(f"Overlapping show pairs: {overlap_errors}")

    total_errors = (
        fk_errors
        + uniqueness_errors
        + consistency_errors
        + overlap_errors
    )

    if total_errors == 0:
        print("\nRESULT: ALL VALIDATIONS PASSED")
    else:
        print(
            f"\nRESULT: VALIDATION FAILED "
            f"({total_errors} errors found)"
        )


if __name__ == "__main__":
    main()
