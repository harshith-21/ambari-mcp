"""Configuration management for Ambari MCP Server."""

import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log format enumeration."""
    JSON = "json"
    TEXT = "text"


class MCPModeType(str, Enum):
    """MCP operational modes."""
    NORMAL = "normal"
    CLUSTER_MAINTENANCE = "cluster_maintenance"
    SCALE_UP = "scale_up"
    CONFIG_EDIT = "config_edit"
    DEVELOPMENT = "development"


class AmbariConfig(BaseSettings):
    """Ambari server configuration."""
    host: str = Field(default="localhost", description="Ambari server hostname")
    port: int = Field(default=8080, description="Ambari server port")
    username: str = Field(default="admin", description="Ambari username")
    password: str = Field(default="admin", description="Ambari password")
    cluster_name: Optional[str] = Field(default=None, description="Default cluster name")
    use_ssl: bool = Field(default=False, description="Use SSL for Ambari connections")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    
    model_config = SettingsConfigDict(
        env_prefix="AMBARI_",
        case_sensitive=False
    )
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Ambari API."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}/api/v1"


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    name: str = Field(default="ambari-mcp", description="MCP server name")
    version: str = Field(default="1.0.0", description="MCP server version")
    mode: MCPModeType = Field(default=MCPModeType.NORMAL, description="Operational mode")
    host: str = Field(default="0.0.0.0", description="MCP server host")
    port: int = Field(default=8001, description="MCP server port")


class FastAPIConfig(BaseModel):
    """FastAPI configuration."""
    host: str = Field(default="0.0.0.0", description="FastAPI host")
    port: int = Field(default=8000, description="FastAPI port")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    format: LogFormat = Field(default=LogFormat.JSON, description="Log format")
    file: Optional[str] = Field(default=None, description="Log file path")


class SecurityConfig(BaseModel):
    """Security configuration."""
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True
    )
    
    # Configuration sections
    ambari: AmbariConfig = Field(default_factory=AmbariConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    fastapi: FastAPIConfig = Field(default_factory=FastAPIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set up logging file path if not provided
        if self.logging.file is None:
            # Try to use logs directory first, fallback to temp if not writable
            try:
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                self.logging.file = os.path.join(log_dir, "ambari-mcp.log")
            except (OSError, PermissionError):
                # If we can't create the log directory, use temp directory
                import tempfile
                try:
                    self.logging.file = os.path.join(tempfile.gettempdir(), "ambari-mcp.log")
                except Exception:
                    # If all else fails, disable file logging
                    self.logging.file = None
        else:
            # If a specific log file was provided, try to create its directory
            try:
                os.makedirs(os.path.dirname(self.logging.file), exist_ok=True)
            except (OSError, PermissionError):
                # If we can't create the directory, disable file logging
                self.logging.file = None


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings 