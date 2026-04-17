"""
🔍 VALIDATION AGENT（獨立驗證）
三重把關機制：
① 信號一致性驗證
② 風控合規性驗證
③ 邏輯反駁驗證（扮演空方）
輸出：通過/否決 + 信心分數
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
import anthropic

from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    CONFIDENCE_THRESHOLD,
    MAX_POSITION_PCT,
    MAX_STOP_LOSS_PCT,
    MIN_RISK_REWARD_RATIO,
    BACKTEST_MIN_WINRATE,
)

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


@dataclass
class ValidationResult:
    symbol: str
    passed: bool                       # 是否通過三重驗證
    confidence_score: float            # 0~1 信心分數
    check1_signal_consistent: bool     # ① 信號一致性
    check2_risk_compliant: bool        # ② 風控合規
    check3_bear_case_cleared: bool     # ③ 空方邏輯
    rejection_reasons: list = field(default_factory=list)
    bear_arguments: list  = field(default_factory=list)
    final_verdict: str = ""


class ValidationAgent:
    """三重獨立驗證 Agent"""

    BLACKLIST = {
        # 已知地雷股、下市股、重大違規股（可定期更新）
        "BBBY", "SVMK", "FXCM",
    }

    def __init__(self):
        self.name = "ValidationAgent"

    # ── 公開介面 ───────────────────────────────────────
    def run(self, candidates: list[dict]) -> list[ValidationResult]:
        """
        candidates: 每個 dict 包含
          symbol, technical_score, sentiment_score, risk_score,
          backtest_score, win_rate, stop_loss_pct, risk_reward_ratio,
          liquidity_ok, signals
        """
        results = []
        for c in candidates:
            result = self._validate(c)
            status = "✅ 通過" if result.passed else "❌ 否決"
            logger.info(
                f"[Validation] {c['symbol']} {status} "
                f"信心={result.confidence_score:.0%}"
            )
            results.append(result)
        return results

    # ── 三重驗證 ───────────────────────────────────────
    def _check1_signal_consistency(self, c: dict) -> tuple[bool, list[str]]:
        """① 信號一致性驗證"""
        issues = []

        # 技術面 vs 回測是否矛盾
        if c["technical_score"] >= 75 and c["backtest_score"] < 40:
            issues.append("技術面強但回測勝率低，信號矛盾")

        # 情緒面與技術面是否吻合
        if c["technical_score"] >= 70 and c["sentiment_score"] < 0.35:
            issues.append("技術面看多但情緒面極度悲觀")

        # 信號強度門檻
        avg_score = (c["technical_score"] + c["backtest_score"]) / 2
        if avg_score < 55:
            issues.append(f"綜合信號強度不足（平均 {avg_score:.1f}/100）")

        return len(issues) == 0, issues

    def _check2_risk_compliance(self, c: dict) -> tuple[bool, list[str]]:
        """② 風控合規性驗證"""
        issues = []

        # 停損距離合理性
        if c.get("stop_loss_pct", 0) > MAX_STOP_LOSS_PCT * 100:
            issues.append(
                f"停損距離 {c['stop_loss_pct']:.1f}% 超過上限 {MAX_STOP_LOSS_PCT*100:.0f}%"
            )

        # 風報比
        if c.get("risk_reward_ratio", 0) < MIN_RISK_REWARD_RATIO:
            issues.append(
                f"風報比 {c['risk_reward_ratio']:.1f} 低於要求 {MIN_RISK_REWARD_RATIO}"
            )

        # 流動性
        if not c.get("liquidity_ok", True):
            issues.append("流動性不足，日均量未達門檻")

        # 黑名單過濾
        if c["symbol"] in self.BLACKLIST:
            issues.append(f"{c['symbol']} 在黑名單中")

        # 回測勝率
        if c.get("win_rate", 1.0) < BACKTEST_MIN_WINRATE:
            issues.append(
                f"歷史勝率 {c['win_rate']:.1%} 低於最低要求 {BACKTEST_MIN_WINRATE:.0%}"
            )

        return len(issues) == 0, issues

    def _check3_bear_case(self, c: dict) -> tuple[bool, list[str], str]:
        """③ 邏輯反駁驗證（用 Claude 扮演空方）"""
        prompt = f"""你是一位嚴格的做空分析師，對 {c['symbol']} 的多方信號提出反向論點。

