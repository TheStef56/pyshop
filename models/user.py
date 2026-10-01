from extensions import db
from datetime import datetime
from models.model import Model
from models.user_roles import UserRoles

class User(Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    reset_hash = db.Column(db.String(256), nullable=True)
    recovery_hash = db.Column(db.String(256), nullable=True)
    reset_expire = db.Column(db.DateTime, nullable=True)
    recovery_expire = db.Column(db.DateTime, nullable=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Aggiungi la relazione one-to-many
    roles = db.relationship('UserRoles', backref='user', lazy=True)

    def has_permission(self, permission_name):
        """Check if the user has a specific permission."""
        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True
        return False

    @staticmethod
    def from_dict(data):
        user = User(
            id=data.get('id'),
            username=data.get('username'),
            email=data.get('email'),
            is_active=data.get('is_active', False),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow()),
            roles=[UserRoles.from_dict(role) for role in data.get('roles', [])]
        )
        return user

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "roles": [role.to_dict() for role in self.roles]
        }