"""Configuration management using 1Password CLI for secure credential handling."""

import logging
import os
import subprocess
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with 1Password integration support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application settings
    app_name: str = "Knowledge Base API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000"]

    # 1Password settings
    op_mongado_service_account_token: Optional[str] = None

    # Database settings (for future use)
    database_url: Optional[str] = None

    # API Keys (examples - load from 1Password when needed)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class SecretManager:
    """Manage secrets using 1Password CLI or SDK."""

    def __init__(self):
        self.client = None
        self.use_cli = False
        self._initialize()

    def _check_cli_available(self) -> bool:
        """Check if 1Password CLI is installed and configured."""
        try:
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _initialize(self):
        """Initialize 1Password client (SDK) or CLI."""
        # Try SDK first (for service accounts)
        service_account_token = os.getenv("OP_MONGADO_SERVICE_ACCOUNT_TOKEN")
        if service_account_token:
            try:
                from onepassword.client import Client
                self.client = Client(service_account_token=service_account_token)
                logger.info("1Password SDK initialized successfully")
                return
            except ImportError:
                logger.warning("1Password SDK not installed, trying CLI...")
            except Exception as e:
                logger.warning("Failed to initialize 1Password SDK: %s", e)

        # Try CLI (for personal accounts)
        if self._check_cli_available():
            self.use_cli = True
            logger.info("1Password CLI detected and available")
        else:
            logger.warning(
                "1Password not configured - install 'op' CLI and sign in, "
                "or set OP_MONGADO_SERVICE_ACCOUNT_TOKEN"
            )

    def get_secret(self, reference: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret from 1Password using a secret reference.

        Args:
            reference: 1Password secret reference (e.g., "op://vault/item/field")
            default: Default value if secret cannot be retrieved

        Returns:
            The secret value or default

        Example:
            secret = secret_manager.get_secret("op://dev/api-keys/openai")
        """
        # Try SDK client
        if self.client:
            try:
                secret = self.client.secrets.resolve(reference)
                return secret
            except Exception as e:
                logger.error("Failed to retrieve secret via SDK '%s': %s", reference, e)
                return default

        # Try CLI
        if self.use_cli:
            try:
                result = subprocess.run(
                    ["op", "read", reference],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    logger.error(
                        "Failed to retrieve secret via CLI '%s': %s",
                        reference,
                        result.stderr.strip(),
                    )
                    return default
            except subprocess.TimeoutExpired:
                logger.error("Timeout retrieving secret '%s'", reference)
                return default
            except Exception as e:
                logger.error("Error retrieving secret via CLI '%s': %s", reference, e)
                return default

        return default

    def is_available(self) -> bool:
        """Check if 1Password is available (either SDK or CLI)."""
        return self.client is not None or self.use_cli


# Global instances
settings = Settings()
secret_manager = SecretManager()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def get_secret_manager() -> SecretManager:
    """Get secret manager instance."""
    return secret_manager
