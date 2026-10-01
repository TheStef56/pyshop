import os
import json
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TelField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange

with open(os.path.dirname(__file__) + "/../../static/country_regions.json", encoding="utf-8") as cr:
    country_data = json.load(cr)

COUNTRIES = [country['countryName'] for country in country_data]

REGIONS = [
    region.get("name")
    for country in country_data
    for region in country.get("regions", [])
]

class CheckoutForm(FlaskForm):
    # Fatturazione
    billing_name = StringField(_('Name'), validators=[DataRequired()])
    billing_lastname = StringField(_('Last name'), validators=[DataRequired()])
    billing_street = StringField(_('Street'), validators=[DataRequired()])
    billing_number = StringField(_('Number'), validators=[DataRequired()])
    billing_postal_code = StringField(_('Postal code'), validators=[DataRequired(), Length(min=2, max=12)])
    billing_city = StringField(_('City'), validators=[DataRequired()])
    billing_email = EmailField(_('Email'), validators=[DataRequired(), Email()])
    billing_phone = TelField(_('Phone number'), validators=[DataRequired(), Length(min=6, max=20)])
    billing_fiscal_code = StringField(_('Fiscal code / VAT'), validators=[DataRequired()])

    billing_country = SelectField(_('Country'), choices=COUNTRIES, validators=[DataRequired()])
    billing_region = SelectField(_('State/Province/Region'), choices=REGIONS, validators=[DataRequired()])
    
    
    # Spedizione
    shipping_name = StringField(_('Name'), validators=[DataRequired()])
    shipping_lastname = StringField(_('Last name'), validators=[DataRequired()])
    shipping_street = StringField(_('Street'), validators=[DataRequired()])
    shipping_number = StringField(_('Number'), validators=[DataRequired()])
    shipping_city = StringField(_('City'), validators=[DataRequired()])
    shipping_postal_code = StringField(_('Postal code'), validators=[DataRequired()])
    
    shipping_country = SelectField(_('Country'), choices=COUNTRIES, validators=[DataRequired()])
    shipping_region = SelectField(_('State/Province/Region'), choices=REGIONS, validators=[DataRequired()])
    
    shipping_notes = TextAreaField(_('Delivery notes'), validators=[])