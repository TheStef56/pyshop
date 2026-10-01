from extensions import db
from datetime import datetime
from models.role_permission import role_permissions_assoc, RolePermission

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazione many-to-many con RolePermission
    permissions = db.relationship(
        'RolePermission',
        secondary=role_permissions_assoc,
        backref=db.backref('roles', lazy='dynamic')
    )
    
    @staticmethod
    def from_dict(data):
        user_role = UserRoles(
            id=data.get('id'),
            user_id=data.get('user_id'),
            role=data.get('role'),
            granted_at=data.get('granted_at', datetime.utcnow()),
            permissions=[RolePermission.from_dict(perm) for perm in data.get('permissions', [])] if 'permissions' in data else []
        )
        return user_role

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "granted_at": self.granted_at.isoformat(),
            "permissions": [perm.to_dict() for perm in self.permissions]
        }

    def __repr__(self):
        return f'<UserRole {self.user_id} - {self.role}>'