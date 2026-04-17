"""
🔍 ValidationAgent 單元測試
"""
import unittest
from unittest.mock import patch

from agents.validation_agent import ValidationAgent


def _make_candidate(symbol="TEST", tech=80, sent=0.72, risk=85,
                    bt=70, win=0.65, stop_pct=5.0, rr=2.5,
                    liq=True, signals=None):
    return {
        "symbol":           symbol,
        "close":            100.0,
        "technical_score":  tech,
        "sentiment_score":  sent,
        "risk_score":       risk,
        "backtest_score":   bt,
        "win_rate":         win,
        "stop_loss_pct":    stop_pct,
        "risk_reward_ratio": rr,
        "liquidity_ok":     liq,
        "signals":          signals or ["MACD 金叉", "成交量暴增 3.0x"],
    }


class TestValidationAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ValidationAgent()

    # ── Check 1 ────────────────────────────────────────
    def test_check1_passes_consistent_signals(self):
        c = _make_candidate(tech=80, bt=75, sent=0.70)
        ok, issues = self.agent._check1_signal_consistency(c)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_check1_fails_when_tech_high_bt_low(self):
        c = _make_candidate(tech=80, bt=30)
        ok, issues = self.agent._check1_signal_consistency(c)
        self.assertFalse(ok)
        self.assertTrue(len(issues) > 0)

    def test_check1_fails_sentiment_contradiction(self):
        c = _make_candidate(tech=75, sent=0.25)
        ok, issues = self.agent._check1_signal_consistency(c)
        self.assertFalse(ok)

    # ── Check 2 ────────────────────────────────────────
    def test_check2_passes_compliant(self):
        c = _make_candidate(stop_pct=5.0, rr=2.5, liq=True, win=0.60)
        ok, issues = self.agent._check2_risk_compliance(c)
        self.assertTrue(ok)

    def test_check2_fails_stop_too_wide(self):
        c = _make_candidate(stop_pct=10.0)
        ok, issues = self.agent._check2_risk_compliance(c)
        self.assertFalse(ok)

    def test_check2_fails_low_rr(self):
        c = _make_candidate(rr=1.2)
        ok, issues = self.agent._check2_risk_compliance(c)
        self.assertFalse(ok)

    def test_check2_fails_illiquid(self):
        c = _make_candidate(liq=False)
        ok, issues = self.agent._check2_risk_compliance(c)
        self.assertFalse(ok)

    def test_check2_blocks_blacklist(self):
        c = _make_candidate(symbol="BBBY")
        ok, issues = self.agent._check2_risk_compliance(c)
        self.assertFalse(ok)
        self.assertTrue(any("黑名單" in i for i in issues))

    # ── Check 3（Mock Claude）─────────────────────────
    @patch.object(ValidationAgent, "_check3_bear_case", return_value=(True, ["無重大空方風險"], "LOW"))
    def test_full_validation_passes(self, mock_bear):
        c = _make_candidate()
        results = self.agent.run([c])
        self.assertTrue(results[0].passed)

    @patch.object(ValidationAgent, "_check3_bear_case", return_value=(False, ["嚴重空方因素"], "HIGH"))
    def test_full_validation_fails_high_severity(self, mock_bear):
        c = _make_candidate()
        results = self.agent.run([c])
        self.assertFalse(results[0].passed)

    # ── 信心分數 ───────────────────────────────────────
    def test_confidence_in_range(self):
        c = _make_candidate()
        with patch.object(self.agent, "_check3_bear_case",
                          return_value=(True, [], "LOW")):
            results = self.agent.run([c])
            conf = results[0].confidence_score
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_low_confidence_rejected(self):
        """各面向均低分時，信心分數應低於門檻而被否決"""
        c = _make_candidate(tech=30, sent=0.30, risk=30, bt=30, win=0.40)
        with patch.object(self.agent, "_check3_bear_case",
                          return_value=(True, [], "LOW")):
            results = self.agent.run([c])
            self.assertFalse(results[0].passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
