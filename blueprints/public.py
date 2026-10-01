import traceback, os, json
from rich.console import Console
from rich.traceback import Traceback
from app import mail_noreply
from extensions import db
from models.product_category_assoc import product_categories
from models.product_label_assoc import product_labels
from flask_babel import _
from flask_mail import Message
from sqlalchemy import desc, asc
from extensions import cache
from datetime import datetime
from models.order import Order
from html2text import html2text
from mails.summary import Summary
from models.product import Product
from models.label import Label
from models.variant import Variant
from models.settings import Setting
from utils.locale import format_money
from utils.paypal import PaypalCheckout
from utils.categories import build_tree
from middlewares.shop import is_shop_open
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from utils.products import flatten_and_sort
from utils.packlink.preview import PacklinkPreview
from utils.packlink.shipping import PacklinkShipping
from utils.packlink.tracking import PacklinkTracking
from utils.locale import country_name_to_code, eur_to_usd
from utils.cart import group_products, remove_product, increase, decrease, prices, group_products_list
from flask import Blueprint, render_template, abort, session, jsonify, request, redirect, url_for, flash, current_app, send_from_directory
from models.order import Status
from math import ceil


public_blueprint = Blueprint('public', __name__, static_folder="../static/uploads/public", template_folder="templates/public")
with open(os.path.dirname(__file__) + "/../static/country_regions.json", encoding="utf-8") as cr:
    country_data = json.load(cr)

REGIONS = {}

for country in country_data:
    REGIONS.update({country["countryName"] : [ region.get("name") for region in country.get("regions", []) ]})

console = Console()

# Add context processor
@public_blueprint.context_processor
def inject_global_settings():
    settings = Setting.query.filter_by(name='global').first()
    return dict(global_settings=settings)

@public_blueprint.before_app_request
def check_language():
    if not session.get('lang'):
        session['lang'] = os.getenv('DEFAULT_LANGUAGE', 'en')
    if not session.get('extended_lang_code'):
        session['extended_lang_code'] = os.getenv('DEFAULT_LANGUAGE_EXTENDED_LANGUAGE', 'en-US')

@public_blueprint.before_app_request
def check_currency():
    if not session.get('currency'):
        session['currency'] = 'eur'

@public_blueprint.route('/favicon<size>')
@public_blueprint.route('/android-chrome<size>')
@public_blueprint.route('/android-chrome<size>')
def favicon(size):
    return send_from_directory(os.path.join(current_app.root_path, 'static/uploads/public'),f'favicon{size}')

@public_blueprint.route('/', methods=['GET'])
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 9, type=int) #TODO: see customize pagination or have it as a preference?
    label_id = request.args.get('brand', type=int)

    total = Variant.query.count()

    variants_query = (
        Variant.query
        .join(Product)
        .filter(Product.variants.any())
        .options(joinedload(Variant.product))
        .order_by(desc(Product.created_at))
    )

    if label_id is not None:
        variants_query = variants_query.filter(
            Product.labels.any(Label.id == label_id)
        )

    variants_page = variants_query.paginate(page=page, per_page=per_page, error_out=False)

    products_for_page = {v.product for v in variants_page.items}

    global_settings = Setting.query.filter_by(name='global').first()
    categories = None
    if global_settings:
        categories = global_settings.meta.get('categories', None)
        if categories:
            categories = build_tree(categories)

    labels = (
        Label.query
        .join(product_labels)
        .join(Product)
        .filter(Product.id.in_([p.id for p in products_for_page]))
        .distinct()
        .order_by(asc(Label.name))
        .all()
    )

    flatted_variants = flatten_and_sort(variants_page.items, request)
    return render_template(
        'public/views/index.html',
        variants = flatted_variants,
        categories = categories,
        labels = labels,
        pagination = {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': ceil(total / per_page)
            },
        relevance=True
    )

@public_blueprint.route('/contacts', methods=['GET'])
def contacts():
    return render_template('public/views/contacts.html')

@public_blueprint.route('/home', methods=['GET'])
def home():
    return render_template('public/views/home.html', hide_sidebar=True, hide_header=False)


@public_blueprint.route('/search', methods=['GET'])
def search():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 9, type=int) #TODO: see customize pagination or have it as a preference?
    search_query = request.args.get('q', '').strip()

    if not search_query:
        return redirect(url_for('public.index'))

    total = Variant.query.count()

    variants_query = (
        Variant.query
        .join(Product)
        .filter(Product.variants.any())
        .filter(Product.name.ilike(f"%{search_query}%"))
        .options(joinedload(Variant.product))
        .order_by(desc(Product.created_at))
    )

    variants_page = variants_query.paginate(page=page, per_page=per_page, error_out=False)

    flatted_variants = flatten_and_sort(variants_page.items, request)

    return render_template(
        'public/views/index.html',
        variants = flatted_variants,
        categories = None,
        labels = None,
        relevance = False,
        pagination = {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': ceil(total / per_page)
            }
    )

