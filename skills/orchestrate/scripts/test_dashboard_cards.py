#!/usr/bin/env python3
"""Tests for the `Decide:` card validation in dashboard.py. Run: python3 test_dashboard_cards.py"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dashboard as d


def card(decide):
    return f"### WI-01: slow list → add index\nProblem: the list is slow.\nDecide: {decide}\n"


class DecideValidation(unittest.TestCase):
    def test_valid_card(self):
        self.assertEqual(len(d.asks(card("I recommend X. Users would see Y."))), 1)

    def test_missing_recommendation(self):
        with self.assertRaises(d.Fail) as cm:
            d.asks(card("Choose X or Y."))
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("recommendation", str(cm.exception))

    def test_approval_only_ask(self):
        for ask in ("I recommend it. Approve to proceed.", "I recommend it; may I build this?", "I recommend X. Approve the ADR."):
            with self.assertRaises(d.Fail, msg=ask) as cm:
                d.asks(card(ask))
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("approval-only", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
