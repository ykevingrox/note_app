from .database import Database, Keyword, Note
from sqlalchemy.orm import joinedload

class KeywordManager:
    def __init__(self, database):
        self.db = database

    def add_keyword_to_note(self, note_id, keyword):
        session = self.db.Session()
        try:
            note = session.query(Note).get(note_id)
            keyword_obj = session.query(Keyword).filter_by(word=keyword).first()
            if not keyword_obj:
                keyword_obj = Keyword(word=keyword)
            note.keywords.append(keyword_obj)
            session.commit()
        finally:
            session.close()

    def get_all_keywords(self):
        session = self.db.Session()
        keywords = session.query(Keyword).all()
        session.close()
        return keywords

    def get_notes_by_keyword(self, keyword):
        return self.db.get_notes_by_keyword(keyword)

    def get_all_keywords_with_notes(self):
        notes_data = self.db.get_all_notes_with_keywords()
        keyword_notes = {}
        for keyword, notes in notes_data.items():
            keyword_notes[keyword] = [{'id': note['id'], 'title': note['title']} for note in notes]
        return keyword_notes
