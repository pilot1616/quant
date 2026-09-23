"""
vnpy_akshare — 基于 akshare（新浪数据源）的 vnpy 数据服务插件

设计说明：
- vnpy 通过 `vnpy_{datafeed.name}` 规则加载插件并实例化模块内的 Datafeed 类
  （见 vnpy/trader/datafeed.py 的 get_datafeed）。
- 本插件支持：
  * 国内期货：日线 futures_zh_daily_sina / 1小时线 futures_zh_minute_sina(period=60)
  * A股股票：日线 stock_zh_a_daily / 1小时线 stock_zh_a_minute（新浪源，
    东财源 stock_zh_a_hist 在部分网络环境下不可用，故不依赖）
  * 指数： stock_zh_index_daily（新浪）
- 周期说明：vnpy 4.4 数据库只支持 1分钟(MINUTE)/1小时(HOUR)/日线(DAILY)；
  新浪分钟接口只能取"最近 N 根"（约1023根），无法深度回溯，日线可回溯全部历史。
- 注意：公司代理环境下需清除 http_proxy/https_proxy 环境变量再运行。
"""

from datetime import datetime, timedelta, time as dtime
from typing import Callable

import akshare as ak
import pandas as pd
from pytz import timezone

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import BarData, HistoryRequest, TickData


CHINA_TZ = timezone("Asia/Shanghai")

# 支持期货的交易所
FUTURES_EXCHANGES: set[Exchange] = {
    Exchange.SHFE,
    Exchange.DCE,
    Exchange.CZCE,
    Exchange.CFFEX,
    Exchange.INE,
    Exchange.GFEX,
}

# 支持股票/指数的交易所
STOCK_EXCHANGES: set[Exchange] = {
    Exchange.SSE,
    Exchange.SZSE,
}

# vnpy 4.4 的 Interval 只有 MINUTE/HOUR/DAILY/WEEKLY/TICK。
# 新浪分钟接口支持 1/5/15/30/60 分钟，但 vnpy 数据库只认 MINUTE(1m)/HOUR(1h)。
# 为兼容两者：1分钟 -> MINUTE，60分钟 -> HOUR，其余周期（5/15/30分钟）
# 新浪虽可取，但 vnpy 存储不了对应周期，同样不支持，避免下载后无法入库。

# 新浪期货分钟周期映射
FUTURES_PERIOD_MAP: dict[Interval, str] = {
    Interval.MINUTE: "1",
    Interval.HOUR: "60",
}

# 新浪股票分钟周期映射
STOCK_PERIOD_MAP: dict[Interval, str] = {
    Interval.MINUTE: "1",
    Interval.HOUR: "60",
}

# 新浪期货合约代码带交易所后缀（如 RB2410 用 "rb2410"，
# 中金所 IF 用大写），实际测试中小写通用，此处统一小写
def to_sina_futures_symbol(symbol: str) -> str:
    return symbol.lower()


def to_sina_stock_symbol(symbol: str, exchange: Exchange) -> str:
    """600030 + SSE -> sh600030；000001 + SZSE -> sz000001"""
    prefix = "sh" if exchange == Exchange.SSE else "sz"
    return f"{prefix}{symbol}"


