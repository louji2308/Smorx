import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    cors_origins: list[str] = ["http://localhost:3000"]

settings = Settings()