多方數據：
- 技術評分：{c['technical_score']}/100
- 情緒評分：{c['sentiment_score']:.2f}/1.0
- 風控評分：{c['risk_score']}/100
- 回測勝率：{c.get('win_rate', 0):.1%}
- 技術信號：{', '.join(c.get('signals', []))}

請從以下角度提出 3 個最有力的做空/反向論點：
1. 技術面陷阱
2. 總體市場風險
3. 個股基本面疑慮

格式：
BEAR1: <論點>
BEAR2: <論點>
BEAR3: <論點>
SEVERITY: <LOW/MEDIUM/HIGH>（整體空方力道）"""

        try:
            resp = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=400,
                system=[{
                    "type": "text",
                    "text": "你是獨立驗證的空方分析師，職責是找出多方邏輯的漏洞。只輸出指定格式。",
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()

            bears    = []
            severity = "LOW"
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith(("BEAR1:", "BEAR2:", "BEAR3:")):
                    bears.append(line.split(":", 1)[1].strip())
                elif line.startswith("SEVERITY:"):
                    severity = line.split(":", 1)[1].strip().upper()

            # HIGH 嚴重度則不通過
            passed = severity != "HIGH"
            return passed, bears, severity

        except Exception as e:
            logger.warning(f"[Validation] Claude 反駁分析失敗 {c['symbol']}: {e}")
            return True, [], "LOW"

    # ── 計算信心分數 ───────────────────────────────────
    def _calc_confidence(self, c: dict, issues1: list, issues2: list,
                          bear_severity: str) -> float:
        score = (
            c["technical_score"]  * 0.25 +
            c["sentiment_score"]  * 100 * 0.20 +
            c["risk_score"]       * 0.25 +
            c.get("backtest_score", 50) * 0.30
        ) / 100  # 正規化到 0~1

        # 扣分
        score -= len(issues1) * 0.05
        score -= len(issues2) * 0.08
        if bear_severity == "HIGH":
            score -= 0.15
        elif bear_severity == "MEDIUM":
            score -= 0.08

        return max(0.0, min(1.0, round(score, 4)))

    # ── 主驗證邏輯 ─────────────────────────────────────
    def _validate(self, c: dict) -> ValidationResult:
        ok1, issues1 = self._check1_signal_consistency(c)
        ok2, issues2 = self._check2_risk_compliance(c)
        ok3, bears, severity = self._check3_bear_case(c)

        confidence = self._calc_confidence(c, issues1, issues2, severity)

        # 信心分數低於門檻也否決
        if confidence < CONFIDENCE_THRESHOLD:
            ok3 = False
            issues2.append(f"信心分數 {confidence:.0%} 低於門檻 {CONFIDENCE_THRESHOLD:.0%}")

        all_passed = ok1 and ok2 and ok3
        all_issues = issues1 + issues2

        if all_passed:
            verdict = f"通過三重驗證，信心分數 {confidence:.0%}，建議納入觀察清單"
        else:
            verdict = f"驗證否決，原因：{'; '.join(all_issues[:2]) if all_issues else '空方力道過強'}"

        return ValidationResult(
            symbol=c["symbol"],
            passed=all_passed,
            confidence_score=confidence,
            check1_signal_consistent=ok1,
            check2_risk_compliant=ok2,
            check3_bear_case_cleared=ok3,
            rejection_reasons=all_issues,
            bear_arguments=bears,
            final_verdict=verdict,
        )
