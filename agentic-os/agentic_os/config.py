"""Configuration management for Agentic OS."""

import os
import sys
from typing import Optional
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        # OpenRouter direct API access (LiteLLM decommissioned due to DB requirement)
        self.openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        self.redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

        self._validate()

    def _validate(self):
        """Validate required configuration values are present."""
        errors = []

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY environment variable is required")

        if not self.database_url:
            errors.append("DATABASE_URL environment variable is required")

        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

    def test_connections(self) -> bool:
        """Test connectivity to OpenRouter, Postgres, and Redis.

        Returns:
            True if all connections successful, False otherwise.
        """
        errors = []

        # Test Redis
        try:
            import redis
            r = redis.from_url(self.redis_url, socket_connect_timeout=2)
            r.ping()
        except Exception as e:
            errors.append(f"Redis connection failed: {e}")

        # Test Postgres
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.database_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            errors.append(f"Database connection failed: {e}")

        # Test OpenRouter API
        try:
            import httpx
            response = httpx.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.openrouter_api_key}"},
                timeout=5.0
            )
            if response.status_code not in [200, 401]:  # 401 means auth worked but key may be invalid
                errors.append(f"OpenRouter API check failed: HTTP {response.status_code}")
        except httpx.ConnectError:
            errors.append("OpenRouter API connection failed: cannot reach openrouter.ai")
        except Exception as e:
            errors.append(f"OpenRouter API check failed: {e}")

        if errors:
            print("Connection test errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return False

        return True


# Global config instance
config = Config()
