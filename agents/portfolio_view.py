"""
持股清單顯示：補上股票名稱、持有成本、參考損益、資料更新日，並支援排序。
股價為 yfinance 即時／盤後參考，非成交價。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

SORT_ALIASES: dict[str, str] = {
    "代碼": "symbol",
    "symbol": "symbol",
    "名稱": "name",
    "name": "name",
    "股數": "shares",
    "shares": "shares",
    "均價": "avg_price",
    "avg": "avg_price",
    "avg_price": "avg_price",
    "成本": "cost",
    "持有成本": "cost",
    "cost": "cost",
    "獲利": "pnl",
    "損益": "pnl",
    "pnl": "pnl",
    "報酬率": "pnl_pct",
    "獲利%": "pnl_pct",
    "pnl_pct": "pnl_pct",
    "更新": "updated_at",
    "日期": "updated_at",
    "updated": "updated_at",
    "updated_at": "updated_at",
}

SORT_KEYS = frozenset(SORT_ALIASES.values())


def _normalize_sort_token(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("依"):
        s = s[1:].strip()
    return s


def parse_list_sort_args(args: list[str]) -> tuple[str, bool]:
    """
    解析「查看持股」後方參數。
    例：[] → symbol, False
        ["股數", "逆序"] → shares, True
        ["依獲利"] → pnl, False
    """
    tokens = [a.strip() for a in args if a and a.strip()]
    reverse = False
    if tokens and tokens[-1] in ("逆序", "desc", "倒序", "降冪"):
        reverse = True
        tokens = tokens[:-1]
    if not tokens:
        return "symbol", reverse
    raw = _normalize_sort_token(tokens[0])
    key = SORT_ALIASES.get(raw, SORT_ALIASES.get(raw.lower(), "symbol"))
    if key not in SORT_KEYS:
        key = "symbol"
    return key, reverse


def _quote_symbol(symbol: str) -> tuple[str, float | None]:
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        info = t.info or {}
        name = (
            info.get("shortName")
            or info.get("longName")
            or info.get("symbol")
            or symbol
        )
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None:
            hist = t.history(period="5d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return str(name), float(price) if price is not None else None
    except Exception as e:
        logger.debug("quote %s: %s", symbol, e)
        return symbol, None


def enrich_portfolio_row(stock: dict) -> dict[str, Any]:
    """合併 DB 持股與即時報價欄位。"""
    symbol = stock.get("symbol", "")
    shares = float(stock.get("shares") or 0)
    avg = float(stock.get("avg_price") or 0)
    name, last = _quote_symbol(symbol)
    cost = shares * avg
    row = {
        **stock,
        "display_name": name,
        "last_price": last,
        "cost_basis": cost,
        "market_value": (shares * last) if last is not None else None,
        "pnl": None,
        "pnl_pct": None,
        "quote_asof": datetime.now().isoformat(timespec="seconds"),
    }
    if last is not None and shares and avg is not None:
        row["pnl"] = (last - avg) * shares
        if avg != 0:
            row["pnl_pct"] = (last - avg) / avg * 100.0
        else:
            row["pnl_pct"] = None
    return row


def sort_portfolio_rows(rows: list[dict], sort_key: str, reverse: bool) -> list[dict]:
    """依 sort_key 排序 enrich 後的列。"""

    if sort_key in ("pnl", "pnl_pct"):
        with_val = [r for r in rows if r.get(sort_key) is not None]
        missing = [r for r in rows if r.get(sort_key) is None]
        with_val.sort(key=lambda r: float(r[sort_key]), reverse=reverse)
        return with_val + missing

    def key_fn(r: dict) -> Any:
        if sort_key == "symbol":
            return r.get("symbol") or ""
        if sort_key == "name":
            return (r.get("display_name") or r.get("symbol") or "").lower()
        if sort_key == "shares":
            return float(r.get("shares") or 0)
        if sort_key == "avg_price":
            return float(r.get("avg_price") or 0)
        if sort_key == "cost":
            return float(r.get("cost_basis") or 0)
        if sort_key == "updated_at":
            return r.get("updated_at") or r.get("added_at") or ""
        return r.get("symbol") or ""

    return sorted(rows, key=key_fn, reverse=reverse)


def _fmt_date(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        return iso_str[:10]
    except Exception:
        return "—"


SORT_LABEL_ZH = {
    "symbol": "代碼",
    "name": "名稱",
    "shares": "股數",
    "avg_price": "均價",
    "cost": "持有成本",
    "pnl": "損益金額",
    "pnl_pct": "報酬率",
    "updated_at": "更新日",
}


def format_portfolio_lines(
    portfolio: list[dict],
    sort_key: str = "symbol",
    reverse: bool = False,
    max_stocks: int = 22,
) -> str:
    """
    產生持股文字表（LINE / CLI 共用）。
    max_stocks：最多顯示檔數，避免超過 LINE 訊息長度。
    """
    if not portfolio:
        return ""

    enriched = [enrich_portfolio_row(dict(s)) for s in portfolio]
    sorted_rows = sort_portfolio_rows(enriched, sort_key, reverse)

    order_desc = f"依{SORT_LABEL_ZH.get(sort_key, sort_key)}{'↓' if reverse else '↑'}"

    total_cost = sum(float(r.get("cost_basis") or 0) for r in sorted_rows)
    total_pnl = sum(
        float(r["pnl"])
        for r in sorted_rows
        if r.get("pnl") is not None
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        f"📊 您的持股（{order_desc}）",
        f"股價擷取：{now}（參考值）\n",
    ]

    display_rows = sorted_rows[:max_stocks]
    if len(sorted_rows) > max_stocks:
        lines.append(f"（以下顯示前 {max_stocks} 檔，共 {len(sorted_rows)} 檔；完整清單請用 CLI）\n")

    for i, r in enumerate(display_rows, 1):
        sym = r.get("symbol", "")
        name = r.get("display_name", sym)
        sh = float(r.get("shares") or 0)
        avg = float(r.get("avg_price") or 0)
        cost = float(r.get("cost_basis") or 0)
        lp = r.get("last_price")
        pnl = r.get("pnl")
        pnl_pct = r.get("pnl_pct")
        upd = _fmt_date(r.get("updated_at") or r.get("added_at"))

        lines.append(f"{i}. {name}")
        lines.append(f"   {sym}")
        lines.append(
            f"   股數 {sh:g}　均價 {avg:,.2f}　持有成本 {cost:,.0f}"
        )
        if lp is not None:
            pnl_s = f"{pnl:+,.0f}" if pnl is not None else "—"
            pct_s = f"{pnl_pct:+.2f}%" if pnl_pct is not None else "—"
            mv = r.get("market_value")
            mv_s = f"{mv:,.0f}" if mv is not None else "—"
            lines.append(
                f"   現價 {lp:,.2f}　市值 {mv_s}　損益 {pnl_s}（{pct_s}）"
            )
        else:
            lines.append("   現價 —（無法取得報價）")
        lines.append(f"   資料更新日 {upd}\n")

    lines.append("─" * 28)
    lines.append(f"總持有成本　{total_cost:,.0f}")
    if any(r.get("pnl") is not None for r in sorted_rows):
        lines.append(f"總損益（參考）　{total_pnl:+,.0f}")
    lines.append("\n排序：查看持股 [代碼|股數|成本|獲利|獲利%|名稱|更新] [逆序]")
    return "\n".join(lines)
