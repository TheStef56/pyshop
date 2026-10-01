from extensions import db
from sqlalchemy import desc
from datetime import datetime
from models.model import Model
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from utils.crypto import encrypt_string, decrypt_string

class Label(Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(255), nullable=True)  # Path to the image file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    def to_dict(self) -> dict:
        return {
            "id" : self.id,
            "name" : self.name,
            "image" : self.image,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }