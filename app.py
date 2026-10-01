import os, sys
from flask_mail import Mail
from dotenv import load_dotenv
from flask import Flask
from flask import session as f_session
from models.settings import Setting
from extensions import db, migrate, session, babel, cache
from utils.smart_translation import smart_translation_update
from sshtunnel import SSHTunnelForwarder
from blueprints.locale import get_locale
from sqlalchemy.pool import NullPool

mail_noreply = Mail()
mail_orders = Mail()

def create_app(cli=False, with_env=True):
    if with_env:
        load_dotenv()

    #configure ssh connection
    if(os.getenv('DATABASE_SSH_HOST', None)):
        server = SSHTunnelForwarder(
            (os.getenv('DATABASE_SSH_HOST'), int(os.getenv('DATABASE_SSH_PORT', 22))),
            ssh_username=os.getenv('DATABASE_SSH_USER'),
            ssh_password=os.getenv('DATABASE_SSH_PASS'),
            remote_bind_address=("127.0.0.1", 3306),
            local_bind_address=("127.0.0.1",)  # scegli una porta libera
        )
        server.start()

    app = Flask(__name__)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'poolclass': NullPool  # solo se vuoi nessun pool
    }
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = "sqlalchemy"
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SESSION_SQLALCHEMY_TABLE'] = "sessions"

    #region no-reply mail
    app.config['MAIL_SERVER'] = os.getenv("NOREPLY_HOST")
    app.config['MAIL_PORT'] = os.getenv("NOREPLY_PORT")
    app.config['MAIL_USE_TLS'] = os.getenv("NOREPLY_TLS") == "True"
    app.config['MAIL_USE_SSL'] = os.getenv("NOREPLY_SSL") == "True"
    app.config['MAIL_USERNAME'] = os.getenv("NOREPLY_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("NOREPLY_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("NOREPLY_EMAIL")

    mail_noreply.init_app(app)
    #endregion

    #region orders mai
    app.config['MAIL_SERVER'] = os.getenv("ORDERS_HOST")
    app.config['MAIL_PORT'] = os.getenv("ORDERS_PORT")
    app.config['MAIL_USE_TLS'] = os.getenv("ORDERS_TLS") == "True"
    app.config['MAIL_USE_SSL'] = os.getenv("ORDERS_SSL") == "True"
    app.config['MAIL_USERNAME'] = os.getenv("ORDERS_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("ORDERS_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("ORDERS_EMAIL")

    mail_orders.init_app(app)
    #endregion

    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'it']
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    
    app.config['CACHE_TYPE'] = 'FileSystemCache'
    app.config['CACHE_DIR'] = 'flask_cache'  # cartella dove salvare i file
    app.config['CACHE_DEFAULT_TIMEOUT'] = 3600  # timeout di default in secondi
    
    db.init_app(app)
    cache.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app, locale_selector=get_locale)

    if not cli:
        session.init_app(app)
        with app.app_context():
            db.create_all()

    @app.context_processor
    def utility_processor():
        def hide_currency_switch():
            return os.getenv('HIDE_CURRENCY_SWITCH','false') == 'true'
        
        def get_app_name():
            header_settings = Setting.query.filter_by(name='header').first()
            if header_settings and header_settings.meta:
                site_name = header_settings.meta.get("site_name")
                if site_name: return site_name
            return os.getenv('APP_NAME', '')
        
        def get_app_description():
            header_settings = Setting.query.filter_by(name='header').first()
            if header_settings and header_settings.meta:
                site_description = header_settings.meta.get("site_description")
                if site_description: return site_description
            return os.getenv('APP_DESCRIPTION', '')
        
        def get_processing_time():
            header_settings = Setting.query.filter_by(name='header').first()
            if header_settings and header_settings.meta:
                processing_time = header_settings.meta.get("processing_time")
                if processing_time: return str(processing_time)
            return "0"

        return dict(
            hide_currency_switch=hide_currency_switch,
            get_app_name=get_app_name,
            get_app_description=get_app_description,
            get_processing_time=get_processing_time
        )

    @app.before_request
    def before_all():
        header_settings = Setting.query.filter_by(name='header').first()
        social_settings = Setting.query.filter_by(name='social').first()

        f_session['settings'] =  {
            'header' : header_settings.meta if header_settings else None,
            'social' : social_settings.meta if social_settings else None
        }

    from blueprints.locale import locale_blueprint
    from blueprints.admin.orders import orders_blueprint
    from blueprints.admin.settings import settings_blueprint
    from blueprints.admin.products import products_blueprint
    from blueprints.admin.admin import admin_blueprint
    from blueprints.admin.users import users_blueprint
    from blueprints.admin.categories import categories_blueprint
    from blueprints.login import login_blueprint
    from blueprints.public import public_blueprint
    from blueprints.admin.labels import labels_blueprint
    from blueprints.admin.earnings import earnings_blueprint
    app.register_blueprint(users_blueprint)
    app.register_blueprint(settings_blueprint)
    app.register_blueprint(locale_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(login_blueprint)
    app.register_blueprint(labels_blueprint)
    app.register_blueprint(categories_blueprint)
    app.register_blueprint(public_blueprint)
    app.register_blueprint(products_blueprint)
    app.register_blueprint(orders_blueprint)
    app.register_blueprint(earnings_blueprint)

    return app

if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")
    
    if flask_env != "production":
        # Sistema intelligente che aggiorna solo quello che serve
        smart_translation_update()
    
    app = create_app()
    app.run(debug=(flask_env != "production"))
    