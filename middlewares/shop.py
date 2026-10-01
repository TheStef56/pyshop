from functools import wraps
from flask import session, abort
from models.settings import Setting

def is_shop_open():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            global_settings = Setting.query.filter_by(name='global').first()
            if not global_settings or global_settings.meta.get('open', 'closed') != 'open':
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator