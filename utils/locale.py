import requests
import pycountry
from babel import Locale
from babel.numbers import format_currency

DEFAULT_TERRITORIES = {
    'it': 'IT',
    'en': 'US',
    'fr': 'FR',
    'de': 'DE',
    'es': 'ES',
    'pt': 'PT',
    # aggiungi altri se necessario
}

def normalize_locale(lang_code):
    if '_' in lang_code or '-' in lang_code:
        return lang_code.replace('-', '_')
    territory = DEFAULT_TERRITORIES.get(lang_code, lang_code.upper())
    return f"{lang_code}_{territory}"

def format_money(value, currency, lang_code):
    locale_code = normalize_locale(lang_code)
    if locale_code == 'it_IT':
        f='#,##0.00 ¤'
    else:
        f='¤#,##0.00'
    return format_currency(value, currency, locale=locale_code, format=f)

def country_name_to_code(country_name : str) -> str|None:
    country = pycountry.countries.get(name=country_name)
    return country.alpha_2 if country else None

def eur_to_usd(eur : float) -> float:
    response = requests.get("https://api.frankfurter.app/latest?amount={}&from=EUR&to=USD".format(eur))
    data = response.json()
    return round(data['rates']['USD'], 2)