from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://football:football@localhost:5432/football"
    REDIS_URL: str = "redis://localhost:6379/0"
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_BYTES: int = 2147483648  # 2 GB
    ALLOWED_EXTENSIONS: str = ".mp4,.mkv"
    CORS_ORIGINS: str = "http://localhost:4200"
    PIPELINE_MODE: str = "real"  # real
    STALE_JOB_SECONDS: int = 300
    JOB_TIMEOUT_SECONDS: int = 7200

    # Real pipeline settings
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_MODEL_ID: str = "football-players-detection-3zvbc/11"
    ROBOFLOW_FIELD_MODEL_ID: str = "football-field-detection-f07vi/14"
    DETECTION_CONFIDENCE: float = 0.3
    FRAME_STRIDE: int = 5
    MAX_CLIP_SECONDS: float = 120.0
    MAX_FRAME_WIDTH: int = 1280
    MIN_TRACK_SECONDS_STORE: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

settings = Settings()
