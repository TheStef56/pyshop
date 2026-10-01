from extensions import db
from models.settings import Setting
from middlewares.with_user import with_user
from middlewares.permission import permission
from models.product_category_assoc import product_categories
from flask import Blueprint, Response, send_file, render_template, abort, redirect, request, flash, jsonify, url_for

categories_blueprint = Blueprint('admin_categories', __name__, template_folder='templates/admin')

@categories_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)
    
@categories_blueprint.route('/admin/categories', methods=['GET'])
@permission('edit_categories')
def view(user):
    setting = Setting.query.filter_by(name='global').first()
    if not setting:
        setting = Setting(name='global', meta={})
        setting.save()
    categories = setting.meta.get('categories', [{ "id": "1", "parent": "#", "text": { "it" : "Nuova categoria", "en": "New category" }, "type": "folder" }])
    for c in categories:
        if not c.get('parent', None):
            c['parent'] = "#"
    return render_template('admin/views/categories.html', user=user, categories=categories)

@categories_blueprint.route('/admin/categories/delete/<id>', methods=['DELETE'])
@permission('edit_categories')
def delete(user, id):
    if not id:
        return jsonify({"status": "error", "message": "ID della categoria non fornito"}), 400
    if id.isdigit():
        id = int(id)
        db.session.execute(
            product_categories.delete().where(
                product_categories.c.category_id == id
            )
        )
        setting = Setting.query.filter_by(name='global').first()
        if setting:
            categories = setting.meta.get('categories', [])
            setting.meta['categories'] = [c for c in categories if int(c['id']) != id]
            setting.save()
    
    return jsonify({"status": "success", "message": "Categoria eliminata con successo"}), 200

@categories_blueprint.route('/admin/categories/save', methods=['POST'])
@permission('edit_categories')
def save(user):
    categories = request.json
    if not categories:
        return jsonify({"status": "error", "message": "Nessuna categoria da salvare"}), 400
    
    active_ids  = [c['id'] for c in categories if c['id'].isdigit()]
    db.session.execute(
        product_categories.delete().where(
            (~product_categories.c.category_id.in_(active_ids))
        )
    )
    db.session.commit()
    setting = Setting.query.filter_by(name='global').first()
    if not setting:
        setting = Setting(name='global' , meta={})
    setting.meta['categories'] = categories
    for c in setting.meta["categories"]:
        if not c.get('parent', None):
            c['parent'] = "#"
    setting.save()
    return jsonify({"status": "success", "message": "Categorie salvate con successo"}), 200