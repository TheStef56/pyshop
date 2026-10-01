import os
import shutil
from extensions import db
from models.product import Product
from models.settings import Setting
from models.variant import Variant
from models.label import Label
from utils.random import rand_hash256
from utils.form import parse_multi_form
from werkzeug.utils import secure_filename
from middlewares.with_user import with_user
from middlewares.permission import permission
from sqlalchemy.orm.attributes import flag_modified
from models.product_label_assoc import product_labels
from models.product_category_assoc import product_categories
from utils.files import allowed_file, filename_to_json_key, convert_to_webp
from flask import Blueprint, render_template, abort, redirect, request, flash, jsonify, url_for, current_app

products_blueprint = Blueprint('admin_products', __name__, template_folder='templates/admin')

@products_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)

@products_blueprint.route('/admin/products', methods=['GET'])

@permission('view_products')
def admin_products(user):
    return render_template('admin/views/products.html', user=user)

@products_blueprint.route('/admin/product/<id>', methods=['GET'])
@permission('edit_products')
def admin_product(user, id):
    product = Product.query.filter_by(id=id).first()
    if product:
        return jsonify(product.to_dict())
    return abort(404)

@products_blueprint.route('/admin/products/list', methods=['GET'])
@permission('view_products')
def admin_products_list(user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search')
    stype = request.args.get('type')

    # Base query
    query = Product.query
    
    # Add pagination
    if search != "":
        if stype == "Nome":
            query = query.filter(Product.name.ilike(f"%{search}%"))
        else:
            query = query.filter(Product.labels.any(Label.name.ilike(f"%{search}%")))
    
    # Get total count for pagination
    total = query.count()

    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'data': [p.to_dict() for p in products.items],
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total / per_page)
        }
    })

@products_blueprint.route('/admin/product/<id>/delete', methods=['DELETE'])
@permission('delete_products')
def admin_product_delete(user, id):
    product = Product.query.filter_by(id=id).first()
    variant = Variant.query.filter_by(product_id=id).all()
    for var in variant:
        images = var.images
        if images:
            for image in images.values():
                absolute_path = os.path.join(current_app.root_path, image['path'][1:])
                if os.path.isfile(absolute_path):
                    os.remove(absolute_path)
        var.delete()
    if product and product.delete():
        return "OK", 200
    return abort(404)

@products_blueprint.route('/admin/product/<id>/edit', methods=['GET'])
@permission('edit_products')
def admin_product_edit(user, id):
    product = Product.query.filter_by(id=id).first()
    if not product:
        return abort(404)
    categories = None
    product.category_ids = product.get_category_ids()
    product.label_id = None
    label_ids = product.get_labels_ids()
    if len(label_ids) > 0:
        product.label_id = label_ids[0]
    global_settings = Setting.query.filter_by(name='global').first()
    if global_settings:
        categories = global_settings.meta.get('categories', None)
    labels = Label.query.all()

    return render_template('/admin/views/products/edit.html', product=product, user=user, categories=categories, labels=labels)

@products_blueprint.route('/admin/product/create', methods=['POST'])
@permission('edit_products')
def admin_product_create(user):
    multiform = parse_multi_form(request.form)
    #TODO: crea un sistema di validazione dei dati
    product = Product(
        name =multiform['name'],
        description=multiform['description'],
        active=request.form.get('active', 'on') == 'on'
    )

    if product.save():
        return """
        window.notyf.success('Prodotto creato correttamente')
        reloadProductsTable();
        """
    else:
        return """
        window.notyf.error('Un errore ha impedito la creazione del prodotto')
        reloadProductsTable();
        """
    
@products_blueprint.route('/admin/product/<id>/update', methods=['POST'])
@permission('edit_products')
def admin_product_update(user, id):
    multiform = parse_multi_form(request.form)
    #TODO: crea un sistema di validazione dei dati
    product = Product.query.filter_by(id=id).first()
    product.name = multiform["name"]
    product.description = multiform['description']
    product.active = request.form.get('active', 'on') == 'on' 
    if request.form.get('more_info', None):
        product.more_info = request.form.get('more_info')
    product.shipping_width = float(request.form.get('width', 0.0))
    product.shipping_length = float(request.form.get('length', 0.0))
    product.shipping_height = float(request.form.get('height', 0.0))
    product.shipping_weight = float(request.form.get('weight', 0.0))

    selected_category_ids = request.form.getlist('categories[]')
    db.session.execute(
        product_categories.delete().where(product_categories.c.product_id == product.id)
    )
    db.session.commit()
    selected_category_ids = [int(cid) for cid in selected_category_ids if cid.isdigit()]
    stmt_delete = product_categories.delete().where(product_categories.c.product_id == product.id)
    db.session.execute(stmt_delete)
    for category_id in selected_category_ids:
        stmt_insert = product_categories.insert().values(product_id=product.id, category_id=category_id)
        db.session.execute(stmt_insert)

    stmt_delete = product_labels.delete().where(product_labels.c.product_id == product.id)
    db.session.execute(stmt_delete)
    if request.form.get('label', None):
        stmt_insert = product_labels.insert().values(product_id=product.id, label_id=request.form.get('label'))
        db.session.execute(stmt_insert)

    if product.save():
        return """
        window.notyf.success('Prodotto aggiornato correttamente');
        """
    else:
        return """
        window.notyf.error('Un errore ha impedito l'aggiornamento del prodotto');
        """
    
