"""
Configuration management for ProRyx Property Management System.
Loads settings from YAML configuration files.
"""

import os

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from YAML config files."""

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_logs_to_file: bool = Field(default=False, alias="APP_LOGS_TO_FILE")

    # Logging Configuration
    log_to_file: bool = Field(default=True, alias="LOG_TO_FILE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file_path: str = Field(default="logs/app.log", alias="LOG_FILE_PATH")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_max_bytes: int = Field(default=50 * 1024 * 1024, alias="LOG_MAX_BYTES")  # 50MB
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    # Database
    database_url: str = Field(
        default="mysql+asyncmy://user:password@localhost:3306/database",
        alias="DATABASE_URL",
    )
    database_ssl_check_hostname: bool = Field(
        default=True, alias="DATABASE_SSL_CHECK_HOSTNAME"
    )
    database_ssl_verify_cert: bool = Field(
        default=True, alias="DATABASE_SSL_VERIFY_CERT"
    )
    database_ssl_verify_identity: bool = Field(
        default=True, alias="DATABASE_SSL_VERIFY_IDENTITY"
    )

    # API Configuration
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    api_title: str = Field(
        default="ProRyx Property Management System", alias="API_TITLE"
    )
    api_version: str = Field(default="0.1.0", alias="API_VERSION")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"], alias="CORS_ORIGINS"
    )

    # Frontend
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-this-in-production", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_token_remember_days: int = Field(
        default=30, alias="REFRESH_TOKEN_REMEMBER_DAYS"
    )

    # Security
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=30, alias="LOCKOUT_DURATION_MINUTES")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=100, alias="RATE_LIMIT_PER_MINUTE")

    # System Initialization (optional)
    init_account_name: str | None = Field(default=None, alias="INIT_ACCOUNT_NAME")
    init_company_name: str | None = Field(default=None, alias="INIT_COMPANY_NAME")
    init_admin_email: str | None = Field(default=None, alias="INIT_ADMIN_EMAIL")
    init_admin_password: str | None = Field(default=None, alias="INIT_ADMIN_PASSWORD")
    init_admin_first_name: str | None = Field(
        default=None, alias="INIT_ADMIN_FIRST_NAME"
    )
    init_admin_last_name: str | None = Field(default=None, alias="INIT_ADMIN_LAST_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"
        populate_by_name = True

    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """Load settings from YAML file."""
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)


def get_settings() -> Settings:
    """Get settings instance - requires CONFIG environment variable.

    Raises:
        ValueError: If CONFIG environment variable is not set
        FileNotFoundError: If config file doesn't exist
    """
    config_path = os.getenv("CONFIG")

    if not config_path:
        raise ValueError(
            "CONFIG environment variable is not set!\n"
            "\n"
            "Please set it to your configuration file path:\n"
            "  export CONFIG=resources/config/local.yaml\n"
            "\n"
            "Or in your shell startup file (~/.bashrc, ~/.zshrc):\n"
            "  export CONFIG=/path/to/your/config.yaml"
        )

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please check the CONFIG environment variable points to a valid file."
        )

    return Settings.from_yaml(config_path)


# Load settings at import time
settings = get_settings()
