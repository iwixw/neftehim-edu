"""Фабрика приложения Flask."""
from flask import Flask

from config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    # Регистрация моделей и blueprint-ов
    from . import models  # noqa: F401  (нужно для создания таблиц)
    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.catalog import catalog_bp
    from .blueprints.cabinet import cabinet_bp
    from .blueprints.glossary import glossary_bp
    from .blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(cabinet_bp)
    app.register_blueprint(glossary_bp)
    app.register_blueprint(admin_bp)

    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="Доступ запрещён. Раздел доступен только администратору."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="Страница не найдена."), 404

    with app.app_context():
        db.create_all()

    return app
