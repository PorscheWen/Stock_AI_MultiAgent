"""portfolio_view 排序與解析（不依賴網路）。"""
import unittest

from agents.portfolio_view import (
    parse_list_sort_args,
    sort_portfolio_rows,
)


class TestPortfolioView(unittest.TestCase):

    def test_parse_sort_args_default(self):
        k, rev = parse_list_sort_args([])
        self.assertEqual(k, "symbol")
        self.assertFalse(rev)

    def test_parse_sort_args_reverse(self):
        k, rev = parse_list_sort_args(["股數", "逆序"])
        self.assertEqual(k, "shares")
        self.assertTrue(rev)

    def test_parse_sort_yi_prefix(self):
        k, rev = parse_list_sort_args(["依獲利"])
        self.assertEqual(k, "pnl")
        self.assertFalse(rev)

    def test_sort_by_shares(self):
        rows = [
            {"symbol": "A", "shares": 10, "cost_basis": 100, "pnl": 1},
            {"symbol": "B", "shares": 3, "cost_basis": 50, "pnl": 10},
        ]
        out = sort_portfolio_rows(rows, "shares", False)
        self.assertEqual([r["symbol"] for r in out], ["B", "A"])

    def test_sort_by_pnl_desc(self):
        rows = [
            {"symbol": "A", "shares": 1, "pnl": 5.0},
            {"symbol": "B", "shares": 1, "pnl": 100.0},
        ]
        out = sort_portfolio_rows(rows, "pnl", True)
        self.assertEqual([r["symbol"] for r in out], ["B", "A"])

    def test_sort_none_pnl_to_bottom_asc(self):
        rows = [
            {"symbol": "A", "pnl": None},
            {"symbol": "B", "pnl": 0.0},
        ]
        out = sort_portfolio_rows(rows, "pnl", False)
        self.assertEqual([r["symbol"] for r in out], ["B", "A"])

    def test_sort_none_pnl_to_bottom_desc(self):
        rows = [
            {"symbol": "A", "pnl": None},
            {"symbol": "B", "pnl": 50.0},
            {"symbol": "C", "pnl": 10.0},
        ]
        out = sort_portfolio_rows(rows, "pnl", True)
        self.assertEqual([r["symbol"] for r in out], ["B", "C", "A"])


if __name__ == "__main__":
    unittest.main()
