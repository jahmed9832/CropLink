import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip()
    MONGODB_URI: str = os.getenv("MONGODB_URI", "").strip()
    MONGODB_DB: str = os.getenv("MONGODB_DB", "agrisphere").strip()
    API_KEY: str = os.getenv("API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-change-me")
    AUTH_REQUIRED: bool = os.getenv("AUTH_REQUIRED", "true").lower() == "true"
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    SEED_DEMO: bool = os.getenv("SEED_DEMO", "false").lower() == "true"
    ALLOW_DEMO_SEED: bool = os.getenv("ALLOW_DEMO_SEED", "false").lower() == "true"
    DEMO_PASSWORD: str = os.getenv("DEMO_PASSWORD", "")
    ALLOW_SYNTHETIC_DATA: bool = os.getenv("ALLOW_SYNTHETIC_DATA", "false").lower() == "true"
    DEFAULT_LANG: str = os.getenv("DEFAULT_LANG", "bn")
    ALLOWED_ORIGINS: list = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
    MODELS_DIR: str = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models"))
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))


settings = Settings()