############
# VARIANTS #
############

@products_blueprint.route('/admin/product/<id>/variant/create', methods=['GET'])
@permission('edit_products')
def create_variant(user, id):
    product = Product.query.filter_by(id=id).first()
    return render_template("/admin/views/variants/edit.html", variant=Variant(), user=user, product=product)

@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/edit', methods=['GET'])
@permission('edit_products')
def edit_variant(user, product_id, variant_id):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    variant.order_options()
    variant.order_images()
    return render_template("/admin/views/variants/edit.html", variant=variant, user=user, product=product)


@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/delete', methods=['DELETE'])
@permission('delete_products')
def delete_variant(user, product_id, variant_id):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    if not product or not variant:
        return abort(404)
    images = variant.images
    if images:
        for image in images.values():
            absolute_path = os.path.join(current_app.root_path, image['path'][1:])
            if os.path.isfile(absolute_path):
                os.remove(absolute_path)
    if variant.delete():
        return "OK", 200
    return abort(403)

@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/clone', methods=['PUT'])
@permission('edit_products')
def clone_variant(user, product_id : int, variant_id : int) -> None:
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return abort(404)
    variant = Variant.query.filter_by(id=variant_id).first()
    if not variant:
        return abort(404)
    cloned_variant = Variant(
        name=variant.name,
        description=variant.description,
        active=variant.active,
        data=variant.data,
        order=variant.order + 1,
        images={},
        price=variant.price,
        discount=variant.discount,
        stock=variant.stock,
        options=variant.options,
        product_id=product.id
    )
    cloned_variant.save()
    return "OK", 200

