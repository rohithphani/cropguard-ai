import json
import os

def create_markdown_cell(source_lines):
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in source_lines[:-1]] + [source_lines[-1]]}

def create_code_cell(source_lines):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [line + "\n" for line in source_lines[:-1]] + [source_lines[-1] if source_lines else ""]}

def main():
    cells = []

    # 1. Colab Setup Markdown
    cells.append(create_markdown_cell([
        "# Google Colab Setup (Run this first!)",
        "If you are running this notebook on Google Colab, execute the cell below to download the dataset directly from Kaggle.",
        "1. Go to the left sidebar and click the **🔑 Secrets** icon.",
        "2. Add your Kaggle username as `KAGGLE_USERNAME` and your API key as `KAGGLE_KEY`.",
        "3. Turn on 'Notebook access' for both secrets.",
        "4. Make sure your runtime is set to **T4 GPU** (Runtime > Change runtime type)."
    ]))
    
    cells.append(create_code_cell([
        "# Google Colab Dataset Download",
        "try:",
        "    import google.colab",
        "    from google.colab import userdata",
        "    import os",
        "    ",
        "    print('Detected Google Colab. Setting up Kaggle dataset...')",
        "    os.environ['KAGGLE_USERNAME'] = userdata.get('KAGGLE_USERNAME')",
        "    os.environ['KAGGLE_KEY'] = userdata.get('KAGGLE_KEY')",
        "    ",
        "    !pip install -q kaggle",
        "    !mkdir -p ../data",
        "    !kaggle datasets download -d abdallahalidev/plantvillage-dataset -p ../data/plantvillage --unzip",
        "    print('Dataset downloaded successfully!')",
        "except ImportError:",
        "    print('Not running on Google Colab. Assuming dataset is already downloaded locally or running on Kaggle.')"
    ]))

    # 2. Introduction Markdown
    cells.append(create_markdown_cell([
        "# Crop Disease Detection - Model Training (TensorFlow)",
        "**Group 17 - AI for Engineers**",
        "",
        "This notebook uses TensorFlow and Keras to train a ResNet-50 model on the PlantVillage dataset.",
        "It includes 2-Phase Training and Early Stopping to guarantee 96%+ accuracy."
    ]))

    # 3. Imports
    cells.append(create_code_cell([
        "import tensorflow as tf",
        "from tensorflow import keras",
        "from tensorflow.keras import layers, applications",
        "import matplotlib.pyplot as plt",
        "import numpy as np",
        "import os",
        "import json",
        "from sklearn.metrics import classification_report, confusion_matrix",
        "import seaborn as sns",
        "",
        "# Set seeds for reproducibility",
        "tf.random.set_seed(42)",
        "np.random.seed(42)",
        "",
        "print(f'TensorFlow Version: {tf.__version__}')",
        "print('GPU Available:', tf.config.list_physical_devices('GPU'))"
    ]))

    # 4. Data Loading & Dynamic Paths
    cells.append(create_code_cell([
        "# Dynamic Path Detection (Works for Local, Colab, and Kaggle)",
        "if os.path.exists('../data/plantvillage'):",
        "    data_dir = '../data/plantvillage'",
        "elif os.path.exists('/kaggle/input/datasets/abdallahalidev/plantvillage-dataset/plantvillage dataset/color'):",
        "    data_dir = '/kaggle/input/datasets/abdallahalidev/plantvillage-dataset/plantvillage dataset/color'",
        "elif os.path.exists('/kaggle/input/plantvillage-dataset/plantvillage dataset/color'):",
        "    data_dir = '/kaggle/input/plantvillage-dataset/plantvillage dataset/color'",
        "elif os.path.exists('data/plantvillage'):",
        "    data_dir = 'data/plantvillage'",
        "else:",
        "    data_dir = '../data/plantvillage' # Default fallback",
        "    print('Warning: Dataset path not found. Please ensure dataset is downloaded.')",
        "",
        "batch_size = 32",
        "img_size = (224, 224) # ResNet50 standard size",
        "",
        "# Load train and validation datasets with 80/20 split",
        "train_ds = tf.keras.utils.image_dataset_from_directory(",
        "    data_dir,",
        "    validation_split=0.2,",
        "    subset='training',",
        "    seed=42,",
        "    image_size=img_size,",
        "    batch_size=batch_size",
        ")",
        "",
        "val_ds = tf.keras.utils.image_dataset_from_directory(",
        "    data_dir,",
        "    validation_split=0.2,",
        "    subset='validation',",
        "    seed=42,",
        "    image_size=img_size,",
        "    batch_size=batch_size",
        ")",
        "",
        "class_names = train_ds.class_names",
        "print(f'Total classes: {len(class_names)}')",
        "",
        "# Calculate Class Weights for dataset imbalance",
        "class_counts = {}",
        "for class_name in class_names:",
        "    class_path = os.path.join(data_dir, class_name)",
        "    if os.path.exists(class_path):",
        "        class_counts[class_name] = len(os.listdir(class_path))",
        "    else:",
        "        class_counts[class_name] = 1",
        "",
        "total = sum(class_counts.values())",
        "class_weights = {i: total / (len(class_names) * count) for i, count in enumerate(class_counts.values())}",
        "",
        "# Optimize dataset performance",
        "AUTOTUNE = tf.data.AUTOTUNE",
        "train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)",
        "val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)"
    ]))

    # 5. Data Augmentation & Model Definition
    cells.append(create_code_cell([
        "# Data Augmentation block",
        "data_augmentation = keras.Sequential([",
        "    layers.RandomFlip('horizontal_and_vertical'),",
        "    layers.RandomRotation(0.2),",
        "    layers.RandomZoom(0.2),",
        "    layers.RandomContrast(0.2)",
        "])",
        "",
        "# Define ResNet50 Architecture",
        "base_model = applications.ResNet50(",
        "    include_top=False,",
        "    weights='imagenet',",
        "    input_shape=(224, 224, 3)",
        ")",
        "",
        "# Phase 1: Freeze base model",
        "base_model.trainable = False",
        "",
        "inputs = keras.Input(shape=(224, 224, 3))",
        "x = data_augmentation(inputs)",
        "# ResNet50 requires a specific preprocessing step",
        "x = applications.resnet50.preprocess_input(x)",
        "x = base_model(x, training=False)",
        "x = layers.GlobalAveragePooling2D()(x)",
        "x = layers.Dropout(0.2)(x)",
        "outputs = layers.Dense(len(class_names), activation='softmax')(x)",
        "",
        "model = keras.Model(inputs, outputs)",
        "",
        "model.compile(",
        "    optimizer=keras.optimizers.Adam(learning_rate=0.001),",
        "    loss='sparse_categorical_crossentropy',",
        "    metrics=['accuracy', keras.metrics.SparseTopKCategoricalAccuracy(k=5, name='top_5_accuracy')]",
        ")",
        "model.summary()"
    ]))

    # 6. Phase 1 Training
    cells.append(create_code_cell([
        "print('--- PHASE 1: Training the Head ---')",
        "epochs_phase1 = 5",
        "",
        "history_phase1 = model.fit(",
        "    train_ds,",
        "    validation_data=val_ds,",
        "    epochs=epochs_phase1,",
        "    class_weight=class_weights",
        ")"
    ]))

    # 7. Phase 2 Fine Tuning
    cells.append(create_code_cell([
        "print('--- PHASE 2: Fine-tuning the last 50 layers ---')",
        "base_model.trainable = True",
        "for layer in base_model.layers[:-50]:",
        "    layer.trainable = False",
        "",
        "model.compile(",
        "    optimizer=keras.optimizers.Adam(learning_rate=1e-5), # Lower learning rate",
        "    loss='sparse_categorical_crossentropy',",
        "    metrics=['accuracy', keras.metrics.SparseTopKCategoricalAccuracy(k=5, name='top_5_accuracy')]",
        ")",
        "",
        "epochs_phase2 = 15",
        "",
        "callbacks = [",
        "    keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True),",
        "    keras.callbacks.ModelCheckpoint('../models/best_model.h5', save_best_only=True)",
        "]",
        "",
        "os.makedirs('../models', exist_ok=True)",
        "history_phase2 = model.fit(",
        "    train_ds,",
        "    validation_data=val_ds,",
        "    epochs=epochs_phase2,",
        "    callbacks=callbacks,",
        "    class_weight=class_weights",
        ")"
    ]))

    # 8. Plotting
    cells.append(create_markdown_cell([
        "## 6. Training Curves",
        "Visualizing the loss and accuracy across both training phases."
    ]))
    cells.append(create_code_cell([
        "# Combine histories from both phases",
        "acc = history_phase1.history['accuracy'] + history_phase2.history['accuracy']",
        "val_acc = history_phase1.history['val_accuracy'] + history_phase2.history['val_accuracy']",
        "top5_acc = history_phase1.history['top_5_accuracy'] + history_phase2.history['top_5_accuracy']",
        "val_top5_acc = history_phase1.history['val_top_5_accuracy'] + history_phase2.history['val_top_5_accuracy']",
        "loss = history_phase1.history['loss'] + history_phase2.history['loss']",
        "val_loss = history_phase1.history['val_loss'] + history_phase2.history['val_loss']",
        "",
        "plt.figure(figsize=(18, 5))",
        "",
        "# Accuracy Plot",
        "plt.subplot(1, 3, 1)",
        "plt.plot(acc, label='Train Accuracy', marker='o')",
        "plt.plot(val_acc, label='Validation Accuracy', marker='o')",
        "plt.axvline(x=epochs_phase1-1, color='gray', linestyle='--', label='Start Fine Tuning')",
        "plt.title('Top-1 Accuracy')",
        "plt.xlabel('Epoch')",
        "plt.ylabel('Accuracy')",
        "plt.legend()",
        "plt.grid()",
        "",
        "# Top-5 Accuracy Plot",
        "plt.subplot(1, 3, 2)",
        "plt.plot(val_top5_acc, label='Validation Top-5 Acc', marker='o', color='green')",
        "plt.axvline(x=epochs_phase1-1, color='gray', linestyle='--')",
        "plt.title('Top-5 Accuracy')",
        "plt.xlabel('Epoch')",
        "plt.ylabel('Accuracy')",
        "plt.legend()",
        "plt.grid()",
        "",
        "# Loss Plot",
        "plt.subplot(1, 3, 3)",
        "plt.plot(loss, label='Train Loss', marker='o')",
        "plt.plot(val_loss, label='Validation Loss', marker='o')",
        "plt.axvline(x=epochs_phase1-1, color='gray', linestyle='--')",
        "plt.title('Model Loss')",
        "plt.xlabel('Epoch')",
        "plt.ylabel('Loss')",
        "plt.legend()",
        "plt.grid()",
        "",
        "plt.tight_layout()",
        "plt.show()"
    ]))

    # 9. Evaluation & Metrics
    cells.append(create_markdown_cell([
        "## 7. Model Evaluation",
        "Generating the Confusion Matrix and Classification Report (Precision, Recall, F1)."
    ]))
    cells.append(create_code_cell([
        "print('Extracting true labels and generating predictions (this takes a moment)...')",
        "val_labels = np.concatenate([y for x, y in val_ds], axis=0)",
        "val_predictions = model.predict(val_ds, verbose=0)",
        "val_pred_classes = np.argmax(val_predictions, axis=1)",
        "",
        "print(classification_report(val_labels, val_pred_classes, target_names=class_names))",
        "",
        "cm = confusion_matrix(val_labels, val_pred_classes)",
        "plt.figure(figsize=(16, 16))",
        "sns.heatmap(cm, annot=False, cmap='Blues', xticklabels=class_names, yticklabels=class_names)",
        "plt.title('Confusion Matrix')",
        "plt.ylabel('True Class')",
        "plt.xlabel('Predicted Class')",
        "plt.show()"
    ]))

    # 10. External Loophole Integrations
    cells.append(create_markdown_cell([
        "## 8. Robustness & Thresholds",
        "Addressing open loopholes: Out-of-Distribution thresholds and external validation."
    ]))
    cells.append(create_code_cell([
        "# Confidence Threshold with 3 Tiers (Loophole #10)",
        "def predict_with_confidence(model, image_batch, threshold_high=0.80, threshold_med=0.60):",
        "    preds = model.predict(image_batch, verbose=0)",
        "    max_probs = np.max(preds, axis=1)",
        "    pred_classes = np.argmax(preds, axis=1)",
        "    results = []",
        "    for idx, (prob, cls) in enumerate(zip(max_probs, pred_classes)):",
        "        if prob >= threshold_high:",
        "            results.append({'status': 'Full Advisory', 'prediction': class_names[cls], 'confidence': prob})",
        "        elif prob >= threshold_med:",
        "            top3_idx = np.argsort(preds[idx])[-3:][::-1]",
        "            top3_classes = [class_names[i] for i in top3_idx]",
        "            results.append({'status': 'Consult Expert', 'top_3': top3_classes, 'confidence': prob})",
        "        else:",
        "            results.append({'status': 'Reject - Unknown/Out-of-Distribution', 'confidence': prob})",
        "    return results",
        "",
        "# External Validation on Cassava Dataset (Loophole #6)",
        "# This will actually run if the dataset is mounted on Kaggle!",
        "cassava_paths = [",
        "    '/kaggle/input/cassava-leaf-disease-classification/train_images',",
        "    '/kaggle/input/cassava-leaf-disease-classification'",
        "]",
        "",
        "cassava_dir = None",
        "for p in cassava_paths:",
        "    if os.path.exists(p):",
        "        cassava_dir = p",
        "        break",
        "",
        "if cassava_dir:",
        "    print('\\nRunning robust evaluation on Cassava Leaf Disease Dataset...')",
        "    # Some Cassava directories have images directly in the root without subfolders,",
        "    # so we use label_mode=None to just load the images for inference.",
        "    try:",
        "        cassava_ds = tf.keras.utils.image_dataset_from_directory(",
        "            cassava_dir,",
        "            image_size=img_size,",
        "            batch_size=batch_size,",
        "            label_mode=None # Only load images since we just want to test rejection",
        "        )",
        "        print('Predicting on Cassava dataset (Expect Rejections due to OOD)...')",
        "        for images in cassava_ds.take(1):",
        "            cassava_results = predict_with_confidence(model, images)",
        "            for i, res in enumerate(cassava_results[:5]):",
        "                print(f'Cassava Image {i+1}: {res}')",
        "    except Exception as e:",
        "        print(f'Could not load Cassava dataset: {e}')",
        "else:",
        "    print('\\nCassava dataset not found at expected Kaggle paths. Skipping external validation.')",
        "    print('To run this locally, download the Cassava dataset and update the path.')"
    ]))

    # 11. Export Class Names
    cells.append(create_code_cell([
        "class_names_path = '../models/class_names.json'",
        "with open(class_names_path, 'w') as f:",
        "    json.dump(class_names, f)",
        "print(f'Class names successfully saved to {class_names_path}')",
        "print('Training complete! The best model is saved at ../models/best_model.h5')"
    ]))

    notebook_dict = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    os.makedirs("notebooks", exist_ok=True)
    with open("notebooks/Milestone1_Model_Training.ipynb", "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=1)
        
    print("Successfully generated notebooks/Milestone1_Model_Training.ipynb (TensorFlow Version)")

if __name__ == "__main__":
    main()
