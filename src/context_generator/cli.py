"""CLI for intelligent project context generation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
import structlog

from ai_code_review.models.config import Config
from context_generator.core.context_builder import ContextBuilder

# Setup logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@click.command()
@click.argument(
    "project_path", default=".", type=click.Path(exists=True, file_okay=False)
)
@click.option(
    "--output", "-o", default=".ai_review/project.md", help="Output file path"
)
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["ollama", "anthropic", "gemini"]),
    help="AI provider for intelligent analysis (default: gemini)",
)
@click.option("--model", help="AI model (defaults to provider default)")
@click.option(
    "--ai-api-key",
    envvar="AI_API_KEY",
    help="API key for cloud providers (Anthropic/Gemini)",
)
@click.option(
    "--ollama-url",
    default=None,
    help="Ollama server URL (default: http://localhost:11434)",
)
@click.option(
    "--dry-run", is_flag=True, help="Dry run mode - no LLM calls, show mock output"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--section",
    multiple=True,
    type=click.Choice(["overview", "tech_stack", "structure", "review_focus"]),
    help="Update only specific sections (can be used multiple times)",
)
def generate_context(
    project_path: str,
    output: str,
    provider: str,
    model: str | None,
    ai_api_key: str | None,
    ollama_url: str,
    dry_run: bool,
    verbose: bool,
    section: tuple[str, ...],
) -> None:
    """Generate intelligent project context using LLM analysis.

    Analyzes your project and generates comprehensive context for AI code reviews
    using intelligent LLM analysis instead of hardcoded patterns.

    \b
    Environment Configuration:
    This tool supports the same .env file configuration as the main ai-code-review tool.
    Key variables include:
        AI_PROVIDER     AI provider to use (ollama, anthropic, gemini)
        AI_MODEL        AI model name (e.g., qwen2.5-coder:7b, claude-sonnet-4-20250514)
        AI_API_KEY      API key for cloud providers
        OLLAMA_BASE_URL Ollama server URL

    \b
    Section Updates:
    You can update specific sections while preserving manual content:
        --section overview          Update only project overview
        --section tech_stack        Update only technology stack
        --section structure         Update only code structure
        --section review_focus      Update only review focus areas
        Multiple sections: --section overview --section tech_stack

    \b
    Examples:
        # Full generation with manual section preservation
        ai-generate-context . --ai-api-key your-gemini-key
        \b
        # Update only tech stack section
        ai-generate-context . --section tech_stack
        \b
        # Update multiple sections while preserving manual content
        ai-generate-context . --section overview --section structure
        \b
        # With Ollama (local, no API key needed)
        ai-generate-context . --provider ollama
        \b
        # Using .env file (recommended)
        echo "AI_PROVIDER=gemini" >> .env
        echo "AI_API_KEY=your_api_key" >> .env
        ai-generate-context .
    """
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)
    else:
        import logging

        logging.basicConfig(level=logging.WARNING)

    # Validate configuration (only validate if provider is explicitly provided)
    # If no provider specified, Config will use its default and validation happens there
    if (
        provider is not None
        and provider in ["anthropic", "gemini"]
        and not ai_api_key
        and not dry_run
    ):
        click.echo(f"❌ {provider} requires --ai-api-key", err=True)
        click.echo("   Set API key: --ai-api-key your_key_here", err=True)
        click.echo(
            "   Or use environment: AI_API_KEY=your_key ai-generate-context .",
            err=True,
        )
        sys.exit(1)

    # Create config using the same system as main CLI (supports .env automatically)
    # Only pass CLI-specific values that were actually provided
    cli_args = {
        "dry_run": dry_run,
        # Force local platform to avoid GitLab/GitHub token validation
        "local": True,
        # Add dummy platform tokens to avoid validation errors (not used by context generator)
        "gitlab_token": "dummy-token-for-context-generator",
        "github_token": "dummy-token-for-context-generator",
    }

    # Only add CLI values if they were explicitly provided (not None)
    # This allows Config to use its natural defaults for unspecified values
    # Use CLI names that match Config.from_cli_args() mapping
    if provider is not None:
        cli_args["provider"] = provider  # Maps to ai_provider in Config
    if model is not None:
        cli_args["model"] = model  # Maps to ai_model in Config
    if ai_api_key is not None:
        cli_args["ai_api_key"] = ai_api_key  # Direct mapping
    if ollama_url is not None:
        cli_args["ollama_url"] = ollama_url  # Maps to ollama_base_url in Config

    try:
        # Use same config creation as main CLI - automatically loads .env
        config = Config.from_cli_args(cli_args)
        asyncio.run(_run_generation(project_path, output, config, section))
    except KeyboardInterrupt:
        click.echo("\n❌ Generation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Generation failed: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


async def _run_generation(
    project_path: str, output_path: str, config: Config, section: tuple[str, ...] = ()
) -> None:
    """Run the context generation process."""
    project_path_obj = Path(project_path).resolve()
    output_path_obj = Path(output_path)

    click.echo(f"🧠 Analysis: {project_path}")
    click.echo(f"🤖 AI Provider: {config.ai_provider.value} ({config.ai_model})")
    click.echo(f"💾 Output: {output_path}")

    if config.dry_run:
        click.echo("🧪 Dry Run Mode: No LLM calls will be made")

    # Create output directory if needed
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Generate context using new architecture
    builder = ContextBuilder(project_path_obj, config)

    try:
        # Convert section names to template keys if sections are specified
        section_mapping = {
            "overview": "project_overview",
            "tech_stack": "tech_stack",
            "structure": "code_structure",
            "review_focus": "review_focus",
        }

        target_sections = None
        if section:
            target_sections = [section_mapping.get(s, s) for s in section]

        if target_sections:
            click.echo(f"🎯 Updating sections: {', '.join(section)}")

        context = await builder.generate_context(output_path_obj, target_sections)

        # Write to file (async I/O to avoid blocking event loop)
        import aiofiles

        async with aiofiles.open(output_path_obj, "w", encoding="utf-8") as f:
            await f.write(context.context_content)

        # Show summary
        click.echo("✅ Context generation completed!")
        summary = builder.get_generation_summary()
        click.echo(f"📊 Analysis: {summary['ai_provider']} ({summary['ai_model']})")
        click.echo(f"📄 Context file: {output_path}")
        click.echo(f"📏 Size: {len(context.context_content):,} characters")

        # Show preview
        lines = context.context_content.split("\n")
        preview_lines = lines[:10] if len(lines) > 10 else lines
        click.echo("\n👀 Preview:")
        for line in preview_lines:
            click.echo(f"   {line}")
        if len(lines) > 10:
            click.echo("   ...")

    except Exception as e:
        logger.error("Context generation failed", error=str(e))
        raise


def main() -> None:
    """Main entry point for ai-generate-context command."""
    generate_context()


if __name__ == "__main__":
    main()
