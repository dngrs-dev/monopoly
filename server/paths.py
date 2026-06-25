import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENTS_ROOT = REPO_ROOT / "clients"
WEB_ROOT = CLIENTS_ROOT / "web"

DB_PATH = os.getenv("DB_PATH", "./.data/deedbound.db")

AVATARS_DIR = Path(__file__).resolve().parents[1] / ".data" / "avatars"
ASSETS_DIR = Path(__file__).resolve().parents[1] / ".data" / "assets"
