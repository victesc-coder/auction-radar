import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sqlite3
import tempfile
import unittest

from auction_radar.core import Lot, analyze, eligible
from auction_radar.__main__ import run


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads(Path("examples/lots.json").read_text())[0]
        self.now = datetime.fromisoformat("2026-10-26T08:00:00-03:00")

    def test_financial_ceiling_respects_margin(self):
        lot = Lot.from_dict(self.row)
        report = analyze(lot)
        self.assertEqual(report["estimated_total"], "62500.00")
        self.assertEqual(report["estimated_profit"], "17500.00")
        self.assertEqual(report["maximum_bid"], "51428.57")
        ceiling = Decimal(report["maximum_bid"])
        for bid, expected in [(ceiling, True), (ceiling + Decimal("0.01"), False)]:
            self.row["bid"] = str(bid)
            self.assertEqual(analyze(Lot.from_dict(self.row))["within_target"], expected)

    def test_calendar_and_location(self):
        self.assertTrue(eligible(Lot.from_dict(self.row), self.now))
        for when in [None, self.now - timedelta(seconds=1), self.now + timedelta(days=7)]:
            self.row["auction_at"] = when.isoformat() if when else None
            self.assertFalse(eligible(Lot.from_dict(self.row), self.now))
        self.row["auction_at"] = self.now.isoformat()
        self.row["state"] = "RJ"
        self.assertFalse(eligible(Lot.from_dict(self.row), self.now))

    def test_missing_resale_does_not_invent_opportunity(self):
        self.row["resale_estimate"] = None
        report = analyze(Lot.from_dict(self.row))
        self.assertIsNone(report["within_target"])
        self.assertIsNone(report["maximum_bid"])

    def test_invalid_input(self):
        for key, value in [("bid", "NaN"), ("additional_costs", "-1"),
                           ("commission_rate", "5"), ("auction_at", "2026-10-28T10:00:00")]:
            with self.subTest(key=key):
                row = dict(self.row, **{key: value})
                with self.assertRaises(ValueError):
                    Lot.from_dict(row)

    def test_persistence_retries_and_changed_bid(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "lots.json"
            database = str(Path(folder) / "radar.sqlite3")
            source.write_text(json.dumps([self.row]))
            for _ in range(2):
                self.assertEqual(run(source, database, self.now, 7, Decimal("0.2"))["eligible"], 1)
            self.row["bid"] = "51000"
            source.write_text(json.dumps([self.row]))
            run(source, database, self.now + timedelta(hours=1), 7, Decimal("0.2"))
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
