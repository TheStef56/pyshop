from extensions import db
from datetime import datetime

admin_permissions =  [
    {'name': 'view_users', 'description': 'View all users'},
    {'name': 'edit_users', 'description': 'Edit user details'},
    {'name': 'delete_users', 'description': 'Delete users'},
    {'name': 'view_products', 'description': 'Create new products'},
    {'name': 'edit_products', 'description': 'Edit existing products'},
    {'name': 'delete_products', 'description': 'Delete products'},
    {'name': 'view_orders', 'description': 'View orders'},
    {'name': 'edit_orders', 'description': 'Edit orders'},
    {'name': 'delete_orders', 'description': 'Delete orders'},
    {'name': 'download_invoices', 'description': 'Download invoices'},
    {'name': 'edit_settings', 'description': 'Edit settings'},
    {'name': 'view_categories', 'description': 'View product categories'},
    {'name': 'edit_categories', 'description': 'Edit product categories'},
    {'name': 'view_labels', 'description': 'View labels'},
    {'name': 'edit_labels', 'description': 'Edit labels'},
    {'name': 'view_earnings', 'description': 'View earnings'}
]

# Tabella di associazione tra UserRoles e RolePermission
role_permissions_assoc = db.Table(
    'role_permissions_assoc',
    db.Column('user_role_id', db.Integer, db.ForeignKey('user_roles.id'), primary_key=True),
    db.Column('role_permission_id', db.Integer, db.ForeignKey('role_permissions.id'), primary_key=True)
)

class RolePermission(db.Model):
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def from_dict(data):
        return RolePermission(
            id=data.get('id'),
            name=data.get('name'),
            description=data.get('description'),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow())
        )
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<RolePermission {self.name}>'