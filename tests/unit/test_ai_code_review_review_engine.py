"""Tests for review engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

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
from tests.conftest import create_gitpython_mock

# Mock GitPython completely to avoid git binary requirement in CI
with patch.dict("sys.modules", {"git": create_gitpython_mock()}):
    from ai_code_review.core.review_engine import ReviewEngine


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
        # Mock review chain BEFORE importing ReviewEngine to fix timing issues
        with patch(
            "ai_code_review.core.review_engine.create_review_chain"
        ) as mock_review_chain:
            # Import ReviewEngine INSIDE the patch to ensure mock is effective
            # NOTE: This local import pattern is necessary because Python's import system
            # resolves `from X import Y` references at import time, not at usage time.
            # By importing inside the patch context, we ensure the mock is active
            # when the module's import references are established.
            from ai_code_review.core.review_engine import ReviewEngine

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

            # Correctly configure AsyncMock for ainvoke method
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            mock_review_chain.return_value = mock_chain

            # Create engine AFTER mock is configured
            engine = ReviewEngine(test_config)

            # Mock GitLab client
            with patch.object(
                engine.platform_client, "get_pull_request_data"
            ) as mock_gitlab:
                mock_gitlab.return_value = sample_pr_data

                # Mock AI provider
                with patch.object(
                    engine.ai_provider, "is_available", return_value=True
                ):
                    result = await engine.generate_review("test/project", 123)

            # Verify create_review_chain was called with config
            mock_review_chain.assert_called_once_with(
                engine.ai_provider.client, engine.config
            )

            assert isinstance(result, ReviewResult)
            # The entire LLM response should be used directly
            assert "AI generated review feedback" in result.review.general_feedback
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
        # Mock review chain BEFORE importing ReviewEngine to fix timing issues
        with patch(
            "ai_code_review.core.review_engine.create_review_chain"
        ) as mock_review_chain:
            # Import ReviewEngine INSIDE the patch to ensure mock is effective
            # NOTE: This local import pattern is necessary because Python's import system
            # resolves `from X import Y` references at import time, not at usage time.
            # By importing inside the patch context, we ensure the mock is active
            # when the module's import references are established.
            from ai_code_review.core.review_engine import ReviewEngine

            # Mock response without MR Summary section
            mock_response = """## AI Code Review

### Detailed Code Review

AI generated review feedback for test purposes. The code changes appear well-structured and follow good practices.

