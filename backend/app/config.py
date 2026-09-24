from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_BACKEND_DIR / ".env", extra="ignore")

    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Absolute path so the app, seed script and daemons all hit the same
    # backend/kiosk.db no matter which directory they are started from.
    database_url: str = f"sqlite:///{(_BACKEND_DIR / 'kiosk.db').as_posix()}"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    camera_index: int = 0
    camera_idle_timeout_seconds: int = 60

    face_recognition_enabled: bool = True
    face_stable_seconds: float = 3.0
    face_confidence_threshold: float = 80.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
