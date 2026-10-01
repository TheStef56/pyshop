import traceback
from extensions import db

class Model(db.Model):
    __abstract__ = True
    
    def save(self) -> bool:
        """save current model and return result"""
        try:
            if not self.id:
                db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            db.session.rollback()
            db.session.flush()
            return False
        
    def delete(self) -> bool:
        """delete current model and return result"""
        try:
            self.query.filter_by(id=self.id).delete()
            db.session.commit()
            return True
        except Exception as e:
            print(traceback.format_exc())
            print(e)
            db.session.rollback()
            db.session.flush()
            return False