from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import files as files_router
from routers import export as export_router
from routers import templates as templates_router
from routers import auto as auto_router
from services.cleanup import CleanupTask


# Storage directory: configurable so production can mount a persistent disk
# (e.g. /var/data on Render) without code changes.
STORAGE = Path(os.environ.get("STORAGE_DIR") or (Path(__file__).parent / "storage"))
STORAGE.mkdir(parents=True, exist_ok=True)

cleanup = CleanupTask(STORAGE)


def _parse_origins() -> list[str]:
    """Parse CORS_ORIGINS env var. Comma-separated. Defaults to '*' for dev.
    For production set, e.g.: CORS_ORIGINS=https://my-app.vercel.app,https://staging.vercel.app
    """
    raw = (os.environ.get("CORS_ORIGINS") or "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup.start()
    try:
        yield
    finally:
        await cleanup.stop()


app = FastAPI(title="Smart Excel Engine", version="4.0.0", lifespan=lifespan)

origins = _parse_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # When using credentials, cannot mix with '*'. We don't currently use cookies/auth.
    allow_credentials=("*" not in origins),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-PDFA-Status", "X-PDFA-Requested", "X-PDFA-Available", "X-PDFA-Message",
    ],
)


@app.get("/api/health")
def health():
    from services.ocr import is_available as ocr_available
    from services.pdfa import is_available as pdfa_available
    return {
        "ok": True,
        "version": "4.0.0",
        "ocr_available": ocr_available(),
        "pdfa_available": pdfa_available(),
        "storage_dir": str(STORAGE),
    }


@app.get("/api/capabilities")
def capabilities():
    from services.ocr import is_available as ocr_available
    from services.pdfa import is_available as pdfa_available
    return {
        "ocr": ocr_available(),
        "pdfa_real": pdfa_available(),
    }


app.include_router(files_router.make_router(STORAGE), prefix="/api")
app.include_router(export_router.make_router(STORAGE), prefix="/api")
app.include_router(auto_router.make_router(STORAGE), prefix="/api")
app.include_router(templates_router.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
