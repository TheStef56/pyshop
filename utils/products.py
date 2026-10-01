from flask import session
from models import Product

def flatten_and_sort(variants, request):
    flatted_variants = []
    for variant in variants:
        product = Product.query.filter(Product.id == variant.product_id).first()
        name = product.name[session['lang']]
        v = {
            "product" : product,
            "location" : variant.get_page_url(),
            "name" : name,
            "images" : variant.get_ordered_images(),
            "discount" : variant.get_best_option_discount(session),
            "original_price": variant.get_best_option_discount_original_price(session, 1),
            "price": variant.get_best_option_discount_price(session, 1)
        }
        flatted_variants.append(v)
    
    sort = request.args.get('order', '') 
    if sort:
        if sort == "best_price":
            flatted_variants = sorted(
                flatted_variants,
                key=lambda item: float(item['price'].replace("$", "").replace("€", "").replace(",","."))
            )
        if sort == "best_discount":
            flatted_variants = sorted(
                flatted_variants,
                key=lambda item: float(item['discount']), reverse=True
            )
            pass
        pass
    return flatted_variants