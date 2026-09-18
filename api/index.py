import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_import_error = None
try:
    from app.main import app as _app
except Exception:
    _import_error = traceback.format_exc()
    _app = None

if _app is not None:
    app = _app
else:
    from fastapi import FastAPI, Request
    from fastapi.responses import PlainTextResponse

    app = FastAPI()
    _err = _import_error

    @app.get("/{path:path}")
    @app.post("/{path:path}")
    async def _error_handler(request: Request, path: str = ""):
        return PlainTextResponse(f"IMPORT FAILED:\n\n{_err}", status_code=500)
