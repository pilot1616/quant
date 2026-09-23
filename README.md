# vn.py 量化交易项目

基于 [vn.py](https://github.com/vnpy/vnpy) 4.4.0 的量化交易研究与实践项目，运行于 Python 3.11 虚拟环境（`.venv/`）。

## 项目结构

```
quant/
├── .venv/               # Python 3.11 虚拟环境（uv 创建）
├── .vntrader/           # vn.py 运行时目录（VT_setting.json 已配置 akshare 数据服务）
├── strategies/          # 自定义 CTA 策略（已含 DoubleMa、AtrRsi 两个官方示例）
├── research/            # 研究/回测脚本（backtest_demo.py 为端到端示例）
├── vnpy_akshare/        # 自研 akshare 数据服务插件（vnpy 按包名自动加载）
├── data/                # 本地数据（K线数据库默认在 .vntrader/database.db）
├── gateway_scripts/     # 各交易接口连接脚本（按需添加）
├── download_data.py     # 命令行下载数据工具（akshare → vnpy 数据库）
├── run_engine_test.py   # 无 GUI 引擎冒烟测试（验证安装）
├── run_trading.py       # 图形界面交易入口
└── README.md
```

## 已安装组件

| 包 | 用途 |
|---|---|
| `vnpy` 4.4.0 | 核心框架（事件引擎、主引擎、OMS） |
| `vnpy_ctastrategy` 1.4.1 | CTA 策略应用（含回测引擎、参数优化） |
| `vnpy_datamanager` 1.2.0 | 数据管理（导入/导出/维护历史数据） |
| `vnpy_sqlite` 1.1.3 | 默认 SQLite 数据库驱动 |
| `vnpy_akshare`（本项目自研） | akshare 新浪源数据服务：期货/股票日线+小时线 |
| `akshare` 1.18.97 | 免费数据源（新浪财经接口） |
| `ta-lib` / `deap` / `numpy` / `pandas` | 技术指标、遗传算法优化、数据计算 |

> 注意：`vnpy_ctp`（国内期货 CTP 接口）无法在 macOS ARM 上编译，CTP 官方库只提供 Linux/Windows 版本。实盘接 CTP 需在 Linux/Windows 上运行。

## 快速开始

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 验证引擎（无 GUI 冒烟测试）
python run_engine_test.py

# 3. 下载数据（akshare 新浪源，免费无需账号）
python download_data.py futures RB2410 SHFE daily            # 期货日线（全历史）
python download_data.py futures RB2410 SHFE hour 2024-06-01  # 期货小时线（需指定日期，只保留最近约1023根）
python download_data.py stock 600030 SSE daily               # A股日线

# 4. 跑一次端到端回测（用已下载的 RB2410 小时线）
python research/backtest_demo.py

# 5. 启动图形界面交易终端
python run_trading.py
```

> ⚠️ 公司代理环境会拦截行情站点，`download_data.py` 和 `backtest_demo.py`
> 已自动清除 `http_proxy/https_proxy`；直接运行 akshare 相关脚本时如遇
> `ProxyError`，先 `unset http_proxy https_proxy`。

## 使用图形界面

1. `python run_trading.py` 启动后，顶部菜单 **功能 → CTA 策略**，右侧面板点击「添加策略」选择 `DoubleMaStrategy` 等已加载的策略类。
2. **功能 → 数据管理** 可导入 CSV 历史数据（需先配置好合约信息：代码、交易所、K线周期）。
3. 在 CTA 策略界面选中策略后点「回测」可直接对数据库中的历史数据进行回测。

## 脚本化回测示例

```python
from vnpy_ctastrategy.backtesting import BacktestingEngine
from vnpy.trader.constant import Interval
from datetime import datetime
from strategies.double_ma_strategy import DoubleMaStrategy

engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol="IF2406.CFFEX",           # 回测合约
    interval=Interval.MINUTE,           # K线周期
    start=datetime(2024, 1, 1),
    end=datetime(2024, 6, 30),
    rate=0.3/10000,                     # 手续费率
    slippage=0.2,                       # 滑点
    size=300,                           # 合约乘数
    pricetick=0.2,                      # 最小价格变动
    capital=1_000_000,                  # 初始资金
)
engine.add_strategy(DoubleMaStrategy, {"fast_window": 10, "slow_window": 30})
engine.load_data()
engine.run_backtesting()
engine.calculate_result()
engine.calculate_statistics()
engine.show_chart()   # 需 GUI 环境时可显示资金曲线图
```

## 数据来源

### akshare（已接入，默认数据服务）

`.vntrader/vt_setting.json` 已配置 `"datafeed.name": "akshare"`，插件在
`vnpy_akshare/`（vnpy 按 `vnpy_{name}` 规则自动加载）。能力与限制：

| 数据 | 接口 | 范围 |
|---|---|---|
| 期货日线 | 新浪 `futures_zh_daily_sina` | 全部历史，含结算价/持仓量 |
| 期货小时线 | 新浪 `futures_zh_minute_sina(60)` | 仅最近约 1023 根 |
| A股日线 | 新浪 `stock_zh_a_daily` | 全部历史 |
| 历史Tick | — | 不支持（需 RQData 等商业服务） |

GUI「数据管理 → 下载数据」同样走此数据服务。到期合约（如 RB2410）
小时线需显式指定起始日期；活配合约直接下即可。

### 其他方式

- 手动导入 CSV：图形界面「数据管理」或 `vnpy_datamanager`
- RQData / Wind / iFinD 等商业数据服务：安装对应 `vnpy_xxx` 包后修改
  `vt_setting.json` 的 `datafeed` 配置

## 下一步可做的事

- [ ] 导入一段真实历史数据（CSV），跑通 DoubleMa 策略回测
- [ ] 在 `strategies/` 下编写自己的策略（继承 `CtaTemplate`）
- [ ] 参数优化：`run_optimization()` 或界面「优化」按钮（遗传算法/穷举）
- [ ] 实盘/模拟盘：Linux 机器上安装 `vnpy_ctp`，在 `gateway_scripts/` 下添加连接脚本
