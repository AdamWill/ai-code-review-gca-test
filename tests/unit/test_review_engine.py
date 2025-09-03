"""Tests for review engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import AIProvider, Config
from ai_code_review.models.platform import (
    PostReviewResponse,
    PullRequestCommit,
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.models.review import CodeReview, ReviewResult, ReviewSummary
from ai_code_review.utils.exceptions import AIProviderError


class TestReviewEngine:
    """Test ReviewEngine functionality."""

    @pytest.fixture
    def test_config(self) -> Config:
        """Test configuration."""
        return Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            dry_run=False,
        )

    @pytest.fixture
    def dry_run_config(self) -> Config:
        """Dry run configuration."""
        return Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
        )

    @pytest.fixture
    def sample_pr_data(self) -> PullRequestData:
        """Sample pull request data."""
        info = PullRequestInfo(
            id=123,
            number=456,
            title="Test MR",
            description="Test description",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="opened",
            web_url="https://gitlab.com/test/-/merge_requests/456",
        )

        diffs = [
            PullRequestDiff(
                file_path="src/test.py",
                diff="@@ -1,3 +1,3 @@\n-old_function()\n+new_function()",
            )
        ]

        commits = [
            PullRequestCommit(
                id="abc123",
                title="Test feature implementation",
                message="Test feature implementation\n\nAdds new functionality for testing.\n- Implements core logic\n- Updates documentation",
                author_name="Test Author",
                author_email="test@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc123",
            )
        ]

        return PullRequestData(info=info, diffs=diffs, commits=commits)

    def test_engine_initialization(self, test_config: Config) -> None:
        """Test review engine initialization."""
        engine = ReviewEngine(test_config)

        assert engine.config == test_config
        assert isinstance(engine.platform_client, object)
        assert engine.ai_provider.provider_name == "ollama"

    def test_unsupported_ai_provider(self) -> None:
        """Test error handling for unsupported AI provider."""
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OPENAI,  # Not yet implemented
            ai_api_key="test_openai_key",  # Need API key for cloud provider validation
        )

        with pytest.raises(AIProviderError, match="not yet implemented"):
            ReviewEngine(config)

    @pytest.mark.asyncio
    async def test_generate_review_dry_run(
        self, dry_run_config: Config, sample_pr_data: PullRequestData
    ) -> None:
        """Test review generation in dry run mode."""
        engine = ReviewEngine(dry_run_config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            result = await engine.generate_review("test/project", 123)

            assert isinstance(result, ReviewResult)
            assert isinstance(result.review, CodeReview)
            assert "[DRY RUN]" in result.review.general_feedback

            # Should include summary by default
            assert result.summary is not None
            assert isinstance(result.summary, ReviewSummary)
            assert "[DRY RUN]" in result.summary.title

    @pytest.mark.asyncio
    async def test_generate_review_always_includes_summary(
        self, dry_run_config: Config, sample_pr_data: PullRequestData
    ) -> None:
        """Test that review generation always includes summary (unified approach)."""
        engine = ReviewEngine(dry_run_config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            result = await engine.generate_review("test/project", 123)

            assert isinstance(result, ReviewResult)
            assert isinstance(result.review, CodeReview)
            assert "[DRY RUN]" in result.review.general_feedback

            # Summary should always be included now
            assert result.summary is not None
            assert isinstance(result.summary, ReviewSummary)
            assert "[DRY RUN]" in result.summary.title

    @pytest.mark.asyncio
    async def test_generate_review_with_ai(
        self, test_config: Config, sample_pr_data: PullRequestData
    ) -> None:
        """Test review generation with AI provider."""
        engine = ReviewEngine(test_config)

        # Mock GitLab client
        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            # Mock AI provider
            with patch.object(engine.ai_provider, "is_available", return_value=True):
                # Mock review chain
                with patch(
                    "ai_code_review.core.review_engine.create_review_chain"
                ) as mock_review_chain:
                    mock_chain = AsyncMock()
                    # Mock complete structured response from LLM (ready to use)
                    mock_response = """## AI Code Review

### 📋 MR Summary
Test merge request with sample code modifications.

- **Key Changes:** Sample code modification in test files
- **Impact:** Test module affected, no user-facing changes
- **Risk Level:** Low - Simple test change with minimal impact

### Detailed Code Review

AI generated review feedback for test purposes. The code changes appear well-structured and follow good practices.

