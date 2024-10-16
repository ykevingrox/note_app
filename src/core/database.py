from sqlalchemy import create_engine, Column, Integer, String, Text, Table, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

Base = declarative_base()

note_keyword = Table('note_keyword', Base.metadata,
    Column('note_id', Integer, ForeignKey('notes.id')),
    Column('keyword_id', Integer, ForeignKey('keywords.id'))
)

class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    url = Column(String)
    domain = Column(String)
    author = Column(String)
    creation_date = Column(DateTime)
    file_path = Column(String)
    keywords = relationship('Keyword', secondary=note_keyword, back_populates='notes')

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    word = Column(String(50), unique=True)
    notes = relationship('Note', secondary=note_keyword, back_populates='keywords')

class Database:
    def __init__(self, db_path='notes.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_note(self, title, content, url=None, domain=None, keywords=None, author=None, creation_date=None, file_path=None):
        session = self.Session()
        try:
            new_note = Note(title=title, content=content, url=url, domain=domain, 
                            author=author, creation_date=creation_date, file_path=file_path)
            session.add(new_note)
            session.flush()

            if keywords:
                for word in keywords:
                    keyword = session.query(Keyword).filter(Keyword.word == word).first()
                    if not keyword:
                        keyword = Keyword(word=word)
                    new_note.keywords.append(keyword)

            session.commit()
            return new_note
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def get_note_by_id(self, note_id):
        session = self.Session()
        try:
            note = session.query(Note).options(joinedload(Note.keywords)).get(note_id)
            return note
        finally:
            session.close()

    def get_notes_by_keyword(self, keyword):
        session = self.Session()
        notes = session.query(Note).join(Note.keywords).filter(Keyword.word == keyword).all()
        session.close()
        return notes

    def search_notes(self, keyword):
        session = self.Session()
        try:
            notes = session.query(Note).join(Note.keywords).filter(Keyword.word == keyword).options(joinedload(Note.keywords)).all()
            
            results = []
            for note in notes:
                results.append({
                    'id': note.id,
                    'title': note.title,
                    'url': note.url,
                    'keywords': [k.word for k in note.keywords],
                    'content': note.content[:200]  # 只取前200个字符作为预览
                })
            return results
        finally:
            session.close()

    def delete_note(self, note_id):
        session = self.Session()
        try:
            note = session.query(Note).options(joinedload(Note.keywords)).get(note_id)
            if note:
                # 删除笔记与关键词的关联
                note.keywords.clear()
                
                # 删除不再与任何笔记关联的关键词
                for keyword in session.query(Keyword).all():
                    if len(keyword.notes) == 0:
                        session.delete(keyword)
                
                # 删除笔记
                session.delete(note)
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"删除笔记时出错: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_note_id_by_title(self, title):
        session = self.Session()
        try:
            note = session.query(Note).filter(Note.title == title).first()
            return note.id if note else None
        finally:
            session.close()

    def get_all_notes_with_keywords(self):
        with self.Session() as session:
            notes = session.query(Note).options(joinedload(Note.keywords)).all()
            return [
                {
                    'id': note.id,
                    'title': note.title,
                    'keywords': [keyword.word for keyword in note.keywords],
                    'author': note.author,  # 确保这里包含 author
                    # ... 其他字段 ...
                }
                for note in notes
            ]
