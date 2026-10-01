import locale
from flask import url_for
from extensions import db
from datetime import datetime
from models.model import Model
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from utils.locale import format_money
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.mutable import MutableDict

class Variant(Model):
    id = db.Column(db.Integer, primary_key=True)
    concrete_id = None
    name = db.Column(MutableDict.as_mutable(JSON))
    description = db.Column(MutableDict.as_mutable(JSON))
    active = db.Column(db.Boolean, default=True, nullable=False)
    data = db.Column(MutableDict.as_mutable(JSON))
    order = db.Column(db.Integer, default=999999, nullable=False)
    images = db.Column(MutableDict.as_mutable(JSON))
    price = db.Column(MutableDict.as_mutable(JSON), nullable=False)
    discount = db.Column(MutableDict.as_mutable(JSON), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    options = db.Column(MutableDict.as_mutable(JSON), nullable=True)
    option = ""
    product_id = db.Column(db.Integer, ForeignKey('product.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship('Product', back_populates="variants")

    def from_option(self, option_id : str) -> dict:
        return {
            "id" : self.id,
            "name" :  self.name,
            "description" : self.description,
            "active" : self.active,
            "product_id" : self.product_id,
            "option" : option_id,
            "data" : self.data,
            "options":  self.options,
            "price" : self.options[option_id]['price'],
            "discount" : self.options[option_id]['discount'],
            "stock" : int(self.options[option_id]['stock']),
            "images" : self.images
        }
    
    @staticmethod
    def from_dict(data, virtual : bool):
        variant = Variant(
            id=data.get('id') if virtual == False else None,
            name=data.get('name'),
            description=data.get('description'),
            active=data.get('active'),
            data=data.get('data'),
            images=data.get('images'),
            price=data.get('price'),
            options=data.get('options'),
            option=data.get('option', None),
            discount=data.get('discount'),
            stock=data.get('stock'),
            product_id=data.get('product_id'),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow()),
        )
        if virtual:
            variant.concrete_id = data.get('id')
        return variant
    
    def to_dict(self):
        data = {
            "id" : self.id,
            "name" : self.name,
            "description": self.description,
            "active": self.active,
            "data": self.data,
            "images": self.images,
            "price": self.price,
            "options": self.options,
            "option": self.option,
            "discount": self.discount,
            "stock": self.stock,
            "product_id": self.product_id,
            "product": self.product.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.concrete_id:
            data['concrete_id'] = self.concrete_id
        return data
    
    def first_image(self):
        if not self.images:
            return None
        return self.images[list(sorted(self.images.keys(), key=lambda k: self.images[k]['order']))[0]]
    
    def get_discount(self, session, option : str) -> float:
        return self.get_discount_for_currency(session['currency'], option)
    
    def get_best_option_discount(self, session) -> float:
        if self.options:
            active_options = [
                opt for opt in self.options.items()
                if opt[1].get("active")
            ]
            if active_options:
                sorted_options = sorted(
                    active_options,
                    key=lambda o: float(o[1]['discount'][session['currency']]),
                    reverse=True
                )
                return self.get_discount(session, sorted_options[0][0])
        return self.get_discount(session, None)
    
    def get_best_option_discount_price(self, session, quantity) -> str:
        if self.options:
            active_options = [
                opt for opt in self.options.items()
                if opt[1].get("active")
            ]
            if active_options:
                sorted_options = sorted(
                    active_options,
                    key=lambda o: float(o[1]['discount'][session['currency']]),
                    reverse=True
                )
                return self.get_price(session, quantity, sorted_options[0][0])
        return self.get_price(session, quantity, None)
    
    def get_best_option_discount_original_price(self, session, quantity) -> str:
        if self.options:
            active_options = [
                opt for opt in self.options.items()
                if opt[1].get("active")
            ]
            if active_options:
                sorted_options = sorted(
                    active_options,
                    key=lambda o: float(o[1]['discount'][session['currency']]),
                    reverse=True
                )
                return self.get_original_price(session, quantity, sorted_options[0][0])
        return self.get_original_price(session, quantity, None)
    
    def get_first_option_discount(self, session) -> float:
        if self.options:
            active_options = [option for option in self.options if self.options[option]['active']]
            if len(active_options) > 0:
                return self.get_discount(session, active_options[0])
        return self.get_discount(session, None)
    
    def get_discount_for_currency(self, currency : str, option : str) -> float:
        discount = 0.0
        if option:
            discount = self.options[option]['discount'][currency.lower()]
            if discount:
                return discount
            return 0.0
        if self.discount:
            discount = self.discount[currency.lower()]
            if discount:
                return discount
        return 0.0
    
    def get_original_price(self, session, quantity : int , option : str) -> str:
        price = float(self.price[list(self.price.keys())[0]])
        if (session["currency"] in list(self.price.keys())):
            price = self.price[session['currency']]
        if option:
            price = self.options[option]['price'][session['currency']]
        price = (float(price)) * quantity
        return format_money(price, session['currency'].upper(), session['lang'])
    
    def get_float_original_price_for_currency(self, currency, quantity, option : str) -> str:
        price = float(self.price[list(self.price.keys())[0]])
        if (currency.lower() in list(self.price.keys())):
            price = self.price[currency.lower()]
        if option:
            price = self.options[option]['price'][currency.lower()]
        return (float(price)) * quantity
    
    def get_first_option_original_price(self, session, quantity) -> str:
        if self.options:
            active_options = [option for option in self.options if self.options[option]['active']]
            if len(active_options) > 0:
                return self.get_original_price(session, quantity, active_options[0])
        return self.get_original_price(session, quantity, None)
    
    def get_price(self, session, quantity : int, option : str) -> str:
        price = float(self.price[list(self.price.keys())[0]])
        discount = self.get_discount(session, option)
        if option:
            price = self.options[option]['price'][session['currency']] 
        elif (session["currency"] in list(self.price.keys())):
            price = self.price[session['currency']]
        price = ((float(price)) - ((float(price) / 100 ) * float(discount))) * quantity
        return format_money(price, session['currency'].upper(), session['lang'])
    
    def get_first_option_price(self, session, quantity) -> str:
        if self.options:
            active_options = [option for option in self.options if self.options[option]['active']]
            if len(active_options) > 0:
                return self.get_price(session, quantity, active_options[0])
        return self.get_price(session, quantity, None)
    
    def get_float_price_for_currency(self, currency : str, quantity : int, option : str) -> float:
        price = float(self.price[list(self.price.keys())[0]])
        discount = self.get_discount_for_currency(currency, option)
        if currency.lower() in list(self.price.keys()):
            price = self.price[currency.lower()]
        return ((float(price)) - ((float(price) / 100 ) * float(discount))) * quantity

    def get_float_price(self, session, quantity : int, option : str) -> float:
        return self.get_float_price_for_currency(session['currency'], quantity, option)
    
    def get_page_url(self):
        active_options = None
        if self.options:
            active_options = [option for option in self.options if self.options[option]['active']].sort(key=lambda x: self.options[x]["order"])
        if not active_options:
            return url_for('public.product', product_id=self.product.id, variant_id=self.id)
        return url_for('public.product_variant_option', product_id=self.product.id, variant_id=self.id, option_id=active_options[0] if active_options else None)

    def order_options(self) -> None:
        if self.options:
            self.options = dict(sorted(self.options.items(), key=lambda item: item[1]['order']))

    def order_images(self) -> None:
        if self.images:
            self.images = dict(sorted(self.images.items(), key=lambda item: item[1]['order']))

    def get_ordered_images(self) -> list:
        self.order_images()
        if self.images:
            return self.images.items()
        return []