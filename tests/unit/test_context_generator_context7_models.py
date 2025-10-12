"""Tests for Context7 models and configuration."""

from __future__ import annotations

import pytest

from context_generator.models import Context7Config


class TestContext7Config:
    """Test Context7Config model."""

    def test_init_defaults(self) -> None:
        """Test Context7Config initialization with defaults."""
        config = Context7Config()

        assert config.enabled is False
        assert config.max_tokens_per_library == 2000
        assert config.priority_libraries == []
        assert config.timeout_seconds == 10

    def test_init_with_values(self) -> None:
        """Test Context7Config initialization with custom values."""
        config = Context7Config(
            enabled=True,
            max_tokens_per_library=1500,
            priority_libraries=["fastapi", "pydantic"],
            timeout_seconds=15,
        )

        assert config.enabled is True
        assert config.max_tokens_per_library == 1500
        assert config.priority_libraries == ["fastapi", "pydantic"]
        assert config.timeout_seconds == 15

    def test_validation_max_tokens_range(self) -> None:
        """Test validation of max_tokens_per_library range."""
        # Valid values
        Context7Config(max_tokens_per_library=100)  # Minimum
        Context7Config(max_tokens_per_library=10000)  # Maximum
        Context7Config(max_tokens_per_library=2000)  # Default

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            Context7Config(max_tokens_per_library=50)  # Below minimum

        with pytest.raises(ValueError):
            Context7Config(max_tokens_per_library=15000)  # Above maximum

    def test_validation_timeout_range(self) -> None:
        """Test validation of timeout_seconds range."""
        # Valid values
        Context7Config(timeout_seconds=1)  # Minimum
        Context7Config(timeout_seconds=60)  # Maximum
        Context7Config(timeout_seconds=10)  # Default

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            Context7Config(timeout_seconds=0)  # Below minimum

        with pytest.raises(ValueError):
            Context7Config(timeout_seconds=120)  # Above maximum

    def test_from_dict_success(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "enabled": True,
            "max_tokens_per_library": 1500,
            "priority_libraries": ["fastapi", "pydantic"],
            "timeout_seconds": 15,
        }

        config = Context7Config.from_dict(data)

        assert config.enabled is True
        assert config.max_tokens_per_library == 1500
        assert config.priority_libraries == ["fastapi", "pydantic"]
        assert config.timeout_seconds == 15

    def test_from_dict_partial(self) -> None:
        """Test creating config from partial dictionary."""
        data = {"enabled": True, "priority_libraries": ["fastapi"]}

        config = Context7Config.from_dict(data)

        assert config.enabled is True
        assert config.priority_libraries == ["fastapi"]
        assert config.max_tokens_per_library == 2000  # Default
        assert config.timeout_seconds == 10  # Default

    def test_from_dict_empty(self) -> None:
        """Test creating config from empty dictionary."""
        config = Context7Config.from_dict({})

        # Should use all defaults
        assert config.enabled is False
        assert config.max_tokens_per_library == 2000
        assert config.priority_libraries == []
        assert config.timeout_seconds == 10
