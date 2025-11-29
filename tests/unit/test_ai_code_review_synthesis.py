"""Tests for synthesis functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_code_review.models.config import (
    _DEFAULT_SYNTHESIS_MODELS,
    AIProvider,
    Config,
    get_default_model_for_provider,
    get_default_synthesis_model_for_provider,
)
from ai_code_review.models.platform import (
    PullRequestCommit,
    PullRequestData,
    PullRequestInfo,
    Review,
    ReviewComment,
)
from ai_code_review.utils.prompts import (
    _format_commit_messages,
    _format_reviews_and_comments,
    create_synthesis_chain,
    create_synthesis_prompt,
)


def test_synthesis_model_defaults():
    """Test that synthesis models use constants."""
    for provider in AIProvider:
        synthesis_model = get_default_synthesis_model_for_provider(provider)
        assert synthesis_model == _DEFAULT_SYNTHESIS_MODELS[provider]
        # Verify it's different from main model for cloud providers
        if provider != AIProvider.OLLAMA:
            main_model = get_default_model_for_provider(provider)
            # Synthesis should generally be faster/cheaper
            assert synthesis_model != main_model


def test_config_get_synthesis_model_default():
    """Test Config.get_synthesis_model() uses constants."""
    # Use OLLAMA to avoid API key requirements
    config = Config(ai_provider=AIProvider.OLLAMA, gitlab_token="test")
    # get_synthesis_model() should return the provider's default
    assert config.get_synthesis_model() == _DEFAULT_SYNTHESIS_MODELS[AIProvider.OLLAMA]


def test_config_get_synthesis_model_custom():
    """Test custom synthesis model override."""
    custom_model = "custom-synthesis-model"
    # Use OLLAMA to avoid API key requirements
    config = Config(
        ai_provider=AIProvider.OLLAMA,
        synthesis_model=custom_model,
        gitlab_token="test",
    )
    assert config.get_synthesis_model() == custom_model


def test_synthesis_model_selection_by_provider():
    """Test synthesis model selection uses constants."""
    # Only test OLLAMA to avoid API key requirements in tests
    provider = AIProvider.OLLAMA
    config = Config(
        ai_provider=provider,
        gitlab_token="test",
    )
    expected = _DEFAULT_SYNTHESIS_MODELS[provider]
    assert config.get_synthesis_model() == expected


def test_create_synthesis_prompt():
    """Test synthesis prompt creation."""
    prompt = create_synthesis_prompt()
    assert prompt is not None
    # Verify prompt has system and human messages
    assert len(prompt.messages) == 2


def test_format_commit_messages_empty():
    """Test formatting with no commits."""
    pr_data = PullRequestData(
        info=PullRequestInfo(
            id=1,
            number=1,
            title="Test",
            description="Test PR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="open",
            web_url="http://test",
        ),
        diffs=[],
        commits=[],
    )
    result = _format_commit_messages(pr_data)
    assert result == "No commits."


def test_format_commit_messages_with_commits():
    """Test formatting commit messages."""
    commits = [
        PullRequestCommit(
            id="abc123",
            title="Add feature",
            message="Add feature\n\nDetailed description",
            author_name="Test Author",
            author_email="test@example.com",
            committed_date="2024-01-01T12:00:00Z",
            short_id="abc123",
        ),
        PullRequestCommit(
            id="def456",
            title="Fix bug",
            message="Fix bug",
            author_name="Test Author",
            author_email="test@example.com",
            committed_date="2024-01-02T12:00:00Z",
            short_id="def456",
        ),
    ]
    pr_data = PullRequestData(
        info=PullRequestInfo(
            id=1,
            number=1,
            title="Test",
            description="Test PR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="open",
            web_url="http://test",
        ),
        diffs=[],
        commits=commits,
    )
    result = _format_commit_messages(pr_data)
    assert "abc123" in result
    assert "Add feature" in result
    assert "def456" in result
    assert "Fix bug" in result


def test_format_reviews_and_comments_empty():
    """Test formatting with no reviews or comments."""
    pr_data = PullRequestData(
        info=PullRequestInfo(
            id=1,
            number=1,
            title="Test",
            description="Test PR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="open",
            web_url="http://test",
        ),
        diffs=[],
        commits=[],
    )
    result = _format_reviews_and_comments(pr_data, "ai-bot")
    assert result == "No reviews or comments yet."


def test_format_reviews_and_comments_with_reviews():
    """Test formatting reviews and comments."""
    reviews = [
        Review(
            id=1,
            author="ai-bot",
            state="COMMENTED",
            body="Previous AI review",
            submitted_at="2024-01-01T10:00:00Z",
        )
    ]
    comments = [
        ReviewComment(
            id=1,
            author="test_user",
            body="Thanks @ai-bot for the review!",
            created_at="2024-01-01T11:00:00Z",
        )
    ]
    pr_data = PullRequestData(
        info=PullRequestInfo(
            id=1,
            number=1,
            title="Test",
            description="Test PR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="open",
            web_url="http://test",
        ),
        diffs=[],
        commits=[],
        reviews=reviews,
        comments=comments,
    )
    result = _format_reviews_and_comments(pr_data, "ai-bot")
    assert "[AI REVIEW]" in result
    assert "CRITICAL: Author Responses" in result
    assert "Thanks @ai-bot for the review!" in result


def test_create_synthesis_chain():
    """Test synthesis chain creation."""
    mock_llm = AsyncMock()
    chain = create_synthesis_chain(mock_llm)
    assert chain is not None


@pytest.mark.asyncio
async def test_synthesis_chain_invocation():
    """Test synthesis chain can be invoked."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value="Mock synthesis result")

    # Create a simpler mock that just returns the synthesis
    with patch(
        "ai_code_review.utils.prompts.StrOutputParser.ainvoke",
        return_value="Mock synthesis result",
    ):
        chain = create_synthesis_chain(mock_llm)
        result = await chain.ainvoke(
            {
                "pr_description": "Test PR",
                "commit_messages": "- abc123: Add feature",
                "reviews_and_comments": "No reviews yet",
            }
        )
        # The chain should process the input
        assert result is not None


