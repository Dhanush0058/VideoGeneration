import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    
    # Mode
    LOW_RESOURCE: bool = True
    
    # Paths
    STORAGE_PATH: str = "./storage"
    
    # LLM Settings
    LLM_PROVIDER: str = "MOCK"  # GEMINI, GROQ, OPENAI, MOCK
    MODEL_NAME: str = "gemini-1.5-flash"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    HF_TOKEN: str = ""
    
    # TTS Settings
    TTS_PROVIDER: str = "EDGE_TTS"  # EDGE_TTS, LOCAL_PYTTSX3
    TTS_VOICE: str = "en-US-GuyNeural"
    
    # Image Settings
    IMAGE_PROVIDER: str = "DIAGRAM_FALLBACK"  # HF_API, DIAGRAM_FALLBACK
    IMAGE_MODEL: str = "stabilityai/stable-diffusion-xl-base-1.0"
    
    # Video Settings
    VIDEO_PROVIDER: str = "NONE"
    VIDEO_MODEL: str = ""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
settings.STORAGE_PATH = os.path.abspath(settings.STORAGE_PATH)

# Ensure directories exist
os.makedirs(settings.STORAGE_PATH, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "jobs"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_PATH, "temp"), exist_ok=True)
