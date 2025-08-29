"""Tests for review engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import AIProvider, Config
from ai_code_review.models.gitlab import (
    MergeRequestCommit,
    MergeRequestData,
    MergeRequestDiff,
    MergeRequestInfo,
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
    def sample_mr_data(self) -> MergeRequestData:
        """Sample merge request data."""
        info = MergeRequestInfo(
            id=123,
            iid=456,
            title="Test MR",
            description="Test description",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="opened",
            web_url="https://gitlab.com/test/-/merge_requests/456",
        )

        diffs = [
            MergeRequestDiff(
                file_path="src/test.py",
                diff="@@ -1,3 +1,3 @@\n-old_function()\n+new_function()",
            )
        ]

        commits = [
            MergeRequestCommit(
                id="abc123",
                title="Test feature implementation",
                message="Test feature implementation\n\nAdds new functionality for testing.\n- Implements core logic\n- Updates documentation",
                author_name="Test Author",
                author_email="test@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc123",
            )
        ]

        return MergeRequestData(info=info, diffs=diffs, commits=commits)

    def test_engine_initialization(self, test_config: Config) -> None:
        """Test review engine initialization."""
        engine = ReviewEngine(test_config)

        assert engine.config == test_config
        assert isinstance(engine.gitlab_client, object)
        assert engine.ai_provider.provider_name == "ollama"

    def test_unsupported_ai_provider(self) -> None:
        """Test error handling for unsupported AI provider."""
        config = Config(
            gitlab_token="test_token",
            ai_provider=AIProvider.OPENAI,  # Not yet implemented
        )

        with pytest.raises(AIProviderError, match="not yet implemented"):
            ReviewEngine(config)

    @pytest.mark.asyncio
    async def test_generate_review_dry_run(
        self, dry_run_config: Config, sample_mr_data: MergeRequestData
    ) -> None:
        """Test review generation in dry run mode."""
        engine = ReviewEngine(dry_run_config)

        with patch.object(
            engine.gitlab_client, "get_merge_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_mr_data

            result = await engine.generate_review("test/project", 123)

            assert isinstance(result, ReviewResult)
            assert isinstance(result.review, CodeReview)
            assert "[DRY RUN]" in result.review.general_feedback

            # Should include summary by default
            assert result.summary is not None
            assert isinstance(result.summary, ReviewSummary)
            assert "[DRY RUN]" in result.summary.title

    @pytest.mark.asyncio
    async def test_generate_review_without_summary(
        self, dry_run_config: Config, sample_mr_data: MergeRequestData
    ) -> None:
        """Test review generation without summary."""
        engine = ReviewEngine(dry_run_config)

        with patch.object(
            engine.gitlab_client, "get_merge_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_mr_data

            result = await engine.generate_review(
                "test/project", 123, include_summary=False
            )

            assert isinstance(result, ReviewResult)
            assert result.summary is None

    @pytest.mark.asyncio
    async def test_generate_review_with_ai(
        self, test_config: Config, sample_mr_data: MergeRequestData
    ) -> None:
        """Test review generation with AI provider."""
        engine = ReviewEngine(test_config)

        # Mock GitLab client
        with patch.object(
            engine.gitlab_client, "get_merge_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_mr_data

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

                    assert isinstance(result, ReviewResult)
                    # The entire LLM response should be used directly
                    assert "AI generated review feedback" in result.review.general_feedback
                    assert "## AI Code Review" in result.review.general_feedback
                    assert "### 📋 MR Summary" in result.review.general_feedback
                    assert "### Detailed Code Review" in result.review.general_feedback
                    assert result.summary is not None
                    assert result.summary.title == "Test MR"

    @pytest.mark.asyncio
    async def test_generate_review_ai_unavailable(
        self, test_config: Config, sample_mr_data: MergeRequestData
    ) -> None:
        """Test error handling when AI provider is unavailable."""
        engine = ReviewEngine(test_config)

        with patch.object(
            engine.gitlab_client, "get_merge_request_data"
        ) as mock_gitlab:
            mock_gitlab.return_value = sample_mr_data

            with patch.object(engine.ai_provider, "is_available", return_value=False):
                with pytest.raises(AIProviderError, match="is not available"):
                    await engine.generate_review("test/project", 123)

    @pytest.mark.asyncio
    async def test_generate_review_gitlab_error(self, test_config: Config) -> None:
        """Test error handling for GitLab API errors."""
        engine = ReviewEngine(test_config)

        with patch.object(
            engine.gitlab_client, "get_merge_request_data"
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
        self, test_config: Config, sample_mr_data: MergeRequestData
    ) -> None:
        """Test diff formatting for AI processing."""
        engine = ReviewEngine(test_config)

        formatted = engine._format_diffs_for_ai(sample_mr_data)

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

    def test_get_project_context_without_hint(self, test_config: Config) -> None:
        """Test project context without language hint."""
        test_config.language_hint = None
        engine = ReviewEngine(test_config)

        context = engine._get_project_context()

        assert "No additional project context available" in context
