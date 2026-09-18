import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Declare at module top level so Vercel's static analyzer finds it.
# Python try/except does NOT create a new scope, so a successful
# "from app.main import app" below replaces this binding in-place.
app = None
_import_error = None

try:
    from app.main import app  # on success, app is replaced with the real FastAPI app
except Exception:
    _import_error = traceback.format_exc()

# If the import failed, stand up a minimal app that exposes the traceback
if app is None:
    from fastapi import FastAPI, Request
    from fastapi.responses import PlainTextResponse

    _e = _import_error
    app = FastAPI()

    @app.get("/{path:path}")
    @app.post("/{path:path}")
    async def _err(request: Request, path: str = ""):
        return PlainTextResponse(f"IMPORT FAILED:\n\n{_e}", status_code=500)
