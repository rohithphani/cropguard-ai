# 🌿 CropGuard AI — Crop Disease Detection & Advisory System

> **Group 17** | Domain: Agriculture Technology

An AI-powered web application that detects crop diseases from leaf images using deep learning and provides expert advisory through Google Gemini AI.

---

## ✨ Features

- 📸 **Drag & drop image upload** with real-time preview
- 🧠 **MobileNetV2** deep learning model trained on PlantVillage (38 disease classes, 14 crops)
- 🤖 **Google Gemini 1.5 Flash** advisory generation (symptoms, causes, treatment, prevention)
- 📊 **Confidence meter** + top-5 predictions
- 📄 **Downloadable PDF report** with full diagnosis
- 🎨 Premium dark-green UI with animations

---

## 🚀 Quick Start

### 1. Clone / Navigate to Project
```bash
cd crop-disease-detection
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Run the App
```bash
python run.py
```

Open your browser at **http://localhost:5000** 🎉

> **Note:** The first run will download the pre-trained MobileNetV2 model from HuggingFace (~14 MB). This is cached locally after the first download.

---

## 📁 Project Structure

```
crop-disease-detection/
├── app/
│   ├── __init__.py       # Flask app factory
│   ├── routes.py         # URL routes
│   ├── model.py          # CNN inference (HuggingFace MobileNetV2)
│   ├── advisor.py        # Gemini AI advisory generation
│   └── utils.py          # Image processing + PDF generation
├── templates/
│   ├── base.html         # Base layout
│   ├── index.html        # Home / upload page
│   ├── result.html       # Prediction + advisory results
│   └── about.html        # About page
├── static/
│   ├── css/style.css     # Premium dark design system
│   ├── js/main.js        # Drag-drop, animations, UX
│   └── uploads/          # Saved user images (auto-created)
├── data/
│   └── class_labels.json # 38-class PlantVillage label map
├── scripts/
│   ├── download_dataset.py  # Kaggle API dataset downloader
│   └── train_model.py       # Transfer learning training script
├── docs/
│   └── technical_report.md  # Full project report
├── requirements.txt
├── config.py
├── run.py
└── .env.example
```

---

## 🌱 Supported Crops & Diseases

| Crop | Diseases Detected |
|---|---|
| Apple | Apple Scab, Black Rot, Cedar Apple Rust, Healthy |
| Tomato | Bacterial Spot, Early Blight, Late Blight, Leaf Mold, Septoria, Spider Mites, Target Spot, TYLCV, Mosaic Virus, Healthy |
| Potato | Early Blight, Late Blight, Healthy |
| Corn | Cercospora Gray Leaf Spot, Common Rust, Northern Leaf Blight, Healthy |
| Grape | Black Rot, Esca, Leaf Blight, Healthy |
| Pepper | Bacterial Spot, Healthy |
| Peach | Bacterial Spot, Healthy |
| + 7 more | Cherry, Blueberry, Orange, Raspberry, Soybean, Squash, Strawberry |

---

## 🗂 Dataset (PlantVillage)

To download the full dataset for training:
```bash
# Set KAGGLE_USERNAME and KAGGLE_KEY in your .env file first
python scripts/download_dataset.py
```

Dataset: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset

---

## 🏋️ Training Your Own Model

After downloading the dataset:
```bash
python scripts/train_model.py --epochs 15 --batch_size 32
```

Outputs saved to `model/`:
- `plant_disease_model.pth` — best model weights
- `training_results.json` — accuracy/loss history

---

## 🧪 Tech Stack

| Component | Technology |
|---|---|
| Deep Learning Model | MobileNetV2 (HuggingFace Transformers) |
| Generative AI | Google Gemini 1.5 Flash |
| Web Framework | Python Flask |
| Image Processing | Pillow (PIL) |
| PDF Generation | ReportLab |
| Dataset | PlantVillage (Kaggle) |
| Frontend | HTML5 + Vanilla CSS + JavaScript |

---

## 👥 Group 17

**Project:** Crop Disease Detection and Advisory System  
**Domain:** Agriculture Technology
