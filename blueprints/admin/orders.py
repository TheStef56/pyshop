from io import BytesIO
from zipfile import ZipFile
from sqlalchemy import desc, func, text, cast, JSON, String
from sqlalchemy.orm import aliased
from models.invoice import Invoice
from utils.fattura.fattura import Fattura
from middlewares.with_user import with_user
from middlewares.permission import permission
from utils.cart import group_products_list, prices_list
from models.order import Order, Status, status_translate
from models.variant import Variant
from extensions import db
from utils.locale import country_name_to_code, format_money
from flask import Blueprint, Response, send_file, render_template, abort, redirect, request, flash, jsonify, url_for


orders_blueprint = Blueprint('admin_orders', __name__, template_folder='templates/admin')

INVOICE_PREFIX = 'DS'

@orders_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)

@orders_blueprint.route('/admin/orders', methods=['GET'])
@permission('view_orders')
def view(user):
    return render_template('admin/views/orders.html', user=user, status=Status, status_translate=status_translate)

@orders_blueprint.route('/admin/orders/list', methods=['GET'])
@permission('view_orders')
def list(user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    group = request.args.get('group', "false") == "true"

    status_filter = request.args.get('status', type=int)

    check = []
    for id, status in enumerate(Status):
        if status_filter & (id << 1):
            check.append(status)

    if not group:
        query = Order.query
        if status_filter != 31:
            query = query.where(Order.status.in_(check))
        total = query.count()
        orders = query.order_by(desc(Order.id)).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        dicted_orders = [o.to_dict() for o in orders.items]
        for o in dicted_orders:
            o['translated_status'] = status_translate[Status(o['status'])]
        
        result = dicted_orders

    else:
        subquery = (
            db.session.query(
                Variant.id.label('variant_id'),
                func.count(Order.id).label('order_count')
            )
            .join(
                Order,
                func.json_contains(
                    func.json_extract(Order.cart, '$.raw[*].id'),
                    cast(Variant.id, JSON)
                )
            )
            .filter(Order.status._in(check) if status_filter != 31 else True)
            .group_by(Variant.id)
            .subquery()
        )

        query = (
            db.session.query(Variant, subquery.c.order_count)
            .join(subquery, Variant.id == subquery.c.variant_id)
            .order_by(subquery.c.order_count.desc())
        )

        total = query.count()
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        result = []
        for variant, order_count in pagination.items:
            d = variant.to_dict()
            d['main_name'] = d['name']['it']
            d['product_name'] = d['product']['name']['it']
            d['order_count'] = order_count
            result.append(d)

    return jsonify({
            'data': result,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total/per_page)
            }
        })

@orders_blueprint.route('/admin/order/<id>/edit', methods=['GET'])
@permission('edit_orders')
def edit(user, id):
    order = Order.query.filter_by(id=id).first()
    products = group_products_list(order.cart['raw'])
    prices = prices_list(order.cart['raw'], order.currency)
    return render_template(
        '/admin/views/orders/edit.html', 
        user=user, 
        order=order,
        products=products, 
        prices=prices,
        status=Status, 
        status_translate=status_translate,
        format_money=format_money
    )

@orders_blueprint.route('/admin/order/<id>/update', methods=['POST'])
@permission('edit_orders')
def update(user, id):
    order = Order.query.filter_by(id=id).first()
    order.status = request.form['status']
    order.payed = request.form['payed'] == 'true'
    if order.save():
        flash('Variante salvata correttamente', "success")
    else:
        flash('Un errore ha impedito l\'aggiornamento dell\'ordine', 'danger')
    return redirect(url_for('admin_orders.edit', id=id))

@orders_blueprint.route('/admin/order/<id>/delete', methods=['DELETE'])
@permission('delete_orders')
def delete(user, id):
    order = Order.query.filter_by(id=id).first()
    invoices = Invoice.query.filter_by(order_id=id).all()
    for invoice in invoices:
        if not invoice.delete():
            return abort(403)
    
    if order and order.delete():
        return "OK", 200
    return abort(404)

def new_order_invoice(order : Order, prefix : str):
    index = Invoice.get_new_index(prefix)
    concrete_index = f"{index:08d}"

    fattura = Fattura(
        enterprise=False,
        divisa=order.currency,
        prog_inv=f"{prefix}{concrete_index}",
    )

    fattura.add_info(
        SSN=order.checkout['billing_fiscal_code'],
        CAP=order.checkout['billing_postal_code'],
        comune=order.checkout['billing_city'],
        nazione=country_name_to_code(order.checkout['billing_country']),
        via=order.checkout["billing_street"],
        numero=order.checkout["billing_number"]
    )

    fattura.add_anagraph(
        nome=order.checkout['billing_name'],
        cognome=order.checkout['billing_lastname'],
    )
    
    cart = group_products_list(order.cart['raw'])

    for variant_id in cart:
        product_name = cart[variant_id]['product'].name['it']
        variant_name = cart[variant_id]['variant'].name['it']
        quantity = cart[variant_id]['quantity']
        price = cart[variant_id]['variant'].get_float_original_price_for_currency(order.currency, 1, cart[variant_id]['variant'].option)
        discount = cart[variant_id]['variant'].get_discount_for_currency(order.currency, cart[variant_id]['variant'].option)
        fattura.add_product(
            amount=quantity,
            description=product_name + " - " + variant_name,
            price=price,
            discount=discount
        )

    fattura.process()
    invoice = Invoice(
        index=index,
        prefix=prefix,
        order_id=order.id,
        invoice=fattura.XML_as_string()
    )
    return invoice

@orders_blueprint.route('/admin/order/<id>/download-invoice', methods=['GET'])
@permission('download_invoices')
def download_invoice(user, id):
    invoice = Invoice.query.filter_by(order_id=id).first()
    if not invoice:
        order = Order.query.filter_by(id=id).first()
        invoice = new_order_invoice(order, INVOICE_PREFIX)
        if not invoice.save():
            return abort(403)
    concrete_index = f"{int(invoice.index):08d}"

    xml_data = invoice.invoice
    mimetype="application/xml"
    headers = {
        "Content-Disposition": f"attachment; filename=invoice_{INVOICE_PREFIX}{concrete_index}.xml"
    }
    return Response(xml_data, mimetype=mimetype, headers=headers)

@orders_blueprint.route('/admin/orders/download-invoice', methods=['GET'])
@permission('download_invoices')
def download_invoices(user):
    status_filter = request.args.get('status', 'all')
    query = Order.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    orders = query.order_by(desc(Order.created_at)).all()

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for order in orders:
            invoice = Invoice.query.filter_by(order_id=order.id).first()
            if not invoice:
                invoice = new_order_invoice(order, INVOICE_PREFIX)
                if not invoice:
                    return abort(403)
            concrete_index = f"{int(invoice.index):08d}"
            filename = f"invoice_{INVOICE_PREFIX}{concrete_index}.xml"
            filedata = invoice.invoice
            zip_file.writestr(filename, filedata)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"invoices_{INVOICE_PREFIX}_{request.args.get('status', 'all')}.zip"
    )

