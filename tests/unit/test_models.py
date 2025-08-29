"""Tests for data models."""

from __future__ import annotations

from ai_code_review.models.config import AIProvider, Config
from ai_code_review.models.gitlab import (
    MergeRequestData,
    MergeRequestDiff,
    MergeRequestInfo,
)
from ai_code_review.models.review import CodeReview, FileReview, ReviewResult


class TestConfig:
    """Test configuration model."""

    def test_config_creation_with_minimal_required_fields(self) -> None:
        """Test creating config with only required fields."""
        config = Config(gitlab_token="test_token")

        assert config.gitlab_token == "test_token"
        assert config.gitlab_url == "https://gitlab.com"
        assert config.ai_provider == AIProvider.OLLAMA
        assert config.ai_model == "qwen2.5-coder:7b"
        assert config.ai_api_key is None

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = Config(
            gitlab_token="custom_token",
            gitlab_url="https://custom-gitlab.com",
            ai_provider=AIProvider.GEMINI,
            ai_model="gemini-pro",
            ai_api_key="test_api_key",
        )

        assert config.gitlab_token == "custom_token"
        assert config.gitlab_url == "https://custom-gitlab.com"
        assert config.ai_provider == AIProvider.GEMINI
        assert config.ai_model == "gemini-pro"
        assert config.ai_api_key == "test_api_key"

    def test_dry_run_defaults_false(self) -> None:
        """Test that dry_run defaults to False."""
        config = Config(gitlab_token="test_token")
        assert config.dry_run is False


class TestGitLabModels:
    """Test GitLab data models."""

    def test_merge_request_diff(self) -> None:
        """Test MergeRequestDiff model."""
        diff = MergeRequestDiff(
            file_path="src/test.py", diff="@@ -1,3 +1,3 @@\n-old line\n+new line"
        )

        assert diff.file_path == "src/test.py"
        assert diff.new_file is False
        assert diff.renamed_file is False
        assert diff.deleted_file is False

    def test_merge_request_info(self) -> None:
        """Test MergeRequestInfo model."""
        info = MergeRequestInfo(
            id=123,
            iid=456,
            title="Test MR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="opened",
            web_url="https://gitlab.com/test/test/-/merge_requests/456",
        )

        assert info.id == 123
        assert info.iid == 456
        assert info.description is None

    def test_merge_request_data_properties(self) -> None:
        """Test MergeRequestData calculated properties."""
        diffs = [
            MergeRequestDiff(file_path="file1.py", diff="short diff"),
            MergeRequestDiff(file_path="file2.py", diff="longer diff content"),
        ]

        info = MergeRequestInfo(
            id=123,
            iid=456,
            title="Test",
            source_branch="feature",
            target_branch="main",
            author="user",
            state="opened",
            web_url="https://gitlab.com/test/-/merge_requests/456",
        )

        mr_data = MergeRequestData(info=info, diffs=diffs)

        assert mr_data.file_count == 2
        assert mr_data.total_chars == len("short diff") + len("longer diff content")


class TestReviewModels:
    """Test review data models."""

    def test_review_result_to_markdown(self) -> None:
        """Test converting ReviewResult to markdown format (MVP simplified version)."""
        # Create a simple review
        file_review = FileReview(
            file_path="test.py", summary="Test review", comments=[]
        )

        review = CodeReview(
            general_feedback="Good code overall",
            file_reviews=[file_review],
            overall_assessment="Looks good",
            priority_issues=["Fix issue X"],
            minor_suggestions=["Minor fix Y"],
        )

        result = ReviewResult(review=review)
        markdown = result.to_markdown()

        # Test MVP simplified markdown output
        assert "### General Feedback" in markdown
        assert "Good code overall" in markdown
        assert "### ✅ Summary" in markdown
        assert "**Overall Assessment:** Looks good" in markdown
        assert "**Priority Issues:** Fix issue X" in markdown
        assert "**Minor Suggestions:** Minor fix Y" in markdown