### ✅ Summary
- **Overall Assessment:** Good code quality with minor suggestions
- **Priority Issues:** None identified
- **Minor Suggestions:** Consider adding more comprehensive tests"""

                    mock_chain.ainvoke.return_value = mock_response
                    mock_review_chain.return_value = mock_chain

                    result = await engine.generate_review("test/project", 123)

                    # Verify create_review_chain was called with config
                    mock_review_chain.assert_called_once_with(
                        engine.ai_provider.client, engine.config
                    )

                    assert isinstance(result, ReviewResult)
                    # The entire LLM response should be used directly
                    assert (
                        "AI generated review feedback" in result.review.general_feedback
                    )
                    assert "## AI Code Review" in result.review.general_feedback
                    assert "### 📋 MR Summary" in result.review.general_feedback
                    assert "### Detailed Code Review" in result.review.general_feedback
                    assert result.summary is not None
                    assert result.summary.title == "Test MR"

    @pytest.mark.asyncio
    async def test_generate_review_without_mr_summary(
        self, sample_pr_data: PullRequestData
    ) -> None:
        """Test review generation without MR Summary section (with AI call)."""
        # Create config with MR Summary disabled, but NOT dry_run (use ollama to avoid API key requirements)
        config = Config(ai_provider="ollama", include_mr_summary=False)
        engine = ReviewEngine(config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            # Mock AI provider
            with patch.object(engine.ai_provider, "is_available", return_value=True):
                # Mock review chain
                with patch(
                    "ai_code_review.core.review_engine.create_review_chain"
                ) as mock_review_chain:
                    mock_chain = AsyncMock()
                    # Mock response without MR Summary section
                    mock_response = """## AI Code Review

### Detailed Code Review

AI generated review feedback for test purposes. The code changes appear well-structured and follow good practices.

