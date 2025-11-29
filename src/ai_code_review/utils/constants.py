"""Constants used throughout the AI Code Review application."""

from __future__ import annotations

# Token estimation constants
SYSTEM_PROMPT_ESTIMATED_CHARS = 500
"""Estimated number of characters in the system prompt template.

This value is used for context window calculations across all AI providers.
It represents a reasonable estimate of the system prompt size including
instructions, format requirements, and fixed template text.
"""

# Token conversion ratio (characters to tokens)
CHARS_TO_TOKENS_RATIO = 2.5
"""Average ratio of characters to tokens for token estimation.

Based on empirical analysis of typical code content, this ratio provides
a reasonable approximation for token usage calculations across different
AI providers and models.
"""

# Auto big-diffs threshold
AUTO_BIG_DIFFS_THRESHOLD_CHARS = 60000
"""Character threshold for automatically activating big diffs mode.

When the total content size (diff + context + system prompt) exceeds this
threshold, the system automatically enables larger context windows across
all AI providers for better handling of large changesets.
"""

# Derived constants
SYSTEM_PROMPT_ESTIMATED_TOKENS = int(
    SYSTEM_PROMPT_ESTIMATED_CHARS / CHARS_TO_TOKENS_RATIO
)
"""Estimated number of tokens in the system prompt (calculated from chars)."""

# Review synthesis constants
MAX_COMMENTS_TO_FETCH = 30
"""Maximum number of comments/discussions to fetch from platform API.

This limit prevents performance issues on PRs with hundreds of comments.
Only the most recent N comments are fetched and processed for synthesis.
Can be overridden via MAX_COMMENTS_TO_FETCH environment variable.
"""

MAX_OTHER_COMMENTS_IN_SYNTHESIS = 20
"""Maximum number of non-author comments to include in synthesis prompt.

After filtering system notes and prioritizing author responses, this limits
the number of "other comments" included to prevent excessively long prompts.
The most recent comments are selected after sorting by created_at DESC.
"""

MAX_COMMENT_BODY_LENGTH = 300
"""Maximum characters per comment body in synthesis prompt.

Long comments are truncated to this length to keep the synthesis prompt
concise while still providing sufficient context for the AI to understand
the discussion points.
"""
