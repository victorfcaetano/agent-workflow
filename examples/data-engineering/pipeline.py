"""Load synthetic customer and order CSVs into a new SQLite database."""

import argparse
import csv
import sqlite3
from contextlib import closing
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"
SCHEMA = """
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(customer_id)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(order_id)) > 0),
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL CHECK (status IN ('paid', 'cancelled')),
    amount_cents INTEGER NOT NULL CHECK (typeof(amount_cents) = 'integer' AND amount_cents >= 0)
);
CREATE VIEW customer_sales AS
SELECT c.customer_id, COUNT(o.order_id) AS paid_orders,
       COALESCE(SUM(o.amount_cents), 0) AS revenue_cents
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id AND o.status = 'paid'
GROUP BY c.customer_id;
"""


def _load_csv(db: sqlite3.Connection, path: Path, columns: list[str], insert: str) -> None:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.reader(stream, strict=True)
        try:
            if next(rows, None) != columns:
                raise ValueError(f"Expected CSV header {','.join(columns)}")
            for row in rows:
                if len(row) != len(columns):
                    raise ValueError(f"Expected {len(columns)} columns, found {len(row)}")
                if "amount_cents" in columns:
                    amount = row[columns.index("amount_cents")]
                    if not amount.isascii() or not amount.isdecimal():
                        raise ValueError("amount_cents must contain nonnegative integer cents")
                db.execute(insert, row)
        except (csv.Error, sqlite3.IntegrityError, ValueError) as error:
            raise ValueError(f"{path.name}, line {rows.line_num}: {error}") from error


def build_database(output: Path, inputs: Path = DATA) -> None:
    output.touch(exist_ok=False)
    try:
        with closing(sqlite3.connect(output)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.executescript(SCHEMA)
            _load_csv(db, inputs / "customers.csv", ["customer_id", "name"],
                      "INSERT INTO customers (customer_id, name) VALUES (?, ?)")
            _load_csv(db, inputs / "orders.csv", ["order_id", "customer_id", "status", "amount_cents"],
                      "INSERT INTO orders (order_id, customer_id, status, amount_cents) VALUES (?, ?, ?, ?)")
            db.commit()
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New SQLite database path.")
    parser.add_argument("--inputs", type=Path, default=DATA, help="Directory containing both source CSVs.")
    args = parser.parse_args()
    try:
        build_database(args.output, args.inputs)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
