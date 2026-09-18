import sys
from pathlib import Path

# Add project root to sys.path so `app` package is importable on Vercel
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app  # noqa: E402
