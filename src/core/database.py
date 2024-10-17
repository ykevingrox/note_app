import sqlite3
from datetime import datetime
import os
from src.core.logging_config import logger

class Database:
    def __init__(self, db_path='notes.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            url TEXT,
            domain TEXT,
            author TEXT,
            creation_date TEXT,
            file_path TEXT
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS note_keyword (
            note_id INTEGER,
            keyword_id INTEGER,
            FOREIGN KEY (note_id) REFERENCES notes (id),
            FOREIGN KEY (keyword_id) REFERENCES keywords (id),
            PRIMARY KEY (note_id, keyword_id)
        )
        ''')

        self.conn.commit()

    def add_note(self, title, content, url=None, domain=None, keywords=None, author=None, creation_date=None, file_path=None):
        try:
            self.cursor.execute('''
            INSERT INTO notes (title, content, url, domain, author, creation_date, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, content, url, domain, author, creation_date, file_path))
            
            note_id = self.cursor.lastrowid

            if keywords:
                for word in keywords:
                    self.cursor.execute('INSERT OR IGNORE INTO keywords (word) VALUES (?)', (word,))
                    self.cursor.execute('SELECT id FROM keywords WHERE word = ?', (word,))
                    keyword_id = self.cursor.fetchone()[0]
                    self.cursor.execute('INSERT INTO note_keyword (note_id, keyword_id) VALUES (?, ?)', (note_id, keyword_id))

            self.conn.commit()
            return note_id
        except sqlite3.Error as e:
            logger.error(f"添加笔记时出错: {e}")
            self.conn.rollback()
            return None

    def get_note_by_id(self, note_id):
        self.cursor.execute('''
        SELECT n.*, GROUP_CONCAT(k.word) as keywords
        FROM notes n
        LEFT JOIN note_keyword nk ON n.id = nk.note_id
        LEFT JOIN keywords k ON nk.keyword_id = k.id
        WHERE n.id = ?
        GROUP BY n.id
        ''', (note_id,))
        note = self.cursor.fetchone()
        if note:
            note_dict = dict(note)
            note_dict['keywords'] = note_dict['keywords'].split(',') if note_dict['keywords'] else []
            return note_dict
        return None

    def get_notes_by_keyword(self, keyword):
        self.cursor.execute('''
        SELECT n.*, GROUP_CONCAT(k.word) as keywords
        FROM notes n
        JOIN note_keyword nk ON n.id = nk.note_id
        JOIN keywords k ON nk.keyword_id = k.id
        WHERE k.word = ?
        GROUP BY n.id
        ''', (keyword,))
        notes = self.cursor.fetchall()
        return [dict(note) for note in notes]

    def search_notes(self, keyword):
        self.cursor.execute('''
        SELECT n.id, n.title, n.url, n.content, GROUP_CONCAT(k.word) as keywords
        FROM notes n
        LEFT JOIN note_keyword nk ON n.id = nk.note_id
        LEFT JOIN keywords k ON nk.keyword_id = k.id
        WHERE n.title LIKE ? OR n.content LIKE ? OR k.word LIKE ?
        GROUP BY n.id
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        notes = self.cursor.fetchall()
        return [
            {
                'id': note['id'],
                'title': note['title'],
                'url': note['url'],
                'keywords': note['keywords'].split(',') if note['keywords'] else [],
                'content': note['content'][:200]  # 只取前200个字符作为预览
            }
            for note in notes
        ]

    def delete_note(self, note_id):
        try:
            self.cursor.execute('DELETE FROM note_keyword WHERE note_id = ?', (note_id,))
            self.cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"删除笔记时出错: {e}")
            self.conn.rollback()
            return False

    def get_note_id_by_title(self, title):
        self.cursor.execute('SELECT id FROM notes WHERE title = ?', (title,))
        result = self.cursor.fetchone()
        return result['id'] if result else None

    def get_all_notes_with_keywords(self):
        try:
            self.cursor.execute('''
            SELECT n.id, n.title, n.author, GROUP_CONCAT(k.word) as keywords
            FROM notes n
            LEFT JOIN note_keyword nk ON n.id = nk.note_id
            LEFT JOIN keywords k ON nk.keyword_id = k.id
            GROUP BY n.id
            ''')
            notes = self.cursor.fetchall()
            return [
                {
                    'id': note['id'],
                    'title': note['title'],
                    'author': note['author'],
                    'keywords': note['keywords'].split(',') if note['keywords'] else []
                }
                for note in notes
            ]
        except sqlite3.Error as e:
            logger.error(f"获取所有笔记时出错: {e}")
            return []

    def update_note(self, note_id, **kwargs):
        try:
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values())
            values.append(note_id)
            self.cursor.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"更新笔记时出错: {e}")
            self.conn.rollback()
            return False

    def get_all_keywords(self):
        try:
            self.cursor.execute("SELECT DISTINCT word FROM keywords")
            return [row['word'] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"获取所有关键词时出错: {e}")
            return []

    def close(self):
        self.conn.close()
