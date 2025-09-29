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
