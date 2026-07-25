from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GEMINI_API_KEY: str = ""
    AI_PROVIDER: str = "openrouter"  # "gemini" for direct API, "openrouter" for OpenRouter
    AI_MODEL_TIER: str = "cheap"     # "free", "cheap", "best" — model quality/cost tier
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    DATABASE_URL: str = "sqlite:///./lingua_ai.db"
    SECRET_KEY: str = ""  # Must be set in .env file
    ADMIN_API_KEY: str = ""  # API key for admin endpoints (backup, etc.)
    # Shared secret guarding the whole API. Empty (default) = no gate, which is
    # what you want on localhost. Set it before exposing the app to the internet
    # (tunnel, cloud) — otherwise anyone with the URL can read/modify your data
    # and spend your AI credits.
    APP_ACCESS_TOKEN: str = ""
    TARGET_LANGUAGE: str = "German"
    NATIVE_LANGUAGE: str = "Polish"
    DISCORD_WEBHOOK_URL: str = ""
    NOTIFY_LESSON_HOUR: int = 8
    NOTIFY_REVIEW_HOUR: int = 18
    # Web Push (VAPID). Empty (default) = push disabled, like DISCORD_WEBHOOK_URL.
    # Generate a keypair with:  python -m backend.scripts.generate_vapid_keys
    # VAPID_SUBJECT must be a mailto: or https: URL identifying the sender.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@linguaai.local"
    GDRIVE_FOLDER_ID: str = ""
    GDRIVE_CLIENT_SECRETS_FILE: str = "backend/gdrive_credentials.json"
    YOUTUBE_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8001"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()