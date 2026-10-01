from functools import wraps
from models.user import User
from flask import session, abort

def permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_data = session.get('user', None)
            if not user_data:
                return abort(403)
            user = User.from_dict(user_data)
            if not user or not user.has_permission(permission):
                return abort(403)
            return f(user, *args, **kwargs)
        return decorated_function
    return decorator