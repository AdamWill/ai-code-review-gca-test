"""Tests for CLI CI/CD integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from ai_code_review.cli import main
from ai_code_review.models.config import PlatformProvider


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

        with patch("ai_code_review.cli.Config") as mock_config:
            # Config should receive CI values automatically
            mock_config.return_value = Mock(
                ci_project_path="group/test-project",
                ci_merge_request_iid=456,
                ci_server_url="https://gitlab.company.com",
                gitlab_token="test-token",
                dry_run=True,
                log_level="INFO",
                ai_provider=Mock(value="ollama"),
                ai_model="qwen2.5-coder:7b",
            )
            mock_config.return_value.is_ci_mode.return_value = True
            mock_config.return_value.get_effective_repository_path.return_value = (
                "group/test-project"
            )
            mock_config.return_value.get_effective_pull_request_number.return_value = (
                456
            )
            mock_config.return_value.get_effective_server_url.return_value = (
                "https://gitlab.company.com"
            )
            mock_config.return_value.platform_provider = Mock(value="gitlab")

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
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(log_level="INFO")

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
        with patch("ai_code_review.cli.Config") as mock_config:
            mock_config.return_value = Mock(
                gitlab_token="test-token",
                dry_run=True,
                log_level="INFO",
                ai_provider=Mock(value="ollama"),
                ai_model="qwen2.5-coder:7b",
            )
            mock_config.return_value.is_ci_mode.return_value = False
            mock_config.return_value.get_effective_repository_path.return_value = None
            mock_config.return_value.get_effective_pull_request_number.return_value = (
                None
            )
            mock_config.return_value.platform_provider = Mock(value="gitlab")
            mock_config.return_value.get_effective_gitlab_url.return_value = (
                "https://gitlab.com"
            )

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
        with patch("ai_code_review.cli.Config") as mock_config:
            config_instance = Mock()
            config_instance.gitlab_token = "test-token"
            config_instance.log_level = "INFO"
            config_instance.platform_provider = PlatformProvider.GITLAB
            config_instance.is_ci_mode.return_value = False
            config_instance.get_effective_repository_path.return_value = None
            config_instance.get_effective_pull_request_number.return_value = None
            mock_config.return_value = config_instance

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

        with patch("ai_code_review.cli.Config") as mock_config:
            config_instance = Mock()
            config_instance.gitlab_token = "test-token"
            config_instance.log_level = "INFO"
            config_instance.platform_provider = PlatformProvider.GITLAB
            config_instance.ci_project_path = "group/test-project"
            config_instance.ci_merge_request_iid = None
            config_instance.is_ci_mode.return_value = False  # Incomplete CI setup
            config_instance.get_effective_repository_path.return_value = (
                "group/test-project"
            )
            config_instance.get_effective_pull_request_number.return_value = None
            mock_config.return_value = config_instance

            result = runner.invoke(main, [], env=ci_env)

            assert result.exit_code == 1
            assert "PROJECT_ID and MR_IID are required" in result.output
