"""基本面与北向资金数据。"""

from __future__ import annotations

import hashlib

from smart_stock.models import FundamentalSnapshot, NorthboundSnapshot
from smart_stock.network import direct_http_get_json


def _is_northbound_eligible(code: str) -> bool:
    digits = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    return digits.startswith(("6", "0", "3"))


def fetch_fundamental_snapshot(code: str, *, demo: bool = False) -> FundamentalSnapshot:
    normalized = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    if demo:
        seed = int(hashlib.md5(normalized.encode()).hexdigest()[:6], 16)
        pe = 10 + seed % 40
        pb = 1 + (seed % 80) / 10
        roe = 5 + seed % 25
        return FundamentalSnapshot(
            pe_ttm=float(pe),
            pb=round(pb, 2),
            roe=round(roe, 2),
            valuation_label=_valuation_label(pe, pb),
            source="demo",
        )

    try:
        from smart_stock.eastmoney import to_secid

        payload = direct_http_get_json(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={
                "fltt": "2",
                "invt": "2",
                "fields": "f57,f58,f162,f167,f173",
                "secid": to_secid(normalized),
            },
        )
        data = payload.get("data") or {}
        pe = _safe_float(data.get("f162"))
        pb = _safe_float(data.get("f167"))
        roe = _safe_float(data.get("f173"))
        if pe is None and pb is None:
            return FundamentalSnapshot(source="unavailable")
        return FundamentalSnapshot(
            pe_ttm=pe,
            pb=pb,
            roe=roe,
            valuation_label=_valuation_label(pe, pb),
            source="live",
        )
    except Exception:
        return FundamentalSnapshot(source="unavailable")


def fetch_northbound_snapshot(code: str, *, demo: bool = False) -> NorthboundSnapshot:
    normalized = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    eligible = _is_northbound_eligible(normalized)
    if not eligible:
        return NorthboundSnapshot(eligible=False, source="not_applicable")

    if demo:
        seed = int(hashlib.md5(normalized.encode()).hexdigest()[:6], 16)
        sign = 1 if seed % 2 == 0 else -1
        return NorthboundSnapshot(
            eligible=True,
            net_inflow_today=float(sign * (seed % 8000 + 500) * 10000),
            holding_ratio=round(2 + seed % 15, 2),
            source="demo",
        )

    try:
        from smart_stock.eastmoney import to_secid

        payload = direct_http_get_json(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={
                "fltt": "2",
                "invt": "2",
                "fields": "f57,f62,f184,f277,f278",
                "secid": to_secid(normalized),
            },
        )
        data = payload.get("data") or {}
        net = _safe_float(data.get("f62"))
        ratio = _safe_float(data.get("f277")) or _safe_float(data.get("f278"))
        if net is None and ratio is None:
            return NorthboundSnapshot(eligible=True, source="unavailable")
        return NorthboundSnapshot(
            eligible=True,
            net_inflow_today=net,
            holding_ratio=ratio,
            source="live",
        )
    except Exception:
        return NorthboundSnapshot(eligible=True, source="unavailable")


def _valuation_label(pe: float | None, pb: float | None) -> str:
    if pe is not None:
        if pe < 0:
            return "亏损"
        if pe < 15:
            return "偏低估"
        if pe > 40:
            return "偏高估"
    if pb is not None:
        if pb < 1.5:
            return "偏低估"
        if pb > 5:
            return "偏高估"
    return "合理"


def _safe_float(value: object) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
