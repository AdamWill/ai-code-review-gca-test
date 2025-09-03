"""Command Line Interface for AI Code Review tool."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import click
import structlog

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import AIProvider, Config, PlatformProvider
from ai_code_review.utils.exceptions import (
    AICodeReviewError,
    AIProviderError,
)
from ai_code_review.utils.platform_exceptions import (
    PlatformAPIError,
)

logger = structlog.get_logger(__name__)


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
    help="GitLab instance URL (default: from config or https://gitlab.com)",
)
@click.option(
    "--github-url",
    default=None,
    help="GitHub API URL (default: from config or https://api.github.com)",
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
    "--context-file",
    default=None,
    help="Path to project context file (default: .ai_review/project.md)",
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
@click.version_option(version="0.1.0", prog_name="ai-code-review")
def main(
    project_id: str | None,
    mr_iid: int | None,
    platform: str | None,
    gitlab_url: str | None,
    github_url: str | None,
    project_id_option: str | None,
    pr_number_option: int | None,
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
    context_file: str | None,
    no_mr_summary: bool,
    ssl_cert_url: str | None,
    ssl_cert_cache_dir: str | None,
    health_check: bool,
    output_file: str | None,
    local: bool,
    target_branch: str,
) -> None:
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

        # GitHub
        ai-code-review --platform github owner/repo 456 --post
        ai-code-review --platform github --project-id owner/repo --pr-number 456

        # CI/CD mode (uses CI environment variables)
        ai-code-review --post

        # Local review (analyze local changes)
        ai-code-review --local
        ai-code-review --local --target-branch develop
        ai-code-review --local --output-file local-review.md
        ai-code-review --local --provider ollama  # Use local LLM for cost-free review

        # Health check
        ai-code-review --health-check

        # Local testing
        ai-code-review group/project 123 --provider ollama --dry-run
    """
    try:
        # Setup configuration by merging environment and CLI overrides
        config_overrides: dict[str, Any] = {}
        if local:
            config_overrides["platform_provider"] = PlatformProvider.LOCAL
        elif platform:
            config_overrides["platform_provider"] = PlatformProvider(platform)
        if gitlab_url:
            config_overrides["gitlab_url"] = gitlab_url
        if github_url:
            config_overrides["github_url"] = github_url
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
        if context_file:
            config_overrides["project_context_file"] = context_file
        if no_mr_summary:
            config_overrides["include_mr_summary"] = False
        if ssl_cert_url:
            config_overrides["ssl_cert_url"] = ssl_cert_url
        if ssl_cert_cache_dir:
            config_overrides["ssl_cert_cache_dir"] = ssl_cert_cache_dir

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

        # Validate incompatible options
        if local and post:
            click.echo(
                "❌ Error: --local and --post are incompatible. "
                "Local reviews cannot be posted. Use --output-file to save the review.",
                err=True,
            )
            sys.exit(1)

        config = Config(**config_overrides)

        # Setup structured logging
        import logging

        # Configure standard logging to use stderr
        logging.basicConfig(
            level=getattr(logging, config.log_level.upper()),
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
        if config.log_level.upper() == "INFO":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

        # Run health check if requested
        if health_check:
            asyncio.run(_run_health_check(config))
            return

        # Determine project_id and pr_number from arguments, options, or CI environment
        # Precedence order: positional arg > CLI option > legacy option > config/env var
        effective_project_id = (
            project_id or project_id_option or config.get_effective_repository_path()
        )
        # Precedence order: positional arg > new CLI option > legacy option > config/env var
        effective_pr_number = (
            mr_iid
            or pr_number_option
            or gitlab_mr_iid
            or config.get_effective_pull_request_number()
        )

        # For local mode, set default values
        if config.platform_provider == PlatformProvider.LOCAL:
            effective_project_id = "local"
            effective_pr_number = 0

        # Validate that we have required parameters (skip for local mode)
        elif not effective_project_id or not effective_pr_number:
            platform_name = config.platform_provider.value
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

        # Run the review process
        asyncio.run(
            _run_review(
                config=config,
                project_id=effective_project_id,
                pr_number=effective_pr_number,
                post_review=post,
                output_file=output_file,
                target_branch=target_branch if local else None,
            )
        )

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


async def _run_review(
    config: Config,
    project_id: str,
    pr_number: int,
    post_review: bool,
    output_file: str | None = None,
    target_branch: str | None = None,
) -> None:
    """Run the review generation process."""
    platform_name = config.platform_provider.value
    logger.info(
        "Starting code review",
        project_id=project_id,
        pr_number=pr_number,
        platform=platform_name,
        provider=config.ai_provider.value,
        dry_run=config.dry_run,
    )

    click.echo("🚀 Starting AI code review...")
    click.echo(f"  Project: {project_id}")
    click.echo(f"  PR/MR Number: {pr_number}")
    click.echo(f"  Platform: {platform_name.title()}")
    click.echo(f"  Server URL: {config.get_effective_server_url()}")
    click.echo(f"  AI Provider: {config.ai_provider.value}")
    click.echo(f"  Model: {config.ai_model}")

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
        platform_name = config.platform_provider.value.title()
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
