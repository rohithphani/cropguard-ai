"""
Reset the CropGuard database and create the default admin user.

Usage:
    python scripts/reset_db.py

This will:
  1. Drop all existing tables (wipes all users and history)
  2. Re-create all tables fresh
  3. Create admin user: username=rohith, password=admin, is_admin=True
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db, bcrypt
from app.models import User, History

def reset_and_seed():
    app = create_app()
    with app.app_context():
        print("[!] Dropping all tables...")
        db.drop_all()
        print("[+] Creating fresh tables...")
        db.create_all()

        # Create admin user
        hashed_pw = bcrypt.generate_password_hash("admin").decode("utf-8")
        admin = User(
            username="rohith",
            password_hash=hashed_pw,
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()

        print("[*] Admin user created:")
        print(f"    Username : rohith")
        print(f"    Password : admin")
        print(f"    Admin    : True")
        print("\n[OK] Database reset complete. You can now log in at /login")

if __name__ == "__main__":
    reset_and_seed()
