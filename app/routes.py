"""Flask routes for the Crop Disease Detection app."""

import os
import json
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, send_file, session)
from io import BytesIO
from app.utils import allowed_file, save_uploaded_image, load_image, generate_pdf_report
from app.model import get_classifier
from app.advisor import generate_advisory, classify_with_gemini_vision
from flask_login import current_user, login_required
from app.models import History
from app.database import db

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/predict", methods=["POST"])
@login_required
def predict():
    if "image" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("main.index"))

    file = request.files["image"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("main.index"))

    if not allowed_file(file.filename):
        flash("Unsupported file type. Please upload a PNG, JPG, JPEG, or WEBP image.", "error")
        return redirect(url_for("main.index"))

    try:
        # Save uploaded image
        filename, filepath = save_uploaded_image(file, current_app.config["UPLOAD_FOLDER"])
        image_url = url_for("static", filename=f"uploads/{filename}")

        # Load image once — reused for both ResNet50 and Gemini Vision fallback
        image = load_image(filepath)

        # Run ResNet50 inference (with TTA)
        classifier = get_classifier()
        prediction = classifier.predict(image)

        # ── Gemini Vision fallback for low/moderate-confidence predictions ───
        # Fire Gemini Vision for ANY prediction below 80% confidence (Tier 2 or 3).
        # ResNet50 often confuses visually similar crops (e.g. Raspberry vs Cherry,
        # Apple Black Rot vs Grape Esca) even at 60-79% confidence.
        if prediction.get("tier", 1) >= 2:
            api_key = current_app.config.get("GEMINI_API_KEY", "")
            gemini_prediction = classify_with_gemini_vision(image, api_key)
            if gemini_prediction:
                # ── Handle Rate Limits ────────────────────────────────────────
                if gemini_prediction.get("rate_limited"):
                    flash(
                        "⚠️ Gemini Vision AI is currently receiving too many requests (Rate Limited). Showing fallback primary model result.",
                        "warning"
                    )
                    # Don't update 'prediction' — let the ResNet50 result fall through
                
                # ── Not a plant leaf — reject and redirect ────────────────
                elif gemini_prediction.get("is_valid") is False:
                    reason = gemini_prediction.get("reasoning", "This does not appear to be a plant leaf.")
                    flash(
                        f"🚫 Invalid image: {reason} Please upload a clear photo of a plant leaf.",
                        "danger"
                    )
                    return redirect(url_for("main.index"))

                # ── Valid Gemini result — use it ──────────────────────────
                else:
                    prediction = gemini_prediction
                    flash(
                        "🤖 Low confidence from primary model — result enhanced by Gemini Vision AI.",
                        "success"
                    )


        language = request.form.get("language", "English")

        # Generate Gemini advisory (gracefully falls back to static advisory on quota errors)
        advisory = generate_advisory(
            crop=prediction["crop"],
            disease=prediction["disease"],
            is_healthy=prediction["is_healthy"],
            api_key=current_app.config["GEMINI_API_KEY"],
            language=language
        )

        # Store in session for PDF download
        session["last_prediction"] = prediction
        session["last_advisory"] = advisory
        session["last_image_path"] = filepath
        session["last_image_url"] = image_url

        if current_user.is_authenticated:
            history_item = History(
                crop=prediction["crop"],
                disease=prediction["disease"],
                advisory_json=json.dumps(advisory),
                image_url=image_url,
                user_id=current_user.id
            )
            db.session.add(history_item)
            db.session.commit()

        return render_template(
            "result.html",
            prediction=prediction,
            advisory=advisory,
            image_url=image_url,
        )

    except RuntimeError as e:
        flash(str(e), "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "error")
        return redirect(url_for("main.index"))


@main.route("/download-report")
def download_report():
    prediction = session.get("last_prediction")
    advisory = session.get("last_advisory")
    image_path = session.get("last_image_path", "")

    if not prediction or not advisory:
        flash("No prediction data found. Please analyse an image first.", "error")
        return redirect(url_for("main.index"))

    try:
        pdf_bytes = generate_pdf_report(prediction, advisory, image_path)
        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        crop = prediction.get("crop", "plant").replace(" ", "_")
        disease = prediction.get("disease", "report").replace(" ", "_")
        return send_file(buf, as_attachment=True,
                         download_name=f"{crop}_{disease}_report.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        flash(f"Could not generate PDF: {e}", "error")
        return redirect(url_for("main.index"))


@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/history")
@login_required
def history():
    user_history = History.query.filter_by(user_id=current_user.id).order_by(History.timestamp.desc()).all()
    return render_template("history.html", history=user_history)

@main.route("/history/<int:item_id>")
@login_required
def view_history_item(item_id):
    item = History.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You do not have permission to view this item.", "error")
        return redirect(url_for('main.history'))
    
    prediction = {"crop": item.crop, "disease": item.disease, "is_healthy": item.disease == "Healthy"}
    
    session["last_prediction"] = prediction
    session["last_advisory"] = item.advisory
    session["last_image_url"] = item.image_url
    
    return render_template("result.html", prediction=prediction, advisory=item.advisory, image_url=item.image_url)


@main.route("/history/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_history_item(item_id):
    item = History.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You do not have permission to delete this item.", "error")
        return redirect(url_for('main.history'))
    db.session.delete(item)
    db.session.commit()
    flash("Scan record deleted.", "success")
    return redirect(url_for('main.history'))
