from .database import Database
from sqlalchemy.orm import joinedload

class KeywordManager:
    def __init__(self, database):
        self.db = database

    def add_keyword_to_note(self, note_id, keyword):
        note = self.db.get_note_by_id(note_id)
        if note:
            keywords = note['keywords']
            if keyword not in keywords:
                keywords.append(keyword)
                return self.db.update_note(note_id, keywords=keywords)
        return False

    def get_all_keywords(self):
        return self.db.get_all_keywords()

    def get_notes_by_keyword(self, keyword):
        return self.db.get_notes_by_keyword(keyword)

    def get_all_notes_with_keywords(self):
        return self.db.get_all_notes_with_keywords()

    def remove_keyword_from_note(self, note_id, keyword):
        note = self.db.get_note_by_id(note_id)
        if note:
            keywords = note['keywords']
            if keyword in keywords:
                keywords.remove(keyword)
                return self.db.update_note(note_id, keywords=keywords)
        return False

    def get_keywords_for_note(self, note_id):
        note = self.db.get_note_by_id(note_id)
        return note['keywords'] if note else []
