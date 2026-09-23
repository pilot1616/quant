"""
vn.py 量化交易系统 - 项目入口脚本（无 GUI 模式）

以纯后端方式启动 vn.py 主引擎，用于：
- 测试环境安装是否正确
- 作为脚本化 / 自动化运行的起点

图形界面启动请运行: python run_trading.py
"""

import os
import sys

# 保证项目根目录在 sys.path 中，方便加载 strategies/ 下的自定义策略
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def main() -> None:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy.trader.utility import get_digits

    print("正在启动 vn.py 引擎（无 GUI 模式）...")

    # 1. 创建事件引擎（不要手动 start，MainEngine 构造时会自动启动）
    event_engine = EventEngine()

    # 2. 创建主引擎（内部会启动事件引擎并初始化功能引擎）
    main_engine = MainEngine(event_engine)
    print("  [1/2] 事件引擎 + 主引擎已启动")

    # 3. 挂载 CTA 策略应用
    from vnpy_ctastrategy.engine import CtaEngine

    main_engine.add_engine(CtaEngine)
    print("  [2/2] CTA 策略引擎已挂载")

    print()
    print("vn.py 启动成功！当前环境信息：")
    import vnpy

    print(f"  vnpy 版本: {vnpy.__version__}")
    print(f"  Python 版本: {sys.version.split()[0]}")
    print(f"  价格最小变动位数示例(get_digits(0.05)): {get_digits(0.05)}")

    print()
    print("提示：")
    print("  - 自定义策略放在 strategies/ 目录下，会自动被扫描加载")
    print("  - 图形界面请运行: python run_trading.py")
    print()

    # 清理退出
    main_engine.close()
    print("引擎已正常关闭，测试通过。")


if __name__ == "__main__":
    main()
