"""Command Line Interface for AI Code Review tool."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import click
import structlog

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import AIProvider, Config
from ai_code_review.utils.exceptions import (
    AICodeReviewError,
    AIProviderError,
    GitLabAPIError,
)

logger = structlog.get_logger(__name__)


@click.command()
@click.argument("project_id", required=False)
@click.argument("mr_iid", type=int, required=False)
@click.option(
    "--gitlab-url",
    default=None,
    help="GitLab instance URL (default: from config or https://gitlab.com)",
)
@click.option(
    "--project-id",
    "gitlab_project_id",
    default=None,
    help="GitLab project ID (default: from CI_PROJECT_PATH or required)",
)
@click.option(
    "--mr-iid",
    "gitlab_mr_iid",
    type=int,
    default=None,
    help="Merge Request IID (default: from CI_MERGE_REQUEST_IID or required)",
)
@click.option(
    "--provider",
    type=click.Choice([p.value for p in AIProvider]),
    default=None,
    help="AI provider to use (default: from config or gemini)",
)
@click.option(
    "--model",
    default=None,
    help="AI model name (default: provider-specific - gemini-2.5-pro, claude-sonnet-4-20250514, qwen2.5-coder:7b)",
)
@click.option(
    "--ollama-url",
    default=None,
    help="Ollama server URL (default: from config or http://localhost:11434)",
)
@click.option(
    "--temperature",
    type=float,
    default=None,
    help="AI response temperature 0.0-2.0 (default: from config or 0.1)",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Maximum AI response tokens (default: from config or 8000)",
)
@click.option(
    "--language-hint",
    default=None,
    help="Programming language hint for better context",
)
@click.option(
    "--max-chars",
    type=int,
    default=None,
    help="Maximum characters to process from diff (default: from config or 100000)",
)
@click.option(
    "--max-files",
    type=int,
    default=None,
    help="Maximum number of files to process (default: from config or 100)",
)
@click.option(
    "--post",
    is_flag=True,
    help="Post review as MR comment to GitLab",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run mode - no actual API calls made",
)
@click.option(
    "--big-diffs",
    is_flag=True,
    help="Force larger context window (24K) - auto-activated for diffs >60K chars",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default=None,
    help="Logging level (default: from config or INFO)",
)
@click.option(
    "--exclude-files",
    multiple=True,
    help="Additional glob patterns for files to exclude from AI review (can be used multiple times)",
)
@click.option(
    "--no-file-filtering",
    is_flag=True,
    help="Disable all file filtering (include lockfiles, build artifacts, etc.)",
)
@click.option(
    "--project-context/--no-project-context",
    default=None,
    help="Enable/disable loading project context from .ai_review/project.md (default: enabled if file exists)",
)
@click.option(
    "--health-check",
    is_flag=True,
    help="Perform health check on all components and exit",
)
@click.version_option(version="0.1.0", prog_name="ai-code-review")
def main(
    project_id: str | None,
    mr_iid: int | None,
    gitlab_url: str | None,
    gitlab_project_id: str | None,
    gitlab_mr_iid: int | None,
    provider: str | None,
    model: str | None,
    ollama_url: str | None,
    temperature: float | None,
    max_tokens: int | None,
    language_hint: str | None,
    max_chars: int | None,
    max_files: int | None,
    post: bool,
    dry_run: bool,
    big_diffs: bool,
    log_level: str | None,
    exclude_files: tuple[str, ...],
    no_file_filtering: bool,
    project_context: bool | None,
    health_check: bool,
) -> None:
    """
    AI-powered code review tool for GitLab Merge Requests.

    Analyzes MR diffs using AI models and generates structured feedback.

    \b
    Arguments (optional in CI/CD mode):
        PROJECT_ID    GitLab project ID (e.g., "group/project" or 123)
        MR_IID        Merge Request IID (internal ID, not global ID)

    \b
    Examples:
        # Manual mode

        ai-code-review group/project 123

        ai-code-review --project-id group/project --mr-iid 123 --post

        # CI/CD mode (uses CI environment variables)

        ai-code-review --post

        # Health check

        ai-code-review --health-check

        # Local testing

        ai-code-review group/project 123 --provider ollama --dry-run
    """
    try:
        # Setup configuration by merging environment and CLI overrides
        config_overrides: dict[str, Any] = {}
        if gitlab_url:
            config_overrides["gitlab_url"] = gitlab_url
        if provider:
            config_overrides["ai_provider"] = AIProvider(provider)
        if model:
            config_overrides["ai_model"] = model
        if ollama_url:
            config_overrides["ollama_base_url"] = ollama_url
        if temperature is not None:
            config_overrides["temperature"] = temperature
        if max_tokens:
            config_overrides["max_tokens"] = max_tokens
        if language_hint:
            config_overrides["language_hint"] = language_hint
        if max_chars:
            config_overrides["max_chars"] = max_chars
        if max_files:
            config_overrides["max_files"] = max_files
        if dry_run:
            config_overrides["dry_run"] = dry_run
        if big_diffs:
            config_overrides["big_diffs"] = big_diffs
        if log_level:
            config_overrides["log_level"] = log_level
        if project_context is not None:
            config_overrides["enable_project_context"] = project_context

        # Handle file filtering options
        if no_file_filtering:
            config_overrides["exclude_patterns"] = []
        elif exclude_files:
            # Start with defaults and add user patterns
            from ai_code_review.models.config import get_default_exclude_patterns

            default_patterns = get_default_exclude_patterns()
            config_overrides["exclude_patterns"] = default_patterns + list(
                exclude_files
            )

        config = Config(**config_overrides)

        # Setup structured logging
        import logging

        logging.basicConfig(
            level=getattr(logging, config.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Silence noisy third-party loggers in INFO mode
        if config.log_level.upper() == "INFO":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

        # Run health check if requested
        if health_check:
            asyncio.run(_run_health_check(config))
            return

        # Determine project_id and mr_iid from arguments, options, or CI environment
        effective_project_id = (
            project_id or gitlab_project_id or config.get_effective_project_id()
        )
        effective_mr_iid = mr_iid or gitlab_mr_iid or config.get_effective_mr_iid()

        # Validate that we have required parameters
        if not effective_project_id or not effective_mr_iid:
            if config.is_ci_mode():
                click.echo(
                    "❌ Error: Missing CI environment variables. "
                    "Expected CI_PROJECT_PATH and CI_MERGE_REQUEST_IID.",
                    err=True,
                )
            else:
                click.echo(
                    "❌ Error: PROJECT_ID and MR_IID are required.\n"
                    "Provide them as arguments or use --project-id and --mr-iid options.\n"
                    "In CI/CD, set CI_PROJECT_PATH and CI_MERGE_REQUEST_IID environment variables.",
                    err=True,
                )
            sys.exit(1)

        # Run the review process
        asyncio.run(
            _run_review(
                config=config,
                project_id=effective_project_id,
                mr_iid=effective_mr_iid,
                post_review=post,
            )
        )

    except AICodeReviewError as e:
        logger.error("AI Code Review error", error=str(e))
        click.echo(f"❌ Error: {e}", err=True)

        # Set appropriate exit code based on error type
        if isinstance(e, GitLabAPIError):
            sys.exit(2)
        elif isinstance(e, AIProviderError):
            sys.exit(3)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n⏹️  Operation cancelled by user", err=True)
        sys.exit(1)

    except Exception as e:
        logger.error("Unexpected error", error=str(e), error_type=type(e).__name__)
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


async def _run_health_check(config: Config) -> None:
    """Run health check on all components."""
    click.echo("🔍 Performing health check...")

    try:
        engine = ReviewEngine(config)
        health_status = await engine.health_check()

        # Display results
        click.echo("\n📊 Health Check Results:")
        click.echo(
            f"  Overall Status: {_format_status(health_status['overall']['status'])}"
        )
        click.echo(
            f"  Configuration: {_format_status(health_status['config']['status'])}"
        )
        click.echo(
            f"  AI Provider: {_format_status(health_status['ai_provider']['status'])}"
        )

        if health_status["ai_provider"].get("available_models"):
            click.echo(
                f"  Available Models: {health_status['ai_provider']['available_models'][:3]}"
            )

        if health_status["overall"]["status"] != "healthy":
            click.echo("\n❌ Issues detected:")
            for component, status in health_status.items():
                if isinstance(status, dict) and status.get("status") != "healthy":
                    if "suggestion" in status:
                        click.echo(f"  {component}: {status['suggestion']}")
                    elif "error" in status:
                        click.echo(f"  {component}: {status['error']}")
            sys.exit(1)
        else:
            click.echo("\n✅ All systems healthy!")

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


async def _run_review(
    config: Config,
    project_id: str,
    mr_iid: int,
    post_review: bool,
) -> None:
    """Run the review generation process."""
    logger.info(
        "Starting code review",
        project_id=project_id,
        mr_iid=mr_iid,
        provider=config.ai_provider.value,
        dry_run=config.dry_run,
    )

    click.echo("🚀 Starting AI code review...")
    click.echo(f"  Project: {project_id}")
    click.echo(f"  MR IID: {mr_iid}")
    click.echo(f"  GitLab URL: {config.get_effective_gitlab_url()}")
    click.echo(f"  AI Provider: {config.ai_provider.value}")
    click.echo(f"  Model: {config.ai_model}")

    if config.is_ci_mode():
        click.echo("  🔄 CI/CD MODE - Using GitLab CI environment variables")

    if config.dry_run:
        click.echo("  🧪 DRY RUN MODE - No actual API calls will be made")

    try:
        # Initialize review engine
        engine = ReviewEngine(config)

        # Generate review (always uses unified approach)
        click.echo("\n📥 Fetching MR data from GitLab...")
        result = await engine.generate_review(project_id, mr_iid)

        # Display results
        click.echo("\n📝 Review generated successfully!")

        if post_review:
            try:
                click.echo("\n📤 Posting review to GitLab...")
                note_info = await engine.post_review_to_gitlab(
                    project_id, mr_iid, result
                )

                if config.dry_run:
                    click.echo("🧪 DRY RUN: Review posting simulated successfully!")
                    click.echo(f"   Mock Note URL: {note_info['url']}")
                else:
                    click.echo("✅ Review posted successfully to GitLab!")
                    click.echo(f"   📝 Note URL: {note_info['url']}")
                    click.echo(f"   🆔 Note ID: {note_info['id']}")

            except Exception as e:
                logger.error("Failed to post review to GitLab", error=str(e))
                click.echo(f"❌ Failed to post review to GitLab: {e}", err=True)
                # Continue execution - show review in stdout as fallback

        # Output review to stdout
        click.echo("\n" + "=" * 80)
        click.echo("AI CODE REVIEW")
        click.echo("=" * 80)
        click.echo(result.to_markdown())

        click.echo("\n✅ Review completed successfully!")

    except Exception:
        # Re-raise to be handled by main error handler
        raise


def _format_status(status: str) -> str:
    """Format status with appropriate emoji."""
    status_map = {
        "healthy": "✅ Healthy",
        "unhealthy": "❌ Unhealthy",
        "unavailable": "⚠️ Unavailable",
        "error": "💥 Error",
    }
    return status_map.get(status, f"❓ {status.title()}")


if __name__ == "__main__":
    main()
