import os
import sys
import logging
from pathlib import Path
import random

# Add project root to path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.model import get_classifier
from config import Config

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from torchvision import datasets

def main():
    print("Initializing MobileNetV2 Model...")
    classifier = get_classifier(Config.MODEL_NAME)
    
    data_dir = Path("data/plantvillage")
    if not data_dir.exists():
        print(f"Error: Dataset not found at {data_dir}.")
        print("Please run `python scripts/download_dataset.py` to download the PlantVillage dataset first.")
        print("Note: The dataset is ~1.5GB and may take a while to download.")
        return

    print("Loading dataset folder structure...")
    # ImageFolder automatically uses subfolders as class labels
    dataset = datasets.ImageFolder(data_dir)
    
    # Sample 200 random images to keep the evaluation fast.
    # To evaluate the entire 54,000 image dataset, remove this random sampling.
    random.seed(42)
    sample_indices = random.sample(range(len(dataset)), min(200, len(dataset)))
    
    y_true = []
    y_pred = []
    
    print(f"\nEvaluating {len(sample_indices)} random images (simulating a test set)...")
    
    for i, idx in enumerate(sample_indices):
        img, class_idx = dataset[idx]
        
        # The true label is the exact folder name
        true_label = dataset.classes[class_idx]
        
        # Run our app's predict method (includes background removal & MobileNetV2)
        res = classifier.predict(img)
        pred_label = res['condition']
        
        y_true.append(true_label)
        y_pred.append(pred_label)
        
        if (i + 1) % 20 == 0:
            print(f"Processed {i+1}/{len(sample_indices)} images...")

    print("\n✅ Evaluation Complete!")
    
    print("\n" + "="*50)
    print("CLASSIFICATION REPORT")
    print("="*50)
    print(classification_report(y_true, y_pred, zero_division=0))
    
    print("\nGenerating Confusion Matrix Plot...")
    cm = confusion_matrix(y_true, y_pred)
    
    # Get the unique labels that actually appeared in this random sample
    labels = sorted(list(set(y_true + y_pred)))
    
    plt.figure(figsize=(14, 12))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=labels, yticklabels=labels)
    plt.xlabel('Predicted Label', fontsize=12, fontweight='bold')
    plt.ylabel('Actual Label', fontsize=12, fontweight='bold')
    plt.title('Confusion Matrix - PlantDisease Classification', fontsize=14, pad=20)
    
    # Rotate x-axis labels so they are readable
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    
    plt.tight_layout()
    out_file = 'confusion_matrix.png'
    plt.savefig(out_file, dpi=300)
    print(f"📊 Confusion matrix graph saved successfully to: {out_file}")

if __name__ == "__main__":
    main()
