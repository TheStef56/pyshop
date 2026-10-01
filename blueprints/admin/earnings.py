from sqlalchemy import desc, func
from models.order import Order
from extensions import db
from werkzeug.utils import secure_filename
from middlewares.with_user import with_user
from middlewares.permission import permission
from flask import Blueprint, abort, jsonify, request, render_template, send_file
from datetime import datetime, timedelta
from utils.earnings_pdf import EarningsPdf
import io

earnings_blueprint = Blueprint('admin_earnings', __name__, template_folder='templates/admin')

@earnings_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)
    
@earnings_blueprint.route('/admin/earnings', methods=['GET'])
@permission('view_earnings')
def view(user):
    return render_template('admin/views/earnings.html', user=user)

@earnings_blueprint.route('/admin/earnings/list', methods=['GET'])
@permission('view_earnings')
def list(user):
    page       = request.args.get('page', 1, type=int)
    per_page   = request.args.get('per_page', 10, type=int)
    period     = request.args.get('period', 1, type=int)
    start_date = request.args.get('sd')
    end_date   = request.args.get('ed')

    query = Order.query
    total = query.count()
    
    # if period is an amount of days

    if period != 0:
        limit = datetime.utcnow() - timedelta(days=period)
        orders = query.filter(Order.created_at > limit).order_by(desc(Order.id)).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
    else:
    # if period is not in date but from startDate to endDate

        orders = query\
        .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
        .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d"))\
        .order_by(desc(Order.id)).paginate(
            page      = page,
            per_page  = per_page,
            error_out = False
        )

    dicted_orders = [o.to_dict() for o in orders.items]

    for o in dicted_orders:
        o['products_base_price'] = round(float(o['products_price'])/1.22, 2)
        o['products_IVA']        = round(float(o['products_price']) - float(o['products_base_price']), 2)
        o['shipment_base_price'] = round(float(o['shipment_price'])/1.22, 2)
        o['shipment_IVA']        = round(float(o['shipment_price']) - float(o['shipment_base_price']), 2)
    

    result = dicted_orders

    return jsonify({
            'data': result,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total / per_page - 1)
            }
        })

@earnings_blueprint.route('/admin/earnings/totals', methods=['GET'])
@permission('view_earnings')
def totals(user):
    period = request.args.get('period', 1, type=int)
    start_date = request.args.get('sd')
    end_date   = request.args.get('ed')

    limit  = datetime.utcnow() - timedelta(days=period)

    totalsEUR = db.session.query(
        func.sum(Order.products_price).label("product_sum"),
        func.sum(Order.shipment_price).label("shipping_sum")
    ).where(Order.currency == "EUR")

    totalsUSD = db.session.query(
        func.sum(Order.products_price).label("product_sum"),
        func.sum(Order.shipment_price).label("shipping_sum")
    ).where(Order.currency == "USD")

    # if period is an amount of days
    if period != 0:
        totalsEUR = totalsEUR.filter(Order.created_at > limit).one()
        totalsUSD = totalsUSD.filter(Order.created_at > limit).one()
    else:
    # if period is not in date but from startDate to endDate
        totalsEUR = totalsEUR\
            .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
            .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d")).one()
            
        totalsUSD = totalsUSD\
                    .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
                    .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d")).one()
    
    EUR_product_sum  = 0.0 if not totalsEUR.product_sum  else totalsEUR.product_sum
    EUR_shipping_sum = 0.0 if not totalsEUR.shipping_sum else totalsEUR.shipping_sum
    USD_product_sum  = 0.0 if not totalsUSD.product_sum  else totalsUSD.product_sum
    USD_shipping_sum = 0.0 if not totalsUSD.shipping_sum else totalsUSD.shipping_sum


    result = [{
        'total_products_prices': round(EUR_product_sum, 2),
        'base_products_prices' : round(EUR_product_sum/1.22, 2),
        'products_IVA'         : round(EUR_product_sum - EUR_product_sum/1.22, 2),
        'total_shipping_costs' : round(EUR_shipping_sum, 2),
        'base_shipping_costs'  : round(EUR_shipping_sum/1.22, 2),
        'shipping_IVA'         : round(EUR_shipping_sum - EUR_shipping_sum/1.22, 2),
        'currency'             : 'EUR'
    },
    {
        'total_products_prices': round(USD_product_sum, 2),
        'base_products_prices' : round(USD_product_sum/1.22, 2),
        'products_IVA'         : round(USD_product_sum - USD_product_sum/1.22, 2),
        'total_shipping_costs' : round(USD_shipping_sum, 2),
        'base_shipping_costs'  : round(USD_shipping_sum/1.22, 2),
        'shipping_IVA'         : round(USD_shipping_sum - USD_shipping_sum/1.22, 2),
        'currency'             : 'USD'
    }]

    return jsonify(result)

