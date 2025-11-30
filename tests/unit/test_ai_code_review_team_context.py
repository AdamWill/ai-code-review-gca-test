"""Tests for team context loading functionality."""

from __future__ import annotations

from unittest.mock import Mock, mock_open, patch

import httpx
import pytest

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import Config


class TestTeamContextLoading:
    """Test team context file loading from local and remote sources."""

    def test_load_local_team_context(self):
        """Test loading team context from local file."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="team-context.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_content = "# Team Standards\n\nFollow these guidelines..."

        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("os.path.isfile", return_value=True):
                result = engine._load_local_context("team-context.md")

        assert result == mock_content

    def test_load_local_team_context_not_found(self):
        """Test loading team context from non-existent local file."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="team-context.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        with patch("os.path.isfile", return_value=False):
            result = engine._load_local_context("team-context.md")

        assert result is None

    def test_load_local_team_context_empty(self):
        """Test loading empty team context file."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="team-context.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        with patch("builtins.open", mock_open(read_data="   \n  ")):
            with patch("os.path.isfile", return_value=True):
                result = engine._load_local_context("team-context.md")

        assert result is None

    def test_load_remote_team_context(self):
        """Test loading team context from URL."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_content = "# Remote Team Standards\n\nFollow these guidelines..."
        mock_response = Mock()
        mock_response.text = mock_content
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response) as mock_get:
            result = engine._load_remote_context(
                "https://company.com/standards/review.md"
            )

        assert result == mock_content
        mock_get.assert_called_once()

    def test_load_remote_context_timeout(self):
        """Test handling of timeout when loading remote context."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        with patch("httpx.get", side_effect=httpx.TimeoutException("Timeout")):
            result = engine._load_remote_context(
                "https://company.com/standards/review.md"
            )

        assert result is None

    def test_load_remote_context_404(self):
        """Test handling of 404 when loading remote context."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_response = Mock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        with patch("httpx.get", side_effect=error):
            result = engine._load_remote_context(
                "https://company.com/standards/review.md"
            )

        assert result is None

    def test_load_remote_context_empty(self):
        """Test loading empty remote context."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_response = Mock()
        mock_response.text = "   \n  "
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            result = engine._load_remote_context(
                "https://company.com/standards/review.md"
            )

        assert result is None

    def test_team_context_priority(self):
        """Test that team context has priority over project context."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="team.md",
            project_context_file="project.md",
            enable_project_context=True,
            dry_run=True,
        )
        engine = ReviewEngine(config)

        team_content = "# Team Context"
        project_content = "# Project Context"

        def mock_isfile(path: str) -> bool:
            return path in ["team.md", "project.md"]

        def mock_open_func(path: str, *args, **kwargs):
            if path == "team.md":
                return mock_open(read_data=team_content)()
            elif path == "project.md":
                return mock_open(read_data=project_content)()
            raise FileNotFoundError(path)

        with patch("os.path.isfile", side_effect=mock_isfile):
            with patch("builtins.open", side_effect=mock_open_func):
                result = engine._get_project_context()

        # Check that team context appears before project context
        assert "**Team/Organization Context:**" in result
        assert "**Project Context:**" in result
        team_pos = result.find("**Team/Organization Context:**")
        project_pos = result.find("**Project Context:**")
        assert team_pos < project_pos

    def test_load_context_from_source_local(self):
        """Test _load_context_from_source with local path."""
        config = Config(
            gitlab_token="test-token",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_content = "# Local Context"

        with patch.object(
            engine, "_load_local_context", return_value=mock_content
        ) as mock_local:
            result = engine._load_context_from_source("local-file.md")

        assert result == mock_content
        mock_local.assert_called_once_with("local-file.md")

    def test_load_context_from_source_remote(self):
        """Test _load_context_from_source with remote URL."""
        config = Config(
            gitlab_token="test-token",
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_content = "# Remote Context"

        with patch.object(
            engine, "_load_remote_context", return_value=mock_content
        ) as mock_remote:
            result = engine._load_context_from_source("https://example.com/context.md")

        assert result == mock_content
        mock_remote.assert_called_once_with("https://example.com/context.md")

    def test_invalid_team_context_url(self):
        """Test validation of invalid team context URL."""
        with pytest.raises(ValueError, match="Invalid team context URL format"):
            Config(
                gitlab_token="test-token",
                team_context_file="http://invalid url with spaces",
                dry_run=True,
            )

    def test_valid_team_context_url(self):
        """Test validation of valid team context URL."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            dry_run=True,
        )
        assert config.team_context_file == "https://company.com/standards/review.md"

    def test_valid_team_context_local_path(self):
        """Test validation of valid local path."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="../team-standards.md",
            dry_run=True,
        )
        assert config.team_context_file == "../team-standards.md"

    def test_team_context_none_by_default(self):
        """Test that team_context_file is None by default."""
        config = Config(
            gitlab_token="test-token",
            dry_run=True,
        )
        assert config.team_context_file is None

    def test_team_context_respects_ssl_settings(self):
        """Test that remote context loading respects SSL settings."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="https://company.com/standards/review.md",
            ssl_verify=False,
            http_timeout=10.0,
            dry_run=True,
        )
        engine = ReviewEngine(config)

        mock_content = "# Remote Content"
        mock_response = Mock()
        mock_response.text = mock_content
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response) as mock_get:
            engine._load_remote_context("https://company.com/standards/review.md")

        # Verify SSL settings were passed
        mock_get.assert_called_once_with(
            "https://company.com/standards/review.md",
            timeout=10.0,
            verify=False,
        )

    def test_team_context_with_ssl_cert_path(self):
        """Test that remote context loading uses SSL cert path when provided."""
        mock_content = "# Remote Content"
        mock_response = Mock()
        mock_response.text = mock_content
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response) as mock_get:
            with patch("os.path.isfile", return_value=True):
                with patch("os.access", return_value=True):
                    # Create config with mocked file validation
                    config = Config(
                        gitlab_token="test-token",
                        team_context_file="https://company.com/standards/review.md",
                        ssl_verify=True,
                        ssl_cert_path="/path/to/cert.pem",
                        http_timeout=5.0,
                        dry_run=True,
                    )
                    engine = ReviewEngine(config)
                    engine._load_remote_context(
                        "https://company.com/standards/review.md"
                    )

                    # Verify SSL cert path was used instead of verify boolean
                    mock_get.assert_called_once_with(
                        "https://company.com/standards/review.md",
                        timeout=5.0,
                        verify="/path/to/cert.pem",
                    )

    def test_team_context_disabled_when_project_context_disabled(self):
        """Test that team context is not loaded when enable_project_context is False."""
        config = Config(
            gitlab_token="test-token",
            team_context_file="team.md",
            enable_project_context=False,
            dry_run=True,
        )
        engine = ReviewEngine(config)

        result = engine._get_project_context()

        assert "**Team/Organization Context:**" not in result
        assert "**Project Context:**" not in result
