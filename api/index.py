import os
import sys
import traceback
from pathlib import Path

_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from app.main import app
except Exception:
    _tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    app = FastAPI()

    @app.get("/{full_path:path}")
    async def _show_error(full_path: str = ""):
        return HTMLResponse(
            "<pre style='color:#f87;background:#111;padding:2rem;font-size:13px'>"
            f"cwd: {os.getcwd()}\nsys.path: {sys.path}\n\n{_tb}</pre>"
        )
