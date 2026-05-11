"""
💾 PortfolioDB 單元測試
"""
import unittest
import tempfile
import shutil
import json
import csv
from pathlib import Path
from database.portfolio_db import PortfolioDB


class TestPortfolioDB(unittest.TestCase):

    def setUp(self):
        """設定測試環境，使用臨時目錄"""
        self.test_dir = tempfile.mkdtemp()
        self.original_db_dir = Path("database/data")
        
        # 暫時修改 DB 路徑為測試目錄
        import database.portfolio_db as db_module
        db_module.DB_DIR = Path(self.test_dir)
        db_module.DB_FILE = Path(self.test_dir) / "portfolios.json"
        
        self.db = PortfolioDB()
        self.test_user = "test_user_123"

    def tearDown(self):
        """清理測試環境"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ── 新增持股 ───────────────────────────────────────
    def test_add_stock(self):
        """測試新增持股"""
        result = self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580)
        self.assertTrue(result)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["symbol"], "2330.TW")
        self.assertEqual(portfolio[0]["shares"], 100)

    def test_add_multiple_stocks(self):
        """測試新增多檔持股"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580)
        self.db.add_stock(self.test_user, "AAPL", shares=50, avg_price=185)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 2)
        
        symbols = [s["symbol"] for s in portfolio]
        self.assertIn("2330.TW", symbols)
        self.assertIn("AAPL", symbols)

    # ── 移除持股 ───────────────────────────────────────
    def test_remove_stock(self):
        """測試移除持股"""
        self.db.add_stock(self.test_user, "2330.TW")
        
        result = self.db.remove_stock(self.test_user, "2330.TW")
        self.assertTrue(result)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 0)

    def test_remove_nonexistent_stock(self):
        """測試移除不存在的持股"""
        result = self.db.remove_stock(self.test_user, "INVALID")
        self.assertFalse(result)

    # ── 查詢持股 ───────────────────────────────────────
    def test_get_portfolio_empty(self):
        """測試取得空持股清單"""
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 0)
        self.assertIsInstance(portfolio, list)

    def test_get_stock(self):
        """測試取得特定持股"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580)
        
        stock = self.db.get_stock(self.test_user, "2330.TW")
        self.assertIsNotNone(stock)
        self.assertEqual(stock["symbol"], "2330.TW")
        self.assertEqual(stock["shares"], 100)

    def test_get_nonexistent_stock(self):
        """測試取得不存在的持股"""
        stock = self.db.get_stock(self.test_user, "INVALID")
        self.assertIsNone(stock)

    # ── 取得代碼列表 ───────────────────────────────────
    def test_get_all_symbols(self):
        """測試取得所有持股代碼"""
        self.db.add_stock(self.test_user, "2330.TW")
        self.db.add_stock(self.test_user, "AAPL")
        self.db.add_stock(self.test_user, "NVDA")
        
        symbols = self.db.get_all_symbols(self.test_user)
        self.assertEqual(len(symbols), 3)
        self.assertIn("2330.TW", symbols)
        self.assertIn("AAPL", symbols)
        self.assertIn("NVDA", symbols)

    def test_get_all_symbols_empty(self):
        """測試空持股的代碼列表"""
        symbols = self.db.get_all_symbols(self.test_user)
        self.assertEqual(len(symbols), 0)

    # ── 清空持股 ───────────────────────────────────────
    def test_clear_portfolio(self):
        """測試清空持股"""
        self.db.add_stock(self.test_user, "2330.TW")
        self.db.add_stock(self.test_user, "AAPL")
        
        result = self.db.clear_portfolio(self.test_user)
        self.assertTrue(result)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 0)

    # ── 更新持股 ───────────────────────────────────────
    def test_update_stock(self):
        """測試更新持股資訊"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580)
        
        result = self.db.update_stock(self.test_user, "2330.TW", shares=150, avg_price=590)
        self.assertTrue(result)
        
        stock = self.db.get_stock(self.test_user, "2330.TW")
        self.assertEqual(stock["shares"], 150)
        self.assertEqual(stock["avg_price"], 590)

    def test_update_nonexistent_stock(self):
        """測試更新不存在的持股"""
        result = self.db.update_stock(self.test_user, "INVALID", shares=100)
        self.assertFalse(result)

    # ── 多用戶支援 ─────────────────────────────────────
    def test_multiple_users(self):
        """測試多用戶獨立持股"""
        user1 = "user_1"
        user2 = "user_2"
        
        self.db.add_stock(user1, "2330.TW")
        self.db.add_stock(user2, "AAPL")
        
        portfolio1 = self.db.get_portfolio(user1)
        portfolio2 = self.db.get_portfolio(user2)
        
        self.assertEqual(len(portfolio1), 1)
        self.assertEqual(len(portfolio2), 1)
        self.assertEqual(portfolio1[0]["symbol"], "2330.TW")
        self.assertEqual(portfolio2[0]["symbol"], "AAPL")

    # ── 資料持久化 ─────────────────────────────────────
    def test_data_persistence(self):
        """測試資料持久化（重新載入後仍存在）"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100)
        
        # 建立新的 DB 實例（模擬重啟）
        new_db = PortfolioDB()
        portfolio = new_db.get_portfolio(self.test_user)
        
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]["symbol"], "2330.TW")

    # ── 匯入/匯出功能 ───────────────────────────────────
    def test_import_from_csv(self):
        """測試從 CSV 匯入"""
        # 建立測試 CSV
        csv_file = Path(self.test_dir) / "test.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['symbol', 'shares', 'avg_price', 'note'])
            writer.writeheader()
            writer.writerow({'symbol': '2330.TW', 'shares': 100, 'avg_price': 580, 'note': '台積電'})
            writer.writerow({'symbol': 'AAPL', 'shares': 50, 'avg_price': 185, 'note': '蘋果'})
        
        result = self.db.import_from_csv(self.test_user, str(csv_file))
        
        self.assertEqual(result['success'], 2)
        self.assertEqual(result['failed'], 0)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 2)
    
    def test_import_from_json(self):
        """測試從 JSON 匯入"""
        # 建立測試 JSON
        json_file = Path(self.test_dir) / "test.json"
        data = [
            {'symbol': '2330.TW', 'shares': 100, 'avg_price': 580, 'note': '台積電'},
            {'symbol': 'AAPL', 'shares': 50, 'avg_price': 185, 'note': '蘋果'}
        ]
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        
        result = self.db.import_from_json(self.test_user, str(json_file))
        
        self.assertEqual(result['success'], 2)
        self.assertEqual(result['failed'], 0)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 2)
    
    def test_import_with_clear_existing(self):
        """測試匯入時清空現有資料"""
        # 先新增一些持股
        self.db.add_stock(self.test_user, "OLD.TW")
        
        # 建立測試 CSV
        csv_file = Path(self.test_dir) / "test.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['symbol', 'shares', 'avg_price', 'note'])
            writer.writeheader()
            writer.writerow({'symbol': '2330.TW', 'shares': 100, 'avg_price': 580, 'note': '台積電'})
        
        # 匯入並清空
        result = self.db.import_from_csv(self.test_user, str(csv_file), clear_existing=True)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 1)
        self.assertEqual(portfolio[0]['symbol'], '2330.TW')
    
    def test_export_to_csv(self):
        """測試匯出到 CSV"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580, note="台積電")
        self.db.add_stock(self.test_user, "AAPL", shares=50, avg_price=185, note="蘋果")
        
        csv_file = Path(self.test_dir) / "export.csv"
        result = self.db.export_to_csv(self.test_user, str(csv_file))
        
        self.assertTrue(result)
        self.assertTrue(csv_file.exists())
        
        # 驗證匯出內容
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['symbol'], '2330.TW')
    
    def test_export_to_json(self):
        """測試匯出到 JSON"""
        self.db.add_stock(self.test_user, "2330.TW", shares=100, avg_price=580, note="台積電")
        self.db.add_stock(self.test_user, "AAPL", shares=50, avg_price=185, note="蘋果")
        
        json_file = Path(self.test_dir) / "export.json"
        result = self.db.export_to_json(self.test_user, str(json_file))
        
        self.assertTrue(result)
        self.assertTrue(json_file.exists())
        
        # 驗證匯出內容
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['symbol'], '2330.TW')
    
    def test_batch_add_stocks(self):
        """測試批量新增持股"""
        stocks = [
            {"symbol": "2330.TW", "shares": 100, "avg_price": 580, "note": "台積電"},
            {"symbol": "AAPL", "shares": 50, "avg_price": 185, "note": "蘋果"},
            {"symbol": "NVDA", "shares": 20, "avg_price": 495, "note": "輝達"}
        ]
        
        result = self.db.batch_add_stocks(self.test_user, stocks)
        
        self.assertEqual(result['success'], 3)
        self.assertEqual(result['failed'], 0)
        
        portfolio = self.db.get_portfolio(self.test_user)
        self.assertEqual(len(portfolio), 3)


if __name__ == "__main__":
    unittest.main()