@products_blueprint.route('/admin/product/<id>/variant/store', methods=['POST'])
@permission('edit_products')
def store_variant(user, id):
    multiform = parse_multi_form(request.form)
    # TODO: scrivi un sistema di validazione per i dati ricevuti dal form
    
    product = Product.query.filter_by(id=id).first()
    if not product:
        return abort(404)
    
    # Parse delle opzioni
    parsed_options = {}
    for option_id in multiform.get('options', {}):
        parsed_options[option_id] = {
            "active": multiform['options'][option_id].get('active', 'off') == 'on',
            "name": multiform['options'][option_id]['name'],
            "price": multiform['options'][option_id]['price'],
            "discount": multiform['options'][option_id]['discount'],
            "stock": int(multiform['options'][option_id]['stock']),
            "order": int(multiform['options'][option_id].get('order', 0))
        }
    
    # Crea la variante
    variant = Variant(
        name=multiform['name'],
        description=multiform['description'],
        active=request.form.get('active', 'on') == 'on',
        price=multiform['price'],
        discount=multiform['discount'],
        stock=request.form.get('stock'),
        options=parsed_options,
        product_id=product.id
    )
    
    # Prima salvataggio per ottenere l'ID della variante
    if not variant.save():
        flash('Un errore ha impedito il salvataggio della variante', 'danger')
        return redirect(url_for('admin_products.create_variant', id=product.id))
    
    # Gestione delle immagini con conversione WebP
    stored_images = {}
    has_images = False
    
    for image in request.files.getlist('images'):
        if image.filename == '':
            continue
        
        has_images = True
        if image and allowed_file(image.filename):
            relative_dir = "static/uploads/private/tmp"
            absolute_dir = os.path.join(current_app.root_path, relative_dir)
            
            if not os.path.exists(absolute_dir):
                os.makedirs(absolute_dir)
            
            # Genera nome file sicuro mantenendo temporaneamente l'estensione originale
            original_filename = secure_filename(image.filename)
            file_path = os.path.join(absolute_dir, original_filename)
            
            # Salva l'immagine temporaneamente
            image.save(file_path)
            
            # Converti in WebP
            webp_path = convert_to_webp(file_path, quality=85)
            webp_filename = os.path.basename(webp_path)
            stored_images[webp_filename] = webp_path
    
    # Se non ci sono immagini valide ma è stato fatto l'upload
    if has_images and not stored_images:
        flash('Nessuna immagine valida selezionata', 'error')
        return redirect(url_for('admin_products.edit_variant', product_id=product.id, variant_id=variant.id))
    
    # Sposta le immagini nella directory finale e aggiorna la variante
    sanified_stored_images = {}
    if stored_images:
        relative_dir = f"static/uploads/public/variants/{variant.id}"
        absolute_dir = os.path.join(current_app.root_path, relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        
        for filename, path in stored_images.items():
            final_path = os.path.join(absolute_dir, filename)
            shutil.move(path, final_path)
            
            sanified_stored_images[filename_to_json_key(filename)] = {
                "path": "/" + relative_dir + "/" + filename,
                "order": 999999999
            }
        
        variant.images = sanified_stored_images
    
    # Salvataggio finale
    if variant.save():
        flash('Variante salvata correttamente', 'success')
        return redirect(url_for('admin_products.edit_variant', product_id=product.id, variant_id=variant.id))
    
    flash('Un errore ha impedito il salvataggio della variante', 'danger')
    return redirect(url_for('admin_products.create_variant', id=product.id))

@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/update', methods=['POST'])
@permission('edit_products')
def update_variant(user, product_id, variant_id):
    multiform = parse_multi_form(request.form)
    # TODO: scrivi un sistema di validazione per i dati ricevuti dal form
    
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    
    variant.name = multiform['name']
    variant.description = multiform['description']
    
    parsed_options = {}
    for option_id in multiform.get('options', {}):
        parsed_options[option_id] = {
            "active": multiform['options'][option_id].get('active', 'off') == 'on',
            "name": multiform['options'][option_id]['name'],
            "price": multiform['options'][option_id]['price'],
            "discount": multiform['options'][option_id]['discount'],
            "stock": int(multiform['options'][option_id]['stock']),
            "order": int(multiform['options'][option_id].get('order', 0))
        }
    
    variant.options = parsed_options
    variant.active = request.form.get('active', 'on') == 'on'
    variant.price = multiform['price']
    variant.discount = multiform['discount']
    variant.stock = int(request.form.get('stock', 0))
    
    # Controllo prodotto e variante
    if not product or not variant:
        return abort(404)
    
    stored_images = {}
    for image in request.files.getlist('images'):
        if image.filename == '':
            continue
            
        if image and allowed_file(image.filename):
            relative_dir = "static/uploads/private/tmp"
            absolute_dir = os.path.join(current_app.root_path, relative_dir)
            
            # Genera un nome file sicuro mantenendo l'estensione originale temporaneamente
            original_filename = secure_filename(image.filename)
            file_path = os.path.join(absolute_dir, original_filename)
            
            if not os.path.exists(absolute_dir):
                os.makedirs(absolute_dir)
            
            # Salva l'immagine temporaneamente
            image.save(file_path)
            
            # Converti in WebP
            webp_path = convert_to_webp(file_path, quality=85)
            
            # Ottieni il nome del file WebP
            webp_filename = os.path.basename(webp_path)
            stored_images[webp_filename] = webp_path
    
    sanified_stored_images = variant.images or {}
    relative_dir = f"static/uploads/public/variants/{variant.id}"
    absolute_dir = os.path.join(current_app.root_path, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)
    
    for filename, path in stored_images.items():
        final_path = os.path.join(absolute_dir, filename)
        shutil.move(path, final_path)
        
        sanified_stored_images[filename_to_json_key(filename)] = {
            "path": "/" + relative_dir + "/" + filename,
            "order": 999999999
        }
    
    variant.images = sanified_stored_images
    
    if variant.save():
        flash('Variante salvata correttamente', 'success')
    else:
        flash('Un errore ha impedito il salvataggio della variante', 'danger')
    
    return redirect(url_for('admin_products.edit_variant', product_id=product.id, variant_id=variant.id))


#TODO: adattare alle varianti di prodotto
@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/<key>/deleteimage', methods=['DELETE'])
@permission('edit_products')
def variant_delete_image(user, product_id, variant_id, key):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    if not product or not variant:
        return abort(404)
    images = variant.images
    absolute_path = os.path.join(current_app.root_path, images[key]['path'][1:])
    if os.path.isfile(absolute_path):
        os.remove(absolute_path)
    del(variant.images[key])
    if variant.save():
        return "OK", 200
    return abort(404)

@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/orderimages', methods=["PUT"])
@permission('edit_products')
def order_images(user, product_id, variant_id):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    if not product or not variant:
        return abort(404)
    received_images = request.get_json()
    for image in received_images:
        if variant.images[image['id']]:
            variant.images[image['id']]['order'] = image['order']
    flag_modified(variant, 'images')
    if variant.save():
        return "OK", 200
    return abort(404)

@products_blueprint.route('/admin/product/<product_id>/variants/order', methods=["PUT"])
@permission('edit_products')
def order_variants(user, product_id):
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return abort(404)
    variants_order = request.get_json()
    for variant_id in variants_order:
        order = variants_order[variant_id]
        Variant.query.filter_by(id=variant_id).update({Variant.order: order})
    return "OK", 200

###########
# OPTIONS #
###########
@products_blueprint.route('/admin/product/<product_id>/variant/<variant_id>/option', methods=['GET'])
@permission('edit_products')
def create_option(user, product_id, variant_id):
    product = Product.query.filter_by(id=product_id).first()
    variant = Variant.query.filter_by(id=variant_id).first()
    option_id=rand_hash256()
    option_data = {
        "active" : True,
        "name" : {
            "it": "",
            "en": ""
        },
        "price" : {
            "usd": 0,
            "eur": 0
        },
        "discount" : {
            "usd": 0,
            "eur": 0
        },
        "order" : 999999999,
        "stock" : 0
    }
    return render_template("admin/views/options/edit.html", product=product, variant=variant, id=option_id, stored=False, option_data=option_data)
