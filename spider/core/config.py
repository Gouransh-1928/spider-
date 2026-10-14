from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:latest"

    spider_host: str = "127.0.0.1"
    spider_port: int = 8000

    spider_api_token: str = ""

    memory_db_path: str = "data/spider.db"

    max_context_messages: int = 12
    max_memory_results: int = 5
    max_memory_chars: int = 6000

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def memory_database(self) -> Path:
        path = BASE_DIR / self.memory_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()