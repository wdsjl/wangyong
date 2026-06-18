"""A 股行情数据获取。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from smart_stock import eastmoney
from smart_stock.network import format_fetch_error, without_system_proxy
from smart_stock.sample_data import generate_demo_bars, generate_demo_intraday, get_demo_name, search_demo_stocks
from smart_stock.models import AnalysisResult

try:
    import akshare as ak
except ImportError:  # pragma: no cover
    ak = None


COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "换手率": "turnover",
}


class DataFetchError(RuntimeError):
    """行情获取失败。"""


def normalize_code(code: str) -> str:
    """标准化股票代码，仅保留数字部分。"""
    return "".join(ch for ch in code.strip() if ch.isdigit())


def _normalize_bars(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = ["open", "close", "high", "low", "volume", "amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def _fetch_via_akshare(code: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    if ak is None:
        raise DataFetchError("未安装 akshare，请执行 pip install akshare")

    with without_system_proxy():
        return ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq",
        )


def search_stock(keyword: str, limit: int = 10, demo: bool = False) -> pd.DataFrame:
    """按代码或名称搜索 A 股。"""
    keyword = keyword.strip()
    if demo:
        return search_demo_stocks(keyword, limit=limit)

    try:
        return eastmoney.suggest_stocks(keyword, limit=limit)
    except Exception as exc:
        if ak is None:
            raise DataFetchError(format_fetch_error(exc)) from exc
        try:
            with without_system_proxy():
                stock_list = ak.stock_info_a_code_name()
        except Exception as ak_exc:
            raise DataFetchError(format_fetch_error(ak_exc)) from ak_exc
        stock_list = stock_list.rename(columns={"code": "代码", "name": "名称"})

        if keyword.isdigit():
            mask = stock_list["代码"].str.contains(keyword)
        else:
            mask = stock_list["名称"].str.contains(keyword, na=False)

        return stock_list[mask].head(limit).reset_index(drop=True)


def get_stock_name(code: str, demo: bool = False) -> str:
    """获取股票名称。"""
    code = normalize_code(code)
    if demo:
        return get_demo_name(code)

    try:
        return eastmoney.get_stock_name(code)
    except Exception:
        try:
            matches = search_stock(code, limit=1, demo=False)
            if not matches.empty:
                return str(matches.iloc[0]["名称"])
        except Exception:
            return code
    return code


def attach_live_spot_price(result: AnalysisResult, code: str, data_source: str) -> AnalysisResult:
    """实盘模式下用东方财富实时报价覆盖顶部展示价格。"""
    if data_source != "live":
        result.price_label = "演示价" if data_source == "demo" else "模拟价"
        return result

    try:
        spot = eastmoney.fetch_spot_quote(code)
    except Exception:
        result.price_label = "收盘价"
        return result

    if spot is None:
        result.price_label = "收盘价"
        return result

    result.latest_price = spot.price
    result.price_label = "实时价"
    result.latest_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if spot.name:
        result.name = spot.name
    return result


def fetch_daily_bars(code: str, days: int = 180, demo: bool = False) -> pd.DataFrame:
    """获取 A 股日线行情（前复权）。"""
    code = normalize_code(code)
    if demo:
        return generate_demo_bars(code, days=days)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=max(days * 2, 365))

    errors: list[Exception] = []
    for fetcher in (
        lambda: eastmoney.fetch_daily_bars(code, start_date, end_date, days),
        lambda: _fetch_via_akshare(code, start_date, end_date),
    ):
        try:
            raw = fetcher()
            if raw.empty:
                raise DataFetchError(f"未获取到股票 {code} 的行情数据")
            df = _normalize_bars(raw)
            return df.tail(days).reset_index(drop=True)
        except Exception as exc:
            errors.append(exc)

    raise DataFetchError(format_fetch_error(errors[-1])) from errors[-1]


def fetch_intraday_bars_safe(
    code: str,
    period: str = "5m",
    bars: int = 48,
    demo: bool = False,
    allow_fallback: bool = False,
) -> tuple[pd.DataFrame, str]:
    """获取分时 K 线，必要时回退演示数据。"""
    normalized = normalize_code(code)
    if demo:
        return generate_demo_intraday(normalized, period=period, bars=bars), "demo"
    try:
        raw = eastmoney.fetch_intraday_bars(normalized, period=period, bars=bars)
        if raw.empty:
            raise DataFetchError(f"未获取到股票 {code} 的分时数据")
        df = _normalize_bars(raw)
        return df, "live"
    except Exception:
        if allow_fallback:
            return generate_demo_intraday(normalized, period=period, bars=bars), "demo_fallback"
        raise


def fetch_daily_bars_safe(
    code: str,
    days: int = 180,
    demo: bool = False,
    allow_fallback: bool = False,
) -> tuple[pd.DataFrame, str]:
    """获取行情，必要时回退到演示数据。

    返回 (dataframe, data_source)，data_source 为 live / demo / demo_fallback。
    """
    if demo:
        return generate_demo_bars(code, days=days), "demo"
    try:
        return fetch_daily_bars(code, days=days, demo=False), "live"
    except Exception:
        if allow_fallback:
            return generate_demo_bars(code, days=days), "demo_fallback"
        raise
