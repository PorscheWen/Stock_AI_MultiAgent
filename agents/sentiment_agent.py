"""
🧬 SENTIMENT AGENT
情緒分析 Agent
- Claude API 新聞情緒分析
- 社群熱度爬蟲（PTT、Reddit）
- 法人籌碼動向分析
- 重大公告偵測（財報、併購）
輸出：情緒評分 0~1
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
import anthropic
import requests
from bs4 import BeautifulSoup

from config.settings import ANTHROPIC_API_KEY, CLAUDE_HAIKU

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


@dataclass
class SentimentResult:
    symbol: str
    sentiment_score: float        # 0~1，越高越正面
    news_score: float
    social_score: float
    institutional_score: float
    major_events: list = field(default_factory=list)
    summary: str = ""


class SentimentAgent:
    """情緒分析 Agent"""

    def __init__(self):
        self.name = "SentimentAgent"

    # ── 公開介面 ───────────────────────────────────────
    def run(self, symbols: list[str]) -> dict[str, SentimentResult]:
        results = {}
        for symbol in symbols:
            try:
                result = self._analyze(symbol)
                results[symbol] = result
                logger.info(f"[Sentiment] {symbol} 情緒分={result.sentiment_score:.2f}")
            except Exception as e:
                logger.warning(f"[Sentiment] {symbol} 分析失敗: {e}")
                results[symbol] = SentimentResult(
                    symbol=symbol,
                    sentiment_score=0.5,
                    news_score=0.5,
                    social_score=0.5,
                    institutional_score=0.5,
                )
        return results

    # ── 內部方法 ───────────────────────────────────────
    def _fetch_news_headlines(self, symbol: str) -> list[str]:
        """從 Yahoo Finance RSS 抓取新聞標題"""
        headlines = []
        try:
            # 去除台股 .TW 後綴
            sym = symbol.replace(".TW", "")
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"
            resp = requests.get(url, timeout=8)
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")[:10]
            headlines = [item.find("title").text for item in items if item.find("title")]
        except Exception as e:
            logger.debug(f"新聞抓取失敗 {symbol}: {e}")
        return headlines

    def _fetch_reddit_sentiment(self, symbol: str) -> float:
        """抓取 Reddit r/stocks r/wallstreetbets 熱度（簡化版）"""
        try:
            sym = symbol.replace(".TW", "")
            url = f"https://www.reddit.com/search.json?q={sym}&sort=new&limit=25&t=day"
            headers = {"User-Agent": "StockAI/1.0"}
            resp = requests.get(url, headers=headers, timeout=8)
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            if not posts:
                return 0.5
            scores = []
            for p in posts:
                ups  = p["data"].get("ups", 0)
                ratio = p["data"].get("upvote_ratio", 0.5)
                scores.append(ratio)
            return float(sum(scores) / len(scores)) if scores else 0.5
        except Exception:
            return 0.5

    def _claude_sentiment(self, symbol: str, headlines: list[str]) -> tuple[float, list[str], str]:
        """用 Claude Haiku 分析新聞情緒，開啟 prompt cache"""
        if not headlines:
            return 0.5, [], "無新聞數據"

        news_text = "\n".join(f"- {h}" for h in headlines)
        prompt = f"""以下是 {symbol} 的最新新聞標題，請分析整體市場情緒。

新聞標題：
{news_text}

請回答：
1. 情緒分數（0.0=極度悲觀 ~ 1.0=極度樂觀），精確到小數點後兩位
2. 重大事件清單（財報、併購、法律、產品發布等），用逗號分隔，沒有則填「無」
3. 一句話摘要

格式（嚴格遵守）：
SCORE: <數字>
EVENTS: <事件列表或「無」>
SUMMARY: <摘要>"""

        try:
            resp = client.messages.create(
                model=CLAUDE_HAIKU,
                max_tokens=256,
                system=[{
                    "type": "text",
                    "text": "你是專業的股票市場情緒分析師，只輸出指定格式，不添加任何多餘內容。",
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()

            score = 0.5
            events = []
            summary = ""

            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("SCORE:"):
                    try:
                        score = float(line.split(":", 1)[1].strip())
                        score = max(0.0, min(1.0, score))
                    except ValueError:
                        pass
                elif line.startswith("EVENTS:"):
                    raw = line.split(":", 1)[1].strip()
                    if raw != "無":
                        events = [e.strip() for e in raw.split(",") if e.strip()]
                elif line.startswith("SUMMARY:"):
                    summary = line.split(":", 1)[1].strip()

            return score, events, summary

        except Exception as e:
            logger.warning(f"Claude 情緒分析失敗 {symbol}: {e}")
            return 0.5, [], "API 呼叫失敗"

    def _analyze(self, symbol: str) -> SentimentResult:
        headlines = self._fetch_news_headlines(symbol)
        news_score, events, summary = self._claude_sentiment(symbol, headlines)

        # 社群熱度（Reddit）
        social_score = self._fetch_reddit_sentiment(symbol)

        # 法人籌碼：簡化為中立值（需接 Finviz/TEJ 等 API）
        institutional_score = 0.5

        # 加權合成
        composite = (
            news_score          * 0.50 +
            social_score        * 0.30 +
            institutional_score * 0.20
        )

        return SentimentResult(
            symbol=symbol,
            sentiment_score=round(composite, 4),
            news_score=round(news_score, 4),
            social_score=round(social_score, 4),
            institutional_score=round(institutional_score, 4),
            major_events=events,
            summary=summary,
        )
