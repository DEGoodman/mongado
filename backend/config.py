"""Configuration management using 1Password CLI for secure credential handling."""

import logging
import os
import subprocess

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with 1Password integration support."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="allow"
    )

    # Application settings
    app_name: str = "Mongado API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings
    cors_origins: str = "http://localhost:3000"  # Comma-separated list of allowed origins

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # 1Password settings
    op_mongado_service_account_token: str | None = None

    # Database settings (for future use)
    database_url: str | None = None

    # Neo4j settings (for notes graph database)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # Load from 1Password or env
    neo4j_database: str = "neo4j"  # Database name (default: neo4j)

    # Static articles configuration

    # LLM feature flag seed default. Only used when the flag has never been
    # toggled via the admin UI (/api/admin/feature-flags) - the persisted
    # value in Neo4j always wins over this setting.
    llm_features_enabled: bool = False  # Default off to save resources in production

    # LLM API provider seed default for the "llm_use_api" feature flag.
    # When enabled (via admin UI), AI generation (Q&A, summaries, suggestions)
    # is routed to hosted APIs (Groq primary, Gemini fallback) instead of
    # local Ollama. Embeddings are routed separately via embedding_provider.
    llm_use_api: bool = False

    # Hosted API providers (OpenAI-compatible chat completions)
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"  # Free tier: 14,400 req/day
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-flash-latest"  # Free tier: 1,500 req/day
    gemini_embed_model: str = "gemini-embedding-001"  # Embeddings via OpenAI-compat endpoint
    llm_api_timeout: float = 30.0  # Per-provider request timeout (seconds)
    llm_api_max_tokens: int = 1024  # Default response cap for API generation

    # Which backend generates embeddings: "ollama" (default, dev) or "api"
    # (Gemini, prod). Startup-level config rather than a runtime flag: query
    # embeddings must match the model tag stored with precomputed embeddings
    # in Neo4j, and embedding_sync only reconciles model changes at startup.
    embedding_provider: str = "ollama"

    # Ollama settings
    ollama_host: str = "http://localhost:11434"  # Default Ollama endpoint
    ollama_embed_model: str = "nomic-embed-text"  # Embedding model (small, fast, optimized)
    ollama_chat_model: str = "llama3.2:1b"  # Chat model (good reasoning for Q&A)
    ollama_structured_model: str = "qwen2.5:1.5b"  # Structured output model (reliable JSON)
    ollama_model: str = "llama3.2:1b"  # Legacy: fallback if embed/chat not set
    ollama_enabled: bool = True  # Enable/disable Ollama features
    ollama_num_ctx: int = 2048  # Context window size (reduce from default 4096 to save memory)

    # Embedding sync settings
    sync_embeddings_on_startup: bool = False  # Set to True to sync embeddings on app startup

    # API Keys (examples - load from 1Password when needed)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Zettelkasten authentication
    admin_token: str = ""  # Admin bearer token for creating persistent notes


class SecretManager:
    """Manage secrets using 1Password CLI or SDK."""

    def __init__(self) -> None:
        self.client = None
        self.use_cli = False
        self._service_account_token = os.getenv("OP_MONGADO_SERVICE_ACCOUNT_TOKEN")
        self._sdk_init_attempted = False
        self._initialize()

    def _check_cli_available(self) -> bool:
        """Check if 1Password CLI is installed and configured."""
        try:
            result = subprocess.run(["op", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _initialize(self) -> None:
        """Initialize 1Password using CLI with service account token or user account."""
        # For now, always use CLI since SDK async initialization is complex
        # CLI supports both service account tokens and user accounts
        if self._service_account_token:
            # Service account token is set - CLI will use it via env var
            if self._check_cli_available():
                self.use_cli = True
                logger.info("1Password CLI available (will use service account token)")
            else:
                logger.warning(
                    "1Password service account token set but 'op' CLI not installed. "
                    "Install from: https://developer.1password.com/docs/cli/get-started/"
                )
        elif self._check_cli_available():
            # No service account token, but CLI is available for user accounts
            self.use_cli = True
            logger.info("1Password CLI detected and available")
        else:
            logger.warning(
                "1Password not configured - install 'op' CLI and sign in, "
                "or set OP_MONGADO_SERVICE_ACCOUNT_TOKEN"
            )

    def get_secret(self, reference: str, default: str | None = None) -> str | None:
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
        # Use CLI (supports both service account tokens via env var and user accounts)
        if self.use_cli:
            try:
                result = subprocess.run(
                    ["op", "read", reference], capture_output=True, text=True, timeout=10
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
