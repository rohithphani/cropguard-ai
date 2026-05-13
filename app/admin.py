"""Admin blueprint for CropGuard AI — full control panel."""

import csv
import io
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, jsonify
from flask_login import current_user, login_required
from app.database import db, bcrypt
from app.models import User, History
from sqlalchemy import func

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ─── Access Guard ────────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: only allow logged-in admins."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("🚫 Access denied. Admins only.", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


# ─── Dashboard ───────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    total_users   = User.query.count()
    total_scans   = History.query.count()
    healthy_scans = History.query.filter(
        func.lower(History.disease) == "healthy"
    ).count()
    disease_scans = total_scans - healthy_scans

    # Top 5 most detected diseases
    top_diseases = (
        db.session.query(History.disease, func.count(History.id).label("cnt"))
        .group_by(History.disease)
        .order_by(func.count(History.id).desc())
        .limit(5)
        .all()
    )

    # Top 5 most scanned crops
    top_crops = (
        db.session.query(History.crop, func.count(History.id).label("cnt"))
        .group_by(History.crop)
        .order_by(func.count(History.id).desc())
        .limit(5)
        .all()
    )

    # Recent 10 scans
    recent_scans = (
        History.query
        .order_by(History.timestamp.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_scans=total_scans,
        healthy_scans=healthy_scans,
        disease_scans=disease_scans,
        top_diseases=top_diseases,
        top_crops=top_crops,
        recent_scans=recent_scans,
    )


# ─── User Management ─────────────────────────────────────────────────────────

@admin_bp.route("/users")
@admin_required
def users():
    all_users = (
        User.query
        .outerjoin(History, User.id == History.user_id)
        .add_columns(func.count(History.id).label("scan_count"))
        .group_by(User.id)
        .order_by(User.id.asc())
        .all()
    )
    return render_template("admin/users.html", all_users=all_users)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("❌ You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))
    # Delete user's history first
    History.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f"🗑️ User '{user.username}' and all their data have been deleted.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin status.", "error")
        return redirect(url_for("admin.users"))
    user.is_admin = not user.is_admin
    db.session.commit()
    status = "promoted to Admin" if user.is_admin else "demoted to User"
    flash(f"'{user.username}' has been {status}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-ban", methods=["POST"])
@admin_required
def toggle_ban(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot ban your own account.", "error")
        return redirect(url_for("admin.users"))
    user.is_banned = not user.is_banned
    db.session.commit()
    status = "suspended" if user.is_banned else "reinstated"
    flash(f"'{user.username}' has been {status}.", "success")
    return redirect(url_for("admin.users"))


# ─── CSV Export ───────────────────────────────────────────────────────────────

@admin_bp.route("/export/users")
@admin_required
def export_users():
    users = User.query.order_by(User.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Username", "Email", "Admin", "Banned", "Joined"])
    for u in users:
        writer.writerow([
            u.id, u.username, u.email or "",
            "Yes" if u.is_admin else "No",
            "Yes" if u.is_banned else "No",
            u.created_at.strftime("%Y-%m-%d") if u.created_at else ""
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=users_export.csv"}
    )


@admin_bp.route("/export/history")
@admin_required
def export_history():
    records = (
        History.query
        .join(User, History.user_id == User.id)
        .add_columns(User.username)
        .order_by(History.timestamp.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User", "Crop", "Disease", "Status", "Timestamp"])
    for scan, username in records:
        writer.writerow([
            scan.id, username, scan.crop, scan.disease,
            "Healthy" if scan.disease.lower() == "healthy" else "Disease",
            scan.timestamp.strftime("%Y-%m-%d %H:%M")
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=history_export.csv"}
    )


# ─── Chart.js Stats API ───────────────────────────────────────────────────────

@admin_bp.route("/api/stats")
@admin_required
def api_stats():
    """JSON endpoint for Chart.js dashboard charts."""
    # Scans per day — last 14 days
    today = datetime.utcnow().date()
    labels, scan_data = [], []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        count = History.query.filter(
            func.date(History.timestamp) == day
        ).count()
        labels.append(day.strftime("%b %d"))
        scan_data.append(count)

    # Disease vs Healthy
    total   = History.query.count()
    healthy = History.query.filter(func.lower(History.disease) == "healthy").count()
    disease = total - healthy

    # Top 8 diseases
    top = (
        db.session.query(History.disease, func.count(History.id).label("cnt"))
        .group_by(History.disease)
        .order_by(func.count(History.id).desc())
        .limit(8).all()
    )

    return jsonify({
        "daily": {"labels": labels, "data": scan_data},
        "ratio": {"healthy": healthy, "disease": disease},
        "top_diseases": {"labels": [r[0] for r in top], "data": [r[1] for r in top]}
    })


# ─── History Management ───────────────────────────────────────────────────────

@admin_bp.route("/history")
@admin_required
def history():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()

    query = (
        History.query
        .join(User, History.user_id == User.id)
        .add_columns(User.username)
        .order_by(History.timestamp.desc())
    )

    if search:
        query = query.filter(
            History.crop.ilike(f"%{search}%") |
            History.disease.ilike(f"%{search}%") |
            User.username.ilike(f"%{search}%")
        )

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/history.html", pagination=pagination, search=search)


@admin_bp.route("/history/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_history(item_id):
    item = History.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("🗑️ Scan record deleted.", "success")
    return redirect(request.referrer or url_for("admin.history"))