@public_blueprint.route('/category/<id>', methods=['GET'])
def category_index(id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 9, type=int) #TODO: see customize pagination or have it as a preference?
    label_id = request.args.get('brand', type=int)

    global_settings = Setting.query.filter_by(name='global').first()
    categories = None
    if global_settings:
        cats = global_settings.meta.get('categories', None)
        if cats:
            categories = build_tree(cats)

    total = Variant.query.count()

    variants_query = (
        Variant.query
        .join(Product)
        .filter(Product.variants.any())
        .filter(Product.id.in_(
            db.session.query(product_categories.c.product_id)
            .filter(product_categories.c.category_id == id)
        ))
        .options(joinedload(Variant.product))
        .order_by(desc(Product.created_at))
    )

    if label_id is not None:
        variants_query = variants_query.filter(
            Product.labels.any(Label.id == label_id)
        )

    variants_page = variants_query.paginate(page=page, per_page=per_page, error_out=False)

    labels = (
        Label.query
        .join(product_labels)
        .join(Product)
        .filter(Product.id.in_(
            db.session.query(product_categories.c.product_id)
            .filter(product_categories.c.category_id == id)
        ))
        .distinct()
        .order_by(asc(Label.name))
        .all()
    )

    flatted_variants = flatten_and_sort(variants_page.items, request)

    return render_template(
        'public/views/index.html',
        variants = flatted_variants,
        categories = categories,
        labels = labels,
        relevance = True,
        pagination = {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': ceil(total / per_page)
            }
    )


@public_blueprint.route('/cookies', methods=['GET'])
def cookies():
    support_mail = ''
    if session.get('settings') and session['settings'].get('header'):
        support_mail = session['settings']['header'].get('support_mail', '')
    return render_template('public/views/cookies.html', support_mail=support_mail)

@public_blueprint.route('/privacy-policy', methods=['GET'])
def privacy_policy():
    pp = ""
    pp = Setting.query.filter_by(name='privacy_policy').first()
    if pp:
        pp = pp.meta.get(session['lang'], '')
    return render_template('public/views/privacy_policy.html', privacy_policy=pp)

@public_blueprint.route('/product/<product_id>/variant/<variant_id>')
def product(product_id, variant_id):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    variant.order_images()
    product.label = product.labels.first()
    if variant.options:
        variant.order_options()
        if len([ option for option in variant.options if variant.options[option]['active']]) > 0:
            return redirect(url_for('public.product_variant_option', product_id=product_id, variant_id=variant_id, option_id=list(variant.options.keys())[0]))
    global_settings = Setting.query.filter_by(name='global').first()
    categories = None
    if global_settings:
        cats = global_settings.meta.get('categories', None)
        if cats:
            categories = build_tree(cats)
    if not product or not variant:
        return abort(404)
    return render_template('public/views/product_variant.html', product=product, variant=variant.to_dict(), Variant=Variant, categories=categories, relevance=None)

@public_blueprint.route('/product/<product_id>/variant/<variant_id>/option/<option_id>')
def product_variant_option(product_id, variant_id, option_id):
    global_settings = Setting.query.filter_by(name='global').first()
    categories = None
    if global_settings:
        cats = global_settings.meta.get('categories', None)
        if cats:
            categories = build_tree(cats)
    product = Product.query.filter_by(id=product_id).first()
    product.label = product.labels.first()
    variant = Variant.query.filter_by(id=variant_id).first()
    variant.order_options()
    variant.order_images()

    if not product or not variant:
        return abort(404)
    if not variant.options.get(option_id):
        return abort(404)
    settings = Setting.query.filter_by(name='global').first()
    preview_variant = variant.from_option(option_id)

    return render_template('public/views/product_variant.html', product=product, variant=preview_variant, Variant=Variant, current_option=option_id, global_settings=settings, categories=categories, relevance=None)

@public_blueprint.route('/cart/<variant_id>/add', methods=['POST'])
def add_product(variant_id):
    variant = Variant.query.filter_by(id=variant_id).first()
    if not variant:
        return abort(404)
    cart = session.get('cart', [])
    cart.append(variant.to_dict())
    session["cart"] = cart
    return "OK", 200

