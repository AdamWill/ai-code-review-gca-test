"""Tests for CLI CI/CD integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from ai_code_review.cli import main
from ai_code_review.models.config import AIProvider, PlatformProvider


def create_mock_config(
    gitlab_token: str = "test",
    dry_run: bool = True,
    log_level: str = "INFO",
    platform_provider: PlatformProvider = PlatformProvider.GITLAB,
    ai_provider: AIProvider = AIProvider.GEMINI,
    ai_model: str = "gemini-2.5-pro",
    **kwargs,
) -> Mock:
    """Create a properly configured Config mock with all required attributes."""
    mock_config = Mock()

    # Basic attributes
    mock_config.gitlab_token = gitlab_token
    mock_config.github_token = kwargs.get(
        "github_token", "test" if platform_provider == PlatformProvider.GITHUB else None
    )
    mock_config.dry_run = dry_run
    mock_config.log_level = log_level
    mock_config.ai_model = ai_model

    # New fields from refactoring
    mock_config.health_check = kwargs.get("health_check", False)
    mock_config.post = kwargs.get("post", False)
    mock_config.output_file = kwargs.get("output_file", None)
    mock_config.target_branch = kwargs.get("target_branch", "main")

    # Enum attributes with proper .value
    mock_config.platform_provider = platform_provider
    mock_config.ai_provider = ai_provider

    # Method returns
    mock_config.is_ci_mode.return_value = kwargs.get("is_ci_mode", False)
    mock_config.get_effective_server_url.return_value = kwargs.get(
        "server_url", "https://gitlab.com"
    )
    mock_config.get_effective_repository_path.return_value = kwargs.get(
        "repo_path", None
    )
    mock_config.get_effective_pull_request_number.return_value = kwargs.get(
        "pr_number", None
    )

    # Additional attributes
    for key, value in kwargs.items():
        if not hasattr(mock_config, key):
            setattr(mock_config, key, value)

    return mock_config


class TestCLICI:
    """Test CLI CI/CD functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Click test runner."""
        return CliRunner()

    def test_cli_ci_mode_with_env_vars(self, runner: CliRunner) -> None:
        """Test CLI in CI mode using environment variables."""
        # Mock CI environment
        ci_env = {
            "CI_PROJECT_PATH": "group/test-project",
            "CI_MERGE_REQUEST_IID": "456",
            "CI_SERVER_URL": "https://gitlab.company.com",
            "GITLAB_TOKEN": "test-token",
        }

        with patch("ai_code_review.cli.Config") as mock_config_class:
            # Config should receive CI values automatically
            mock_config = create_mock_config(
                ci_project_path="group/test-project",
                ci_merge_request_iid=456,
                ci_server_url="https://gitlab.company.com",
                gitlab_token="test-token",
                platform_provider=PlatformProvider.GITLAB,
                ai_provider=AIProvider.OLLAMA,
                ai_model="qwen2.5-coder:7b",
                is_ci_mode=True,
                repo_path="group/test-project",
                pr_number=456,
                server_url="https://gitlab.company.com",
            )
            mock_config_class.return_value = mock_config
            mock_config_class.from_cli_args.return_value = mock_config

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.return_value = Mock(
                    to_markdown=lambda: "# CI Test Review"
                )
                mock_engine_class.return_value = mock_engine

                # Run without arguments (CI mode)
                result = runner.invoke(main, ["--dry-run"], env=ci_env)

                assert result.exit_code == 0
                assert "CI/CD MODE" in result.output
                assert "group/test-project" in result.output
                assert "456" in result.output

    def test_cli_health_check_no_args_required(self, runner: CliRunner) -> None:
        """Test health check doesn't require project arguments."""
        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = create_mock_config(health_check=True)
            mock_config_class.return_value = mock_config
            mock_config_class.from_cli_args.return_value = mock_config

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.health_check.return_value = {
                    "overall": {"status": "healthy"},
                    "config": {"status": "healthy"},
                    "ai_provider": {"status": "healthy"},
                }
                mock_engine_class.return_value = mock_engine

                # Health check should work without any arguments
                result = runner.invoke(
                    main, ["--health-check"], env={"GITLAB_TOKEN": "test"}
                )

                assert result.exit_code == 0
                assert "All systems healthy" in result.output

    def test_cli_mixed_arguments_and_options(self, runner: CliRunner) -> None:
        """Test CLI with mix of arguments and options."""
        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = create_mock_config(
                gitlab_token="test-token",
                platform_provider=PlatformProvider.GITLAB,
                ai_provider=AIProvider.OLLAMA,
                ai_model="qwen2.5-coder:7b",
                is_ci_mode=False,
                repo_path=None,
                pr_number=None,
                server_url="https://gitlab.com",
            )
            # Add gitlab-specific method
            mock_config.get_effective_gitlab_url.return_value = "https://gitlab.com"
            mock_config_class.return_value = mock_config
            mock_config_class.from_cli_args.return_value = mock_config

            with patch("ai_code_review.cli.ReviewEngine") as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine.generate_review.return_value = Mock(
                    to_markdown=lambda: "# Mixed Test Review"
                )
                mock_engine_class.return_value = mock_engine

                # Use --project-id and --mr-iid options instead of arguments
                result = runner.invoke(
                    main,
                    [
                        "--project-id",
                        "group/mixed-project",
                        "--mr-iid",
                        "789",
                        "--dry-run",
                    ],
                )

                assert result.exit_code == 0
                assert "mixed-project" in result.output
                assert "789" in result.output

    def test_cli_missing_params_error_message(self, runner: CliRunner) -> None:
        """Test descriptive error messages for missing parameters."""
        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = create_mock_config(
                gitlab_token="test-token",
                platform_provider=PlatformProvider.GITLAB,
                is_ci_mode=False,
                repo_path=None,
                pr_number=None,
            )
            mock_config_class.return_value = mock_config
            mock_config_class.from_cli_args.return_value = mock_config

            # Should fail with helpful error message
            result = runner.invoke(main, [])

            assert result.exit_code == 1
            assert "PROJECT_ID and MR_IID are required" in result.output
            assert "Provide them as arguments" in result.output
            assert "CI_PROJECT_PATH and CI_MERGE_REQUEST_IID" in result.output

    def test_cli_ci_mode_missing_vars_error(self, runner: CliRunner) -> None:
        """Test error message when CI vars are incomplete."""
        # Only set one CI var to simulate misconfiguration
        ci_env = {
            "CI_PROJECT_PATH": "group/test-project",
            # Missing CI_MERGE_REQUEST_IID
            "GITLAB_TOKEN": "test-token",
        }

        with patch("ai_code_review.cli.Config") as mock_config_class:
            mock_config = create_mock_config(
                gitlab_token="test-token",
                platform_provider=PlatformProvider.GITLAB,
                ci_project_path="group/test-project",
                ci_merge_request_iid=None,
                is_ci_mode=False,  # Incomplete CI setup
                repo_path="group/test-project",
                pr_number=None,
            )
            mock_config_class.return_value = mock_config
            mock_config_class.from_cli_args.return_value = mock_config

            result = runner.invoke(main, [], env=ci_env)

            assert result.exit_code == 1
            assert "PROJECT_ID and MR_IID are required" in result.output
