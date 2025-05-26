import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PORT: int = int(os.getenv("PORT",8000))

    BRIGHT_DATA_PROXY_HOST: str = os.getenv("BRIGHT_DATA_PROXY_HOST", "")
    BRIGHT_DATA_PROXY_PORT: str = os.getenv("BRIGHT_DATA_PROXY_PORT", "")
    BRIGHT_DATA_PROXY_USERNAME: str = os.getenv("BRIGHT_DATA_PROXY_USERNAME", "")
    BRIGHT_DATA_PROXY_PASSWORD: str = os.getenv("BRIGHT_DATA_PROXY_PASSWORD", "")

    ENVIRONMENT: Optional[str] = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # Let it be a string initially (raw from .env)
    CORS_ORIGINS: Union[str, List[Union[AnyHttpUrl, str]]] = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            if v.startswith("["):
                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS_ORIGINS: {v}")

    class Config:
        case_sensitive = True
        env_file = [".env", f".env.{os.getenv('ENVIRONMENT', 'development')}"]
        env_file_encoding = "utf-8"