@public_blueprint.route('/cart/<variant_id>/option/<option_id>/add', methods=['POST'])
def add_product_option(variant_id, option_id):
    variant = Variant.query.filter_by(id=variant_id).first()
    if not variant:
        return abort(404)
    if not variant.options[option_id]:
        return abort(404)
    cart = session.get('cart', [])
    cart.append(variant.from_option(option_id))
    session["cart"] = cart
    return "OK", 200

@public_blueprint.route('/cart', methods=["GET"])
@is_shop_open()
def cart():
    product_variants = group_products()
    return render_template('public/views/cart.html', product_variants=product_variants)

@public_blueprint.route('/cart/<id>/remove', methods=["PUT"])
def cart_remove(id):
    if remove_product(id):
        return "OK", 200
    return abort(403)

@public_blueprint.route('/cart/<id>/remove_quantity', methods=['PUT'])
def cart_remove_quantity(id):
    if decrease(id):
        return "OK", 200
    return abort(403)

@public_blueprint.route('/cart/<id>/add_quantity', methods=['PUT'])
@is_shop_open()
def cart_add_product_variant(id):
    if increase(id):
        return "OK", 200
    return abort(403)

@public_blueprint.route('/cart/prices', methods=['GET'])
def cart_prices():
    return jsonify(prices())

@public_blueprint.route('/checkout', methods=['GET'])
@is_shop_open()
def checkout():
    products = group_products()
    products_price = prices()

    from forms.public.checkout import CheckoutForm
    form = CheckoutForm() 
    shipping_country = None
    shipping_region = None
    billing_country = None
    billing_region = None
    if 'checkout_data' in session: #if form stored in session load it
        data = session['checkout_data']
        shipping_country = data["shipping_country"]
        shipping_region = data["shipping_region"]
        billing_country = data["billing_country"]
        billing_region = data["billing_region"]
        form.process(data=data)
    return render_template("/public/views/checkout.html", 
                           product_variants=products,
                           prices = products_price,
                           form=form, 
                           shipping_country=shipping_country,
                           shipping_region=shipping_region,
                           billing_country=billing_country,
                           billing_region=billing_region
                           )

@public_blueprint.route('/shipment-checkout', methods=['POST', 'GET'])
@is_shop_open()
def shipment_checkout():
    if request.method == 'GET':
        return redirect(url_for('public.checkout'))
    raw_cart = session.get('cart', [])
    if len(raw_cart) == 0: #check that cart have products
        return redirect(url_for('public.cart'))
    from forms.public.checkout import CheckoutForm
    form = CheckoutForm()
    session['checkout_data'] = request.form.to_dict()
    if form.validate_on_submit():
        shipping_country_code = country_name_to_code(session['checkout_data']['shipping_country'])
        shipping_postal_code = session['checkout_data']['shipping_postal_code']
        if not shipping_country_code or not shipping_postal_code:
            #TODO: ritorna una pagina di avviso che informa del malfunzionamento, con invito a segnalare via email
            pass
        try:
            user = os.getenv("PACKLINK_EMAIL")
            password = os.getenv("PACKLINK_PASSWORD")
            packlink = PacklinkPreview(user, password, os.getenv('SHIPPING_COUNTRY'),shipping_country_code,int(os.getenv('SHIPPING_POSTAL_CODE')),int(shipping_postal_code))
            packlink.login()

            products = group_products_list(raw_cart)
            for key in products:
                product = products[key]
                for i in range(0, product['quantity']):
                    packlink.add_package(
                        int(product['product'].shipping_width),
                        int(product['product'].shipping_length),
                        int(product['product'].shipping_height),
                        float(product['product'].shipping_weight)
                    )
            packlink.makereq()
            packlink.select_best()        
            packlink.logout()   
            if session["currency"] == "usd":
                packlink.price = eur_to_usd(packlink.price)
            packlink.display_price = format_money(packlink.price, session["currency"].upper(), session['lang'])
        except Exception as e:
            packlink = None
            #TODO: ritorna una pagina di avviso che informa del malfunzionamento, con invito a segnalare via email
            tb = Traceback.from_exception(type(e), e, e.__traceback__)
            console.print(tb)
            pass

        raw_cart = session.get('cart', [])
        grouped = {}
        grouped["total_price"] = 0

        products_price = prices()
        
        products_price = round(float(products_price["total_price"]) * 1.22, 2)
        shipment_price = round(float(packlink.price) * 1.22, 2)
        total_price = products_price + shipment_price
        session['total_price'] = round(total_price,2)

        # crea template dell'ordine in sessione
        session['order'] = {
            "id"                  : None,
            "cart"                : {"raw": raw_cart},
            "checkout"            : session['checkout_data'],
            "currency"            : session['currency'].upper(),
            "products_price"      : products_price,
            "shipment_price"      : shipment_price,
            "shipment_carrier"    : packlink.carrier,
            "shipment_service"    : packlink.service,
            "shipment_service_id" : packlink.id,
            "collection_date"     : packlink.collection_date,
            "collection_time"     : packlink.collection_time,
            "meta"                : {},
            "payed"               : True,
            "status"              : Status.PENDING,
            "reference"           : "",
            "created_at"          : datetime.now(),
            "updated_at"          : datetime.now()
        }

        total_price = format_money(total_price, session['currency'].upper(), session['lang'])

        return render_template(
            "/public/views/shipment-checkout.html", 
            packlink=packlink, 
            product_variants=group_products(), 
            total_price = total_price
        )
    else:
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
    return redirect(url_for('public.checkout'))

