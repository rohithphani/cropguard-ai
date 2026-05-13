"""
Disease classification using custom trained TensorFlow ResNet-50 on PlantVillage.
Reads class_names.json and best_model.keras from the models/ directory.
Requires TF 2.18 + Keras 3.x (standalone).
"""

import os
os.environ["KERAS_BACKEND"] = "tensorflow"  # Must be set before keras import

import json
import logging
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ─── Singleton ───────────────────────────────────────────────────────────────
_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = CustomTFClassifier()
    return _classifier


class CustomTFClassifier:
    def __init__(self):
        print("[Model] Loading custom TensorFlow ResNet-50 ...")
        
        # Load class names
        class_names_path = os.path.join("models", "class_names.json")
        try:
            with open(class_names_path, "r") as f:
                self.label_map = {i: name for i, name in enumerate(json.load(f))}
        except Exception as e:
            logger.warning(f"Failed to load class names: {e}. Fallback to empty map.")
            self.label_map = {}
            
        try:
            import tensorflow as tf
            import keras
            self.tf = tf
            self.keras = keras
            
            # Load weights - prefer patched (quantization_config-stripped) version,
            # fall back to original .keras then .h5
            model_path_fixed = os.path.join("models", "final_model.keras")
            model_path_keras = os.path.join("models", "best_model.keras")
            model_path_h5    = os.path.join("models", "best_model.h5")

            if os.path.exists(model_path_fixed):
                self.model = keras.models.load_model(model_path_fixed)
                print(f"[Model] [OK] Weights loaded successfully from {model_path_fixed}!")
            elif os.path.exists(model_path_keras):
                self.model = keras.models.load_model(model_path_keras)
                print(f"[Model] [OK] Weights loaded successfully from {model_path_keras}!")
            elif os.path.exists(model_path_h5):
                self.model = keras.models.load_model(model_path_h5)
                print(f"[Model] [OK] Weights loaded successfully from {model_path_h5}!")
            else:
                logger.warning(f"Weights file not found. Using UNTRAINED model until training finishes.")
                # Create a dummy model
                base = keras.applications.ResNet50(include_top=False, input_shape=(224, 224, 3))
                x = keras.layers.GlobalAveragePooling2D()(base.output)
                outputs = keras.layers.Dense(38, activation='softmax')(x)
                self.model = keras.Model(base.input, outputs)
                
        except Exception as e:
            logger.error(f"Failed to initialize TensorFlow model: {e}")
            self.model = None

    def predict(self, image: Image.Image) -> dict:
        """
        Run inference with Test-Time Augmentation (TTA).

        TTA strategy: generate 8 views of the image (original + flips + rotations +
        center-crop), run each through the model, then average the softmax outputs.
        This significantly improves accuracy on real-world photos that differ from
        the controlled PlantVillage training distribution.
        """
        if not self.label_map:
            raise RuntimeError("Model classes not loaded. Please ensure class_names.json exists in models directory.")
        if self.model is None:
            raise RuntimeError("TensorFlow model failed to load.")

        rgb = image.convert("RGB")

        # ── Build 8 augmented views ───────────────────────────────────────────
        views = []

        # 1. Center-crop (removes background edges) then full resize
        views.append(_center_crop_resize(rgb, crop_frac=0.85))

        # 2. Full image, standard resize
        views.append(rgb.resize((224, 224), Image.LANCZOS))

        # 3. Horizontal flip
        views.append(rgb.transpose(Image.FLIP_LEFT_RIGHT).resize((224, 224), Image.LANCZOS))

        # 4. Vertical flip
        views.append(rgb.transpose(Image.FLIP_TOP_BOTTOM).resize((224, 224), Image.LANCZOS))

        # 5. 180° rotation
        views.append(rgb.rotate(180).resize((224, 224), Image.LANCZOS))

        # 6. Center-crop 70% + flip
        views.append(_center_crop_resize(rgb, crop_frac=0.70)
                     .transpose(Image.FLIP_LEFT_RIGHT))

        # 7. Slight zoom-in crop (top-left quadrant leaning)
        views.append(_corner_crop_resize(rgb, corner="tl"))

        # 8. Slight zoom-in crop (bottom-right quadrant leaning)
        views.append(_corner_crop_resize(rgb, corner="br"))

        # ── Batch predict all views at once ──────────────────────────────────
        preprocess = self.keras.applications.resnet50.preprocess_input
        img_to_arr = self.keras.utils.img_to_array

        batch = np.stack([
            preprocess(np.expand_dims(img_to_arr(v), 0))[0]
            for v in views
        ])  # shape: (8, 224, 224, 3)

        all_preds = self.model.predict(batch, verbose=0)   # shape: (8, 38)
        predictions = all_preds.mean(axis=0)               # averaged softmax

        # ── Build output ─────────────────────────────────────────────────────
        top_indices = np.argsort(predictions)[-5:][::-1]
        top_probs   = predictions[top_indices]

        top_label      = self.label_map[top_indices[0]]
        top_conf_float = float(top_probs[0])
        top_conf       = round(top_conf_float * 100, 2)
        crop, disease  = _parse_label(top_label)

        top_predictions = [
            {
                "label":       _format_label(self.label_map[i]),
                "probability": round(float(p) * 100, 2),
            }
            for i, p in zip(top_indices, top_probs)
        ]

        # 3-Tier Confidence Logic
        tier = 3
        if top_conf_float >= 0.80:
            tier = 1
        elif top_conf_float >= 0.60:
            tier = 2

        return {
            "raw_label":       top_label,
            "crop":            crop,
            "disease":         disease,
            "confidence":      top_conf,
            "is_healthy":      "healthy" in disease.lower(),
            "top_predictions": top_predictions,
            "tier":            tier,
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_label(label: str) -> tuple[str, str]:
    """'Tomato___Late_blight' -> ('Tomato', 'Late Blight')"""
    parts = label.split("___")
    crop    = parts[0].replace("_", " ").strip()
    disease = parts[1].replace("_", " ").strip().title() if len(parts) > 1 else label
    return crop, disease


def _format_label(label: str) -> str:
    return label.replace("___", " - ").replace("_", " ").title()


def _center_crop_resize(img: Image.Image, crop_frac: float = 0.85) -> Image.Image:
    """
    Crop the central `crop_frac` fraction of the image then resize to 224×224.
    Reduces background clutter in real-world photos.
    """
    w, h = img.size
    new_w = int(w * crop_frac)
    new_h = int(h * crop_frac)
    left  = (w - new_w) // 2
    top   = (h - new_h) // 2
    return img.crop((left, top, left + new_w, top + new_h)).resize((224, 224), Image.LANCZOS)


def _corner_crop_resize(img: Image.Image, corner: str = "tl", frac: float = 0.80) -> Image.Image:
    """
    Crop a corner region (tl/br) of `frac` size then resize to 224×224.
    Provides off-center views to improve robustness.
    """
    w, h = img.size
    cw, ch = int(w * frac), int(h * frac)
    if corner == "tl":
        box = (0, 0, cw, ch)
    else:  # "br"
        box = (w - cw, h - ch, w, h)
    return img.crop(box).resize((224, 224), Image.LANCZOS)
