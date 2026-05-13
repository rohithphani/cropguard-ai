"""
Download the PlantVillage dataset from Kaggle using the Kaggle API.

SETUP (one-time):
  1. Go to https://www.kaggle.com/settings → API → Create New Token
  2. Place the downloaded kaggle.json in:
       Windows: C:\\Users\\<YourName>\\.kaggle\\kaggle.json
  3. Or set environment variables KAGGLE_USERNAME and KAGGLE_KEY in your .env file.

USAGE:
  python scripts/download_dataset.py
"""

import os
import zipfile
import sys
from pathlib import Path

DATASET = "abdallahalidev/plantvillage-dataset"
DEST_DIR = Path(__file__).parent.parent / "data" / "plantvillage"


def setup_kaggle_credentials():
    """Load Kaggle credentials from .env if not already in environment."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")

    if username and key:
        kaggle_dir = Path.home() / ".kaggle"
        kaggle_dir.mkdir(exist_ok=True)
        kaggle_json = kaggle_dir / "kaggle.json"
        if not kaggle_json.exists():
            import json
            kaggle_json.write_text(json.dumps({"username": username, "key": key}))
            kaggle_json.chmod(0o600)
            print(f"[Kaggle] Credentials written to {kaggle_json}")


def download_dataset():
    setup_kaggle_credentials()

    try:
        import kaggle  # noqa — triggers credential check
    except ImportError:
        print("[Error] kaggle package not installed. Run: pip install kaggle")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] Kaggle auth failed: {e}")
        print("Make sure your kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY are configured.")
        sys.exit(1)

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DEST_DIR / "plantvillage-dataset.zip"

    print(f"[Kaggle] Downloading '{DATASET}' to {DEST_DIR} ...")
    print("[Kaggle] This may take a few minutes (dataset is ~1.5 GB) ...")

    import subprocess
    print("\n[Kaggle] Starting download (Progress bar should appear below)...\n")
    kaggle_exe = str(Path(sys.executable).parent / "kaggle.exe")
    subprocess.run([
        kaggle_exe, "datasets", "download", 
        "-d", DATASET, "-p", str(DEST_DIR), "--unzip"
    ], check=True)

    print(f"\n[✓] Dataset downloaded and extracted to: {DEST_DIR}")
    print("[✓] You can now use the data for model training.")
    print("\nDirectory structure:")
    for p in sorted(DEST_DIR.iterdir()):
        print(f"  {p.name}/")


if __name__ == "__main__":
    download_dataset()
