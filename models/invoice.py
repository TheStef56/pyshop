from extensions import db
from sqlalchemy import desc
from datetime import datetime
from models.model import Model
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from utils.crypto import encrypt_string, decrypt_string

class Invoice(Model):
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String(255))
    index = db.Column(db.String(255))
    order_id = db.Column(db.Integer, ForeignKey('order.id'))
    _invoice = db.Column("invoice", db.Text)  # encrypted field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def invoice(self) -> str:
        try:
            return decrypt_string(self._invoice) if self._invoice else ""
        except Exception as e:
            return ""

    @invoice.setter
    def invoice(self, value) -> None:
        if isinstance(value, str):
            self._invoice = encrypt_string(value)
        else:
            raise ValueError("Checkout must be a string")
        
    @staticmethod
    def get_new_index(prefix : str) -> int:
        index = 1
        invoice = Invoice.query.filter_by(prefix=prefix).order_by(desc(Invoice.index)).first()
        if invoice:
            index = int(invoice.index) + 1
        return index
