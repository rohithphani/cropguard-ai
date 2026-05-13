"""
Transfer Learning Training Script for PlantVillage Disease Classification.

Prerequisites:
  1. Download the dataset first: python scripts/download_dataset.py
  2. GPU recommended (CUDA or Apple MPS). CPU will work but slowly.

Usage:
  python scripts/train_model.py --epochs 15 --batch_size 32

Output:
  model/plant_disease_model.pth   — best model weights
  model/training_results.json     — accuracy/loss history
"""

import argparse
import json
import os
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms
from torchvision.models import MobileNet_V2_Weights

DATA_DIR  = Path(__file__).parent.parent / "data" / "plantvillage" / "plantvillage dataset" / "color"
MODEL_DIR = Path(__file__).parent.parent / "model"
MODEL_DIR.mkdir(exist_ok=True)


def get_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)
    # Freeze base layers
    for param in model.features.parameters():
        param.requires_grad = False
    # Replace classifier head
    model.classifier[1] = nn.Linear(model.last_channel, num_classes)
    return model


def train(args):
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    print(f"[Train] Using device: {device}")

    if not DATA_DIR.exists():
        print(f"[Error] Dataset not found at {DATA_DIR}")
        print("Run: python scripts/download_dataset.py")
        return

    train_tf, val_tf = get_transforms()

    full_dataset = datasets.ImageFolder(str(DATA_DIR), transform=train_tf)
    num_classes = len(full_dataset.classes)
    print(f"[Train] Classes: {num_classes}, Samples: {len(full_dataset)}")

    # 80/20 train-val split
    val_size  = int(0.2 * len(full_dataset))
    train_size = len(full_dataset) - val_size
    train_ds, val_ds = random_split(full_dataset, [train_size, val_size])
    val_ds.dataset.transform = val_tf

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    model = build_model(num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    history = {"train_acc": [], "val_acc": [], "train_loss": [], "val_loss": []}
    best_acc = 0.0

    for epoch in range(args.epochs):
        # Training
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += imgs.size(0)
        train_loss = running_loss / total
        train_acc  = correct / total * 100

        # Validation
        model.eval()
        v_loss, v_correct, v_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                v_loss += loss.item() * imgs.size(0)
                _, preds = torch.max(outputs, 1)
                v_correct += (preds == labels).sum().item()
                v_total += imgs.size(0)
        val_loss = v_loss / v_total
        val_acc  = v_correct / v_total * 100

        scheduler.step()
        history["train_acc"].append(round(train_acc, 2))
        history["val_acc"].append(round(val_acc, 2))
        history["train_loss"].append(round(train_loss, 4))
        history["val_loss"].append(round(val_loss, 4))

        print(f"Epoch [{epoch+1}/{args.epochs}] "
              f"Train: loss={train_loss:.4f} acc={train_acc:.1f}%  "
              f"Val: loss={val_loss:.4f} acc={val_acc:.1f}%")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_DIR / "plant_disease_model.pth")
            print(f"  ✓ Best model saved (val_acc={best_acc:.1f}%)")

    # Save class labels
    class_map = {str(v): k for k, v in full_dataset.class_to_idx.items()}
    with open(MODEL_DIR / "class_labels.json", "w") as f:
        json.dump(class_map, f, indent=2)

    # Save history
    with open(MODEL_DIR / "training_results.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n[✓] Training complete. Best val accuracy: {best_acc:.1f}%")
    print(f"[✓] Model saved to: {MODEL_DIR / 'plant_disease_model.pth'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int, default=15)
    parser.add_argument("--batch_size", type=int, default=32)
    train(parser.parse_args())
