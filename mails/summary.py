import os
from mjml import mjml2html
from flask_babel import _
from dotenv import load_dotenv
from models.order import Order
from flask import session, url_for
from models.variant import Variant
from models.product import Product

load_dotenv()

APP_DOMAIN = os.getenv('DOMAIN')

class Summary():
    def __init__(self, grouped_products : dict, order : Order):
        self.grouped_products = grouped_products
        self.order = order

    def html(self):
        title = _('Thank for your order!')
        order_confirmed = _('Hello! We received your order')
        order_details = _('Order details')
        logo = session.get('settings', {}).get('header', {}).get('logo') or 'images/logo_placeholder.png'
        template = f"""
        <mjml>
            <mj-body background-color="#f5f5f5" font-family="Helvetica, Arial, sans-serif">
                <mj-section background-color="#ffffff" padding="20px">
                    <mj-column>
                        <mj-image width="120px" src="{url_for('static', filename=logo)}" alt="Logo"/>
                    </mj-column>
                </mj-section>

                <mj-section background-color="#ffffff" padding="20px">
                    <mj-column>
                        <mj-text font-size="20px" font-weight="bold">{title}</mj-text>
                        <mj-text font-size="16px">{order_confirmed}</mj-text>
                    </mj-column>
                </mj-section>

                <mj-section background-color="#ffffff" padding="0 20px">
                    <mj-column>
                        <mj-divider border-color="#cccccc"/>
                        <mj-text font-size="18px" font-weight="bold" padding-bottom="10px">{order_details}</mj-text>
                        <mj-table>
        """
        domain = os.getenv("DOMAIN")

        for identifier in self.grouped_products:
            variant = self.grouped_products[identifier]['variant']
            product = self.grouped_products[identifier]['product']
            variant_name = product.name[session['lang']]
            if session['lang'] in variant.name:
                variant_name = f"{product.name[session['lang']]} - {variant.name[session['lang']]}"
                if variant.option:
                    variant_name = f"{product.name[session['lang']]} - ({variant.options[variant.option]['name'][session['lang']] if variant.options[variant.option]['name'][session['lang']] != '' else variant.options[variant.option]['name']['it']})"
            quantity = _('Quantity: ') + str(self.grouped_products[identifier]['quantity'])
            variant_price = variant.get_price(session, int(self.grouped_products[identifier]['quantity']), variant.option)

            template+=f"""
                        <tr>
                            <td><img src="{domain}{variant.first_image()['path']}" width="50px"/></td>
                            <td>
                            <p style="margin:0;"><strong>{variant_name}</strong></p>
                            <p style="margin:0;">{quantity}</p>
                            </td>
                            <td align="right">{variant_price}</td>
                        </tr>"""
        
        shipping_address = _('Shipping address')
        all_rights_reserved = _('All rights reserved')
        need_help=_('Need help? Contact us at')

        checkout=self.order.checkout
        shipment = _('Shipment')
        total = _('Total')
        can_track = _('You can track your order at')
        template+=f"""
                        </mj-table>

                        <mj-divider border-color="#cccccc"/>

                        <mj-text font-size="16px">
                        <strong>{shipment}:</strong> {self.order.get_shipment_cost(session['lang'])}<br/>
                        <strong>{total}:</strong> <span style="font-size:18px;">{self.order.get_total(session['lang'])}</span>
                        </mj-text>
                    </mj-column>
                </mj-section>

                <mj-section background-color="#ffffff" padding="20px">
                    <mj-column>
                        <mj-text font-size="16px" font-weight="bold">{shipping_address}</mj-text>
                        <mj-text font-size="14px">
                        {checkout['shipping_name']} {checkout['shipping_lastname']}<br/>
                        {checkout['shipping_street']} {checkout['shipping_number']}<br/>
                        {checkout['shipping_postal_code']} {checkout['shipping_city']} ({checkout['shipping_region']})<br/>
                        {checkout['shipping_country']}
                        </mj-text>
                        <mj-text font-size="16px">
                        {can_track} <a href="{domain}/track/{self.order.reference}">{domain}/track/{self.order.reference}</a>.<br/>
                        </mj-text>
                    </mj-column>
                </mj-section>

                <mj-section background-color="#f5f5f5" padding="20px">
                    <mj-column>
                        <mj-text font-size="12px" color="#999999" align="center">
                        {need_help} <a href="mailto:{session['settings']['header']['support_mail']}">{session['settings']['header']['support_mail']}</a><br/>
                        © 2025 {session['settings']['header']['site_name']}. {all_rights_reserved}.
                        </mj-text>
                    </mj-column>
                </mj-section>
            </mj-body>
            </mjml>"""
        
        return mjml2html(template)

        