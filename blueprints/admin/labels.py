import os
from sqlalchemy import desc
from models.label import Label
from werkzeug.utils import secure_filename
from middlewares.with_user import with_user
from middlewares.permission import permission
from flask import Blueprint, abort, jsonify, request, render_template, current_app, flash, url_for, redirect

labels_blueprint = Blueprint('labels', __name__)

@labels_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)
    
@labels_blueprint.route('/admin/labels', methods=['GET'])
@permission('view_labels')
def view(user):
    return render_template('admin/views/labels.html', user=user)

@labels_blueprint.route('/admin/labels/list', methods=['GET'])
@permission('view_labels')
def list_labels(user):
    search = request.args.get('search')

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = Label.query
    total = query.count()

    if search != "":
        query = query.filter(Label.name.ilike(f"%{search}%"))

    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    labels = query.order_by(desc(Label.id)).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    dicted_labels = [l.to_dict() for l in labels.items]
    
    return jsonify({
        'data': dicted_labels,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total / per_page)
        }
    })

@labels_blueprint.route('/admin/labels/create/', methods=['GET'])
@permission('edit_labels')
def create(user):
    label = Label()
    from forms.admin.label import LabelForm
    form = LabelForm()
    return render_template(
        '/admin/views/labels/edit.html', 
        user=user,
        label=label,
        form=form
    )

@labels_blueprint.route('/admin/labels/edit/<id>', methods=['GET'])
@permission('edit_labels')
def edit(user, id):
    from forms.admin.label import LabelForm
    form = LabelForm()
    label = Label.query.filter_by(id=id).first()
    if not label:
        return abort(404)
    form.name.data = label.name
    form.image.data = label.image
    return render_template(
        '/admin/views/labels/edit.html',
        user=user,
        label=label,
        form=form
    )

@labels_blueprint.route('/admin/labels/store', methods=['POST'])
@permission('edit_labels')
def store(user):
    from forms.admin.label import LabelForm
    form = LabelForm()
    if form.validate_on_submit():
        label = Label()
        label.name = form.name.data
        label.save()

        if form.image and form.image.data:
            label_image = form.image.data
            if label_image and label_image.filename:
                label.image = label_image.filename
                ext = os.path.splitext(secure_filename(label_image.filename))[1].lower()
                if ext:
                    relative_path = os.path.join(f"/uploads/public/labels/{label.id}/logo{ext}").replace("\\", "/")
                    absolute_path = os.path.join(current_app.root_path, "static" + relative_path)
                    if not os.path.exists(os.path.dirname(absolute_path)):
                        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                    label_image.save(absolute_path)
                    label.image = relative_path
                    label.save()

        flash("Marca salvata con successo", "success")
        redirect_url = request.args.get('redirect', url_for('labels.edit', id=label.id))
        return redirect(redirect_url)
    flash("Un errore ha impedito il salvataggio della marca", "error")
    return redirect(url_for('labels.create'))

@labels_blueprint.route('/admin/labels/update/<id>', methods=['POST'])
@permission('edit_labels')
def update(user, id):
    from forms.admin.label import LabelForm
    form = LabelForm()
    if form.validate_on_submit():
        label = Label.query.filter_by(id=id).first()
        label.name = form.name.data
        label.save()

        if form.image and form.image.data:
            label_image = form.image.data
            if label.image:
                current_absolute_path = os.path.join(current_app.root_path, "static" + label.image)
                if os.path.exists(current_absolute_path):
                    os.remove(current_absolute_path)
            if label_image and label_image.filename:
                label.image = label_image.filename
                ext = os.path.splitext(secure_filename(label_image.filename))[1].lower()
                if ext:
                    relative_path = os.path.join(f"/uploads/public/labels/{label.id}/logo{ext}").replace("\\", "/")
                    absolute_path = os.path.join(current_app.root_path, "static" + relative_path)
                    if not os.path.exists(os.path.dirname(absolute_path)):
                        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                    label_image.save(absolute_path)
                    label.image = relative_path
                    label.save()

        flash("Marca salvata con successo", "success")
        redirect_url = request.args.get('redirect', url_for('labels.edit', id=label.id))
        return redirect(redirect_url)
    flash("Un errore ha impedito il salvataggio della marca", "error")
    return redirect(url_for('labels.create'))

@labels_blueprint.route('/admin/labels/<id>/delete', methods=['DELETE'])
@permission('edit_labels')
def delete_label(user, id):
    label = Label.query.filter_by(id=id).first()
    if label:
        if label.image:
            current_absolute_path = os.path.join(current_app.root_path, "static" + label.image)
            if os.path.exists(current_absolute_path):
                os.remove(current_absolute_path)
    if label and label.delete():
        return "OK", 200
    return abort(404)