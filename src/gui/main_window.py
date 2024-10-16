from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QLineEdit, QTextEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex, QUrl

from .drag_drop import DropArea
from core.web_scraper import scrape_webpage
from core.database import Database,Note
from core.keyword_manager import KeywordManager
import re
from core.pdf_handler import extract_pdf_info
from datetime import datetime
import pytz


class ScraperThread(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词（用逗号分隔多个关键词）")

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
        self.file_tree.setIndentation(15)  # 设置缩进为15像素
        self.file_model = QStandardItemModel()
        self.file_tree.setModel(self.file_model)
        self.file_model.setHorizontalHeaderLabels(['笔记结构'])
        left_layout.addWidget(self.file_tree)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词进行精确搜索")
        left_layout.addWidget(self.search_input)

        layout.addLayout(left_layout, 1)

        right_layout = QVBoxLayout()
        
        # 拖放区域
        self.drop_area = DropArea()
        self.drop_area.setAcceptDrops(True)
        self.drop_area.dragEnterEvent = self.dragEnterEvent
        self.drop_area.dropEvent = self.handle_drop
        right_layout.addWidget(self.drop_area, 1)

        # 关键词输入
        keyword_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词（用逗号分隔多个关键词）")
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

    def split_keywords(self, keyword_string):
        # 使用正则表达式拆分关键词，同时处理英文逗号
        return [kw.strip() for kw in re.split(r'[,，]', keyword_string) if kw.strip()]

    def handle_keyword_input(self):
        keyword_string = self.keyword_input.text().strip()
        if keyword_string and hasattr(self, 'current_note'):
            keywords = self.split_keywords(keyword_string)
            
            # 将创建日期字符串转换为 datetime 对象
            creation_date_str = self.current_note.get('creation_date')
            if creation_date_str:
                try:
                    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S%z")
                except ValueError:
                    # 如果无法解析，则使用当前时间
                    creation_date = datetime.now(pytz.utc)
            else:
                creation_date = datetime.now(pytz.utc)

            note = self.db.add_note(
                self.current_note['title'],
                self.current_note['content'],
                url=self.current_note.get('url'),
                domain=self.current_note.get('domain'),
                keywords=keywords,
                author=self.current_note.get('author'),
                creation_date=creation_date,
                file_path=self.current_note.get('file_path')
            )
            self.keyword_input.clear()
            self.update_file_tree()
            print(f"已添加关键词: {', '.join(keywords)}")
        else:
            print("请先拖放一个URL或PDF文件，然后再添加关键词")

    def handle_search(self):
        keyword = self.search_input.text().strip()
        if keyword:
            results = self.db.search_notes(keyword)
            self.display_search_results(results)
        else:
            QMessageBox.warning(self, "搜索错误", "请输入要搜索的关键词")

    def update_file_tree(self):
        self.file_model.clear()
        self.file_model.setHorizontalHeaderLabels(['笔记结构'])
        root = self.file_model.invisibleRootItem()

        notes = self.keyword_manager.get_all_notes_with_keywords()
        
        for note in notes:
            note_item = QStandardItem(note['title'])
            note_item.setData(note['id'])  # 存储笔记ID以便后续操作
            root.appendRow(note_item)
            
            if note['keywords']:
                keywords_str = ", ".join(note['keywords'])
                keywords_item = QStandardItem(f"关键词: {keywords_str}")
                
                # 设置关键词项的字体为斜体
                font = QFont()
                font.setItalic(True)
                keywords_item.setFont(font)
                
                note_item.appendRow(keywords_item)

        self.file_tree.expandAll()  # 展开所有项

    def display_search_results(self, results):
        self.content_preview.clear()
        if not results:
            self.content_preview.append("没有找到匹配的笔记")
            return

        for note in results:
            self.content_preview.append(f"标题: {note['title']}")
            self.content_preview.append(f"URL: {note['url']}")
            self.content_preview.append(f"关键词: {', '.join(note['keywords'])}")
            self.content_preview.append(f"内容预览: {note['content']}...")
            self.content_preview.append("\n" + "-"*50 + "\n")

    def handle_tree_item_click(self, index):
        item = self.file_model.itemFromIndex(index)
        parent = item.parent()
        if parent is None:  # 这是一个笔记项
            self.delete_button.setEnabled(True)
            self.current_note_id = item.data()
        else:  # 这是一个关键词项
            self.delete_button.setEnabled(True)
            self.current_note_id = parent.data()

    def handle_delete_note(self):
        if hasattr(self, 'current_note_id'):
            note_title = self.file_model.itemFromIndex(self.file_tree.currentIndex()).text()
            reply = QMessageBox.question(self, '确认删除', 
                                         f'确定要删除笔记 "{note_title}" 吗？',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.db.delete_note(self.current_note_id):
                    QMessageBox.information(self, "成功", "笔记已成功删除")
                    self.update_file_tree()
                    self.content_preview.clear()
                else:
                    QMessageBox.warning(self, "错误", "删除笔记失败")

    def get_note_id_by_title(self, title):
        # 这个方法需要实现，用于根据标题查找笔记ID
        return self.db.get_note_id_by_title(title)

    def handle_drop(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            url = mime_data.urls()[0]
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.pdf'):
                    self.handle_pdf_drop(file_path)
                else:
                    self.drop_area.setText("不支持的文件类型")
            else:
                self.handle_url_drop(url.toString())
        event.acceptProposedAction()

    def handle_pdf_drop(self, file_path):
        self.drop_area.setText("正在处理 PDF 文件...")
        pdf_info = extract_pdf_info(file_path)
        if pdf_info:
            self.current_note = pdf_info
            self.content_preview.setText(f"标题: {pdf_info['title']}\n\n"
                                         f"作者: {pdf_info['author']}\n"
                                         f"创建日期: {pdf_info['creation_date']}\n"
                                         f"文件路径: {pdf_info['file_path']}\n\n"
                                         f"内容预览:\n{pdf_info['content'][:500]}...")
            self.drop_area.setText("PDF 文件已处理，请添加关键词")
        else:
            self.drop_area.setText("PDF 文件处理失败")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

