from flask import Flask, request
import os
import sys
import json
import time
import logging
from config import Config
from app.database import db, bcrypt, login_manager, migrate

_RESERVED_LOG_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    configure_logging(app)

    # Initialize Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.before_request
    def _start_timer():
        request._start_time = time.time()

    @app.after_request
    def _log_request(response):
        app.logger.info(
            "request",
            extra={
                "path": request.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((time.time() - getattr(request, "_start_time", time.time())) * 1000, 1),
            },
        )
        return response

    with app.app_context():
        from app import models  # noqa
        # Schema is managed by Alembic migrations (`flask db upgrade`).
        # db.create_all() was intentionally removed here — leaving it in would
        # silently bypass migration tracking and mask schema drift between
        # environments (e.g. local SQLite vs Cloud SQL). Run migrations before
        # starting the app in any new environment.

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
