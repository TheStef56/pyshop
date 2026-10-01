import hashlib
import json
import copy
from flask import session
from models.product import Product
from models.variant import Variant

def get_variant_virtual_identifier(data: dict) -> str:
    return "variant_" + str(data['id']) + "_option_" + data.get('option', '')

def group_products_list(cart : dict) -> dict:
    group = {}
    for o in cart:
        identifier = get_variant_virtual_identifier(o)
        if not identifier in group:
            group[identifier] = {
                "product": Product.query.filter_by(id=o['product_id']).first(),
                "variant": Variant.from_dict(o, True),
                "quantity": 0
            }
        group[identifier]["quantity"] += 1
    return group 

def group_products() -> dict:
    cart = session.get('cart', [])
    return group_products_list(cart)

def prices_list(cart : dict, currency : str) -> dict:
    products = group_products_list(cart)
    grouped = {"total_price" : 0}
    for identifier in products:
        grouped[identifier] = {}
        grouped[identifier]['total_price'] = products[identifier]['variant'].get_float_price_for_currency(currency, int(products[identifier]['quantity']), products[identifier]['variant'].option)
        grouped['total_price'] += grouped[identifier]['total_price']
    return grouped

def prices() -> dict:
    cart = session.get('cart', [])
    return prices_list(cart, session['currency'])


def remove_product(identifier: str) -> bool:
    cart = session.get('cart', [])
    new_cart = []
    for o in cart:
        current_id = get_variant_virtual_identifier(o)
        if current_id == identifier:
            continue
        new_cart.append(o)

    session['cart'] = new_cart
    return True

def increase(identifier : str) -> bool:
    cart = session.get('cart', [])
    products = group_products()
    for _id in products:
        if _id == identifier:
            if not products[_id]['variant'].stock >= (products[_id]['quantity'] + 1):
                return False

    for o in cart:
        current_id = get_variant_virtual_identifier(o)
        if current_id == identifier:
            cart.append(copy.deepcopy(o))
            return True
    return False

def decrease(identifier: str) -> bool:
    cart = session.get('cart', [])
    new_cart = []
    removed = False

    for o in cart:
        current_id = get_variant_virtual_identifier(o)
        if not removed and current_id == identifier:
            removed = True
            continue
        new_cart.append(o)

    session['cart'] = new_cart
    return True
