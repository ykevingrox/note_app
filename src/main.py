import sys
import os

# 将项目根目录添加到 Python 路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.cloud_storage import CloudStorage
from src.core.logging_config import logger

def main():
    logger.info("程序启动")
    try:
        cloud_storage = CloudStorage()
        cloud_storage.init_database()

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
        logger.info("程序正常结束")
    except Exception as e:
        logger.exception("程序异常终止")
        raise

if __name__ == "__main__":
    main()