@public_blueprint.route('/pay/paypal', methods=['GET'])
@is_shop_open()
def paypal_pay():
    #TODO: incapsulare in un try catch e nel caso restituire una pagina "riprova più tardi"
    total_price = session.get('total_price',0)
    if total_price <= 0:
        return abort(401)
    paypal_checkout = PaypalCheckout(cache)

    c_data = session['checkout_data']

    billing_street =    f"{c_data['billing_street']} {c_data['billing_number']}"
    billing_name =         c_data['billing_name']
    billing_lastname =      c_data['billing_lastname']
    billing_city =         c_data['billing_city']
    billing_country_name = c_data['billing_country']
    billing_postal_code =  c_data['billing_postal_code']
    billing_country_code = ""
    for c in country_data:
        if c['countryName'] == billing_country_name:
            billing_country_code = c['countryShortCode']
            break

    shipping_street =    f"{c_data['shipping_street']} {c_data['shipping_number']}"
    shipping_name =         c_data['shipping_name']
    shipping_lastname =      c_data['shipping_lastname']
    shipping_city =         c_data['shipping_city']
    shipping_country_name = c_data['shipping_country']
    shipping_postal_code =  c_data['shipping_postal_code']
    shipping_country_code = ""
    for c in country_data:
        if c['countryName'] == shipping_country_name:
            shipping_country_code = c['countryShortCode']
            break

    paypal_checkout.add_billing_data(billing_name, billing_lastname, billing_street, billing_city, "", billing_postal_code, billing_country_code)
    paypal_checkout.add_shipping_data(shipping_name, shipping_lastname, shipping_street, shipping_city, "", shipping_postal_code, shipping_country_code)
    order = paypal_checkout.create_order(total_price, session['currency'].upper())
    return redirect(next(link["href"] for link in order["links"] if link["rel"] == "approve"))

