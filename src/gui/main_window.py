from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QLineEdit, QTextEdit, QPushButton, QMessageBox, QProgressBar, QStatusBar, QLabel, QSplitter, QSpacerItem, QSizePolicy, QFrame
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex, QUrl
from .drag_drop import DropArea
from core.web_scraper import scrape_webpage
from core.database import Database
from core.keyword_manager import KeywordManager
from core.cloud_storage import CloudStorage
from core.pdf_handler import extract_pdf_info
from core.ai_handler import call_ai_model
import re
from datetime import datetime
import pytz
import logging
import hashlib

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

class AIThread(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, content, prompt):
        super().__init__()
        self.content = content
        self.prompt = prompt

    def run(self):
        result = call_ai_model(self.content, self.prompt)
        self.result_ready.emit(result)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mac笔记工具")
        self.setGeometry(100, 100, 1000, 600)

        # 定义按钮样式为类属性
        self.button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """

        # 添加整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                padding: 3px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧部件
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 右侧部件
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 左侧文件结构
        self.file_tree = QTreeView()
        self.file_tree.setIndentation(15)  # 设置缩进15像素
        self.file_model = QStandardItemModel()
        self.file_tree.setModel(self.file_model)
        self.file_model.setHorizontalHeaderLabels(['笔记结构'])
        left_layout.addWidget(self.file_tree)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词进行精确搜索")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                padding: 5px 15px;
            }
        """)
        left_layout.addWidget(self.search_input)

        splitter.addWidget(left_widget)

        # 拖放区域
        self.drop_area = DropArea()
        self.drop_area.setAcceptDrops(True)
        self.drop_area.dragEnterEvent = self.dragEnterEvent
        self.drop_area.dropEvent = self.handle_drop
        right_layout.addWidget(self.drop_area, 1)

        # 调用大模型的输入框和按钮（移到关键词输入之前）
        self.ai_prompt_input = QTextEdit()  # 使用 QTextEdit 替代 QLineEdit
        self.ai_prompt_input.setPlaceholderText("输入 prompt 调用大模型")
        self.ai_prompt_input.setFixedHeight(75)  # 设置固定高度，大约三行的高度
        self.call_ai_button = QPushButton("调用大模型")
        self.call_ai_button.setEnabled(False)
        ai_layout = QHBoxLayout()
        ai_layout.addWidget(self.ai_prompt_input, 3)  # 给予输入框更多的水平空间
        ai_layout.addWidget(self.call_ai_button, 1)
        right_layout.addLayout(ai_layout)

        # 关键词输入（保持不变，但位置调整到大模型调用之后）
        keyword_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词（用逗号分隔多个关键词）")
        keyword_layout.addWidget(self.keyword_input)
        self.add_keyword_button = QPushButton("添加关键词")
        keyword_layout.addWidget(self.add_keyword_button)
        right_layout.addLayout(keyword_layout)

        # 内容预览（保持不变）
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        right_layout.addWidget(self.content_preview, 2)

        # 添加删除按钮
        self.delete_button = QPushButton("删除笔记")
        self.delete_button.setEnabled(False)  # 初始时禁用删除按钮
        self.delete_button.setStyleSheet(self.button_style)
        right_layout.addWidget(self.delete_button)

        # 在右侧布局中添加同步按钮和进度条
        self.sync_button = QPushButton("同步到阿里云 OSS")
        self.sync_button.setIcon(QIcon("path/to/sync_icon.png"))
        self.sync_button.setStyleSheet(self.button_style)
        right_layout.addWidget(self.sync_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """)
        right_layout.addWidget(self.progress_bar)

        # 添加 AI 响应显示框
        self.ai_response_display = QTextEdit()
        self.ai_response_display.setReadOnly(True)
        self.ai_response_display.setPlaceholderText("AI 响应将显示在这里")
        ai_response_layout = QVBoxLayout()
        ai_response_label = QLabel("AI 响应:")
        ai_response_layout.addWidget(ai_response_label)
        ai_response_layout.addWidget(self.ai_response_display)
        right_layout.addLayout(ai_response_layout)

        # 添加状态栏
        self.setStatusBar(QStatusBar())

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        self.db = Database()
        self.keyword_manager = KeywordManager(self.db)
        self.cloud_storage = CloudStorage()
        self.init_connections()
        self.update_file_tree()

        font = QFont("Arial", 11)
        self.setFont(font)

        # 文件树样式
        self.file_tree.setStyleSheet("""
            QTreeView {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
            }
            QTreeView::item:hover {
                background-color: #e6f3ff;
            }
            QTreeView::item:selected {
                background-color: #3399ff;
                color: white;
            }
        """)

        # 应用按钮样式
        self.add_keyword_button.setStyleSheet(self.button_style)
        self.delete_button.setStyleSheet(self.button_style)
        self.sync_button.setStyleSheet(self.button_style)
        self.call_ai_button.setStyleSheet(self.button_style)

        # 预览样式
        preview_style = """
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                padding: 5px;
            }
        """
        self.content_preview.setStyleSheet(preview_style)
        self.ai_response_display.setStyleSheet(preview_style)

        right_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        right_layout.addWidget(self.create_horizontal_line())
        right_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

    def init_connections(self):
        self.drop_area.url_dropped.connect(self.handle_url_drop)
        self.keyword_input.returnPressed.connect(self.handle_keyword_input)
        self.add_keyword_button.clicked.connect(self.handle_keyword_input)
        self.search_input.returnPressed.connect(self.handle_search)
        self.delete_button.clicked.connect(self.handle_delete_note)
        self.file_tree.clicked.connect(self.handle_tree_item_click)
        
        # 添加新的同步按钮连接
        self.sync_button.clicked.connect(self.sync_with_oss)

        # 在 init_connections 方法中添加新的连接
        self.call_ai_button.clicked.connect(self.handle_call_ai)

    def handle_url_drop(self, url):
        self.drop_area.setText("正在抓取网页内容...")
        self.scraper_thread = ScraperThread(url)
        self.scraper_thread.result_ready.connect(self.handle_scrape_result)
        self.scraper_thread.start()

    def handle_scrape_result(self, result):
        self.drop_area.setText("将链接拖放到这")
        if result:
            self.content_preview.setText(f"标题: {result['title']}\n\n"
                                         f"URL: {result['url']}\n"
                                         f"域名: {result['domain']}\n\n"
                                         f"内容预览:\n{result['content'][:500]}...")
            self.current_note = result
        else:
            self.content_preview.setText("抓取网页内容失败")

    def split_keywords(self, keyword_string):
        # 使用正则表达式拆分关键，同时处理英文逗号
        return [kw.strip() for kw in re.split(r'[,，]', keyword_string) if kw.strip()]

    def handle_keyword_input(self):
        keyword_string = self.keyword_input.text().strip()
        if keyword_string and hasattr(self, 'current_note'):
            keywords = self.split_keywords(keyword_string)
            
            creation_date_str = self.current_note.get('creation_date')
            if creation_date_str:
                try:
                    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M:%S%z")
                except ValueError:
                    creation_date = datetime.now(pytz.utc)
            else:
                creation_date = datetime.now(pytz.utc)

            note_id = self.db.add_note(
                self.current_note['title'],
                self.current_note['content'],
                url=self.current_note.get('url'),
                domain=self.current_note.get('domain'),
                keywords=keywords,
                author=self.current_note.get('author'),
                creation_date=creation_date.strftime("%Y-%m-%d %H:%M:%S"),
                file_path=self.current_note.get('file_path')
            )
            if note_id:
                self.keyword_input.clear()
                self.update_file_tree()
                print(f"已添加笔记和关键词: {', '.join(keywords)}")
            else:
                print("添加笔记失败")
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

        notes = self.db.get_all_notes_with_keywords()
        
        if notes is None:
            logger.error("获取笔记失败")
            return

        for note in notes:
            note_item = QStandardItem(note['title'])
            note_item.setData(note['id'])
            root.appendRow(note_item)
            
            if note['keywords']:
                keywords_str = ", ".join(note['keywords'])
                keywords_item = QStandardItem(f"关键词: {keywords_str}")
                
                font = QFont()
                font.setItalic(True)
                keywords_item.setFont(font)
                
                note_item.appendRow(keywords_item)

        self.file_tree.expandAll()

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
            self.call_ai_button.setEnabled(True)  # 启用 AI 调用按钮
            self.current_note_id = item.data()
            self.display_note_content(self.current_note_id)
        else:  # 这是一个关键词项
            self.delete_button.setEnabled(True)
            self.call_ai_button.setEnabled(True)  # 启用 AI 调用按钮
            self.current_note_id = parent.data()
            self.display_note_content(self.current_note_id)

    def display_note_content(self, note_id):
        note = self.db.get_note_by_id(note_id)
        if note:
            self.content_preview.setText(f"标题: {note['title']}\n\n"
                                         f"URL: {note['url']}\n"
                                         f"作者: {note['author']}\n"
                                         f"创建日期: {note['creation_date']}\n"
                                         f"关键词: {', '.join(note['keywords'])}\n\n"
                                         f"内容预览:\n{note['content'][:500]}...")
            if note.get('ai_response'):
                self.ai_response_display.setText(note['ai_response'])
            else:
                self.ai_response_display.clear()
        else:
            self.content_preview.setText("无法加载笔记内容")
            self.ai_response_display.clear()

    def handle_delete_note(self):
        if hasattr(self, 'current_note_id'):
            note = self.db.get_note_by_id(self.current_note_id)
            if note:
                reply = QMessageBox.question(self, '确认删除', 
                                             f'确定要删笔记 "{note["title"]}" 吗？',
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if self.db.delete_note(self.current_note_id):
                        QMessageBox.information(self, "成功", "笔记已成功删除")
                        self.update_file_tree()
                        self.content_preview.clear()
                    else:
                        QMessageBox.warning(self, "错误", "删除笔记失败")
            else:
                QMessageBox.warning(self, "错误", "找不到要删除的笔记")

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

    def sync_with_oss(self):
        try:
            self.sync_button.setEnabled(False)
            self.sync_button.setText("正在同步...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            local_hash = self.calculate_file_hash(self.db.db_path)
            cloud_hash = self.cloud_storage.get_cloud_file_hash(self.cloud_storage.cloud_db_name)

            if local_hash != cloud_hash:
                self.progress_bar.setValue(25)
                self.db.close()

                cloud_db_path = self.cloud_storage.download_database_temp()
                cloud_db = Database(cloud_db_path)

                self.progress_bar.setValue(50)
                self.merge_databases(self.db, cloud_db)

                self.progress_bar.setValue(75)
                self.cloud_storage.upload_database()

                self.db = Database()
                self.keyword_manager = KeywordManager(self.db)

                self.update_file_tree()
                self.progress_bar.setValue(100)
                self.statusBar().showMessage("同步成功", 3000)
            else:
                self.progress_bar.setValue(100)
                self.statusBar().showMessage("本地数据已是最新，无需同步", 3000)
        except Exception as e:
            logging.error(f"同步失败: {str(e)}", exc_info=True)
            self.statusBar().showMessage(f"同步失败: {str(e)}", 5000)
        finally:
            self.sync_button.setEnabled(True)
            self.sync_button.setText("同步到阿里云 OSS")
            self.progress_bar.setVisible(False)

    def calculate_file_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def merge_databases(self, local_db, cloud_db):
        # 实现数据库合并逻辑
        pass

    # 添加新的方法来处理调用大模型的逻辑
    def handle_call_ai(self):
        if hasattr(self, 'current_note_id'):
            prompt = self.ai_prompt_input.toPlainText().strip()
            if prompt:
                self.call_ai_button.setEnabled(False)
                self.call_ai_button.setText("正在调用...")
                note = self.db.get_note_by_id(self.current_note_id)
                if note:
                    self.ai_thread = AIThread(note['content'], prompt)
                    self.ai_thread.result_ready.connect(self.handle_ai_result)
                    self.ai_thread.start()
                else:
                    QMessageBox.warning(self, "错误", "无法获取笔记内容")
            else:
                QMessageBox.warning(self, "提示", "请输入 prompt")
        else:
            QMessageBox.warning(self, "提示", "请先选择一个笔记")

    def handle_ai_result(self, result):
        self.call_ai_button.setEnabled(True)
        self.call_ai_button.setText("调用大模型")
        if result:
            self.update_note_with_ai_response(result)
            self.ai_response_display.setText(result)
            self.ai_response_display.ensureCursorVisible()
        else:
            QMessageBox.warning(self, "错误", "调用大模型失败")

    def update_note_with_ai_response(self, ai_response):
        if hasattr(self, 'current_note_id'):
            current_note = self.db.get_note_by_id(self.current_note_id)
            if current_note:
                ai_prompt = self.ai_prompt_input.toPlainText().strip()
                success = self.db.update_note(self.current_note_id, ai_prompt=ai_prompt, ai_response=ai_response)
                if success:
                    self.display_note_content(self.current_note_id)  # 刷新显示
                    QMessageBox.information(self, "成功", "笔记已更新")
                else:
                    QMessageBox.warning(self, "错误", "更新笔记失败")
            else:
                QMessageBox.warning(self, "错误", "无法获取当前笔记")
        else:
            QMessageBox.warning(self, "错误", "没有选中的笔记")

    def create_horizontal_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

