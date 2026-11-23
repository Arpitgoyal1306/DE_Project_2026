"""Compare the two workload files on a loaded, idle coursework database.

Usage: python3 benchmarks/check_results.py DATABASE
Connection settings come from libpq. Each comparison uses a repeatable-read
snapshot. Write variants start from the same savepoint and always roll back.
"""
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def workload(filename):
    blocks = re.split(r"^-- @(\w+)\s*$", (ROOT / filename).read_text(), flags=re.M)
    return {
        key: "\n".join(line for line in body.splitlines()
                       if not line.lstrip().startswith("--")).strip().removesuffix(";")
        for key, body in zip(blocks[1::2], blocks[2::2]) if key != "END"
    }


def execute(db, statements):
    sql = ("BEGIN ISOLATION LEVEL REPEATABLE READ;\n"
           "SET LOCAL search_path TO bms, public;\n"
           "SET LOCAL TIME ZONE 'Asia/Kolkata';\n" + statements + "\nROLLBACK;")
    return subprocess.run(
        ["psql", "-XAtq", "-v", "ON_ERROR_STOP=1", "-d", db],
        input=sql, capture_output=True, text=True, check=True
    ).stdout.rstrip("\n")


def compare_reads(db, original, optimized):
    statement = f"""
    WITH a AS MATERIALIZED ({original}), b AS MATERIALIZED ({optimized})
    SELECT (SELECT count(*) FROM a), (SELECT count(*) FROM b),
           (SELECT count(*) FROM (TABLE a EXCEPT ALL TABLE b) d),
           (SELECT count(*) FROM (TABLE b EXCEPT ALL TABLE a) d);
    """
    return tuple(map(int, execute(db, statement).split("|")))


def compare_writes(db, key, original, optimized):
    rows = "bs.*" if key == "W04" else "*"
    statement = f"""SAVEPOINT clean;
COPY ({original} RETURNING {rows}) TO STDOUT;
ROLLBACK TO clean;
\\echo __second__
COPY ({optimized} RETURNING {rows}) TO STDOUT;"""
    lines = execute(db, statement).splitlines()
    split = lines.index("__second__")
    a, b = Counter(lines[:split]), Counter(lines[split + 1:])
    return sum(a.values()), sum(b.values()), sum((a-b).values()), sum((b-a).values())


def check_boundaries(db, queries):
    # UTC session exposes accidental dependence on the session's local weekday.
    fixture = """SET LOCAL TIME ZONE 'UTC';
    CREATE TEMP TABLE bookings (booking_id int, show_id int, booked_at timestamptz, status text);
    CREATE TEMP TABLE shows (show_id int, movie_id int, screen_id int, starts_at timestamptz, base_price numeric);
    CREATE TEMP TABLE seats (seat_id int, screen_id int);
    CREATE TEMP TABLE booking_seats (booking_id int, show_id int, seat_id int, price numeric, UNIQUE(show_id, seat_id));
    INSERT INTO bookings VALUES (1,1,'2026-06-03','PENDING'), (9,1,'2026-06-01','PENDING'),
        (7,1,'2026-06-01','PENDING'), (2,1,'2026-05-01','CONFIRMED');
    INSERT INTO seats VALUES (1,1),(2,1),(3,1),(4,2);
    INSERT INTO booking_seats VALUES (2,1,1,100);
    INSERT INTO shows VALUES (1,2,1,'2026-07-04 00:00+05:30',100),
        (2,2,1,'2026-08-01 00:00+05:30',100),(3,2,1,'2026-07-06 00:00+05:30',100),
        (4,3,1,'2026-07-05 12:00+05:30',100),(5,2,1,'2026-06-28 12:00+05:30',100);
    """
    for key, columns, expected in [
        ("W02", "booking_id, seat_id", ["7|2", "7|3"]),
        ("W03", "booking_id, status", ["7|CONFIRMED"]),
        ("W05", "show_id, base_price", ["1|110"]),
    ]:
        actual = execute(db, fixture + queries[key] + " RETURNING " + columns + ";")
        assert sorted(actual.splitlines()) == expected, (key, actual)


def check_pricing_year(db, query):
    # Each included show and its booking fall in different calendar years.
    fixture = """SET LOCAL TIME ZONE 'UTC';
    CREATE TEMP TABLE shows (show_id int, starts_at timestamptz);
    CREATE TEMP TABLE bookings (booking_id int, booked_at timestamptz);
    CREATE TEMP TABLE seats (seat_id int, screen_id int, seat_class text);
    CREATE TEMP TABLE screens (screen_id int, venue_id int);
    CREATE TEMP TABLE venues (venue_id int, city_id int);
    CREATE TEMP TABLE booking_seats (booking_id int, show_id int, seat_id int, price numeric);
    INSERT INTO shows VALUES (1,'2025-12-31 23:59:59+05:30'), (2,'2026-01-01 00:00+05:30'),
        (3,'2026-12-31 23:59:59+05:30'), (4,'2027-01-01 00:00+05:30');
    INSERT INTO bookings VALUES (1,'2025-12-30'), (2,'2025-12-31'), (3,'2025-12-31'), (4,'2026-12-31');
    INSERT INTO venues VALUES (1,7);
    INSERT INTO screens VALUES (1,1);
    INSERT INTO seats VALUES (1,1,'REGULAR');
    INSERT INTO booking_seats VALUES (1,1,1,900),(2,2,1,100),(3,3,1,200),(4,4,1,800);
    """
    assert execute(db, fixture + query + ";") == "7|REGULAR|150.00|2"


def main(db):
    original = workload("queries/workload_30.sql")
    optimized = workload("sql/06_optimized_queries.sql")
    assert original.keys() == optimized.keys() and len(original) == 30
    for queries in (original, optimized):
        check_boundaries(db, queries)
        check_pricing_year(db, queries["R24"])
    print("query,original_rows,optimized_rows,original_only,optimized_only")
    for key, query in original.items():
        if key.startswith("W"):
            result = compare_writes(db, key, query, optimized[key])
        else:
            result = compare_reads(db, query, optimized[key])
        print(key, *result, sep=",", flush=True)
        if key == "R13":
            assert result == (0, 7, 0, 7), result
            reference = """SELECT offer_code, description, discount_pct FROM offers
                WHERE offer_code NOT IN (SELECT offer_code FROM bookings WHERE offer_code IS NOT NULL)"""
            assert compare_reads(db, reference, optimized[key]) == (7, 7, 0, 0)
        else:
            assert result[2:] == (0, 0), (key, result)

    # Independently rank all bookings, then compare the actual ordered page.
    page = optimized["R22"]
    ranked = """SELECT booking_id FROM (
        SELECT booking_id, row_number() OVER (ORDER BY booked_at DESC, booking_id DESC) AS pos
        FROM bookings) ranked WHERE pos BETWEEN 100001 AND 100025 ORDER BY pos"""
    lines = execute(db, f"COPY ({page}) TO STDOUT;\n\\echo __ranked__\nCOPY ({ranked}) TO STDOUT;").splitlines()
    split = lines.index("__ranked__")
    assert split == 25 and [row.split("\t")[0] for row in lines[:split]] == lines[split + 1:]


if __name__ == "__main__":
    main(sys.argv[1])
