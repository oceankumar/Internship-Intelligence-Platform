from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_env: str = "local"
    frontend_origin: str = "http://localhost:3000"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    local_data_path: str = "data/internships.json"
    discovery_user_agent: str = "InternshipIntelligenceBot/0.1"
    request_timeout_seconds: float = 20.0
    provider_concurrency: int = Field(default=2, ge=1, le=8)
    provider_cache_seconds: int = 3600
    provider_request_interval: float = 1.0
    discovery_cooldown_seconds: int = 60
    stale_days: int = 30
    inactive_days: int = 90
    minimum_trust: int = 40
    enable_ai_classification: bool = False
    ai_base_url: str = "http://127.0.0.1:11434/v1"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_confidence_threshold: float = 0.8
    ai_cache_seconds: int = 604800
    api_token: str = ""
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    resume_max_bytes: int = 2_000_000
    greenhouse_boards: list[str] = ["stripe", "reddit", "gitlab", "anthropic", "figma", "vercel"]
    blocked_companies: list[str] = ["unified mentor", "wake up whistle", "bharat intern", "internpe"]
    blocked_domains: list[str] = []
    enabled_sources: list[str] = ["remoteok", "yc_jobs", "simplify_jobs", "github_jobs", "public_datasets", "startup_career_pages"]
    simplify_urls: list[str] = ["https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"]
    github_tracker_urls: list[str] = ["https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md", "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/INTERN_INTL.md", "https://raw.githubusercontent.com/vanshb03/Summer2026-Internships/main/README.md"]
    discovery_lease_seconds: int = Field(default=900, ge=180, le=3600)
    discovery_timeout_seconds: int = Field(default=150, ge=30, le=600)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def data_path(self) -> Path:
        config_dir = Path(__file__).parent.resolve()
        backend_dir = config_dir.parent
        return (backend_dir / self.local_data_path).resolve()

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
