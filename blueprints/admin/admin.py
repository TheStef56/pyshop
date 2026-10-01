import re
from bs4 import BeautifulSoup, NavigableString
from flask import Blueprint, render_template, redirect, jsonify, request
from middlewares.with_user import with_user
from googletrans import Translator

admin_blueprint = Blueprint('admin', __name__, template_folder="templates/admin")

@admin_blueprint.route('/admin', methods=['GET'])
@with_user()
def admin(user):
    return render_template('/admin/views/admin.html', user=user)

def is_html(text):
    return bool(re.search(r"<[^>]+>", text))

import re
from bs4 import BeautifulSoup

@admin_blueprint.route('/admin/translate', methods=["POST"])
@with_user()
def translate(user):
    data = request.get_json()
    text = data.get("q", "")
    from_code = data.get("source", "it")
    to_code = data.get("target", "en")
    translator = Translator()

    soup = BeautifulSoup(text, 'html.parser')
    
    text_nodes = soup.find_all(string=True)
    
    for node in text_nodes:
        if isinstance(node, NavigableString) and node.strip():
            original_text = node.strip()
            if original_text:
                translated_text = original_text
                r = translator.translate(original_text, dest=to_code, src=from_code)
                if r and r.text:
                    translated_text = r.text
                node.replace_with(translated_text)
    
    translated_html = str(soup)
    
    return jsonify({'translatedText': translated_html})
