"""
截圖辨識 Agent 測試
"""
import base64
import json
import unittest
from unittest.mock import MagicMock, patch

from agents.screenshot_agent import ScreenshotAgent


class TestScreenshotAgentParsing(unittest.TestCase):
    """測試 JSON 解析和資料正規化邏輯（不呼叫真實 API）"""

    def setUp(self):
        self.agent = ScreenshotAgent.__new__(ScreenshotAgent)

    # ── _parse_number ──────────────────────────────────
    def test_parse_number_int(self):
        self.assertEqual(self.agent._parse_number(100), 100.0)

    def test_parse_number_float(self):
        self.assertAlmostEqual(self.agent._parse_number(580.5), 580.5)

    def test_parse_number_string_with_comma(self):
        self.assertEqual(self.agent._parse_number("1,000"), 1000.0)

    def test_parse_number_string_with_dollar(self):
        self.assertAlmostEqual(self.agent._parse_number("$123.45"), 123.45)

    def test_parse_number_empty(self):
        self.assertEqual(self.agent._parse_number(""), 0.0)

    def test_parse_number_invalid(self):
        self.assertEqual(self.agent._parse_number("N/A"), 0.0)

    # ── _normalize_stocks ──────────────────────────────
    def test_normalize_tw_stock_appends_tw(self):
        stocks = [{"symbol": "2330", "name": "台積電", "shares": 100, "avg_price": 580}]
        result = self.agent._normalize_stocks(stocks)
        self.assertEqual(result[0]["symbol"], "2330.TW")

    def test_normalize_us_stock_no_tw(self):
        stocks = [{"symbol": "AAPL", "name": "Apple", "shares": 10, "avg_price": 190}]
        result = self.agent._normalize_stocks(stocks)
        self.assertEqual(result[0]["symbol"], "AAPL")

    def test_normalize_already_has_tw(self):
        stocks = [{"symbol": "2330.TW", "name": "台積電", "shares": 100, "avg_price": 580}]
        result = self.agent._normalize_stocks(stocks)
        self.assertEqual(result[0]["symbol"], "2330.TW")

    def test_normalize_skips_empty_symbol(self):
        stocks = [{"symbol": "", "name": "unknown", "shares": 0, "avg_price": 0}]
        result = self.agent._normalize_stocks(stocks)
        self.assertEqual(result, [])

    def test_normalize_cleans_number_strings(self):
        stocks = [{"symbol": "NVDA", "shares": "500", "avg_price": "1,000.50"}]
        result = self.agent._normalize_stocks(stocks)
        self.assertEqual(result[0]["shares"], 500.0)
        self.assertAlmostEqual(result[0]["avg_price"], 1000.50)

    # ── _parse_response ────────────────────────────────
    def test_parse_valid_json(self):
        raw = json.dumps({
            "stocks": [{"symbol": "2330.TW", "name": "台積電", "shares": 100, "avg_price": 580}],
            "confidence": 0.95,
            "note": "辨識成功"
        })
        result = self.agent._parse_response(raw)
        self.assertEqual(len(result["stocks"]), 1)
        self.assertAlmostEqual(result["confidence"], 0.95)

    def test_parse_json_embedded_in_text(self):
        raw = 'AI說明文字\n{"stocks": [], "confidence": 0, "note": "找不到"}\n其他說明'
        result = self.agent._parse_response(raw)
        self.assertEqual(result["stocks"], [])

    def test_parse_invalid_json_returns_empty(self):
        result = self.agent._parse_response("這不是 JSON 格式的文字")
        self.assertEqual(result["stocks"], [])
        self.assertEqual(result["confidence"], 0)

    # ── format_preview ─────────────────────────────────
    def test_format_preview_empty(self):
        preview = self.agent.format_preview([])
        self.assertIn("未辨識", preview)

    def test_format_preview_with_stocks(self):
        stocks = [
            {"symbol": "2330.TW", "name": "台積電", "shares": 100, "avg_price": 580.0},
            {"symbol": "AAPL", "name": "Apple", "shares": 10, "avg_price": 195.5},
        ]
        preview = self.agent.format_preview(stocks)
        self.assertIn("2330.TW", preview)
        self.assertIn("AAPL", preview)
        self.assertIn("100", preview)


class TestScreenshotAgentVision(unittest.TestCase):
    """測試 Claude Vision API 呼叫（Mock）"""

    @patch("agents.screenshot_agent.anthropic.Anthropic")
    def test_analyze_success(self, mock_anthropic_cls):
        # 模擬 Claude 回傳 JSON
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=json.dumps({
            "stocks": [{"symbol": "2330.TW", "name": "台積電", "shares": 100, "avg_price": 580}],
            "confidence": 0.9,
            "note": ""
        }))]
        mock_client.messages.create.return_value = mock_msg

        agent = ScreenshotAgent()
        result = agent.analyze(b"fake_image_bytes")

        self.assertEqual(len(result["stocks"]), 1)
        self.assertEqual(result["stocks"][0]["symbol"], "2330.TW")
        self.assertAlmostEqual(result["confidence"], 0.9)

    @patch("agents.screenshot_agent.anthropic.Anthropic")
    def test_analyze_api_failure(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API 連線失敗")

        agent = ScreenshotAgent()
        result = agent.analyze(b"fake_image_bytes")

        self.assertEqual(result["stocks"], [])
        self.assertEqual(result["confidence"], 0)
        self.assertIn("API 連線失敗", result["note"])

    @patch("agents.screenshot_agent.anthropic.Anthropic")
    def test_analyze_no_stocks_found(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=json.dumps({
            "stocks": [],
            "confidence": 0,
            "note": "無法辨識：請上傳持倉頁面截圖"
        }))]
        mock_client.messages.create.return_value = mock_msg

        agent = ScreenshotAgent()
        result = agent.analyze(b"not_a_stock_image")

        self.assertEqual(result["stocks"], [])
        self.assertIn("無法辨識", result["note"])


if __name__ == "__main__":
    unittest.main()
