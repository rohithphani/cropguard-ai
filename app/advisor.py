"""
Advisory generation using Google Gemini 1.5 Flash.
Returns structured JSON with disease description, causes, treatment and prevention.
"""

from google import genai
from google.genai import types
import json
import logging
import io
import time
from PIL import Image

logger = logging.getLogger(__name__)

# ── All 38 PlantVillage class names (must match class_names.json order) ──────
PLANT_CLASSES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy",
    "Grape___Black_rot", "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus", "Tomato___healthy",
]

VISION_CLASSIFY_PROMPT = """You are an expert plant pathologist analyzing a leaf image.

STEP 1 — Check if the image is a plant leaf:
- If it is NOT a plant leaf (e.g. person, animal, vehicle, food, object, random photo), respond with:
{{"predicted_class": "not_a_plant_leaf", "confidence": 0.0, "reasoning": "This image shows <what it actually is>, not a plant leaf."}}

STEP 2 — Check if the plant is in the supported list:
The system ONLY supports these 38 plant/disease classes:

{classes}

- If the plant leaf IS one of the above, classify it and return the exact class name.
- If the plant leaf is NOT in the list (e.g. mango, wheat, rice, banana), respond with:
{{"predicted_class": "not_a_plant_leaf", "confidence": 0.0, "reasoning": "This appears to be a <plant name> leaf, which is not supported. Supported crops are: Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, and Tomato."}}

Rules:
- Never guess or pick the closest match for unsupported species.
- Respond with ONLY a valid JSON object, no markdown, no extra text.

JSON format:
{{
  "predicted_class": "<exact class name from the list OR not_a_plant_leaf>",
  "confidence": <float 0.0 to 1.0>,
  "reasoning": "<one sentence explanation>"
}}
"""


def classify_with_gemini_vision(image: Image.Image, api_key: str) -> dict | None:
    """
    Use Gemini Vision to classify a plant disease from a real-world image.
    Returns a prediction dict compatible with ResNet50 output, or None on failure.
    Called as a fallback when ResNet50 confidence < 60%.
    """
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)

        # Convert PIL image to JPEG bytes for the API
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=90)
        image_bytes = buf.getvalue()

        classes_str = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(PLANT_CLASSES))
        prompt = VISION_CLASSIFY_PROMPT.format(classes=classes_str)

        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        prompt,
                    ],
                )
                text = response.text.strip()
                # Strip markdown fences if present
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()

                result = json.loads(text)
                predicted_class = result.get("predicted_class", "").strip()
                reasoning  = result.get("reasoning", "")

                # ── Reject non-plant images ───────────────────────────────
                if predicted_class == "not_a_plant_leaf":
                    logger.info(f"Gemini Vision rejected image: {reasoning}")
                    return {
                        "is_valid":  False,
                        "reasoning": reasoning,
                    }

                # Validate the class is in our list
                if predicted_class not in PLANT_CLASSES:
                    # Try partial match
                    matches = [c for c in PLANT_CLASSES if predicted_class.lower() in c.lower()]
                    predicted_class = matches[0] if matches else PLANT_CLASSES[0]

                confidence = float(result.get("confidence", 0.75))
                reasoning  = result.get("reasoning", "")

                # Parse crop / disease from class name
                parts   = predicted_class.split("___")
                crop    = parts[0].replace("_", " ").strip()
                disease = parts[1].replace("_", " ").strip().title() if len(parts) > 1 else predicted_class

                top_conf = round(confidence * 100, 2)
                tier = 1 if confidence >= 0.80 else (2 if confidence >= 0.60 else 3)

                logger.info(f"Gemini Vision classified: {predicted_class} ({top_conf}%) via {model_name}")

                return {
                    "raw_label":       predicted_class,
                    "crop":            crop,
                    "disease":         disease,
                    "confidence":      top_conf,
                    "is_healthy":      "healthy" in disease.lower(),
                    "top_predictions": [{"label": predicted_class.replace("___", " - ").replace("_", " ").title(),
                                         "probability": top_conf}],
                    "tier":            tier,
                    "gemini_enhanced": True,
                    "gemini_reasoning": reasoning,
                }

            except json.JSONDecodeError:
                logger.warning(f"Gemini Vision ({model_name}) returned non-JSON.")
                continue
            except Exception as e:
                err = str(e)
                if "429" in err or "EXHAUSTED" in err:
                    logger.warning(f"Gemini Vision ({model_name}) rate limited.")
                    continue
                if "404" in err or "NOT_FOUND" in err:
                    continue
                logger.error(f"Gemini Vision error ({model_name}): {e}")
                break

        # If we reach here, all models either failed or were rate limited
        return {
            "is_valid": False,
            "rate_limited": True,
            "reasoning": "Gemini AI is currently receiving too many requests. Please wait a minute and try again."
        }

    except Exception as e:
        logger.error(f"Gemini Vision setup error: {e}")

    return None



