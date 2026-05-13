from flask import Flask
import os
from config import Config
from app.database import db, bcrypt, login_manager

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        from app import models  # noqa
        db.create_all()

        # ── Auto-seed admin on first run (e.g. fresh Render deploy) ──────────
        from app.models import User
        if User.query.count() == 0:
            from app.database import bcrypt as _bcrypt
            admin = User(
                username="rohith",
                password_hash=_bcrypt.generate_password_hash("admin").decode("utf-8"),
                is_admin=True,
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Admin user 'rohith' created automatically.")

    from app.routes import main
    from app.auth import auth
    from app.admin import admin_bp
    from app.api import api_bp
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    return app
