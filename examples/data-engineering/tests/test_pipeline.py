import csv
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from pipeline import build_database


INPUTS = Path(__file__).resolve().parents[1] / "data"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "sales.sqlite"
        self.inputs = self.root / "data"
        shutil.copytree(INPUTS, self.inputs)

    def test_load_preserves_source_rows_and_checks_foreign_keys(self):
        build_database(self.database, self.inputs)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM customers").fetchone(), (4,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone(), (5,))
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(db.execute("SELECT DISTINCT typeof(amount_cents) FROM orders").fetchall(),
                             [("integer",)])
            fk = db.execute("PRAGMA foreign_key_list(orders)").fetchone()
            self.assertEqual(fk[2:5], ("customers", "customer_id", "customer_id"))

    def test_sales_aggregate_includes_zero_activity_customers_and_excludes_cancellations(self):
        build_database(self.database, self.inputs)
        with closing(sqlite3.connect(self.database)) as db:
            result = db.execute("SELECT customer_id, paid_orders, revenue_cents "
                                "FROM customer_sales ORDER BY customer_id").fetchall()
        self.assertEqual(result, [("C001", 2, 2000), ("C002", 1, 1800),
                                  ("C003", 0, 0), ("C004", 0, 0)])

    def test_bad_order_rows_fail_without_publishing_a_partial_database(self):
        orders = self.inputs / "orders.csv"
        clean = orders.read_bytes()
        bad_rows = [
            ["O101", "C001", "paid", "100"],      # Duplicate order ID
            ["O999", "C404", "paid", "100"],      # Unknown customer
            ["O999", "C001", "pending", "100"],   # Unknown status
            ["O999", "C001", "paid", "-1"],       # Negative amount
            ["O999", "C001", "paid", "12.50"],    # Fractional cents
            ["", "C001", "paid", "100"],          # Missing order ID
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                orders.write_bytes(clean)
                with orders.open("a", encoding="utf-8", newline="") as stream:
                    csv.writer(stream).writerow(row)
                with self.assertRaisesRegex(ValueError, "orders.csv"):
                    build_database(self.database, self.inputs)
                self.assertFalse(self.database.exists())

    def test_header_must_match_the_input_contract(self):
        (self.inputs / "customers.csv").write_text("id,name\nC001,Test\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "customers.csv"):
            build_database(self.database, self.inputs)
        self.assertFalse(self.database.exists())

    def test_existing_output_is_preserved(self):
        self.database.write_bytes(b"Existing project file")
        with self.assertRaises(FileExistsError):
            build_database(self.database, self.inputs)
        self.assertEqual(self.database.read_bytes(), b"Existing project file")