class Datafeed(BaseDatafeed):
    """akshare（新浪源）数据服务接口"""

    def init(self, output: Callable = print) -> bool:
        return True

    def query_bar_history(
        self, req: HistoryRequest, output: Callable = print
    ) -> list[BarData]:
        """查询K线数据"""
        if req.exchange in FUTURES_EXCHANGES:
            bars = self._query_futures_bars(req, output)
        elif req.exchange in STOCK_EXCHANGES:
            bars = self._query_stock_bars(req, output)
        else:
            output(f"vnpy_akshare：暂不支持交易所 {req.exchange.value}")
            bars = []
        return bars

    def query_tick_history(
        self, req: HistoryRequest, output: Callable = print
    ) -> list[TickData]:
        """新浪免费源无历史Tick，如需请用RQData等商业服务"""
        output("vnpy_akshare：不支持历史Tick数据查询")
        return []

    # ------------------------------------------------------------------
    # 期货
    # ------------------------------------------------------------------
    def _query_futures_bars(
        self, req: HistoryRequest, output: Callable
    ) -> list[BarData]:
        symbol = to_sina_futures_symbol(req.symbol)

        if req.interval == Interval.DAILY:
            output(f"下载期货日线 {req.symbol}.{req.exchange.value} ...")
            df: pd.DataFrame = ak.futures_zh_daily_sina(symbol=symbol)
            # 新浪日线列为 date/open/high/low/close/volume/hold/settle
            return self._df_to_bars(
                df, req,
                dt_col="date",
                oi_col="hold",
                settlement_col="settle",
                intraday=False,
            )
        elif req.interval in FUTURES_PERIOD_MAP:
            period = FUTURES_PERIOD_MAP[req.interval]
            output(
                f"下载期货{period}分钟线 {req.symbol}.{req.exchange.value} "
                f"（新浪仅提供最近约1023根，早于该范围的数据无法回溯）..."
            )
            df: pd.DataFrame = ak.futures_zh_minute_sina(
                symbol=symbol, period=period
            )
            return self._df_to_bars(df, req, dt_col="datetime", oi_col="hold")
        else:
            output(f"vnpy_akshare：期货不支持周期 {req.interval.value}")
            return []

    # ------------------------------------------------------------------
    # 股票 / 指数
    # ------------------------------------------------------------------
    def _query_stock_bars(
        self, req: HistoryRequest, output: Callable
    ) -> list[BarData]:
        if req.interval == Interval.DAILY:
            sina_symbol = to_sina_stock_symbol(req.symbol, req.exchange)
            output(f"下载股票日线 {req.symbol}.{req.exchange.value} ...")
            df: pd.DataFrame = ak.stock_zh_a_daily(
                symbol=sina_symbol,
                start_date=req.start.strftime("%Y%m%d"),
                end_date=req.end.strftime("%Y%m%d"),
            )
            return self._df_to_bars(df, req, dt_col="date", turnover_col="amount")
        elif req.interval in STOCK_PERIOD_MAP:
            sina_symbol = to_sina_stock_symbol(req.symbol, req.exchange)
            period = STOCK_PERIOD_MAP[req.interval]
            output(
                f"下载股票{period}分钟线 {req.symbol}.{req.exchange.value} "
                f"（新浪仅提供最近数据，无法深度回溯）..."
            )
            df: pd.DataFrame = ak.stock_zh_a_minute(
                symbol=sina_symbol, period=period, adjust="qfq"
            )
            return self._df_to_bars(df, req, dt_col="day")
        else:
            output(f"vnpy_akshare：股票不支持周期 {req.interval.value}")
            return []

    # ------------------------------------------------------------------
    # DataFrame -> BarData 公共转换
    # ------------------------------------------------------------------
    def _df_to_bars(
        self,
        df: pd.DataFrame,
        req: HistoryRequest,
        dt_col: str,
        oi_col: str | None = None,
        settlement_col: str | None = None,
        turnover_col: str | None = None,
        intraday: bool = True,
    ) -> list[BarData]:
        bars: list[BarData] = []

        # vnpy 约定：BarData.datetime 是K线"开始"时点。
        # 新浪分钟数据的时间戳是K线"结束"时点，需要减去一个周期；
        # 日线的时间戳就是交易日当天，不减。
        if intraday:
            adjustment = {
                Interval.MINUTE: timedelta(minutes=1),
                Interval.HOUR: timedelta(hours=1),
            }.get(req.interval, timedelta())
        else:
            adjustment = timedelta()

        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(row[dt_col]).to_pydatetime()
            except Exception:
                continue

            # 按请求范围过滤（新浪分钟接口不支持日期参数）
            if req.start and dt < req.start.replace(tzinfo=None) - timedelta(days=1):
                continue
            if req.end and dt > req.end.replace(tzinfo=None) + timedelta(days=1):
                continue

            try:
                open_price = float(row["open"])
                high_price = float(row["high"])
                low_price = float(row["low"])
                close_price = float(row["close"])
                volume = float(row["volume"])
            except (KeyError, ValueError, TypeError):
                continue

            # 过滤无效行情（停牌等）
            if volume <= 0 and close_price <= 0:
                continue

            turnover = float(row[turnover_col]) if turnover_col else 0.0
            open_interest = float(row[oi_col]) if oi_col and oi_col in row else 0.0

            bar = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                datetime=CHINA_TZ.localize(dt - adjustment),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover=turnover,
                open_interest=open_interest,
                gateway_name="AKSHARE",
            )

            # 结算价：vnpy BarData 无此字段，存到 extra 里意义不大，
            # 期货日线常见的用法是把结算价用于逐日盯市，此处忽略
            _ = settlement_col

            bars.append(bar)

        return bars
