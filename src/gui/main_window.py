from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QLineEdit, QTextEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex

from .drag_drop import DropArea
from core.web_scraper import scrape_webpage
from core.database import Database,Note
from core.keyword_manager import KeywordManager


class ScraperThread(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        result = scrape_webpage(self.url)
        if result:
            self.result_ready.emit(result)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mac笔记工具")
        self.setGeometry(100, 100, 1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()

        # 左侧文件结构
        left_layout = QVBoxLayout()
        self.file_tree = QTreeView()
        self.file_model = QStandardItemModel()
        self.file_tree.setModel(self.file_model)
        self.file_model.setHorizontalHeaderLabels(['笔记结构'])
        left_layout.addWidget(self.file_tree)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索笔记")
        left_layout.addWidget(self.search_input)

        layout.addLayout(left_layout, 1)

        right_layout = QVBoxLayout()
        
        # 拖放区域
        self.drop_area = DropArea()
        right_layout.addWidget(self.drop_area, 1)

        # 关键词输入
        keyword_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词")
        keyword_layout.addWidget(self.keyword_input)
        self.add_keyword_button = QPushButton("添加关键词")
        keyword_layout.addWidget(self.add_keyword_button)
        right_layout.addLayout(keyword_layout)

        # 内容预览
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        right_layout.addWidget(self.content_preview, 2)

        # 添加删除按钮
        self.delete_button = QPushButton("删除笔记")
        self.delete_button.setEnabled(False)  # 初始时禁用删除按钮
        right_layout.addWidget(self.delete_button)

        layout.addLayout(right_layout, 2)

        central_widget.setLayout(layout)

        self.db = Database()
        self.keyword_manager = KeywordManager(self.db)
        self.init_connections()
        self.update_file_tree()  # 在初始化时更新文件树

    def init_connections(self):
        self.drop_area.url_dropped.connect(self.handle_url_drop)
        self.keyword_input.returnPressed.connect(self.handle_keyword_input)
        self.add_keyword_button.clicked.connect(self.handle_keyword_input)
        self.search_input.returnPressed.connect(self.handle_search)
        self.delete_button.clicked.connect(self.handle_delete_note)
        self.file_tree.clicked.connect(self.handle_tree_item_click)

    def handle_url_drop(self, url):
        self.drop_area.setText("正在抓取网页内容...")
        self.scraper_thread = ScraperThread(url)
        self.scraper_thread.result_ready.connect(self.handle_scrape_result)
        self.scraper_thread.start()

    def handle_scrape_result(self, result):
        self.drop_area.setText("将链接拖放到这里")
        if result:
            self.content_preview.setText(f"标题: {result['title']}\n\n"
                                         f"URL: {result['url']}\n"
                                         f"域名: {result['domain']}\n\n"
                                         f"内容预览:\n{result['content'][:500]}...")
            self.current_note = result
        else:
            self.content_preview.setText("抓取网页内容失败")

    def handle_keyword_input(self):
        keyword = self.keyword_input.text().strip()
        if keyword and hasattr(self, 'current_note'):
            note = self.db.add_note(
                self.current_note['title'],
                self.current_note['content'],
                self.current_note['url'],
                self.current_note['domain'],
                [keyword]  # 直接在添加笔记时添加关键词
            )
            self.keyword_input.clear()
            self.update_file_tree()
            print(f"已添加关键词: {keyword}")
        else:
            print("请先拖放一个URL，然后再添加关键词")

    def handle_search(self):
        search_term = self.search_input.text().strip()
        if search_term:
            results = self.db.search_notes(search_term)
            self.display_search_results(results)

    def update_file_tree(self):
        self.file_model.clear()
        self.file_model.setHorizontalHeaderLabels(['笔记结构'])
        root = self.file_model.invisibleRootItem()

        keyword_notes = self.keyword_manager.get_all_keywords_with_notes()
        
        for keyword, notes in keyword_notes.items():
            keyword_item = QStandardItem(keyword)
            root.appendRow(keyword_item)
            
            for note in notes:
                note_item = QStandardItem(note['title'])
                note_item.setData(note['id'])  # 存储笔记ID以便后续操作
                keyword_item.appendRow(note_item)

        self.file_tree.expandAll()  # 展开所有项

    def display_search_results(self, results):
        self.content_preview.clear()
        for note in results:
            self.content_preview.append(f"标题: {note['title']}")
            self.content_preview.append(f"URL: {note['url']}")
            self.content_preview.append(f"关键词: {', '.join(note['keywords'])}")
            self.content_preview.append(f"内容预览: {note['content']}...")
            self.content_preview.append("\n" + "-"*50 + "\n")

    def handle_tree_item_click(self, index):
        item = self.file_model.itemFromIndex(index)
        if item.parent() is not None:  # 如果不是根节点（即不是关键词节点）
            self.delete_button.setEnabled(True)
            self.current_note_title = item.text()
        else:
            self.delete_button.setEnabled(False)
            self.current_note_title = None

    def handle_delete_note(self):
        if hasattr(self, 'current_note_title'):
            reply = QMessageBox.question(self, '确认删除', 
                                         f'确定要删除笔记 "{self.current_note_title}" 吗？',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 这里需要根据标题查找笔记ID，然后删除
                note_id = self.get_note_id_by_title(self.current_note_title)
                if note_id and self.db.delete_note(note_id):
                    QMessageBox.information(self, "成功", "笔记已成功删除")
                    self.update_file_tree()
                    self.content_preview.clear()
                else:
                    QMessageBox.warning(self, "错误", "删除笔记失败")

    def get_note_id_by_title(self, title):
        # 这个方法需要实现，用于根据标题查找笔记ID

        return self.db.get_note_id_by_title(title)

