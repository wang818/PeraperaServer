from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = "PeraperaServer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/perapera_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - use string type to avoid JSON parsing issues
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "PeraperaServer"
    
    # RapidAPI
    RAPIDAPI_KEY: str = ""

    # Tencent Cloud COS
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""
    COS_BUCKET: str = ""
    COS_REGION: str = "ap-tokyo"
    COS_UPLOAD_PREFIX: str = "audios/"

    # Apple In-App Purchase (IAP)
    APPLE_IAP_ENVIRONMENT: str = "sandbox"  # "sandbox" or "production"
    APPLE_IAP_BUNDLE_ID: str = ""           # e.g. "com.perapera.app"
    APPLE_IAP_ISSUER_ID: str = ""           # App Store Connect → Keys → Issuer ID
    APPLE_IAP_KEY_ID: str = ""              # App Store Connect → Keys → Key ID
    APPLE_IAP_PRIVATE_KEY: str = ""         # .p8 private key content (PEM format, can be inline or path)
    APPLE_IAP_APP_SHARED_SECRET: str = ""   # App Store Connect shared secret for receipt verification
    
    def get_allowed_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]


settings = Settings()
