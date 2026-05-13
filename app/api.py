"""REST API blueprint for CropGuard AI.

All endpoints under /api/
Authentication: X-API-Key header must match API_KEY in .env
"""

import os
from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from app.models import History, User
from app.database import db

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ─── API Key Auth ─────────────────────────────────────────────────────────────

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        server_key = current_app.config.get("API_KEY", "")
        if not server_key or key != server_key:
            return jsonify({"error": "Unauthorized. Provide a valid X-API-Key header."}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Health Check ─────────────────────────────────────────────────────────────

@api_bp.route("/health")
def health():
    """Public endpoint — confirms the API is running."""
    total_scans = History.query.count()
    total_users = User.query.count()
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "service": "CropGuard AI",
        "stats": {
            "total_users": total_users,
            "total_scans": total_scans
        }
    })


# ─── Predict ─────────────────────────────────────────────────────────────────

@api_bp.route("/predict", methods=["POST"])
@require_api_key
def predict():
    """
    POST /api/predict
    Headers: X-API-Key: <your_api_key>
    Body: multipart/form-data with 'image' file field
    Returns: JSON with crop, disease, confidence, is_healthy, advisory
    """
    from app.utils import allowed_file, save_uploaded_image, load_image
    from app.model import get_classifier
    from app.advisor import generate_advisory, classify_with_gemini_vision

    if "image" not in request.files:
        return jsonify({"error": "No image file provided. Send a file under the 'image' key."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use PNG, JPG, JPEG, or WEBP."}), 400

    try:
        filename, filepath = save_uploaded_image(file, current_app.config["UPLOAD_FOLDER"])

        image = load_image(filepath)
        classifier = get_classifier()
        prediction = classifier.predict(image)

        # Gemini fallback for low confidence
        if prediction.get("tier", 1) >= 2:
            api_key = current_app.config.get("GEMINI_API_KEY", "")
            gemini = classify_with_gemini_vision(image, api_key)
            if gemini and not gemini.get("rate_limited") and gemini.get("is_valid") is not False:
                prediction = gemini

        language = request.form.get("language", "English")
        advisory = generate_advisory(
            crop=prediction["crop"],
            disease=prediction["disease"],
            is_healthy=prediction["is_healthy"],
            api_key=current_app.config["GEMINI_API_KEY"],
            language=language
        )

        return jsonify({
            "success": True,
            "prediction": {
                "crop": prediction.get("crop"),
                "disease": prediction.get("disease"),
                "is_healthy": prediction.get("is_healthy"),
                "confidence": prediction.get("confidence"),
                "tier": prediction.get("tier", 1)
            },
            "advisory": advisory
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── User History (session auth) ──────────────────────────────────────────────

@api_bp.route("/history")
@login_required
def user_history():
    """GET /api/history — returns the current user's scan history as JSON."""
    records = (
        History.query
        .filter_by(user_id=current_user.id)
        .order_by(History.timestamp.desc())
        .limit(50)
        .all()
    )
    return jsonify({
        "user": current_user.username,
        "count": len(records),
        "history": [
            {
                "id": r.id,
                "crop": r.crop,
                "disease": r.disease,
                "is_healthy": r.disease.lower() == "healthy",
                "timestamp": r.timestamp.isoformat(),
                "image_url": r.image_url
            }
            for r in records
        ]
    })