@earnings_blueprint.route('/admin/earnings/download', methods=['GET'])
@permission('view_earnings')
def download(user):
    period     = request.args.get('period', 1, type=int)
    start_date = request.args.get('sd')
    end_date   = request.args.get('ed')

    # creating file name based on period

    period_names = {
        1 : "daily",
        7 : "weekly",
        30 : "monthly",
        180 : "semestral",
        365 : "annual",
    }

    report_name = period_names[period] if period in period_names.keys() else f"{start_date}_{end_date}"

    # ------------------------------------
    # Querying for all orders filtering on period

    query = Order.query
    
    if period != 0:
        limit = datetime.utcnow() - timedelta(days=period)
        orders = query.filter(Order.created_at > limit).order_by(desc(Order.id)).all()
    else: 
        orders = query\
        .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
        .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d"))\
        .order_by(desc(Order.id)).all()

    dicted_orders = [o.to_dict() for o in orders]

    for o in dicted_orders:
        o['products_base_price'] = round(float(o['products_price'])/1.22, 2)
        o['products_IVA']        = round(float(o['products_price']) - float(o['products_base_price']), 2)
        o['shipment_base_price'] = round(float(o['shipment_price'])/1.22, 2)
        o['shipment_IVA']        = round(float(o['shipment_price']) - float(o['shipment_base_price']), 2)

    # ------------------------------------
    # Querying for totals filtering on period
    
    limit  = datetime.utcnow() - timedelta(days=period)

    totalsEUR = db.session.query(
        func.sum(Order.products_price).label("product_sum"),
        func.sum(Order.shipment_price).label("shipping_sum")
    ).where(Order.currency == "EUR")

    totalsUSD = db.session.query(
        func.sum(Order.products_price).label("product_sum"),
        func.sum(Order.shipment_price).label("shipping_sum")
    ).where(Order.currency == "USD")

    if period != 0:
        totalsEUR = totalsEUR.filter(Order.created_at > limit).one()
        totalsUSD = totalsUSD.filter(Order.created_at > limit).one()
    else:
        totalsEUR = totalsEUR\
            .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
            .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d")).one()
            
        totalsUSD = totalsUSD\
                    .filter(Order.created_at > datetime.strptime(start_date, "%Y-%m-%d"))\
                    .filter(Order.created_at < datetime.strptime(end_date,   "%Y-%m-%d")).one()
    
    EUR_product_sum  = 0.0 if not totalsEUR.product_sum  else totalsEUR.product_sum
    EUR_shipping_sum = 0.0 if not totalsEUR.shipping_sum else totalsEUR.shipping_sum
    USD_product_sum  = 0.0 if not totalsUSD.product_sum  else totalsUSD.product_sum
    USD_shipping_sum = 0.0 if not totalsUSD.shipping_sum else totalsUSD.shipping_sum

    # ------------------------------------
    # Creating PDF

    pdf = EarningsPdf()
    pdf.add_paragraph("Totals")

    totals_table = [[
        'Lordo prod.',
        'Utile tot.',
        'IVA tot.',
        'Lordo spe.',
        'Base spe.',
        'IVA spe.',
        'Valuta',
    ],
    [
        round(EUR_product_sum, 2),
        round(EUR_product_sum/1.22, 2),
        round(EUR_product_sum - EUR_product_sum/1.22, 2),
        round(EUR_shipping_sum, 2),
        round(EUR_shipping_sum/1.22, 2),
        round(EUR_shipping_sum - EUR_shipping_sum/1.22, 2),
        'EUR'
    ],
    [
        round(USD_product_sum, 2),
        round(USD_product_sum/1.22, 2),
        round(USD_product_sum - USD_product_sum/1.22, 2),
        round(USD_shipping_sum, 2),
        round(USD_shipping_sum/1.22, 2),
        round(USD_shipping_sum - USD_shipping_sum/1.22, 2),
        'USD'
    ]
    ] 

    pdf.add_table(totals_table)

    pdf.add_paragraph("Orders")

    orders_table = [
        [
            'ID',
            'Prezzo prod.',
            'Prezzo base',
            'IVA prod.',
            'Costo sped.',
            'Costo base',
            'IVA sped.',
            'Valuta',
            'Data'
        ]
    ]

    for o in dicted_orders:
        orders_table.append([
                    o['id'],
                    o['products_price'],
                    o['products_base_price'],
                    o['products_IVA'],
                    o['shipment_price'],
                    o['shipment_base_price'],
                    o['shipment_IVA'],
                    o['currency'],
                    o['created_at'].split('T')[0]
                ])

    pdf.add_table(orders_table)
    raw_pdf = pdf.build()
    return send_file(
        io.BytesIO(raw_pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"report-{report_name}.pdf"
    )