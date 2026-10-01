from extensions import db
from datetime import datetime
from models.model import Model
from models.variant import Variant
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict
from .product_category_assoc import product_categories
from .product_label_assoc import product_labels
from models.label import Label

class Product(Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(MutableDict.as_mutable(JSON))
    description = db.Column(MutableDict.as_mutable(JSON))
    active = db.Column(db.Boolean, default=True, nullable=False)
    data = db.Column(MutableDict.as_mutable(JSON))
    more_info = db.Column(db.String(2048), nullable=True)
    shipping_width = db.Column(db.Integer, default=0.0, nullable=False)
    shipping_length = db.Column(db.Integer, default=0.0, nullable=False)
    shipping_height = db.Column(db.Integer, default=0.0, nullable=False)
    shipping_weight = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # one to many relation
    variants = relationship(
        Variant, back_populates="product", cascade="all, delete-orphan", order_by="Variant.order"
    )

    labels = db.relationship(
        Label,
        secondary=product_labels,
        backref=db.backref("products", lazy="dynamic"),
        lazy="dynamic"
    )


    @staticmethod
    def from_dict(data):
        return Product(
            id=data.get("id"),
            name=data.get("name"),
            active=data.get("active"),
            description=data.get("description"),
            data=data.get("data"),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
            shipping_width=data.get("shipping_width", 0),
            shipping_length=data.get("shipping_length", 0),
            shipping_height=data.get("shipping_height", 0),
            shipping_weight=data.get("shipping_weight", 0.0)
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
            "shipping_width": self.shipping_width,
            "shipping_length": self.shipping_length,
            "shipping_height": self.shipping_height,
            "shipping_weight": self.shipping_weight,
        }

    def first_variant(self) -> Variant:
        if len(self.variants) == 0:
            return Variant()
        return self.variants[0]

    def first_variant_images(self) -> dict:
        if len(self.variants) == 0:
            return {}
        self.variants[0].order_images()
        return self.variants[0].images

    def first_variant_discount(self, session) -> float:
        if len(self.variants) == 0:
            return 0.0
        #se la variante ha almeno una versione attiva prendi quella
        if self.variants[0].options:
            active_options = [option for option in self.variants[0].options if self.variants[0].options[option]['active']]
            if len(active_options) > 0:
                return self.variants[0].get_discount(session, active_options[0])
        return self.variants[0].get_discount(session, None)

    def first_variant_original_price(self, session, quantity) -> str:
        if len(self.variants) == 0:
            return ""
        if self.variants[0].options:
            active_options = [option for option in self.variants[0].options if self.variants[0].options[option]['active']]
            if len(active_options) > 0:
                return self.variants[0].get_original_price(session, quantity, active_options[0])
        return self.variants[0].get_original_price(session, quantity, None)

    def first_variant_price(self, session, quantity) -> str:
        if len(self.variants) == 0:
            return ""
        #se la variante ha almeno una versione attiva prendi quella 
        if self.variants[0].options:
            active_options = [option for option in self.variants[0].options if self.variants[0].options[option]['active']]
            if len(active_options) > 0:
                return self.variants[0].get_price(session, quantity, active_options[0])
        return self.variants[0].get_price(session, quantity, None)

    def add_category(self, category_id):
        """Add a category by ID"""
        stmt = product_categories.insert().values(
            product_id=self.id,
            category_id=category_id
        )
        db.session.execute(stmt)
        
    def remove_category(self, category_id):
        """Remove a category by ID"""
        stmt = product_categories.delete().where(
            product_categories.c.product_id == self.id,
            product_categories.c.category_id == category_id
        )
        db.session.execute(stmt)
    
    def get_category_ids(self):
        """Get all category IDs for this product"""
        stmt = product_categories.select().where(
            product_categories.c.product_id == self.id
        )
        result = db.session.execute(stmt)
        return [row.category_id for row in result]
    
    def get_labels_ids(self):
        """Get all label IDs for this product"""
        stmt = db.select(product_labels.c.label_id).where(
            product_labels.c.product_id == self.id
        )
        result = db.session.execute(stmt)
        return [row.label_id for row in result]
    
