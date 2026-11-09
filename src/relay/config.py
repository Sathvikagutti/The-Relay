"""Configuration loading.

Rule: structure lives in YAML, secrets live in the environment. Nothing that
looks like a credential is ever read from a config file or written to a log.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/relay/config.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PaperSpec(BaseModel):
    """One pinned paper. `version` is part of the citation contract."""

    key: str
    arxiv_id: str = Field(pattern=r"^\d{4}\.\d{4,5}$")
    version: int = Field(ge=1)
    title: str

    @property
    def filename(self) -> str:
        return f"{self.arxiv_id}v{self.version}.pdf"

    @property
    def url(self) -> str:
        return f"https://arxiv.org/pdf/{self.arxiv_id}v{self.version}"


class CorpusConfig(BaseModel):
    dir: Path
    index_dir: Path
    papers: list[PaperSpec]


class RelayConfig(BaseModel):
    corpus: CorpusConfig


class RetrievalSetting(BaseModel):
    chunk_tokens: int = Field(ge=50)
    overlap_tokens: int = Field(ge=0)
    fetch_k: int = Field(ge=1)
    top_k: int = Field(ge=1)
    rerank: Literal["none", "cross_encoder"] = "none"


class RetrievalConfig(BaseModel):
    settings: dict[str, RetrievalSetting]
    default: str

    def setting(self, name: str | None = None) -> tuple[str, RetrievalSetting]:
        key = name or self.default
        if key not in self.settings:
            raise KeyError(f"unknown retrieval setting {key!r}; have {sorted(self.settings)}")
        return key, self.settings[key]


class Settings(BaseSettings):
    """Runtime settings from `.env` (never from version control)."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    standin_base_url: str = "http://127.0.0.1:8788/v1"
    relay_max_real_requests_per_run: int = 40


def resolve(path: Path) -> Path:
    """Resolve a config path against the project root, not the caller's cwd."""
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_config(path: str | Path | None = None) -> RelayConfig:
    cfg_path = Path(path) if path else PROJECT_ROOT / "config" / "default.yaml"
    with cfg_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return RelayConfig.model_validate(raw)


def load_retrieval(path: str | Path | None = None) -> RetrievalConfig:
    cfg_path = Path(path) if path else PROJECT_ROOT / "config" / "retrieval.yaml"
    with cfg_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return RetrievalConfig.model_validate(raw)
