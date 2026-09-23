"""
端到端验证：从 akshare 下载的数据跑一次双均线策略回测

用法: python research/backtest_demo.py
"""

import os
import sys
from datetime import datetime

for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(key, None)
os.environ["no_proxy"] = "*"

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)


def main() -> None:
    from vnpy.trader.constant import Exchange, Interval
    from vnpy_ctastrategy.backtesting import BacktestingEngine

    from strategies.double_ma_strategy import DoubleMaStrategy

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol="RB2410.SHFE",
        interval=Interval.HOUR,
        start=datetime(2024, 6, 1),
        end=datetime(2024, 10, 31),
        rate=1 / 10000,      # 手续费率
        slippage=1.0,        # 滑点
        size=10,             # 螺纹钢合约乘数（10吨/手）
        pricetick=1.0,       # 最小价格变动
        capital=100_000,     # 初始资金
    )
    engine.add_strategy(DoubleMaStrategy, {"fast_window": 10, "slow_window": 30})
    engine.load_data()
    engine.run_backtesting()
    engine.calculate_result()
    engine.calculate_statistics(output=print)


if __name__ == "__main__":
    main()