### ✅ Summary
- **Overall Assessment:** Good code quality with minor suggestions
- **Priority Issues:** None identified
- **Minor Suggestions:** Consider adding more comprehensive tests"""

                    mock_chain.ainvoke.return_value = mock_response
                    mock_review_chain.return_value = mock_chain

                    result = await engine.generate_review("test/project", 123)

                    # Verify create_review_chain was called with config that has include_mr_summary=False
                    mock_review_chain.assert_called_once_with(
                        engine.ai_provider.client, engine.config
                    )

                    assert isinstance(result, ReviewResult)
                    assert isinstance(result.review, CodeReview)
                    assert isinstance(result.summary, ReviewSummary)
                    # Verify MR Summary section is NOT present
                    assert "### 📋 MR Summary" not in result.review.general_feedback
                    assert "### Detailed Code Review" in result.review.general_feedback
                    assert "## AI Code Review" in result.review.general_feedback

    @pytest.mark.asyncio
    async def test_generate_review_dry_run_without_mr_summary(
        self, sample_pr_data: PullRequestData
    ) -> None:
        """Test dry run mode without MR Summary section."""
        # Create config with MR Summary disabled AND dry_run=True (use ollama to avoid API key requirements)
        config = Config(ai_provider="ollama", include_mr_summary=False, dry_run=True)
        engine = ReviewEngine(config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            result = await engine.generate_review("test/project", 123)

            assert isinstance(result, ReviewResult)
            assert isinstance(result.review, CodeReview)
            assert isinstance(result.summary, ReviewSummary)
            # Verify mock review respects the configuration
            assert "### 📋 MR Summary" not in result.review.general_feedback
            assert "### Detailed Code Review" in result.review.general_feedback
            assert "[DRY RUN]" in result.review.general_feedback

    @pytest.mark.asyncio
    async def test_generate_review_ai_unavailable(
        self, test_config: Config, sample_pr_data: PullRequestData
    ) -> None:
        """Test error handling when AI provider is unavailable."""
        engine = ReviewEngine(test_config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_pr_data

            with patch.object(engine.ai_provider, "is_available", return_value=False):
                with pytest.raises(AIProviderError, match="is not available"):
                    await engine.generate_review("test/project", 123)

    @pytest.mark.asyncio
    async def test_generate_review_gitlab_error(self, test_config: Config) -> None:
        """Test error handling for GitLab API errors."""
        engine = ReviewEngine(test_config)

        with patch.object(
            engine.platform_client, "get_pull_request_data"
        ) as mock_gitlab:
            mock_gitlab.side_effect = Exception("GitLab API error")

            with pytest.raises(AIProviderError, match="Failed to generate review"):
                await engine.generate_review("test/project", 123)

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, test_config: Config) -> None:
        """Test health check when all components are healthy."""
        engine = ReviewEngine(test_config)

        with patch.object(engine.ai_provider, "health_check") as mock_health:
            mock_health.return_value = {"status": "healthy", "model": "test"}

            result = await engine.health_check()

            assert result["overall"]["status"] == "healthy"
            assert result["config"]["status"] == "healthy"
            assert result["ai_provider"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_ai_unhealthy(self, test_config: Config) -> None:
        """Test health check when AI provider is unhealthy."""
        engine = ReviewEngine(test_config)

        with patch.object(engine.ai_provider, "health_check") as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "error": "Connection failed",
            }

            result = await engine.health_check()

            assert result["overall"]["status"] == "unhealthy"
            assert result["ai_provider"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_ai_error(self, test_config: Config) -> None:
        """Test health check when AI provider throws exception."""
        engine = ReviewEngine(test_config)

        with patch.object(engine.ai_provider, "health_check") as mock_health:
            mock_health.side_effect = Exception("Health check failed")

            result = await engine.health_check()

            assert result["overall"]["status"] == "unhealthy"
            assert result["ai_provider"]["status"] == "error"
            assert "Health check failed" in result["ai_provider"]["error"]

    def test_format_diffs_for_ai(
        self, test_config: Config, sample_pr_data: PullRequestData
    ) -> None:
        """Test diff formatting for AI processing."""
        engine = ReviewEngine(test_config)

        formatted = engine._format_diffs_for_ai(sample_pr_data)

        assert "# Merge Request: Test MR" in formatted
        assert "**Author:** test_user" in formatted
        assert "feature → main" in formatted
        assert "### src/test.py" in formatted
        assert "```diff" in formatted
        assert "old_function()" in formatted
        assert "new_function()" in formatted

    def test_get_project_context_with_language_hint(self, test_config: Config) -> None:
        """Test project context with language hint."""
        test_config.language_hint = "python"
        engine = ReviewEngine(test_config)

        context = engine._get_project_context()

        assert "Primary Language: python" in context

    def test_get_project_context_without_hint(
        self, test_config: Config, chdir_tmp
    ) -> None:
        """Test project context without language hint."""

        test_config.language_hint = None

        engine = ReviewEngine(test_config)
        context = engine._get_project_context()
        assert "No additional project context available" in context

    @pytest.mark.asyncio
    async def test_post_review_to_platform_success(self, test_config: Config) -> None:
        """Test successful review posting to GitLab."""
        engine = ReviewEngine(test_config)

        # Mock review result
        review = CodeReview(
            general_feedback="Test review feedback",
            file_reviews=[],
            overall_assessment="Good quality",
            priority_issues=["Issue 1"],
            minor_suggestions=["Suggestion 1"],
        )
        summary = ReviewSummary(
            title="Test Summary",
            key_changes=["Change 1"],
            modules_affected=["module1"],
            user_impact="None",
            technical_impact="Minor",
            risk_level="Low",
            risk_justification="Safe changes",
        )
        review_result = ReviewResult(review=review, summary=summary)

        # Mock GitLab client response
        mock_note_info = PostReviewResponse(
            id="123",
            url="https://gitlab.com/test/-/merge_requests/456#note_123",
            created_at="2024-01-01T12:00:00Z",
            author="AI Code Review",
        )

        with patch.object(engine.platform_client, "post_review") as mock_post:
            mock_post.return_value = mock_note_info

            result = await engine.post_review_to_platform(
                "test/project", 456, review_result
            )

            # Verify the post_review was called with correct parameters
            mock_post.assert_called_once()
            args = mock_post.call_args[0]
            assert args[0] == "test/project"
            assert args[1] == 456
            assert "Test review feedback" in args[2]  # Review content
            assert "🤖 **AI Code Review**" in args[2]  # Footer

            # Verify return value
            assert result == mock_note_info

    @pytest.mark.asyncio
    async def test_post_review_to_platform_dry_run(
        self, dry_run_config: Config
    ) -> None:
        """Test review posting to GitLab in dry run mode."""
        engine = ReviewEngine(dry_run_config)

        # Mock review result
        review = CodeReview(
            general_feedback="Test review feedback",
            file_reviews=[],
            overall_assessment="Good quality",
            priority_issues=[],
            minor_suggestions=[],
        )
        summary = ReviewSummary(
            title="Test Summary",
            key_changes=["Change 1"],
            modules_affected=["module1"],
            user_impact="None",
            technical_impact="Minor",
            risk_level="Low",
            risk_justification="Safe changes",
        )
        review_result = ReviewResult(review=review, summary=summary)

        # Mock GitLab client response for dry run
        mock_note_info = PostReviewResponse(
            id="mock_note_123",
            url="https://gitlab.com/mock/project/-/merge_requests/456#note_mock_123",
            created_at="2024-01-01T12:00:00Z",
            author="AI Code Review (DRY RUN)",
            content_preview="Test review feedback...",
        )

        with patch.object(engine.platform_client, "post_review") as mock_post:
            mock_post.return_value = mock_note_info

            result = await engine.post_review_to_platform(
                "test/project", 456, review_result
            )

            # Verify the post_review was called
            mock_post.assert_called_once()
            args = mock_post.call_args[0]
            assert "**Mode:** DRY RUN" in args[2]  # Footer includes dry run mode

            # Verify return value
            assert result == mock_note_info
            assert "DRY RUN" in result.author

    def test_create_review_footer_normal_mode(self, test_config: Config) -> None:
        """Test review footer creation in normal mode."""
        engine = ReviewEngine(test_config)

        footer = engine._create_review_footer()

        assert "🤖 **AI Code Review**" in footer
        assert f"**AI Provider:** {test_config.ai_provider.value}" in footer
        assert f"**Model:** {test_config.ai_model}" in footer
        assert "DRY RUN" not in footer

    def test_create_review_footer_dry_run_mode(self, dry_run_config: Config) -> None:
        """Test review footer creation in dry run mode."""
        engine = ReviewEngine(dry_run_config)

        footer = engine._create_review_footer()

        assert "🤖 **AI Code Review**" in footer
        assert f"**AI Provider:** {dry_run_config.ai_provider.value}" in footer
        assert f"**Model:** {dry_run_config.ai_model}" in footer
        assert "**Mode:** DRY RUN" in footer

    def test_load_project_context_file_exists(
        self, test_config: Config, chdir_tmp
    ) -> None:
        """Test loading project context when file exists."""

        # Create a project context file
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()
        context_file = project_dir / "project.md"
        context_content = "# Project Context\nThis is a test project."
        context_file.write_text(context_content)

        engine = ReviewEngine(test_config)
        result = engine._load_project_context_file()

        assert result == context_content

    def test_load_project_context_file_not_exists(
        self, test_config: Config, chdir_tmp
    ) -> None:
        """Test loading project context when file doesn't exist."""

        engine = ReviewEngine(test_config)
        result = engine._load_project_context_file()
        assert result is None

    def test_load_project_context_file_empty(
        self, test_config: Config, chdir_tmp
    ) -> None:
        """Test loading empty project context file."""

        # Create an empty project context file
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()
        context_file = project_dir / "project.md"
        context_file.write_text("")

        engine = ReviewEngine(test_config)
        result = engine._load_project_context_file()

        assert result is None

    def test_get_project_context_with_enabled_context(self, chdir_tmp) -> None:
        """Test getting project context when enabled and file exists."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            enable_project_context=True,
        )

        # Create a project context file
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()
        context_file = project_dir / "project.md"
        context_content = "This is project context."
        context_file.write_text(context_content)

        engine = ReviewEngine(config)
        result = engine._get_project_context()

        assert "**Project Context:**" in result
        assert context_content in result

    def test_get_project_context_with_disabled_context(self, chdir_tmp) -> None:
        """Test getting project context when disabled."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            enable_project_context=False,
        )

        # Create a project context file (should be ignored)
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()
        context_file = project_dir / "project.md"
        context_file.write_text("This is project context.")

        engine = ReviewEngine(config)
        result = engine._get_project_context()

        assert "**Project Context:**" not in result
        assert "This is project context." not in result

    def test_get_project_context_with_language_hint_and_context(
        self, chdir_tmp
    ) -> None:
        """Test getting project context with both language hint and project context."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            enable_project_context=True,
            language_hint="Python",
        )

        # Create a project context file
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()
        context_file = project_dir / "project.md"
        context_content = "Python web application"
        context_file.write_text(context_content)

        engine = ReviewEngine(config)
        result = engine._get_project_context()

        assert "Primary Language: Python" in result
        assert "**Project Context:**" in result
        assert context_content in result

    def test_load_project_context_uses_config_path(self, chdir_tmp) -> None:
        """Test that context loading uses the configured path."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            project_context_file="custom-context.md",
        )

        # Create context file with custom name
        context_content = "Custom context file content"
        context_file = chdir_tmp / "custom-context.md"
        context_file.write_text(context_content)

        engine = ReviewEngine(config)
        result = engine._load_project_context_file()

        assert result == context_content

    def test_load_project_context_custom_subdirectory_path(self, chdir_tmp) -> None:
        """Test that context loading works with custom paths in subdirectories."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            project_context_file="docs/ai-context.md",
        )

        # Create context file in custom subdirectory
        docs_dir = chdir_tmp / "docs"
        docs_dir.mkdir()
        context_content = "AI context in docs directory"
        context_file = docs_dir / "ai-context.md"
        context_file.write_text(context_content)

        engine = ReviewEngine(config)
        result = engine._load_project_context_file()

        assert result == context_content
