import os
from extensions import babel
from flask import Blueprint, request, session, redirect, url_for

def get_locale():
    return session.get('lang', request.args.get('lang', os.getenv('DEFAULT_LANGUAGE', 'en') ))

locale_blueprint =  Blueprint('locale', __name__)

@locale_blueprint.route('/theme/<theme>')
def change_theme(theme):
    session['shop-theme'] = theme
    next_url = request.referrer or url_for('public.index')
    return redirect(next_url)

@locale_blueprint.route('/lang/<lang_code>')
def change_lang(lang_code):
    session['lang'] = lang_code
    if lang_code == "it":
        session['extended_lang_code'] = 'it-IT'
    if lang_code == "en":
        session['extended_lang_code'] = 'en-US'
    # Torna alla pagina precedente oppure a home
    next_url = request.referrer or url_for('public.index')
    return redirect(next_url)

@locale_blueprint.route('/currency/<currency_code>')
def change_currency(currency_code):
    if currency_code in ['eur', 'usd']:
        session['currency'] = currency_code
    next_url = request.referrer or url_for('public.index')
    return redirect(next_url)
