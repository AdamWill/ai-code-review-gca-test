"""Tests for CLI interface."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from ai_code_review.cli import main
from ai_code_review.models.review import CodeReview, ReviewResult, ReviewSummary
from ai_code_review.utils.exceptions import AIProviderError, GitLabAPIError


class TestCLI:
    """Test CLI functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_review_result(self) -> ReviewResult:
        """Sample review result."""
        review = CodeReview(
            general_feedback="Code looks good overall",
            file_reviews=[],
            overall_assessment="Good quality",
            priority_issues=[],
            minor_suggestions=[],
        )

        summary = ReviewSummary(
            title="Test MR",
            key_changes=["Added feature X"],
            modules_affected=["core"],
            user_impact="Minor",
            technical_impact="Low impact",
            risk_level="Low",
            risk_justification="Simple changes",
        )

        return ReviewResult(review=review, summary=summary)

    def test_cli_basic_execution_dry_run(self, runner: CliRunner) -> None:
        """Test basic CLI execution in dry-run mode."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=True, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.return_value = Mock(
                    to_markdown=lambda: "# Test Review"
                )
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["test/project", "123", "--dry-run"])

                assert result.exit_code == 0
                assert "Starting AI code review" in result.output
                assert "DRY RUN MODE" in result.output
                assert "Review completed successfully" in result.output

    def test_cli_with_overrides(self, runner: CliRunner) -> None:
        """Test CLI with configuration overrides."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=True, log_level="DEBUG"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.return_value = Mock(
                    to_markdown=lambda: "# Test Review"
                )
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(
                    main,
                    [
                        "test/project",
                        "123",
                        "--provider",
                        "ollama",
                        "--model",
                        "custom-model",
                        "--temperature",
                        "0.5",
                        "--max-tokens",
                        "2048",
                        "--language-hint",
                        "python",
                        "--dry-run",
                        "--log-level",
                        "DEBUG",
                    ],
                )

                assert result.exit_code == 0
                # Verify config was called with overrides
                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args[1]
                assert call_kwargs["ai_provider"] == "ollama"
                assert call_kwargs["ai_model"] == "custom-model"
                assert call_kwargs["temperature"] == 0.5
                assert call_kwargs["max_tokens"] == 2048
                assert call_kwargs["language_hint"] == "python"
                assert call_kwargs["dry_run"] is True
                assert call_kwargs["log_level"] == "DEBUG"

    def test_cli_health_check(self, runner: CliRunner) -> None:
        """Test health check functionality."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(log_level="INFO")

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.health_check.return_value = {
                    "overall": {"status": "healthy"},
                    "config": {"status": "healthy"},
                    "ai_provider": {
                        "status": "healthy",
                        "available_models": ["model1", "model2"],
                    },
                }
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["dummy", "0", "--health-check"])

                assert result.exit_code == 0
                assert "Performing health check" in result.output
                assert "All systems healthy" in result.output
                assert "Available Models" in result.output

    def test_cli_health_check_failure(self, runner: CliRunner) -> None:
        """Test health check with failures."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(log_level="INFO")

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.health_check.return_value = {
                    "overall": {"status": "unhealthy"},
                    "config": {"status": "healthy"},
                    "ai_provider": {"status": "error", "error": "Connection failed"},
                }
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["dummy", "0", "--health-check"])

                assert result.exit_code == 1
                assert "Issues detected" in result.output
                assert "Connection failed" in result.output

    def test_cli_gitlab_api_error(self, runner: CliRunner) -> None:
        """Test GitLab API error handling."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=False, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.side_effect = GitLabAPIError(
                    "API error", 401
                )
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["test/project", "123"])

                assert result.exit_code == 2
                assert "Error:" in result.output

    def test_cli_ai_provider_error(self, runner: CliRunner) -> None:
        """Test AI provider error handling."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=False, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.side_effect = AIProviderError(
                    "AI error", "ollama"
                )
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["test/project", "123"])

                assert result.exit_code == 3
                assert "Error:" in result.output

    def test_cli_keyboard_interrupt(self, runner: CliRunner) -> None:
        """Test graceful handling of keyboard interrupt."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=False, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.side_effect = KeyboardInterrupt()
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["test/project", "123"])

                assert result.exit_code == 1
                assert "Operation cancelled" in result.output

    def test_cli_unexpected_error(self, runner: CliRunner) -> None:
        """Test handling of unexpected errors."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=False, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.side_effect = RuntimeError(
                    "Unexpected error"
                )
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(main, ["test/project", "123"])

                assert result.exit_code == 1
                assert "Unexpected error:" in result.output

    def test_cli_missing_required_args(self, runner: CliRunner) -> None:
        """Test error handling for missing required arguments."""
        # Test without any args
        result = runner.invoke(main, [])
        assert result.exit_code != 0

        # Test with only project_id
        result = runner.invoke(main, ["test/project"])
        assert result.exit_code != 0

    def test_cli_post_functionality(self, runner: CliRunner) -> None:
        """Test that --post functionality works in dry run mode."""
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test", dry_run=True, log_level="INFO"
            )

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.return_value = Mock(
                    to_markdown=lambda: "# Test Review"
                )
                # Mock the new post_review_to_gitlab method
                mock_engine.post_review_to_gitlab.return_value = {
                    "id": "mock_note_123",
                    "url": "https://gitlab.com/mock/project/-/merge_requests/123#note_mock_123",
                    "created_at": "2024-01-01T12:00:00Z",
                    "author": "AI Code Review (DRY RUN)",
                }
                mock_engine_class.return_value = mock_engine

                result = runner.invoke(
                    main, ["test/project", "123", "--post", "--dry-run"]
                )

                assert result.exit_code == 0
                assert (
                    "DRY RUN: Review posting simulated successfully!" in result.output
                )
                assert "Mock Note URL:" in result.output
                mock_engine.post_review_to_gitlab.assert_called_once()

    def test_cli_version(self, runner: CliRunner) -> None:
        """Test version display."""
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test help display."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "AI-powered code review tool" in result.output
        assert "PROJECT_ID" in result.output
        assert "MR_IID" in result.output
        assert "--provider" in result.output

    def test_cli_exclude_files_option(self, runner: CliRunner) -> None:
        """Test --exclude-files CLI option adds to default patterns."""
        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            runner.invoke(
                main,
                [
                    "test/project",
                    "123",
                    "--exclude-files",
                    "*.custom",
                    "--exclude-files",
                    "temp/**",
                    "--dry-run",
                ],
                env={"GITLAB_TOKEN": "test_token"},
            )

            # Should create config with both default patterns and custom ones
            called_args, called_kwargs = mock_config_class.call_args
            exclude_patterns = called_kwargs.get("exclude_patterns", [])

            # Should include default patterns
            assert "*.lock" in exclude_patterns
            assert "package-lock.json" in exclude_patterns

            # Should include custom patterns
            assert "*.custom" in exclude_patterns
            assert "temp/**" in exclude_patterns

    def test_cli_no_file_filtering_option(self, runner: CliRunner) -> None:
        """Test --no-file-filtering CLI option disables all filtering."""
        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            runner.invoke(
                main,
                [
                    "test/project",
                    "123",
                    "--no-file-filtering",
                    "--dry-run",
                ],
                env={"GITLAB_TOKEN": "test_token"},
            )

            # Should create config with empty exclude patterns
            called_args, called_kwargs = mock_config_class.call_args
            exclude_patterns = called_kwargs.get("exclude_patterns", [])
            assert exclude_patterns == []
