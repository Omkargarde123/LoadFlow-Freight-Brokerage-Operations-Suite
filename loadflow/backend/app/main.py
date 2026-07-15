import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth, roles, staff, loads, compliance, dashboard, audit

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LoadFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All API routes live under /api so they never collide with the React app's
# client-side routes (both "sides" use paths like /loads, /staff, /compliance
# — this is what makes serving both from one origin possible).
app.include_router(auth.router, prefix="/api")
app.include_router(roles.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
app.include_router(loads.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve the built React app (frontend/dist) from this same service, so the
# whole thing is one deployable unit with one URL. Falls back to index.html
# for any non-API path so React Router's client-side routing works on a
# hard refresh (e.g. GET /loads returns the SPA shell, not a 404).
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")

