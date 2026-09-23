"""
vn.py 量化交易系统 - 图形界面交易入口

用法:
    python run_trading.py          # 启动图形界面（默认）

依赖 PyQt6（已随 vnpy 安装）。在 macOS 上首次运行可能需要在
系统设置中授予终端辅助权限。
"""

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def main() -> None:
    from vnpy.event import EventEngine

    from vnpy.trader.engine import MainEngine
    from vnpy.trader.ui import MainWindow, create_qapp

    from vnpy_ctastrategy.engine import CtaEngine
    from vnpy_datamanager.engine import ManagerEngine

    qapp = create_qapp()

    event_engine = EventEngine()
    event_engine.start()

    main_engine = MainEngine(event_engine)
    main_engine.add_engine(CtaEngine)
    main_engine.add_engine(ManagerEngine)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
