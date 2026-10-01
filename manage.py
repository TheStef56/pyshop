from flask.cli import FlaskGroup
from app import create_app, db
from sqlalchemy import text
from models.user import User
from models.role_permission import RolePermission, admin_permissions
from models.user_roles import UserRoles
from werkzeug.security import generate_password_hash

app = create_app(True)
cli = FlaskGroup(app)

@cli.command("seed")
def seed():
    "Insert initial data into the database"

    # Disabilita foreign key checks
    db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
    db.session.query(RolePermission).delete()
    db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
    db.session.commit()

    # Crea o aggiorna i permessi
    existing_permissions = {perm.name: perm for perm in RolePermission.query.all()}
    
    for perm in admin_permissions:
        if perm['name'] not in existing_permissions:
            # Crea nuovo permesso
            new_permission = RolePermission(
                name=perm['name'], 
                description=perm['description']
            )
            db.session.add(new_permission)
            existing_permissions[perm['name']] = new_permission
    db.session.commit()

    # Crea admin se non esiste
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user and User.query.count() == 0:
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            email='dopeshirts.social@gmail.com',
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()

        # Crea ruolo admin per nuovo utente
        user_role = UserRoles(user_id=admin_user.id, role='admin')
        db.session.add(user_role)
        db.session.commit()

    # Aggiorna permessi per TUTTI i ruoli admin
    admin_roles = UserRoles.query.filter_by(role='admin').all()
    for role in admin_roles:
        existing_role_permissions = {p.name for p in role.permissions}
        for perm in admin_permissions:
            if perm['name'] not in existing_role_permissions:
                permission = existing_permissions[perm['name']]
                role.permissions.append(permission)
    
    db.session.commit()

if __name__ == "__main__":
    cli()
    