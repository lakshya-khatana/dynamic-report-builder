"""
Dynamic Report Builder Engine — FastAPI entry point.

Run locally with:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes_reports import router as reports_router
from api.routes_schema import router as schema_router
from api.routes_sources import router as sources_router
from api.routes_templates import router as templates_router
from config import settings
from data_admin import router as data_router  # NEW
from errors.handlers import register_error_handlers
from templates_store.models import init_app_db

UI_FILE = Path(__file__).parent / "ui" / "report-builder.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Modern replacement for the deprecated @app.on_event("startup") — creates
    # the app's own tables (data_sources, report_templates) if missing.
    init_app_db()
    yield


app = FastAPI(
    title="Dynamic Report Builder Engine",
    version="0.1.0",
    description="Schema-agnostic report builder over RDBMS and flat-file sources.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)


@app.get("/health")
def health_check():
    """Basic liveness probe. No DB touch here on purpose — keep it fast and dumb."""
    return {"status": "ok", "env": settings.ENV}


@app.get("/", include_in_schema=False)
def ui_home():
    """Serve the report builder UI so the app works from a single URL."""
    return FileResponse(UI_FILE)


app.include_router(sources_router, prefix="/sources", tags=["sources"])
app.include_router(schema_router, prefix="/sources", tags=["schema"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])
app.include_router(templates_router, prefix="/templates", tags=["templates"])
app.include_router(data_router)  # NEW (prefix "/data" is already inside data_admin.py)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)