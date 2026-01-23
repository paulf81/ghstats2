"""Configuration management for ghstats2."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RepoConfig(BaseModel):
    """Configuration for a single repository."""

    owner: str
    name: str
    docs_url: str | None = None
    ga_property_id: str | None = None


class ReposConfig(BaseModel):
    """Repository list configuration loaded from repos.yaml."""

    defaults: dict[str, str] = Field(default_factory=dict)
    repos: list[dict]

    def get_repos(self) -> list[RepoConfig]:
        """Resolve repos with defaults applied.

        Returns:
            List of RepoConfig with owner defaulted if not specified.
        """
        default_owner = self.defaults.get("owner", "")
        return [
            RepoConfig(
                owner=r.get("owner", default_owner),
                name=r["name"],
                docs_url=r.get("docs_url"),
                ga_property_id=r.get("ga_property_id"),
            )
            for r in self.repos
        ]


class Settings(BaseSettings):
    """Application settings from environment variables and config files."""

    model_config = SettingsConfigDict(
        env_prefix="GHSTATS_",
        env_file=".env",
        extra="ignore",
    )

    github_token: str = ""
    data_dir: Path = Path("data")
    config_dir: Path = Path("config")

    def load_repos(self) -> list[RepoConfig]:
        """Load repository configuration from repos.yaml.

        Returns:
            List of configured repositories.
        """
        repos_file = self.config_dir / "repos.yaml"
        if not repos_file.exists():
            return []

        with open(repos_file) as f:
            data = yaml.safe_load(f)

        config = ReposConfig(**data)
        return config.get_repos()


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings loaded from environment and config files.
    """
    return Settings()
