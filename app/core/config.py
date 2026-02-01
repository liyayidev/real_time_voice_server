from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Realtime Voice Agent Server"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_FILE: str = "server.log"
    
    # Security
    SECRET_KEY: str = "changethis"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Audio
    SAMPLE_RATE: int = 16000
    FRAME_DURATION_MS: int = 20
    
    # AI Config
    DEFAULT_AGENT_PROVIDER: str = "mock" # options: "mock", "google"
    
    # AI Providers (Keys)
    OPENAI_API_KEY: Optional[str] = None
    DEEPGRAM_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    
    # Google Config
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None # OR path to file
    GOOGLE_PROJECT_ID: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()
