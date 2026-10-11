import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pyogrio

from app.config import settings
from app.models.database import init_db
from app.models.schemas import HealthResponse
from app.routers.files import router as files_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Production-ready FastAPI service for geospatial file upload, CRS reprojection, and precise geometric measurements (Shapefile & KML).",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(files_router, prefix=settings.API_PREFIX)

# Static files for web visualization dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", tags=["Dashboard"], include_in_schema=False)
def serve_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"Welcome to {settings.PROJECT_NAME}. View docs at /docs"}

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    drivers = [d for d in pyogrio.list_drivers() if any(k in d for k in ["KML", "ESRI", "GeoJSON"])]
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        supported_formats=[".zip (Shapefile)", ".kml"],
        gdal_pyogrio_drivers=drivers
    )
