from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/{full_path:path}")
async def _test(full_path: str = ""):
    return HTMLResponse("<h1>Vercel Python runtime works</h1>")
