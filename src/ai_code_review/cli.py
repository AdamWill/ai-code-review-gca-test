"""Command Line Interface for AI Code Review tool."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import click
import structlog

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import (
    _DEFAULT_MODELS,
    AIProvider,
    Config,
    PlatformProvider,
)
from ai_code_review.utils.exceptions import (
    EXIT_CODE_SKIPPED,
    AICodeReviewError,
    AIProviderError,
    ReviewSkippedError,
)
from ai_code_review.utils.platform_exceptions import (
    PlatformAPIError,
)

logger = structlog.get_logger(__name__)


def _get_enum_value(enum_obj: Any) -> str:
    """Get the value from an enum safely, handling both real enums and mocks."""
    if hasattr(enum_obj, "value"):
        return str(enum_obj.value)
    else:
        return str(enum_obj)


def _resolve_project_params(params: dict[str, Any], config: Config) -> tuple[str, int]:
    """Resolve project ID and PR number from various sources.

    Args:
        params: CLI parameters from Click context
        config: Configuration instance

    Returns:
        tuple[str, int]: Resolved project_id and pr_number

    Raises:
        SystemExit: If required parameters cannot be resolved
    """
    # Determine project_id and pr_number from arguments, options, or CI environment
    # Precedence order: positional arg > CLI option > legacy option > config/env var
    effective_project_id = (
        params.get("project_id")
        or params.get("project_id_option")
        or config.get_effective_repository_path()
    )
    # Precedence order: positional arg > new CLI option > legacy option > config/env var
    effective_pr_number = (
        params.get("mr_iid")
        or params.get("pr_number_option")
        or params.get("gitlab_mr_iid")
        or config.get_effective_pull_request_number()
    )

    # For local mode, set default values
    if config.platform_provider == PlatformProvider.LOCAL:
        effective_project_id = "local"
        effective_pr_number = 0
    elif not effective_project_id or not effective_pr_number:
        # Validate that we have required parameters
        platform_name = _get_enum_value(config.platform_provider)
        if config.is_ci_mode():
            if platform_name == "gitlab":
                click.echo(
                    "❌ Error: Missing GitLab CI environment variables. "
                    "Expected CI_PROJECT_PATH and CI_MERGE_REQUEST_IID.",
                    err=True,
                )
            else:
                click.echo(
                    "❌ Error: Missing GitHub Actions environment variables. "
                    "Expected GITHUB_REPOSITORY and PR number from event.",
                    err=True,
                )
        else:
            if platform_name == "gitlab":
                click.echo(
                    "❌ Error: PROJECT_ID and MR_IID are required for GitLab.\n"
                    "Provide them as arguments or use --project-id and --pr-number options.\n"
                    "In GitLab CI/CD, set CI_PROJECT_PATH and CI_MERGE_REQUEST_IID environment variables.",
                    err=True,
                )
            else:
                click.echo(
                    "❌ Error: PROJECT_ID and PR_NUMBER are required for GitHub.\n"
                    "Provide them as arguments or use --project-id and --pr-number options.\n"
                    "In GitHub Actions, set GITHUB_REPOSITORY and derive PR number from event.",
                    err=True,
                )
        sys.exit(1)

    return effective_project_id, effective_pr_number


def _validate_local_mode_options(params: dict[str, Any]) -> None:
    """Validate options when using local mode.

    Args:
        params: CLI parameters from Click context
    """
    # Validate incompatible options
    if params.get("local") and params.get("post"):
        click.echo(
            "❌ Error: --local and --post are incompatible. "
            "Local reviews cannot be posted. Use --output-file to save the review.",
            err=True,
        )
        sys.exit(1)

    # Check for ignored options when using --local
    if params.get("local"):
        ignored_options = []
        if params.get("project_id") or params.get("project_id_option"):
            ignored_options.append("--project-id")
        if (
            params.get("mr_iid")
            or params.get("pr_number_option")
            or params.get("gitlab_mr_iid")
        ):
            ignored_options.append("--pr-number/--mr-iid")
        if params.get("gitlab_url"):
            ignored_options.append("--gitlab-url")
        if params.get("github_url"):
            ignored_options.append("--github-url")

        if ignored_options:
            click.echo(
                f"⚠️  Warning: The following options are ignored in local mode: {', '.join(ignored_options)}",
                err=True,
            )


def _setup_logging(config: Config) -> None:
    """Setup structured logging configuration.

    Args:
        config: Configuration instance with log level
    """
    import logging

    # Configure standard logging to use stderr
    # Handle both real strings and mocked values for test compatibility
    log_level = config.log_level
    if hasattr(log_level, "upper"):
        log_level_name = log_level.upper()
    else:
        log_level_name = str(log_level).upper()

    logging.basicConfig(
        level=getattr(logging, log_level_name, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Send logs to stderr, keep stdout clean for review output
    )

    # Configure structlog to also use stderr
    import structlog

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers in INFO mode
    # Handle both real strings and mocked values for test compatibility
    log_level_check = config.log_level
    if hasattr(log_level_check, "upper"):
        log_level_upper = log_level_check.upper()
    else:
        log_level_upper = str(log_level_check).upper()

    if log_level_upper == "INFO":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


@click.command()
@click.argument("project_id", required=False)
@click.argument("mr_iid", type=int, required=False)
@click.option(
    "--platform",
    type=click.Choice([p.value for p in PlatformProvider]),
    default=None,
    help="Code hosting platform to use (default: gitlab)",
)
@click.option(
    "--gitlab-url",
    default=None,
    help="GitLab instance URL (default: https://gitlab.com)",
)
@click.option(
    "--github-url",
    default=None,
    help="GitHub API URL (default: https://api.github.com)",
)
@click.option(
    "--project-id",
    "project_id_option",
    default=None,
    help="Project identifier (GitLab: group/project, GitHub: owner/repo)",
)
@click.option(
    "--pr-number",
    "pr_number_option",
    type=int,
    default=None,
    help="Pull/merge request number (GitLab: MR IID, GitHub: PR number)",
)
# Legacy options for backward compatibility
@click.option(
    "--mr-iid",
    "gitlab_mr_iid",
    type=int,
    default=None,
    help="Merge Request IID (legacy, use --pr-number instead)",
)
@click.option(
    "--provider",
    type=click.Choice([p.value for p in AIProvider]),
    default=None,
    help="AI provider to use (default: gemini)",
)
@click.option(
    "--model",
    default=None,
    help=f"AI model name (default: provider-specific - {_DEFAULT_MODELS[AIProvider.GEMINI]}, {_DEFAULT_MODELS[AIProvider.ANTHROPIC]}, {_DEFAULT_MODELS[AIProvider.OLLAMA]})",
)
@click.option(
    "--ollama-url",
    default=None,
    help="Ollama server URL (default: http://localhost:11434)",
)
@click.option(
    "--temperature",
    type=float,
    default=None,
    help="AI response temperature 0.0-2.0 (default: 0.1)",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Maximum AI response tokens (default: 8000)",
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
    help="Maximum characters to process from diff (default: 100000)",
)
@click.option(
    "--max-files",
    type=int,
    default=None,
    help="Maximum number of files to process (default: 100)",
)
@click.option(
    "--post",
    is_flag=True,
    help="Post review as MR comment to GitLab/GitHub",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run mode - no actual API calls made",
)
@click.option(
    "--big-diffs",
    is_flag=True,
    help="Force larger context window - auto-activated for large diffs/content",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default=None,
    help="Logging level (default: INFO)",
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
    "--context-file",
    default=None,
    help="Path to project context file (default: .ai_review/project.md)",
)
@click.option(
    "--team-context",
    default=None,
    help="Team/organization context file (local path or URL, e.g., https://company.com/standards/review-context.md)",
)
@click.option(
    "--no-mr-summary",
    is_flag=True,
    help="Skip MR Summary section and show only detailed code review",
)
@click.option(
    "--ssl-cert-url",
    default=None,
    help="URL to download SSL certificate automatically (alternative to manual cert path)",
)
@click.option(
    "--ssl-cert-cache-dir",
    default=None,
    help="Directory to cache downloaded SSL certificates (default: .ssl_cache)",
)
@click.option(
    "--health-check",
    is_flag=True,
    help="Perform health check on all components and exit",
)
@click.option(
    "-o",
    "--output-file",
    default=None,
    help="Save review output to file (default: display in terminal)",
)
@click.option(
    "--local",
    is_flag=True,
    help="Review local git changes instead of remote PR/MR (compares current branch to target)",
)
@click.option(
    "--target-branch",
    default="main",
    help="Target branch for local comparison (default: main)",
)
@click.option(
    "--no-config-file",
    is_flag=True,
    help="Skip loading config file (auto-detected .ai_review/config.yml or custom path)",
)
@click.option(
    "--config-file",
    default=None,
    help="Custom config file path (default: auto-detect .ai_review/config.yml)",
)
@click.option(
    "--no-skip-detection",
    is_flag=True,
    help="Disable automatic review skipping (force review even for bots/dependencies)",
)
@click.option(
    "--test-skip-only",
    is_flag=True,
    help="Test skip detection without running review (dry-run for skip logic only)",
)
@click.version_option(version="0.1.0", prog_name="ai-code-review")
def main(**kwargs: Any) -> None:
    """
    AI-powered code review tool for GitLab Merge Requests and GitHub Pull Requests.

    Analyzes PR/MR diffs using AI models and generates structured feedback.

    \b
    Arguments (optional in CI/CD mode):
        PROJECT_ID    Project identifier (GitLab: "group/project", GitHub: "owner/repo")
        MR_IID        Pull/merge request number (GitLab: MR IID, GitHub: PR number)

    \b
    Examples:
        # GitLab (default platform)
        ai-code-review group/project 123
        ai-code-review --project-id group/project --pr-number 123 --post
        \b
        # GitHub
        ai-code-review --platform github owner/repo 456 --post
        ai-code-review --platform github --project-id owner/repo --pr-number 456
        \b
        # CI/CD mode (uses CI environment variables)
        ai-code-review --post
        \b
        # Local review (analyze local changes)
        ai-code-review --local
        ai-code-review --local --target-branch develop
        ai-code-review --local --output-file local-review.md
        ai-code-review --local --provider ollama  # Use local LLM for cost-free review
        \b
        # Team context (shared across projects)
        ai-code-review --team-context https://gitlab.com/org/standards/-/raw/main/review.md --local
        ai-code-review group/project 123 --team-context ../team-standards.md --post
        \b
        # Health check
        ai-code-review --health-check
        \b
        # Local testing
        ai-code-review group/project 123 --provider ollama --dry-run
    """
    try:
        # Build configuration using intelligent auto-mapping - Config handles everything
        config = Config.from_cli_args(kwargs)

        # Validate local mode options early
        _validate_local_mode_options(kwargs)

        # Setup structured logging
        _setup_logging(config)

        # Handle health check early exit
        if config.health_check:
            asyncio.run(_run_health_check(config))
            return

        # Handle test-skip-only mode
        if kwargs.get("test_skip_only"):
            asyncio.run(_run_test_skip_only(config, kwargs))
            return

        # Resolve project parameters (ID and PR number) - Config knows how to do this
        effective_project_id, effective_pr_number = _resolve_project_params(
            kwargs, config
        )

        # Run the review process - Config contains all needed parameters
        asyncio.run(
            _run_review(
                config=config,
                project_id=effective_project_id,
                pr_number=effective_pr_number,
                post_review=config.post,
                output_file=config.output_file,
                target_branch=config.target_branch
                if config.platform_provider == PlatformProvider.LOCAL
                else None,
            )
        )

    except ReviewSkippedError as e:
        # Handle review skipped - this is expected behavior, not an error
        logger.info("Review skipped", reason=e.reason, trigger=e.trigger)
        click.echo(f"ℹ️ {e}", err=False)  # Not an error, just info
        sys.exit(EXIT_CODE_SKIPPED)

    except AICodeReviewError as e:
        logger.error("AI Code Review error", error=str(e))
        click.echo(f"❌ Error: {e}", err=True)

        # Set appropriate exit code based on error type
        if isinstance(e, PlatformAPIError):
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


async def _run_test_skip_only(config: Config, cli_kwargs: dict[str, Any]) -> None:
    """Test skip detection without running full review."""
    click.echo("🧪 Testing skip detection logic...")

    try:
        # Resolve project parameters
        effective_project_id, effective_pr_number = _resolve_project_params(
            cli_kwargs, config
        )

        # Initialize review engine
        engine = ReviewEngine(config)

        # Fetch PR/MR data (but don't run full review)
        platform_name = _get_enum_value(config.platform_provider).title()
        click.echo(f"📥 Fetching PR/MR data from {platform_name}...")

        pr_data = await engine.platform_client.get_pull_request_data(
            str(effective_project_id), effective_pr_number
        )

        click.echo("📊 PR/MR Info:")
        click.echo(f"   Title: {pr_data.info.title}")
        click.echo(f"   Author: {pr_data.info.author}")
        click.echo(f"   Files: {pr_data.file_count}")

        # Test skip detection
        should_skip, skip_reason, skip_trigger = engine.should_skip_review(pr_data)

        if should_skip:
            click.echo("✅ Review would be SKIPPED")
            click.echo(f"   Reason: {skip_reason}")
            click.echo(f"   Trigger: {skip_trigger}")
            click.echo(f"   Exit code would be: {EXIT_CODE_SKIPPED}")
            sys.exit(EXIT_CODE_SKIPPED)
        else:
            click.echo("❌ Review would NOT be skipped")
            click.echo("   Review would proceed normally")
            sys.exit(0)

    except Exception as e:
        click.echo(f"❌ Error testing skip detection: {e}", err=True)
        sys.exit(1)


async def _run_review(
    config: Config,
    project_id: str,
    pr_number: int,
    post_review: bool,
    output_file: str | None = None,
    target_branch: str | None = None,
) -> None:
    """Run the review generation process."""
    platform_name = _get_enum_value(config.platform_provider)
    logger.info(
        "Starting code review",
        project_id=project_id,
        pr_number=pr_number,
        platform=platform_name,
        provider=_get_enum_value(config.ai_provider),
        dry_run=config.dry_run,
    )

    click.echo("🚀 Starting AI code review...")
    click.echo(f"  Project: {project_id}")
    click.echo(f"  PR/MR Number: {pr_number}")
    click.echo(f"  Platform: {platform_name.title()}")
    click.echo(f"  Server URL: {config.get_effective_server_url()}")
    click.echo(f"  AI Provider: {_get_enum_value(config.ai_provider)}")
    click.echo(f"  Model: {config.get_ai_model()}")

    if config.is_ci_mode():
        ci_system = "GitLab CI" if platform_name == "gitlab" else "GitHub Actions"
        click.echo(f"  🔄 CI/CD MODE - Using {ci_system} environment variables")

    if config.dry_run:
        click.echo("  🧪 DRY RUN MODE - No actual API calls will be made")

    try:
        # Initialize review engine
        engine = ReviewEngine(config)

        # Configure LocalGitClient if in local mode
        if config.platform_provider == PlatformProvider.LOCAL and target_branch:
            from ai_code_review.core.local_git_client import LocalGitClient

            if isinstance(engine.platform_client, LocalGitClient):
                engine.platform_client.set_target_branch(target_branch)

        # Generate review (always uses unified approach)
        platform_name = _get_enum_value(config.platform_provider).title()
        click.echo(f"\n📥 Fetching PR/MR data from {platform_name}...")
        result = await engine.generate_review(project_id, pr_number)

        # Display results
        click.echo("\n📝 Review generated successfully!")

        if post_review:
            try:
                click.echo(f"\n📤 Posting review to {platform_name}...")
                note_info = await engine.post_review_to_platform(
                    project_id, pr_number, result
                )

                if config.dry_run:
                    click.echo("🧪 DRY RUN: Review posting simulated successfully!")
                    click.echo(f"   Mock Note URL: {note_info.url}")
                else:
                    click.echo(f"✅ Review posted successfully to {platform_name}!")
                    click.echo(f"   📝 Comment URL: {note_info.url}")
                    click.echo(f"   🆔 Comment ID: {note_info.id}")

            except Exception as e:
                logger.error(f"Failed to post review to {platform_name}", error=str(e))
                click.echo(
                    f"❌ Failed to post review to {platform_name}: {e}", err=True
                )
                # Continue execution - show review in stdout as fallback

        # Output review
        review_output = result.to_markdown()

        if output_file:
            # Save to file
            try:
                from pathlib import Path

                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(review_output, encoding="utf-8")
                click.echo(f"📄 Review saved to: {output_file}")
            except Exception as e:
                logger.error(
                    "Failed to write output file", file=output_file, error=str(e)
                )
                click.echo(f"❌ Failed to write output file: {e}", err=True)
                # Fallback: show review in stdout
                click.echo("\n" + "=" * 80)
                click.echo("AI CODE REVIEW")
                click.echo("=" * 80)
                click.echo(review_output)
        else:
            # Display in terminal (stdout)
            click.echo("\n" + "=" * 80)
            click.echo("AI CODE REVIEW")
            click.echo("=" * 80)
            click.echo(review_output)

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
