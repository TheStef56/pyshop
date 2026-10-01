from functools import wraps
from flask import  abort, session, redirect
from models import User

def with_user(_ = None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_data = session.get('user', None)
            if not user_data:
                return redirect("/admin/login")
            user = User.from_dict(user_data)
            if not user:
                return abort(401)
            return f(user, *args, **kwargs)
        return decorated_function
    return decorator
