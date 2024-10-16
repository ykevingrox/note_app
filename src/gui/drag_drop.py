from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal

class DropArea(QLabel):
    url_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setText("将链接拖放到这里")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            border: 2px dashed #999;
            border-radius: 5px;
            font-size: 18px;
            color: #666;
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                border: 2px solid #5c85d6;
                border-radius: 5px;
                font-size: 18px;
                color: #5c85d6;
                background-color: #e6f3ff;
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            border: 2px dashed #999;
            border-radius: 5px;
            font-size: 18px;
            color: #666;
        """)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            url = urls[0].toString()
            self.url_dropped.emit(url)
        self.setStyleSheet("""
            border: 2px dashed #999;
            border-radius: 5px;
            font-size: 18px;
            color: #666;
        """)

