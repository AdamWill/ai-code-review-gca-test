"""Tests for context generator CLI module."""

from __future__ import annotations

import tempfile
import warnings
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from click.testing import CliRunner

from context_generator.cli import generate_context

# Suppress RuntimeWarning about unawaited coroutines from async mocks
warnings.filterwarnings(
    "ignore", message=".*coroutine.*was never awaited.*", category=RuntimeWarning
)
warnings.filterwarnings(
    "ignore", message=".*_run_generation.*was never awaited.*", category=RuntimeWarning
)


class TestContextGeneratorCLI:
    """Tests for context generator CLI."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def teardown_method(self) -> None:
        """Clean up after each test to prevent interference."""
        import gc
        import warnings

        # Suppress warnings during garbage collection
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            gc.collect()

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        result = self.runner.invoke(generate_context, ["--help"])

        assert result.exit_code == 0
        assert "Generate intelligent project context" in result.output
        assert "--provider" in result.output
        assert "--model" in result.output
        assert "--ai-api-key" in result.output
        assert "--dry-run" in result.output

    def test_cli_with_defaults_dry_run(self) -> None:
        """Test CLI with default values in dry run mode."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch("context_generator.cli.Config"):
                with patch(
                    "context_generator.cli.ContextBuilder"
                ) as mock_context_builder_class:
                    # Mock the async generate_context method
                    from context_generator.models import ContextResult

                    mock_builder = Mock()
                    mock_result = ContextResult(
                        project_path=Path("/tmp/test"),
                        project_name="test-project",
                        context_content="Mock context content",
                        generation_timestamp="2024-01-01T00:00:00",
                        ai_provider="ollama",
                        ai_model="qwen2.5-coder:7b",
                    )
                    mock_builder.generate_context = AsyncMock(return_value=mock_result)
                    mock_builder.get_generation_summary = Mock(
                        return_value={
                            "project_name": "test",
                            "ai_provider": "ollama",
                            "ai_model": "qwen2.5-coder:7b",
                        }
                    )
                    mock_context_builder_class.return_value = mock_builder

                    # Specify output file in temp directory to avoid writing to real project
                    output_file = tmp_path / ".ai_review" / "project.md"
                    result = self.runner.invoke(
                        generate_context,
                        [str(tmp_path), "--output", str(output_file), "--dry-run"],
                    )

                    assert result.exit_code == 0

    def test_cli_with_provider_override(self) -> None:
        """Test CLI with provider override."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch("context_generator.cli.Config"):
                with patch(
                    "context_generator.cli.ContextBuilder"
                ) as mock_context_builder_class:
                    # Mock the async generate_context method
                    from context_generator.models import ContextResult

                    mock_builder = Mock()
                    mock_result = ContextResult(
                        project_path=Path("/tmp/test"),
                        project_name="test-project",
                        context_content="Mock context content",
                        generation_timestamp="2024-01-01T00:00:00",
                        ai_provider="ollama",
                        ai_model="qwen2.5-coder:7b",
                    )
                    mock_builder.generate_context = AsyncMock(return_value=mock_result)
                    mock_builder.get_generation_summary = Mock(
                        return_value={
                            "project_name": "test",
                            "ai_provider": "ollama",
                            "ai_model": "qwen2.5-coder:7b",
                        }
                    )
                    mock_context_builder_class.return_value = mock_builder

                    # Specify output file in temp directory to avoid writing to real project
                    output_file = tmp_path / ".ai_review" / "project.md"
                    result = self.runner.invoke(
                        generate_context,
                        [
                            str(tmp_path),
                            "--output",
                            str(output_file),
                            "--provider",
                            "anthropic",
                            "--dry-run",
                        ],
                    )

                    assert result.exit_code == 0

    def test_cli_with_custom_output(self) -> None:
        """Test CLI with custom output file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            output_file = tmp_path / "custom_context.md"

            with patch("context_generator.cli.Config"):
                with patch(
                    "context_generator.cli.ContextBuilder"
                ) as mock_context_builder_class:
                    # Mock the async generate_context method
                    from context_generator.models import ContextResult

                    mock_builder = Mock()
                    mock_result = ContextResult(
                        project_path=Path("/tmp/test"),
                        project_name="test-project",
                        context_content="Mock context content",
                        generation_timestamp="2024-01-01T00:00:00",
                        ai_provider="ollama",
                        ai_model="qwen2.5-coder:7b",
                    )
                    mock_builder.generate_context = AsyncMock(return_value=mock_result)
                    mock_builder.get_generation_summary = Mock(
                        return_value={
                            "project_name": "test",
                            "ai_provider": "ollama",
                            "ai_model": "qwen2.5-coder:7b",
                        }
                    )
                    mock_context_builder_class.return_value = mock_builder

                    result = self.runner.invoke(
                        generate_context,
                        [str(tmp_path), "--output", str(output_file), "--dry-run"],
                    )

                    assert result.exit_code == 0

    def test_cli_with_all_options(self) -> None:
        """Test CLI with all options specified."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch("context_generator.cli.Config"):
                with patch(
                    "context_generator.cli.ContextBuilder"
                ) as mock_context_builder_class:
                    # Mock the async generate_context method
                    from context_generator.models import ContextResult

                    mock_builder = Mock()
                    mock_result = ContextResult(
                        project_path=Path("/tmp/test"),
                        project_name="test-project",
                        context_content="Mock context content",
                        generation_timestamp="2024-01-01T00:00:00",
                        ai_provider="ollama",
                        ai_model="qwen2.5-coder:7b",
                    )
                    mock_builder.generate_context = AsyncMock(return_value=mock_result)
                    mock_builder.get_generation_summary = Mock(
                        return_value={
                            "project_name": "test",
                            "ai_provider": "ollama",
                            "ai_model": "qwen2.5-coder:7b",
                        }
                    )
                    mock_context_builder_class.return_value = mock_builder

                    # Specify output file in temp directory to avoid writing to real project
                    output_file = tmp_path / ".ai_review" / "project.md"
                    result = self.runner.invoke(
                        generate_context,
                        [
                            str(tmp_path),
                            "--output",
                            str(output_file),
                            "--provider",
                            "ollama",
                            "--model",
                            "qwen2.5-coder:7b",
                            "--ollama-url",
                            "http://localhost:11434",
                            "--dry-run",
                            "--verbose",
                        ],
                    )

                    assert result.exit_code == 0

    @patch("context_generator.cli.asyncio.run")
    @patch("context_generator.cli.Config.from_cli_args")
    def test_run_generation_called_correctly(
        self, mock_config_from_cli: Mock, mock_asyncio_run: Mock
    ) -> None:
        """Test that _run_generation is called with correct parameters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            mock_config = Mock()
            mock_config_from_cli.return_value = mock_config
            mock_asyncio_run.return_value = None

            # Specify output file in temp directory to avoid writing to real project
            output_file = tmp_path / ".ai_review" / "project.md"
            result = self.runner.invoke(
                generate_context,
                [str(tmp_path), "--output", str(output_file), "--dry-run"],
            )

            assert result.exit_code == 0
            mock_asyncio_run.assert_called_once()

    def test_cli_args_mapping_to_config_format(self) -> None:
        """Test that CLI args are correctly mapped to Config format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with patch("context_generator.cli.Config") as mock_config_class:
                with patch(
                    "context_generator.cli.ContextBuilder"
                ) as mock_context_builder_class:
                    # Mock the async generate_context method
                    from context_generator.models import ContextResult

                    mock_builder = Mock()
                    mock_result = ContextResult(
                        project_path=Path("/tmp/test"),
                        project_name="test-project",
                        context_content="Mock context content",
                        generation_timestamp="2024-01-01T00:00:00",
                        ai_provider="ollama",
                        ai_model="qwen2.5-coder:7b",
                    )
                    mock_builder.generate_context = AsyncMock(return_value=mock_result)
                    mock_builder.get_generation_summary = Mock(
                        return_value={
                            "project_name": "test",
                            "ai_provider": "ollama",
                            "ai_model": "qwen2.5-coder:7b",
                        }
                    )
                    mock_context_builder_class.return_value = mock_builder

                    # Specify output file in temp directory to avoid writing to real project
                    output_file = tmp_path / ".ai_review" / "project.md"
                    result = self.runner.invoke(
                        generate_context,
                        [
                            str(tmp_path),
                            "--output",
                            str(output_file),
                            "--provider",
                            "ollama",
                            "--model",
                            "qwen2.5-coder:7b",
                            "--ollama-url",
                            "http://localhost:11434",
                            "--dry-run",
                        ],
                    )

                    assert result.exit_code == 0

                    # Verify mapping follows Config.from_cli_args expectations
                    call_args = mock_config_class.from_cli_args.call_args[0][0]
                    assert "provider" in call_args  # Maps to ai_provider
                    assert "model" in call_args  # Maps to ai_model
                    assert "ollama_url" in call_args  # Maps to ollama_base_url
                    assert "gitlab_token" in call_args  # Dummy token
                    assert "github_token" in call_args  # Dummy token

    @patch("context_generator.cli.asyncio.run")
    @patch("context_generator.cli.Config.from_cli_args")
    def test_cli_only_passes_non_none_values(
        self, mock_config_from_cli: Mock, mock_asyncio_run: Mock
    ) -> None:
        """Test that CLI only passes non-None values to Config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            mock_config = Mock()
            mock_config_from_cli.return_value = mock_config
            mock_asyncio_run.return_value = None

            # Only specify dry-run, leave other options as defaults (None)
            # Specify output file in temp directory to avoid writing to real project
            output_file = tmp_path / ".ai_review" / "project.md"
            result = self.runner.invoke(
                generate_context,
                [str(tmp_path), "--output", str(output_file), "--dry-run"],
            )

            assert result.exit_code == 0
            mock_asyncio_run.assert_called_once()

            # Verify only non-None values are passed
            call_args = mock_config_from_cli.call_args[0][0]
            assert call_args["dry_run"] is True
            assert "gitlab_token" in call_args  # Always present (dummy)
            assert "github_token" in call_args  # Always present (dummy)

            # These should NOT be present if None
            assert "provider" not in call_args or call_args["provider"] is not None
            assert "model" not in call_args or call_args["model"] is not None

    def test_cli_error_handling_config_validation(self) -> None:
        """Test CLI error handling for Config validation errors."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Don't mock Config to let the real validation happen
            # Specify output file in temp directory to avoid writing to real project
            output_file = tmp_path / ".ai_review" / "project.md"
            result = self.runner.invoke(
                generate_context,
                [
                    str(tmp_path),
                    "--output",
                    str(output_file),
                    "--provider",
                    "anthropic",  # Missing API key should cause error
                ],
            )

            assert result.exit_code == 1
            assert "anthropic requires --ai-api-key" in result.output

    @patch("context_generator.cli.Config")
    def test_cli_error_handling_keyboard_interrupt(
        self, mock_config_class: Mock
    ) -> None:
        """Test CLI error handling for keyboard interrupt."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            mock_config_class.from_cli_args.side_effect = KeyboardInterrupt()

            # Specify output file in temp directory to avoid writing to real project
            output_file = tmp_path / ".ai_review" / "project.md"
            result = self.runner.invoke(
                generate_context,
                [str(tmp_path), "--output", str(output_file), "--dry-run"],
            )

            assert result.exit_code == 1
            assert "Generation cancelled" in result.output
