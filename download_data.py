"""
通过 akshare 数据服务下载历史数据到 vnpy 数据库

用法:
    # 期货日线（全部历史）
    python download_data.py futures RB2410 SHFE daily

    # 期货1小时线（新浪只保留最近约1023根）
    python download_data.py futures RB2410 SHFE hour

    # A股日线
    python download_data.py stock 600030 SSE daily

    # 指定起始日期（默认日线取近2年，小时线取近3个月）
    python download_data.py futures RB2410 SHFE daily 2023-01-01

注意:
    - 公司代理环境会拦截行情站点，脚本已自动清除代理环境变量
    - 下载后数据存在 .vntrader/database.db，回测/策略暖机直接可用
"""

import os
import sys
from datetime import datetime, timedelta

# 关键：清除代理，否则新浪/东财接口在企业网络下无法访问
for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(key, None)
os.environ["no_proxy"] = "*"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)


def main() -> None:
    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.database import get_database
    from vnpy.trader.object import HistoryRequest
    from vnpy.trader.datafeed import get_datafeed

    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    asset_type = sys.argv[1]        # futures / stock
    symbol = sys.argv[2].upper()    # RB2410 / 600030
    exchange = Exchange(sys.argv[3].upper())
    interval_str = sys.argv[4] if len(sys.argv) > 4 else "daily"
    start_str = sys.argv[5] if len(sys.argv) > 5 else None

    interval_map = {
        "minute": Interval.MINUTE,
        "hour": Interval.HOUR,
        "daily": Interval.DAILY,
    }
    interval = interval_map[interval_str]

    # 默认起始日期：日线近2年，小时线近3个月。
    # 注意：新浪分钟线是"最近约1023根"的滚动窗口，若请求的起止范围
    # 与窗口完全不相交（如已换月的活配合约），会取到 0 根——
    # 遇到这种情况请显式指定起始日期，或改用日线。
    if start_str:
        start = datetime.strptime(start_str, "%Y-%m-%d")
    elif interval == Interval.DAILY:
        start = datetime.now() - timedelta(days=730)
    else:
        start = datetime.now() - timedelta(days=90)

    end = datetime.now()

    req = HistoryRequest(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start=start,
        end=end,
    )

    datafeed = get_datafeed()
    print(f"数据服务: {type(datafeed).__module__}.{type(datafeed).__name__}")

    bars = datafeed.query_bar_history(req, output=print)
    if not bars:
        print("未取到数据，请检查合约代码/交易所/网络。")
        sys.exit(1)

    database = get_database()
    database.save_bar_data(bars)

    print()
    print(f"入库完成: {symbol}.{exchange.value} {interval.value}")
    print(f"  K线数量: {len(bars)}")
    print(f"  时间范围: {bars[0].datetime} ~ {bars[-1].datetime}")


if __name__ == "__main__":
    main()
