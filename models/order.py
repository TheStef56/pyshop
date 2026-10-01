from extensions import db
from datetime import datetime
from models.model import Model
from models.variant import Variant
from models.product import Product
from utils.locale import format_money
from utils.crypto import encrypt_json, decrypt_json
from utils.datetime import parse_datetime
from sqlalchemy import Enum
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict
from enum import Enum as PyEnum

class Status(PyEnum):
    PENDING = 'pending'
    TO_SHIPP = 'to_shipp'
    TO_BILL = 'to_bill'
    TO_BS = 'to_bs'
    COMPLETED = 'completed'

status_translate = {
    Status.PENDING : "In attesa",
    Status.TO_SHIPP : "Da spedire",
    Status.TO_BILL : "Da fatturare",
    Status.TO_BS : "Da spedire e fatturare",
    Status.COMPLETED : "Completato"
}

class Order(Model):
    id = db.Column(db.Integer, primary_key=True)
    cart = db.Column(MutableDict.as_mutable(JSON))
    _checkout = db.Column("checkout", db.Text)  # encrypted field
    products_price = db.Column(db.Float, nullable=False)
    shipment_price = db.Column(db.Float, nullable=False)
    shipment_carrier = db.Column(db.String(64), nullable=False)
    shipment_service = db.Column(db.String(64), nullable=False)
    shipment_service_id = db.Column(db.Integer, nullable=False)
    collection_date = db.Column(db.String(10), nullable=False)
    collection_time = db.Column(db.String(11), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    meta = db.Column(MutableDict.as_mutable(JSON))
    payed = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(Enum(Status), default=Status.PENDING.value)
    reference = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def checkout(self):
        try:
            return decrypt_json(self._checkout) if self._checkout else {}
        except Exception as e:
            return {}

    @checkout.setter
    def checkout(self, value):
        if isinstance(value, dict):
            self._checkout = encrypt_json(value)
        else:
            raise ValueError("Checkout must be a dictionary")

    @staticmethod
    def from_dict(data):
        order = Order(
            id                   = data.get('id'),
            cart                 = data.get('cart'),
            currency             = data.get('currency'),
            products_price       = float(data.get('products_price')),
            shipment_price       = float(data.get('shipment_price')),
            shipment_carrier     = data.get('shipment_carrier'),
            shipment_service     = data.get('shipment_service'),
            shipment_service_id  = int(data.get('shipment_price')),
            collection_date      = data.get('collection_date'),
            collection_time      = data.get('collection_time'),
            meta                 = data.get('meta'),
            payed                = data.get('payed'),
            status               = data.get('staus'),
            reference            = data.get('reference'),
            created_at           = parse_datetime(data.get('created_at')),
            updated_at           = parse_datetime(data.get('updated_at'))
        )
        if 'checkout' in data:
            order.checkout = data['checkout']
        return order

    def to_dict(self) -> dict:
        status = self.status
        if status is None:
            status = Status.PENDING.value
        if not isinstance(status, str):
            status = status.value
        return {
            "id"                  : self.id,
            "cart"                : self.cart,
            "checkout"            : self.checkout,
            "currency"            : self.currency,
            "products_price"      : float(self.products_price),
            "shipment_price"      : float(self.shipment_price),
            "shipment_carrier"    : self.shipment_carrier,
            "shipment_service"    : self.shipment_service,
            "shipment_service_id" : self.shipment_service_id,
            "collection_date"     : self.collection_date,
            "collection_time"     : self.collection_time,
            "meta"                : self.meta,
            "payed"               : self.payed,
            "status"              : status,
            "reference"           : self.reference,
            "created_at"          : self.created_at.isoformat(),
            "updated_at"          : self.updated_at.isoformat()
        }

    def get_total(self, lang_code: str) -> str:
        return format_money(self.shipment_price + self.products_price, self.currency, lang_code)

    def get_shipment_cost(self, lang_code: str) -> str:
        return format_money(self.shipment_price, self.currency, lang_code)
