from pathlib import Path
from typing import Optional
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so the server works regardless of cwd
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    api_base_url: str = Field(default="https://localhost:8445", alias="API_BASE_URL")
    api_username: str = Field(alias="API_USERNAME")
    api_password: str = Field(alias="API_PASSWORD")
    ssl_verify: bool = Field(default=False, alias="SSL_VERIFY")
    attackmate_docs_path: Optional[Path] = Field(default=None, alias="ATTACKMATE_DOCS_PATH")
    command_timeout: Optional[float] = Field(
        default=300.0,
        alias="COMMAND_TIMEOUT",
        description="Seconds to wait for a command/playbook response. Set to 0 for no timeout.",
    )
    mcp_transport: str = Field(default="stdio", alias="MCP_TRANSPORT")
    mcp_host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    mcp_port: int = Field(default=8000, alias="MCP_PORT")

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


try:
    settings = Settings()
except ValidationError as exc:
    missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
    if missing:
        raise RuntimeError(
            f"Missing required configuration: {', '.join(str(f) for f in missing)}. "
            f"Copy env-example to .env and fill in the values."
        ) from exc
    raise