def test_synthesis_config_defaults():
    """Test synthesis configuration defaults."""
    # Use OLLAMA to avoid API key requirements
    config = Config(ai_provider=AIProvider.OLLAMA, gitlab_token="test")
    assert config.enable_review_context is True
    assert config.enable_review_synthesis is True
    assert config.synthesis_max_tokens == 2000


def test_synthesis_config_disable():
    """Test disabling synthesis."""
    # Use OLLAMA to avoid API key requirements
    config = Config(
        ai_provider=AIProvider.OLLAMA,
        gitlab_token="test",
        enable_review_synthesis=False,
    )
    assert config.enable_review_synthesis is False


def test_format_reviews_prioritizes_author_responses():
    """Test that author responses to bot are prioritized."""
    reviews = [
        Review(
            id=1,
            author="ai-bot",
            state="COMMENTED",
            body="You should fix X",
            submitted_at="2024-01-01T10:00:00Z",
        )
    ]
    comments = [
        ReviewComment(
            id=1,
            author="other_user",
            body="Looks good to me",
            created_at="2024-01-01T11:00:00Z",
        ),
        ReviewComment(
            id=2,
            author="test_user",
            body="@ai-bot I've fixed X as you suggested",
            created_at="2024-01-01T12:00:00Z",
        ),
    ]
    pr_data = PullRequestData(
        info=PullRequestInfo(
            id=1,
            number=1,
            title="Test",
            description="Test PR",
            source_branch="feature",
            target_branch="main",
            author="test_user",
            state="open",
            web_url="http://test",
        ),
        diffs=[],
        commits=[],
        reviews=reviews,
        comments=comments,
    )
    result = _format_reviews_and_comments(pr_data, "ai-bot")

    # Author response should appear before other comments
    critical_idx = result.find("CRITICAL: Author Responses")
    other_idx = result.find("Other Comments")
    assert critical_idx < other_idx
    assert "I've fixed X as you suggested" in result