HEALTHY_PROMPT = """
You are an expert agricultural advisor. A farmer's {crop} plant has been identified as HEALTHY.
IMPORTANT: You MUST respond ENTIRELY in {language}. Provide ALL JSON values in {language}.
Provide advice as a valid JSON object with exactly these keys:
{{
  "status": "Healthy",
  "description": "2-sentence description of what a healthy {crop} plant looks like",
  "symptoms": "No disease symptoms detected",
  "causes": "N/A — Plant is healthy",
  "treatment": "Maintenance tips to keep the plant thriving",
  "prevention": "General disease prevention best practices for {crop}",
  "severity": "None",
  "recommendations": ["tip 1", "tip 2", "tip 3", "tip 4"]
}}
Return ONLY the JSON object, no markdown or extra text.
"""

DISEASE_PROMPT = """
You are an expert agricultural advisor. A farmer's {crop} plant has been diagnosed with "{disease}".
IMPORTANT: You MUST respond ENTIRELY in {language}. Provide ALL JSON values in {language}.
Provide detailed advice as a valid JSON object with exactly these keys:
{{
  "status": "Diseased",
  "description": "2-3 sentences explaining what this disease is",
  "symptoms": "Visible symptoms the farmer should look for",
  "causes": "What causes this disease (pathogen type, environmental triggers)",
  "treatment": "Specific treatment steps and recommended products/fungicides/pesticides",
  "prevention": "How to prevent this disease in future growing seasons",
  "severity": "One of: Low, Medium, or High",
  "recommendations": ["immediate action 1", "action 2", "action 3", "action 4", "action 5"]
}}
Use simple language a farmer can understand. Return ONLY the JSON object, no markdown or extra text.
"""


# Models to try in order (cheapest first)
CANDIDATE_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


def generate_advisory(crop: str, disease: str, is_healthy: bool, api_key: str, language: str = "English") -> dict:
    """Try multiple Gemini models in order; retry once after delay on rate limits."""
    if not api_key:
        logger.warning("No GEMINI_API_KEY — using fallback advisory.")
        return _fallback_advisory(crop, disease, is_healthy)

    client = genai.Client(api_key=api_key)
    prompt = (
        HEALTHY_PROMPT.format(crop=crop, language=language)
        if is_healthy
        else DISEASE_PROMPT.format(crop=crop, disease=disease, language=language)
    )

    def _try_models():
        for model_name in CANDIDATE_MODELS:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                advisory = json.loads(text)
                logger.info(f"Advisory generated with {model_name} in {language}.")
                return advisory
            except json.JSONDecodeError:
                logger.warning(f"{model_name} returned non-JSON.")
                return None
            except Exception as e:
                err = str(e)
                if "429" in err or "404" in err or "NOT_FOUND" in err or "EXHAUSTED" in err:
                    logger.warning(f"{model_name} rate limited, trying next...")
                    continue
                logger.error(f"Unexpected Gemini error on {model_name}: {e}")
                return None
        return None  # all models exhausted

    # First attempt
    result = _try_models()
    if result:
        return result

    # All models rate-limited — wait 10s and retry ONCE
    logger.warning("All models rate-limited. Retrying in 10 seconds...")
    time.sleep(10)
    result = _try_models()
    if result:
        return result

    # Both attempts failed — fall back to static advisory
    logger.warning("Advisory generation failed after retry. Using fallback.")
    return _fallback_advisory(crop, disease, is_healthy)


def _fallback_advisory(crop: str, disease: str, is_healthy: bool) -> dict:
    """Return a basic advisory when Gemini fails to parse."""
    if is_healthy:
        return {
            "status": "Healthy",
            "description": f"Your {crop} plant appears to be in good health.",
            "symptoms": "No disease symptoms detected.",
            "causes": "N/A — Plant is healthy",
            "treatment": "Continue regular watering and fertilisation.",
            "prevention": "Monitor regularly for early signs of disease.",
            "severity": "None",
            "recommendations": [
                "Maintain regular irrigation",
                "Apply balanced fertiliser",
                "Inspect leaves weekly",
                "Ensure good air circulation",
            ],
        }
    return {
        "status": "Diseased",
        "description": f"Your {crop} plant shows signs of {disease}.",
        "symptoms": "Visible discolouration or lesions on leaves.",
        "causes": "Fungal, bacterial, or viral infection.",
        "treatment": "Consult a local agricultural extension officer for specific treatment.",
        "prevention": "Rotate crops, remove infected debris, use disease-resistant varieties.",
        "severity": "Medium",
        "recommendations": [
            "Remove and destroy infected plant parts",
            "Apply appropriate fungicide/pesticide",
            "Improve field drainage",
            "Avoid overhead irrigation",
            "Consult agricultural extension services",
        ],
    }
