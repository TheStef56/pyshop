from .role_permission import RolePermission
from .user import User
from .user_roles import UserRoles
from .product import Product 

# Use strings in __all__ for imports, but expose classes for direct use
__all__ = ['RolePermission', 'User', 'UserRoles', 'Product']

# Make classes available directly from models package
MODELS = [RolePermission, User, UserRoles, Product]