### ✅ Summary
- **Overall Assessment:** Good code quality with minor suggestions
- **Priority Issues:** None identified
- **Minor Suggestions:** Consider adding more comprehensive tests"""

            # Correctly configure AsyncMock for ainvoke method
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            mock_review_chain.return_value = mock_chain

            # Create config with MR Summary disabled, but NOT dry_run (use ollama to avoid API key requirements)
            config = Config(
                gitlab_token="test-token",
                ai_provider="ollama",
                include_mr_summary=False,
            )
            engine = ReviewEngine(config)

            with patch.object(
                engine.platform_client, "get_pull_request_data"
            ) as mock_gitlab:
                mock_gitlab.return_value = sample_pr_data

                # Mock AI provider
                with patch.object(
                    engine.ai_provider, "is_available", return_value=True
                ):
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
        config = Config(
            gitlab_token="test-token",
            ai_provider="ollama",
            include_mr_summary=False,
            dry_run=True,
        )
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

    @pytest.mark.parametrize(
        "context_path, content",
        [
            ("custom-context.md", "Custom context file content"),
            ("docs/ai-context.md", "AI context in docs directory"),
            ("config/project-info.txt", "Project info in config directory"),
            ("README.md", "README content as context"),
        ],
    )
    def test_load_project_context_uses_custom_config_path(
        self, chdir_tmp, context_path: str, content: str
    ) -> None:
        """Test that context loading uses the configured custom path."""

        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            project_context_file=context_path,
        )

        # Create context file at custom path (create directory if needed)
        context_file = chdir_tmp / context_path
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text(content)

        engine = ReviewEngine(config)
        result = engine._load_project_context_file()

        assert result == content

    def test_create_platform_client_factory_methods(self) -> None:
        """Test platform client factory creation - hits lines 48-57."""
        from ai_code_review.models.config import PlatformProvider

        # Test GitHub client creation
        github_config = Config(
            github_token="test_token",
            platform_provider=PlatformProvider.GITHUB,
            ai_provider=AIProvider.OLLAMA,
        )

        github_engine = ReviewEngine(github_config)
        assert github_engine.platform_client is not None
        assert github_engine.platform_client.get_platform_name() == "github"

        # Test LOCAL client creation (mock to avoid GitPython)
        local_config = Config(
            platform_provider=PlatformProvider.LOCAL,
            ai_provider=AIProvider.OLLAMA,
        )

        # Mock the entire _create_platform_client method for LOCAL to avoid GitPython
        with patch.object(ReviewEngine, "_create_platform_client") as mock_create:
            mock_local_client = Mock()
            mock_local_client.get_platform_name.return_value = "local"
            mock_create.return_value = mock_local_client

            local_engine = ReviewEngine(local_config)
            assert local_engine.platform_client is not None
            assert local_engine.platform_client.get_platform_name() == "local"

    def test_create_platform_client_unsupported_provider(self) -> None:
        """Test unsupported platform provider raises error - hits lines 56-60."""
        # Create a mock config with an invalid platform provider that looks like enum
        mock_config = Mock()
        mock_provider = Mock()
        mock_provider.value = "UNSUPPORTED"
        mock_config.platform_provider = mock_provider  # Mock enum-like object

        with pytest.raises(AIProviderError, match="Platform provider .* not supported"):
            ReviewEngine(mock_config)

    @patch("ai_code_review.core.review_engine.create_review_chain")
    async def test_generate_review_exception_handling(
        self, mock_chain: Mock, test_config: Config
    ) -> None:
        """Test _generate_review exception handling - hits lines 274-278."""
        # Mock AI provider that raises exception
        mock_ai_provider = Mock()
        mock_ai_provider.provider_name = "test_provider"
        mock_ai_provider.is_available.return_value = True  # Sync method
        mock_ai_provider.generate_review = AsyncMock(
            side_effect=Exception("AI service down")
        )

        # Mock platform client
        mock_platform_client = Mock()
        mock_platform_client.get_platform_name.return_value = "test_platform"

        # Mock review chain creation
        mock_chain.return_value = Mock()

        engine = ReviewEngine(test_config)
        engine.ai_provider = mock_ai_provider
        engine.platform_client = mock_platform_client

        # Mock PR data
        mock_pr_data = Mock()
        mock_pr_data.info = Mock()
        mock_pr_data.diffs = []

        # Should raise AIProviderError with provider context - hits lines 274-278
        with pytest.raises(
            AIProviderError, match="Failed to generate review with test_provider"
        ):
            await engine._generate_review_response(
                mock_pr_data, "test context", 100, 500
            )

    def test_load_project_context_file_exception_handling(
        self, test_config: Config, chdir_tmp
    ) -> None:
        """Test _load_project_context_file exception handling - hits lines 385-391."""

        # Create directory but with permission issues
        project_dir = chdir_tmp / ".ai_review"
        project_dir.mkdir()

        engine = ReviewEngine(test_config)

        # Mock file operations to raise exception
        with patch(
            "pathlib.Path.read_text", side_effect=PermissionError("Access denied")
        ):
            result = engine._load_project_context_file()

            # Should handle exception gracefully and return None - hits lines 385-391
            assert result is None

    def test_anthropic_provider_creation(self) -> None:
        """Test Anthropic provider creation - hits lines 70-73."""
        config = Config(
            gitlab_token="test-token",
            ai_api_key="test_key",  # Use generic ai_api_key field
            ai_provider=AIProvider.ANTHROPIC,
        )

        engine = ReviewEngine(config)
        assert engine.ai_provider is not None
        assert engine.ai_provider.provider_name == "anthropic"

    def test_gemini_provider_creation(self) -> None:
        """Test Gemini provider creation - hits lines 67-69."""
        config = Config(
            gitlab_token="test-token",
            ai_api_key="test_key",  # Use generic ai_api_key field
            ai_provider=AIProvider.GEMINI,
        )

        engine = ReviewEngine(config)
        assert engine.ai_provider is not None
        assert engine.ai_provider.provider_name == "gemini"

    # Note: Removed extremely dangerous test that patched len() builtin
    # It was causing real Ollama connections and 14+ second execution times

    def test_calculate_context_parameters_small_diff_large_context_triggers_auto_big_diffs(
        self, test_config: Config
    ) -> None:
        """Test small diff with large project context triggers auto_big_diffs."""
        engine = ReviewEngine(test_config)

        # Small diff (1000 chars) + large context (60000 chars) + system prompt (500)
        # Total: 61500 chars > AUTO_BIG_DIFFS_THRESHOLD_CHARS (60000)
        original_total_chars = 1000
        project_context_chars = 60000
        system_prompt_chars = 500
        manual_big_diffs = False

        total_content_chars, context_window_size, auto_big_diffs = (
            engine._calculate_context_parameters(
                original_total_chars,
                project_context_chars,
                system_prompt_chars,
                manual_big_diffs,
            )
        )

        assert total_content_chars == 61500
        assert auto_big_diffs is True
        assert context_window_size >= 16384  # Should get larger context window

    def test_calculate_context_parameters_large_diff_no_context_triggers_auto_big_diffs(
        self, test_config: Config
    ) -> None:
        """Test large diff with no project context triggers auto_big_diffs."""
        engine = ReviewEngine(test_config)

        # Large diff (61000 chars) + no context (0 chars) + system prompt (500)
        # Total: 61500 chars > AUTO_BIG_DIFFS_THRESHOLD_CHARS (60000)
        original_total_chars = 61000
        project_context_chars = 0
        system_prompt_chars = 500
        manual_big_diffs = False

        total_content_chars, context_window_size, auto_big_diffs = (
            engine._calculate_context_parameters(
                original_total_chars,
                project_context_chars,
                system_prompt_chars,
                manual_big_diffs,
            )
        )

        assert total_content_chars == 61500
        assert auto_big_diffs is True
        assert context_window_size >= 16384

    def test_calculate_context_parameters_below_threshold_does_not_trigger_auto_big_diffs(
        self, test_config: Config
    ) -> None:
        """Test content below threshold does NOT trigger auto_big_diffs."""
        engine = ReviewEngine(test_config)

        # Total just below threshold: 59500 chars < AUTO_BIG_DIFFS_THRESHOLD_CHARS (60000)
        original_total_chars = 50000
        project_context_chars = 9000
        system_prompt_chars = 500
        manual_big_diffs = False

        total_content_chars, context_window_size, auto_big_diffs = (
            engine._calculate_context_parameters(
                original_total_chars,
                project_context_chars,
                system_prompt_chars,
                manual_big_diffs,
            )
        )

        assert total_content_chars == 59500
        assert auto_big_diffs is False
        assert context_window_size == 16384  # Default context window

    def test_calculate_context_parameters_manual_big_diffs_prevents_auto_activation(
        self, test_config: Config
    ) -> None:
        """Test manual big_diffs prevents auto activation even above threshold."""
        engine = ReviewEngine(test_config)

        # Content above threshold but manual_big_diffs=True should prevent auto activation
        original_total_chars = 50000
        project_context_chars = 15000
        system_prompt_chars = 500
        manual_big_diffs = True  # Manually enabled

        total_content_chars, context_window_size, auto_big_diffs = (
            engine._calculate_context_parameters(
                original_total_chars,
                project_context_chars,
                system_prompt_chars,
                manual_big_diffs,
            )
        )

        assert total_content_chars == 65500  # Above threshold
        assert auto_big_diffs is False  # Should not auto-activate when manually set
        assert context_window_size >= 16384

    def test_calculate_context_parameters_calls_adaptive_context_size(
        self, test_config: Config
    ) -> None:
        """Test that _calculate_context_parameters correctly calls get_adaptive_context_size."""
        engine = ReviewEngine(test_config)

        # Mock AI provider with get_adaptive_context_size
        expected_context_size = 32768
        mock_get_adaptive = Mock(return_value=expected_context_size)
        engine.ai_provider.get_adaptive_context_size = mock_get_adaptive

        # Test parameters
        original_total_chars = 25000
        project_context_chars = 10000
        system_prompt_chars = 500
        manual_big_diffs = False

        total_content_chars, context_window_size, auto_big_diffs = (
            engine._calculate_context_parameters(
                original_total_chars,
                project_context_chars,
                system_prompt_chars,
                manual_big_diffs,
            )
        )

        # Verify get_adaptive_context_size was called with correct parameters
        mock_get_adaptive.assert_called_once_with(
            original_total_chars, project_context_chars, system_prompt_chars
        )

        # Verify returned values
        assert context_window_size == expected_context_size
        assert total_content_chars == 35500  # 25000 + 10000 + 500
        assert auto_big_diffs is False  # Below threshold (60000)
