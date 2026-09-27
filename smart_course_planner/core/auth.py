"""
Authentication service with salted password hashing.
Golden Rule 4: Never save a plain password. Save only its salted hash.
Uses hashlib.pbkdf2_hmac with sha256 and unique random salts.
"""

import os
import json
import hashlib
import secrets
from typing import Optional, Dict, Any


class AuthService:
    """
    Manages user registration, authentication, and secure salted password hashing.
    """

    def __init__(self, users_file_path: str = "data/users.json"):
        self.users_file_path = users_file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensures the users.json file and directory exist with default seed data."""
        os.makedirs(os.path.dirname(os.path.abspath(self.users_file_path)), exist_ok=True)
        if not os.path.exists(self.users_file_path):
            with open(self.users_file_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.users_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        with open(self.users_file_path, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)

    def _hash_password(self, password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
        """
        Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
        Returns (hash_hex, salt_hex).
        """
        if not salt_hex:
            salt_bytes = secrets.token_bytes(16)
            salt_hex = salt_bytes.hex()
        else:
            salt_bytes = bytes.fromhex(salt_hex)

        key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt_bytes,
            iterations=100000,
        )
        return key.hex(), salt_hex

    def register(
        self,
        username: str,
        password: str,
        full_name: str = "",
        student_id: str = "",
        current_semester: str = "Fall 2026",
    ) -> tuple[bool, str]:
        """
        Registers a new user with a salted password hash.
        """
        u = username.strip().lower()
        if not u or not password:
            return False, "Username and password cannot be empty."

        users = self._load_users()
        if u in users:
            return False, f"User '{username}' already exists."

        pwd_hash, salt_hex = self._hash_password(password)

        users[u] = {
            "username": u,
            "full_name": full_name.strip() or username.capitalize(),
            "student_id": student_id.strip() or "2026-001",
            "current_semester": current_semester,
            "password_hash": pwd_hash,
            "salt": salt_hex,
            "max_credits": 15.0,
            "registered_credits": 0.0,
        }

        self._save_users(users)
        return True, "Registration successful."

    def login(self, username: str, password: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authenticates a user against the stored salted hash.
        Returns (success, user_dict, message).
        """
        u = username.strip().lower()
        users = self._load_users()
        if u not in users:
            return False, None, "Invalid username or password."

        record = users[u]
        salt_hex = record.get("salt", "")
        stored_hash = record.get("password_hash", "")

        test_hash, _ = self._hash_password(password, salt_hex=salt_hex)
        if secrets.compare_digest(test_hash, stored_hash):
            user_data = {k: v for k, v in record.items() if k not in ("password_hash", "salt")}
            return True, user_data, "Login successful."
        else:
            return False, None, "Invalid username or password."
