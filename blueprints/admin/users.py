from extensions import db
from models.user import User
from forms.admin.user import UserForm
from models.user_roles import UserRoles
from middlewares.with_user import with_user
from middlewares.permission import permission
from werkzeug.security import generate_password_hash
from wtforms.validators import DataRequired, Length, EqualTo
from models.role_permission import RolePermission, admin_permissions
from flask import Blueprint, render_template, abort, redirect, request, flash, jsonify, url_for

users_blueprint = Blueprint('admin_users', __name__, template_folder='templates/admin')


@users_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)
    
@users_blueprint.route('/admin/users', methods=['GET'])
@permission('view_users')
def view(user):
    return render_template('admin/views/users.html', user=user)

@users_blueprint.route('/admin/users/list', methods=['GET'])
@permission('view_users')
def list(user):
    users = User.query.all()
    return jsonify([ u.to_dict() for u in users])

@users_blueprint.route('/admin/users/<id>/edit', methods=['GET'])
@permission('edit_users')
def edit(user, id):
    model_user = User.query.filter_by(id=id).first()
    form = UserForm(obj=model_user)
    form.password.data = None
    return render_template('/admin/views/users/edit.html', user=user, model_user=model_user, form=form)

@users_blueprint.route('/admin/users/create', methods=['GET'])
@permission('edit_users')
def create(user):
    model_user = User()
    form = UserForm()
    form.password.validators = [DataRequired(), Length(min=6)]
    form.confirm_password.validators = [DataRequired(), EqualTo('password')]
    return render_template('/admin/views/users/edit.html', user=user, model_user=model_user, form=form)


@users_blueprint.route('/admin/users/<id>/update', methods=['POST'])
@permission('edit_users')
def update(user, id):
    form = UserForm()
    if form.validate_on_submit():
        model_user = User.query.filter_by(id=id).first()
        if form.password.data:
            model_user.password = generate_password_hash(form.password.data)
        model_user.is_active = form.is_active.data
        model_user.username = form.username.data
        model_user.email = form.email.data
        if model_user.save():
            flash("Utente aggiornato con successo", "success")
        else:
            flash("Un errore ha impedito l'aggiornamento dell'utente", "error")
    else:
        flash("Un errore ha impedito l'aggiornamento dell'utente", "error")
    return redirect(url_for('admin_users.edit', id=id))

@users_blueprint.route('/admin/users/store', methods=['POST'])
@permission('edit_users')
def store(user):
    form = UserForm()
    if form.validate_on_submit():

        user = User(
            username=form.username.data,
            password=generate_password_hash(form.password.data),
            email=form.email.data,
            is_active=form.is_active.data
        )
        if user.save():
            user_role = UserRoles(user_id=user.id, role='admin') #assegna i ruoli 
            db.session.add(user_role)
            db.session.commit()

            for perm in admin_permissions:
                permission = RolePermission.query.filter_by(name=perm['name']).first()
                user_role.permissions.append(permission)
            db.session.commit()

            flash("Utente creato con successo", "success")
            return redirect(url_for('admin_users.edit', id=user.id))
    flash("Un errore ha impedito la creazioen dell'utente", "error")
    return redirect(url_for('admin_users.create'))
    
