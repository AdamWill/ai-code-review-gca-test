"""Tests for skip review mechanism."""

from __future__ import annotations

import pytest

from ai_code_review.core.review_engine import ReviewEngine
from ai_code_review.models.config import AIProvider, Config, SkipReviewConfig
from ai_code_review.models.platform import (
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.utils.exceptions import ReviewSkippedError


class TestSkipReviewConfig:
    """Test SkipReviewConfig validation and defaults."""

    def test_default_config(self) -> None:
        """Test default skip review configuration."""
        config = SkipReviewConfig()

        assert config.enabled is True
        assert config.skip_dependency_updates is True
        assert config.skip_documentation_only is False  # Conservative default
        assert config.skip_bot_authors is True

        # Check default keywords
        assert "[skip ai-review]" in config.keywords
        assert "[no-review]" in config.keywords
        assert "[bot]" in config.keywords

        # Check default patterns include dependency updates
        patterns_str = " ".join(config.patterns)
        assert "deps" in patterns_str
        assert "bump" in patterns_str

        # Check default bot authors
        assert "renovate[bot]" in config.bot_authors
        assert "dependabot[bot]" in config.bot_authors

    def test_pattern_validation(self) -> None:
        """Test that invalid regex patterns are rejected."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            SkipReviewConfig(patterns=["[invalid_regex"])

    def test_disabled_config(self) -> None:
        """Test skip review can be disabled."""
        config = SkipReviewConfig(enabled=False)
        assert config.enabled is False


class TestSkipReviewDetection:
    """Test skip review detection logic in ReviewEngine."""

    @pytest.fixture
    def mock_pr_data(self) -> PullRequestData:
        """Create mock PR data for testing."""
        return PullRequestData(
            info=PullRequestInfo(
                id=123,
                number=123,
                title="feat: add user authentication",
                description="Implements user login and registration",
                author="developer@company.com",
                source_branch="feature/auth",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/123",
            ),
            diffs=[
                PullRequestDiff(
                    file_path="src/auth.py",
                    diff="+ def login():\n+     pass",
                    new_file=True,
                    deleted_file=False,
                    renamed_file=False,
                )
            ],
            commits=[],
        )

    @pytest.fixture
    def skip_config(self) -> Config:
        """Create config with skip review enabled."""
        return Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirements
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(enabled=True),
        )

    @pytest.fixture
    def disabled_skip_config(self) -> Config:
        """Create config with skip review disabled."""
        return Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirements
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(enabled=False),
        )

    def test_skip_disabled(
        self, disabled_skip_config: Config, mock_pr_data: PullRequestData
    ) -> None:
        """Test that skip detection is disabled when configured."""
        engine = ReviewEngine(disabled_skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mock_pr_data)

        assert should_skip is False
        assert reason is None
        assert trigger is None

    def test_no_skip_for_regular_pr(
        self, skip_config: Config, mock_pr_data: PullRequestData
    ) -> None:
        """Test that regular PRs are not skipped."""
        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mock_pr_data)

        assert should_skip is False
        assert reason is None
        assert trigger is None

    @pytest.mark.parametrize(
        "title,expected_skip",
        [
            # Renovate dependency updates
            ("chore(deps): update dependency express to v4.18.2", True),
            ("build(deps): bump lodash from 4.17.20 to 4.17.21", True),
            ("ci(deps): update actions/checkout to v4", True),
            ("feat(deps): add new dependency for feature", True),
            ("fix(deps): resolve vulnerability in package", True),
            # Version releases
            ("chore: release v1.2.3", True),
            ("release: version 2.0.0", True),
            ("bump: version 1.0.1", True),
            # Auto-generated changes - NOTE: [automated] is keyword, not pattern
            (
                "[automated] update translations",
                "keyword",
            ),  # Special case: detected as keyword
            ("auto update documentation", True),
            # Documentation only (should not skip by default)
            (
                "docs: update README",
                False,
            ),  # skip_documentation_only is False by default
            ("docs(api): add endpoint documentation", False),
            # False positives to avoid
            ("feat: implement dependency injection", False),
            ("fix: resolve deps loading issue", False),
            ("chore: clean up dependencies in code", False),
            ("Add bump to shopping cart feature", False),
        ],
    )
    def test_pattern_detection(
        self,
        skip_config: Config,
        mock_pr_data: PullRequestData,
        title: str,
        expected_skip: bool,
    ) -> None:
        """Test pattern-based skip detection."""
        # Update PR title
        mock_pr_data.info.title = title

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mock_pr_data)

        if expected_skip == "keyword":
            # Special case: [automated] is detected as keyword, not pattern
            assert should_skip is True
            assert reason == "keyword"
            assert trigger in skip_config.skip_review.keywords
        elif expected_skip:
            assert should_skip is True
            assert reason == "pattern"
            assert trigger in skip_config.skip_review.patterns
        else:
            assert should_skip is False

    @pytest.mark.parametrize(
        "author,expected_skip",
        [
            ("renovate[bot]", True),
            ("dependabot[bot]", True),
            ("github-actions[bot]", True),
            ("gitlab-ci-token", True),
            ("developer@company.com", False),
            ("bot-user", False),  # Partial match should not trigger
            ("user-renovate", False),  # Partial match should not trigger
        ],
    )
    def test_bot_author_detection(
        self,
        skip_config: Config,
        mock_pr_data: PullRequestData,
        author: str,
        expected_skip: bool,
    ) -> None:
        """Test bot author-based skip detection."""
        # Update PR author
        mock_pr_data.info.author = author

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mock_pr_data)

        if expected_skip:
            assert should_skip is True
            assert reason == "bot_author"
            assert trigger in skip_config.skip_review.bot_authors
        else:
            assert should_skip is False

    @pytest.mark.parametrize(
        "title,description,keyword,expected_skip",
        [
            # Keywords in title
            (
                "hotfix: critical security update [skip ai-review]",
                "",
                "[skip ai-review]",
                True,
            ),
            ("feat: new feature [no-review]", "", "[no-review]", True),
            ("Bot update [bot]", "", "[bot]", True),
            # Keywords in description
            (
                "hotfix: security update",
                "This is urgent [skip ai-review]",
                "[skip ai-review]",
                True,
            ),
            ("feat: new feature", "Automated change [automated]", "[automated]", True),
            # Case insensitive
            ("FEAT: NEW FEATURE [SKIP AI-REVIEW]", "", "[skip ai-review]", True),
            ("fix: bug", "AUTOMATED UPDATE [BOT]", "[bot]", True),
            # No match
            ("feat: add skip functionality", "This adds skip review", "", False),
        ],
    )
    def test_keyword_detection(
        self,
        skip_config: Config,
        mock_pr_data: PullRequestData,
        title: str,
        description: str,
        keyword: str,
        expected_skip: bool,
    ) -> None:
        """Test keyword-based skip detection."""
        # Update PR info
        mock_pr_data.info.title = title
        mock_pr_data.info.description = description

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mock_pr_data)

        if expected_skip:
            assert should_skip is True
            assert reason == "keyword"
            assert trigger == keyword
        else:
            assert should_skip is False

    def test_documentation_only_detection_enabled(self, skip_config: Config) -> None:
        """Test documentation-only detection when enabled."""
        # Enable documentation-only skipping
        skip_config.skip_review.skip_documentation_only = True

        # Create PR with only documentation files
        doc_pr_data = PullRequestData(
            info=PullRequestInfo(
                id=456,
                number=456,
                title="docs: update API documentation",
                description="Updates API docs",
                author="developer@company.com",
                source_branch="docs/api",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/456",
            ),
            diffs=[
                PullRequestDiff(
                    file_path="docs/api.md",
                    diff="+ ## New API endpoint",
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                ),
                PullRequestDiff(
                    file_path="README.md",
                    diff="+ Updated installation instructions",
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                ),
            ],
            commits=[],
        )

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(doc_pr_data)

        assert should_skip is True
        assert reason == "documentation_pattern"  # Changed from documentation_only
        assert trigger in skip_config.skip_review.documentation_patterns

    def test_documentation_only_mixed_files(self, skip_config: Config) -> None:
        """Test that mixed doc/code changes are not skipped."""
        # Enable documentation-only skipping
        skip_config.skip_review.skip_documentation_only = True

        # Create PR with mixed documentation and code files
        mixed_pr_data = PullRequestData(
            info=PullRequestInfo(
                id=789,
                number=789,
                title="feat: update API docs and fix typo",  # Changed to avoid doc pattern match
                description="Updates docs and fixes code typo",
                author="developer@company.com",
                source_branch="docs/fix",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/789",
            ),
            diffs=[
                PullRequestDiff(
                    file_path="docs/api.md",
                    diff="+ ## New API endpoint",
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                ),
                PullRequestDiff(
                    file_path="src/main.py",  # Non-documentation file
                    diff="- typo = True\n+ typo = False",
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                ),
            ],
            commits=[],
        )

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(mixed_pr_data)

        # Should NOT skip because there are non-documentation files
        assert should_skip is False

    def test_priority_order(self, skip_config: Config) -> None:
        """Test that detection stops at first match (keyword has priority)."""
        # Create PR that matches both keyword and pattern
        priority_pr_data = PullRequestData(
            info=PullRequestInfo(
                id=999,
                number=999,
                title="chore(deps): update dependency [skip ai-review]",  # Matches both
                description="",
                author="renovate[bot]",  # Also matches bot author
                source_branch="deps/update",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/999",
            ),
            diffs=[
                PullRequestDiff(
                    file_path="package.json",
                    diff='+ "express": "^4.18.2"',
                    new_file=False,
                    deleted_file=False,
                    renamed_file=False,
                )
            ],
            commits=[],
        )

        engine = ReviewEngine(skip_config)
        should_skip, reason, trigger = engine.should_skip_review(priority_pr_data)

        # Should match keyword first (checked first in logic)
        assert should_skip is True
        assert reason == "keyword"
        assert trigger == "[skip ai-review]"


class TestSkipReviewIntegration:
    """Test integration of skip review with generate_review method."""

    @pytest.mark.asyncio
    async def test_generate_review_skip_raises_exception(self) -> None:
        """Test that generate_review raises ReviewSkippedError when skip conditions are met."""
        config = Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,  # Use Ollama to avoid API key requirements
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(enabled=True),
        )

        engine = ReviewEngine(config)

        # Mock platform client to return skip-triggering data
        skip_pr_data = PullRequestData(
            info=PullRequestInfo(
                id=555,
                number=555,
                title="chore(deps): update dependency express",
                description="",
                author="renovate[bot]",
                source_branch="deps/express",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/555",
            ),
            diffs=[],
            commits=[],
        )

        # Mock the platform client method
        async def mock_get_pull_request_data(
            project_id: str, pr_number: int
        ) -> PullRequestData:
            return skip_pr_data

        engine.platform_client.get_pull_request_data = mock_get_pull_request_data

        # Should raise ReviewSkippedError
        with pytest.raises(ReviewSkippedError) as exc_info:
            await engine.generate_review("test/project", 123)

        assert exc_info.value.reason == "pattern"  # Matches dependency pattern
        assert "deps" in str(exc_info.value)


class TestSkipReviewCLIFlags:
    """Test CLI flag handling for skip review."""

    def test_no_skip_detection_flag(self) -> None:
        """Test --no-skip-detection flag disables skip detection."""
        cli_args = {
            "no_skip_detection": True,
            "gitlab_token": "test-token",
            "ai_provider": "ollama",
            "ai_model": "qwen2.5-coder:7b",
            "dry_run": True,
        }

        config = Config.from_cli_args(cli_args)

        assert config.skip_review.enabled is False

    def test_skip_detection_enabled_by_default(self) -> None:
        """Test that skip detection is enabled by default."""
        cli_args = {
            "gitlab_token": "test-token",
            "ai_provider": "ollama",
            "ai_model": "qwen2.5-coder:7b",
            "dry_run": True,
        }

        config = Config.from_cli_args(cli_args)

        assert config.skip_review.enabled is True


class TestDraftPRSkipping:
    """Test draft PR/MR skipping functionality."""

    def test_draft_pr_skipped_when_enabled(self) -> None:
        """Test that draft PRs are skipped when skip_draft_prs is enabled."""
        pr_data = PullRequestData(
            info=PullRequestInfo(
                id=123,
                number=123,
                title="feat: work in progress feature",
                description="",
                author="developer",
                source_branch="feature",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/123",
                draft=True,  # Draft PR
            ),
            diffs=[PullRequestDiff(file_path="src/feature.py", diff="mock diff")],
            commits=[],
        )

        config = Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(enabled=True, skip_draft_prs=True),
        )
        engine = ReviewEngine(config)

        should_skip, reason, trigger = engine.should_skip_review(pr_data)

        assert should_skip is True
        assert reason == "draft"
        assert trigger == "pull/merge request is in draft mode"

    def test_draft_pr_not_skipped_when_disabled(self) -> None:
        """Test that draft PRs are NOT skipped when skip_draft_prs is disabled."""
        pr_data = PullRequestData(
            info=PullRequestInfo(
                id=123,
                number=123,
                title="feat: work in progress feature",
                description="",
                author="developer",
                source_branch="feature",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/123",
                draft=True,  # Draft PR
            ),
            diffs=[PullRequestDiff(file_path="src/feature.py", diff="mock diff")],
            commits=[],
        )

        config = Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(
                enabled=True, skip_draft_prs=False
            ),  # Disabled
        )
        engine = ReviewEngine(config)

        should_skip, reason, trigger = engine.should_skip_review(pr_data)

        assert should_skip is False
        assert reason is None
        assert trigger is None

    def test_normal_pr_not_affected_by_draft_logic(self) -> None:
        """Test that normal (non-draft) PRs are not affected by draft skipping logic."""
        pr_data = PullRequestData(
            info=PullRequestInfo(
                id=123,
                number=123,
                title="feat: ready feature",
                description="",
                author="developer",
                source_branch="feature",
                target_branch="main",
                state="open",
                web_url="https://example.com/pr/123",
                draft=False,  # Normal PR
            ),
            diffs=[PullRequestDiff(file_path="src/feature.py", diff="mock diff")],
            commits=[],
        )

        config = Config(
            gitlab_token="test-token",
            ai_provider=AIProvider.OLLAMA,
            ai_model="qwen2.5-coder:7b",
            dry_run=True,
            skip_review=SkipReviewConfig(enabled=True, skip_draft_prs=True),
        )
        engine = ReviewEngine(config)

        should_skip, reason, trigger = engine.should_skip_review(pr_data)

        # Normal PRs should not be skipped by draft logic
        assert should_skip is False
        assert reason is None
        assert trigger is None

    def test_default_draft_config(self) -> None:
        """Test that skip_draft_prs is enabled by default."""
        config = SkipReviewConfig()
        assert config.skip_draft_prs is True  # Should be enabled by default
