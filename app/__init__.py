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
        try:
            db.create_all()
        except Exception:
            db.session.rollback()

        # ── Auto-seed admin on first run (e.g. fresh Render deploy) ──────────
        from app.models import User
        try:
            if not User.query.filter_by(username="rohith").first():
                from app.database import bcrypt as _bcrypt
                admin = User(
                    username="rohith",
                    password_hash=_bcrypt.generate_password_hash("admin").decode("utf-8"),
                    is_admin=True,
                )
                db.session.add(admin)
                db.session.commit()
                app.logger.info("Admin user 'rohith' created automatically.")
        except Exception:
            db.session.rollback()

    from app.routes import main
    from app.auth import auth
    from app.admin import admin_bp
    from app.api import api_bp
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # ── One-time setup route (use once, then it's a no-op) ───────────────────
    from flask import jsonify as _jsonify
    @app.route("/setup-admin")
    def setup_admin():
        from app.models import User
        from app.database import db as _db, bcrypt as _bcrypt
        existing = User.query.filter_by(username="rohith").first()
        if existing:
            existing.is_admin = True
            existing.password_hash = _bcrypt.generate_password_hash("admin").decode("utf-8")
            _db.session.commit()
            return _jsonify({"status": "ok", "message": "rohith promoted to admin, password reset to 'admin'"})
        new_admin = User(
            username="rohith",
            password_hash=_bcrypt.generate_password_hash("admin").decode("utf-8"),
            is_admin=True,
        )
        _db.session.add(new_admin)
        _db.session.commit()
        return _jsonify({"status": "ok", "message": "Admin user 'rohith' created with password 'admin'"})

    return app
