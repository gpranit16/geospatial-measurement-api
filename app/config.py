import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Geospatial File Measurement API"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/geomeasure.db"
    
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = [".zip", ".kml"]
    
    # CRS configuration
    DEFAULT_GEOGRAPHIC_CRS: str = "EPSG:4326"

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
