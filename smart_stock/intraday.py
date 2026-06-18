"""分时行情指标。"""

from __future__ import annotations

import pandas as pd

from smart_stock.indicators import add_macd, add_rsi
from smart_stock.models import IntradaySnapshot


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "amount" in result.columns and result["amount"].notna().any():
        cum_amount = result["amount"].cumsum()
        cum_volume = result["volume"].cumsum().replace(0, pd.NA)
        result["vwap"] = cum_amount / cum_volume
    else:
        typical = (result["high"] + result["low"] + result["close"]) / 3
        cum_tp_vol = (typical * result["volume"]).cumsum()
        cum_volume = result["volume"].cumsum().replace(0, pd.NA)
        result["vwap"] = cum_tp_vol / cum_volume
    return result


def enrich_intraday(df: pd.DataFrame) -> pd.DataFrame:
    enriched = add_rsi(df, period=14)
    enriched = add_macd(enriched, fast=12, slow=26, signal=9)
    return add_vwap(enriched)


def latest_intraday_snapshot(df: pd.DataFrame) -> IntradaySnapshot:
    if df.empty:
        return IntradaySnapshot(source="unavailable")

    enriched = enrich_intraday(df)
    row = enriched.iloc[-1]
    price = float(row["close"])
    vwap = row.get("vwap")
    vwap_val = float(vwap) if vwap is not None and not pd.isna(vwap) else None

    if vwap_val is None:
        vwap_signal = "未知"
    elif price > vwap_val * 1.002:
        vwap_signal = "均价上方"
    elif price < vwap_val * 0.998:
        vwap_signal = "均价下方"
    else:
        vwap_signal = "贴近均价"

    rsi = row.get("rsi")
    rsi_val = float(rsi) if rsi is not None and not pd.isna(rsi) else None
    if rsi_val is None:
        momentum = "未知"
    elif rsi_val < 30:
        momentum = "超卖"
    elif rsi_val > 70:
        momentum = "超买"
    elif rsi_val >= 55:
        momentum = "偏强"
    elif rsi_val <= 45:
        momentum = "偏弱"
    else:
        momentum = "中性"

    macd_hist = row.get("macd_hist")
    trend = "震荡"
    if macd_hist is not None and not pd.isna(macd_hist):
        trend = "多头" if float(macd_hist) > 0 else "空头"

    time_label = row["date"].strftime("%H:%M") if hasattr(row["date"], "strftime") else str(row["date"])

    return IntradaySnapshot(
        latest_price=round(price, 2),
        latest_time=time_label,
        rsi=round(rsi_val, 2) if rsi_val is not None else None,
        macd_hist=round(float(macd_hist), 4) if macd_hist is not None and not pd.isna(macd_hist) else None,
        vwap=round(vwap_val, 2) if vwap_val is not None else None,
        vwap_signal=vwap_signal,
        momentum_label=momentum,
        trend_label=trend,
        bar_count=len(df),
        source="computed",
    )


def intraday_to_chart(df: pd.DataFrame) -> dict:
    enriched = enrich_intraday(df)
    times: list[str] = []
    payload: dict = {
        "times": times,
        "close": [],
        "volume": [],
        "vwap": [],
        "rsi": [],
    }
    for _, row in enriched.iterrows():
        if hasattr(row["date"], "strftime"):
            times.append(row["date"].strftime("%H:%M"))
        else:
            times.append(str(row["date"]))
        for key in ("close", "volume", "vwap", "rsi"):
            value = row.get(key)
            if value is None or pd.isna(value):
                payload[key].append(None)
            elif key == "volume":
                payload[key].append(int(value))
            else:
                payload[key].append(round(float(value), 4))
    return payload
