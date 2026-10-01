from extensions import db
from datetime import datetime
from models.model import Model
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict

class Setting(Model):
    id = db.Column(db.Integer, primary_key=True)
    meta = db.Column(MutableDict.as_mutable(JSON))
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)