@public_blueprint.route("/payment/paypal/success")
@is_shop_open()
def paypal_success():
    order_id = request.args.get("token")
    paypal_checkout = PaypalCheckout(cache)

    result = None
    status = None

    # Prova a leggere 'status' fino a 3 volte
    for attempt in range(3):
        try:
            result = paypal_checkout.capture_order(order_id)
            status = result.get('status')
            if status:
                break
            if status == 'COMPLETED':
                break
        except Exception as e:
            print(f"Tentativo {attempt + 1}: errore nell’ottenere 'status' - {e}")
            traceback.print_exc()

    # Se dopo 3 tentativi status non è stato ottenuto
    if status != 'COMPLETED':
        # TODO: manda un’email di avviso con l’errore
        return render_template('/public/views/payment/error.html')

    # Elabora l'ordine come pagato
    order = session.get('order', None)
    if not order:
        return render_template('/public/views/payment/error.html')

    # TODO: capire che cazzo fare se si arriva in questo punto con sessione vuota ( NON DOVREBBE SUCCEDERE )
    order = Order.from_dict(session['order'])
    order.payed = True
    order.meta = {
        "payment_method": "paypal",
        "order_id": order_id
    }
    db.session.add(order)
    db.session.flush()

    # Crea la spedizione su pro.packlink.it
    user = os.getenv("PACKLINK_EMAIL")
    password = os.getenv("PACKLINK_PASSWORD")
    shipping = PacklinkShipping(user, password)
    shipping.login()
    checkout = order.checkout
    address = f"{checkout['shipping_street']}, {checkout['shipping_number']}"
    with open(os.path.dirname(__file__) + "/../static/country_regions.json", encoding="utf-8") as cr:
        country_data = json.load(cr)
        for state in country_data:
            if state["countryName"] == checkout["billing_country"]:
                short_code = state["countryShortCode"]
    shipping.set_shipping_details(
        checkout["billing_city"],
        short_code,
        checkout["billing_country"],
        checkout["billing_postal_code"],
        checkout["billing_email"],
        checkout["billing_name"],
        checkout["billing_phone"],
        address,
        checkout["billing_lastname"],
        'to'
        )
    shipping.set_shipping_details(
        os.getenv("SHIPPING_CITY"),
        os.getenv("SHIPPING_COUNTRY"),
        os.getenv("SHIPPING_STATE"),
        os.getenv("SHIPPING_POSTAL_CODE"),
        os.getenv("SHIPPING_EMAIL"),
        os.getenv("SHIPPING_NAME"),
        os.getenv("SHIPPING_PHONE"),
        os.getenv("SHIPPING_ADDRESS"),
        os.getenv("SHIPPING_SURNAME"),
        'from'
    )
    shipping.carrier_details(
        order.shipment_carrier,
        order.shipment_service,
        order.shipment_service_id,
        order.collection_date,
        order.collection_time,
        round(order.products_price,2),
        "Abbigliamento",
        "EUR"
    )

    products = group_products_list(order.cart['raw'])
    for key in products:
        product = products[key]
        for i in range(0, product['quantity']):
            shipping.append_package(
                int(product['product'].shipping_width),
                int(product['product'].shipping_length),
                int(product['product'].shipping_height),
                float(product['product'].shipping_weight)
            )
            
    shipping.additional_data(
        os.getenv("SHIPPING_REGION"),
        checkout["shipping_region"]
    )
    if not shipping.commit_shipment():
        print("Error with automatic shipping generation")
    shipping.logout()
    order.reference = shipping.reference

    if order.save():
        products = group_products_list(order.cart['raw'])
        for identifier in products:
            concrete_variant = Variant.query.filter_by(id=products[identifier]['variant'].concrete_id).first()
            if (products[identifier]['variant'].option):
                concrete_variant.options[products[identifier]['variant'].option]['stock'] = int(concrete_variant.options[products[identifier]['variant'].option]['stock']) - int(products[identifier]['quantity'])
                flag_modified(concrete_variant, 'options')
                concrete_variant.save()
            else:
                concrete_variant.stock -= int(products[identifier]['quantity'])
                concrete_variant.save()

        summary_mail = Summary(products, order)
        html = summary_mail.html()
        msg = Message(
            subject=_('Order received'),
            recipients=[order.checkout['billing_email']],
            body=html2text(html),
            html=html,
            bcc=["dopeshirts.orders@gmail.com"]
        )
        mail_noreply.send(msg)

        session.pop('cart', None)
        session.pop('order', None)

        return render_template('/public/views/payment/completed.html', order=order)
    return abort(500)

@public_blueprint.route("/payment/paypal/cancel")
def paypal_cancelled():
    order = session.get('order', None)
    if order:
        order = Order.from_dict(order)
        order.delete() #cancella l'ordine dal database
        session.pop('order')
    return render_template('/public/views/payment/cancelled.html')

@public_blueprint.route("/track/<reference>")
def track(reference):
    # test = {
    #         "history": [
    #             {
    #             "timestamp": 14242322,
    #             "description": "DELIVERED",
    #             "city": "MIAMI"
    #             },
    #             {
    #             "timestamp": 14124132,
    #             "description": "DESTINATION SCAN",
    #             "city": "MIAMI"
    #             },
    #             {
    #             "timestamp": 12424312,
    #             "description": "ARRIVAL SCAN",
    #             "city": "MIAMI"
    #             }
    #         ]
    #     }
    # for entry in test["history"]:
    #                 entry["timestamp"] = datetime.fromtimestamp(entry["timestamp"]*100).strftime("%Y/%m/%d - %H:%M:%S")
    # return render_template("/public/views/tracking.html", result=test, error=None)
    error = None
    result = None
    user = os.getenv("PACKLINK_EMAIL")
    password = os.getenv("PACKLINK_PASSWORD")
    tracking = PacklinkTracking(user, password)
    tracking.login()
    tracking.get_shipment(reference)
    if tracking.shipping_res.status_code == 404:
        tracking.logout()
        error=_("Package not found!")
    else:
        tracking.get_tracking(reference) 
        tracking.logout()
        if tracking.tracking_res.status_code == 404:
            error= _("Shipping has not begun yet!")
        else:
            try:
                result = tracking.tracking_res.json()
                for entry in result["history"]:
                    entry["timestamp"] = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y/%m/%d - %H:%M:%S")
            except:
                error = f"Error getting tracking info for shipping {reference}"
    return render_template("/public/views/tracking.html", result=result, error=error)

@public_blueprint.route("/get_regions/<country>")
def regions(country):
    res =  REGIONS.get(country)
    return res if res else []