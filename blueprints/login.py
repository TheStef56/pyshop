from app import mail_noreply
from models import User
from extensions import db
from flask_mail import Message
from utils.random import rand_hash256
from middlewares.with_user import with_user 
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, url_for, session, url_for, redirect, session, request, flash, abort
from forms.admin.password import PassForm
from datetime import datetime, timedelta
import os

login_blueprint = Blueprint('login', __name__, template_folder='templates/admin')

@login_blueprint.route('/admin/recovery', methods=['GET'])
def recovery():
    req_type = request.args.get("type")
    rec = request.args.get('recovery')
    username = request.args.get('user')
    user = User.query.filter_by(username=username).first()
    if user and user.is_active:
        user.attempts = 0
        if req_type == "attempts":
            if not user.reset_expire or datetime.utcnow() > user.reset_expire:
                user.reset_hash = None
                user.reset_expire = None
                user.save()
                return abort(401)
            if rec and rec == user.reset_hash:
                user.reset_hash = None
                user.reset_expire = None
        elif req_type == "password":
            if not user.recovery_expire or datetime.utcnow() > user.recovery_expire:
                user.recovery_hash = None
                user.recovery_expire = None
                user.save()
                return abort(401)
            if rec and rec == user.recovery_hash:
                return render_template('/admin/recovery_password.html', hash=rec)
            else:
                return abort(401)
        user.save()
        return redirect(url_for('login.admin_login'))
    return abort(401)

@login_blueprint.route('/admin/recoverymail', methods=['POST'])
def recovery_mail():
    try:
        req_type = request.args.get("type")
        if req_type not in ("attempts", "password"):
            return "Error during mail sending"
        
        username = request.json['username']
        user = User.query.filter_by(username=username).first()
        
        domain = os.getenv('DOMAIN')
        rhash = rand_hash256()
        link = f"{domain}/admin/recovery?user={username}&recovery={rhash}&type={req_type}"
        if req_type == "attempts":
            user.reset_hash = rhash
            user.reset_expire = datetime.utcnow() + timedelta(days=2)
            msg = Message(
                "Sblocco login",
                recipients=[user.email]
            )
            msg.body = f"Sblocca i tentativi di login con questo link:\n\n  {link}"
        else:
            user.recovery_hash = rhash
            user.recovery_expire = datetime.utcnow() + timedelta(days=2)
            msg = Message(
                "Reimposta password",
                recipients=[user.email]
            )
            msg.body = f"Reimposta la password con questo link:\n\n  {link}"
        db.session.commit()
        mail_noreply.send(msg)
        flash("Mail sent successfully", "success")
        return "Mail sent successfully"
    except:
        # Non dovremmo mai giungere qui, se c'è un'exception,
        # allora la request è malformata e non è leggittima.
        flash("Error during mail sending", "danger")
        return "Error during mail sending"
    
@login_blueprint.route('/admin/recoverypassword', methods=['POST'])
def recovery_password():
    password = request.form['password']
    confirm_password = request.form['confirm-password']

    rhash = request.args.get('hash')
    user = User.query.filter_by(recovery_hash=rhash).first()
    
    if datetime.utcnow() > user.recovery_expire:
        user.recovery_expire = None
        user.recovery_hash = None
        user.save()
        return abort(401)

    user.recovery_hash = None
    user.recovery_expire = None

    user.save()

    if password != confirm_password:
        return render_template('/admin/recovery_password.html', hash=rhash, error="Password and Confirm password must be equal")

    if user:
        user.password = generate_password_hash(password)
        if not user.save():
            return render_template('/admin/recovery_password.html', hash=rhash, error="An error occured saving the new credentials")
        flash("Password changed successfully", "success")
        return redirect('/admin/login')
    else:
        return abort(401)


@login_blueprint.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    max_attempts = False
    if session.get('user'):
        return redirect(url_for('admin.admin'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.is_active and int(user.attempts) >= 2:
            error = "Max login attempts"
            max_attempts = True

        elif user and user.is_active and check_password_hash(user.password, password):
            #TODO: carica i permessi dell'utente
            #TODO: se l'utente non ha i permessi per accedere al backoffice cancella la sessione
            session['user'] = user.to_dict()
            user.attempts = 0
            db.session.commit()
            return redirect(url_for('admin.admin'))
        else:
            if user:
                user.attempts += 1
                db.session.commit()
            error = "Username or password is incorrect"
    if error:
        flash(error, "danger")
    return render_template('admin/views/login.html', max_attempts=max_attempts)

@login_blueprint.route('/admin/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect("/admin/login")

@login_blueprint.route('/admin/changepassword', methods=['GET', 'POST'])
@with_user()
def change_password(user):
    form = PassForm()
    if request.method == 'GET':
        return render_template('/admin/change_password.html', user=user, form=form)
    
    if form.validate_on_submit():
        dbuser = User.query.filter_by(id=user.id).first()
        if form.new_password.data:
            if not check_password_hash(dbuser.password, form.old_password.data):
                flash("Password vecchia errata", "error")
                return redirect(url_for('login.change_password'))
            dbuser.password = generate_password_hash(form.new_password.data)
            if dbuser.save():
                flash("Password cambiata con successo", "success")
            else:
                flash("Un errore ha impedito il cambiamento della password", "error")
        else:
            flash("Un errore ha impedito il cambiamento della password", "error")
    else:
        flash("Un errore ha impedito il cambiamento della password", "error")
    return redirect(url_for('login.change_password'))