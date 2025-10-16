"""Context7 provider for fetching official library documentation via REST API."""

from __future__ import annotations

from typing import Any

import structlog

from context_generator.constants import (
    CONTEXT7_LIBRARY_DENYLIST_PATTERNS,
    CONTEXT7_MIN_TRUST_SCORE,
    CONTEXT7_OFFICIAL_LIBRARY_PATTERNS,
)

logger = structlog.get_logger(__name__)


class Context7Provider:
    """Provider for fetching documentation from Context7 REST API."""

    def __init__(self, timeout_seconds: int = 10, api_key: str | None = None) -> None:
        """Initialize Context7 provider.

        Args:
            timeout_seconds: Timeout for API calls
            api_key: Context7 API key (should be resolved by Context7Config)
        """
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self._session_cache: dict[str, str | None] = {}
        self.base_url = "https://context7.com/api/v1"

    async def resolve_library_id(self, library_name: str) -> str | None:
        """Search for a library using Context7 API and return the best match ID.

        Args:
            library_name: Name of the library to resolve

        Returns:
            Context7-compatible library ID or None if not found
        """
        if not self.api_key:
            logger.warning("Context7 API key not available", library=library_name)
            return None

        cache_key = f"resolve:{library_name}"
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]

        try:
            # Import aiohttp here to avoid hard dependency
            import aiohttp

            logger.info("Searching Context7 for library", library=library_name)

            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"query": library_name}

            # Configure timeout for the entire request operation
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}/search", headers=headers, params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        library_id = self._extract_best_library_id(data, library_name)
                        self._session_cache[cache_key] = library_id

                        if library_id:
                            logger.info(
                                "Library found in Context7",
                                library=library_name,
                                library_id=library_id,
                            )
                        else:
                            logger.info(
                                "Library not found in Context7", library=library_name
                            )
                        return library_id
                    else:
                        logger.warning(
                            "Context7 API error",
                            library=library_name,
                            status=response.status,
                        )
                        return None

        except ImportError:
            logger.warning(
                "aiohttp not available for Context7 API calls", library=library_name
            )
            return None
        except TimeoutError:
            logger.warning(
                "Context7 API timeout",
                library=library_name,
                timeout=self.timeout_seconds,
            )
            return None
        except Exception as e:
            logger.warning("Context7 API error", library=library_name, error=str(e))
            return None

    async def get_library_docs(
        self, library_id: str, topic: str | None = None, max_tokens: int = 2000
    ) -> str | None:
        """Fetch documentation for a library from Context7 API.

        Args:
            library_id: Context7-compatible library ID (e.g., "/vercel/next.js")
            topic: Optional topic to focus on
            max_tokens: Maximum tokens to retrieve

        Returns:
            Documentation content or None if unavailable
        """
        if not self.api_key:
            logger.warning("Context7 API key not available", library_id=library_id)
            return None

        cache_key = f"docs:{library_id}:{topic}:{max_tokens}"
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]

        try:
            # Import aiohttp here to avoid hard dependency
            import aiohttp

            logger.info(
                "Fetching library docs from Context7",
                library_id=library_id,
                topic=topic,
            )

            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Build URL: /api/v1/{org}/{project}
            # Remove leading slash if present
            clean_library_id = library_id.lstrip("/")
            docs_url = f"{self.base_url}/{clean_library_id}"

            # Build query parameters
            params: dict[str, str] = {
                "type": "txt",  # Request text format
                "tokens": str(max_tokens),
            }
            if topic:
                params["topic"] = topic

            # Configure timeout for the entire request operation
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    docs_url, headers=headers, params=params
                ) as response:
                    if response.status == 200:
                        # Response should be plain text based on the API example
                        docs = await response.text()
                        self._session_cache[cache_key] = docs

                        if docs:
                            logger.info(
                                "Library docs fetched",
                                library_id=library_id,
                                doc_length=len(docs),
                            )
                        return docs
                    else:
                        logger.warning(
                            "Context7 docs API error",
                            library_id=library_id,
                            status=response.status,
                        )
                        return None

        except ImportError:
            logger.warning(
                "aiohttp not available for Context7 API calls", library_id=library_id
            )
            return None
        except TimeoutError:
            logger.warning(
                "Context7 docs timeout",
                library_id=library_id,
                timeout=self.timeout_seconds,
            )
            return None
        except Exception as e:
            logger.warning("Context7 docs error", library_id=library_id, error=str(e))
            return None

    async def get_library_documentation(
        self, library_name: str, topic: str | None = None, max_tokens: int = 2000
    ) -> str | None:
        """Convenience method to resolve library ID and fetch docs in one call.

        Args:
            library_name: Name of the library
            topic: Optional topic to focus on
            max_tokens: Maximum tokens to retrieve

        Returns:
            Documentation content or None if unavailable
        """
        # First resolve the library ID
        library_id = await self.resolve_library_id(library_name)
        if not library_id:
            return None

        # Then fetch the documentation
        return await self.get_library_docs(library_id, topic, max_tokens)

    def _extract_best_library_id(
        self, search_data: dict[str, Any], library_name: str
    ) -> str | None:
        """Extract the best matching library ID from Context7 search results.

        Uses intelligent selection with multiple filtering strategies:
        1. Prioritizes official library repositories
        2. Filters out documentation sites (denylist)
        3. Requires minimum trust score
        4. Validates relevance through title/description matching

        Args:
            search_data: JSON response from Context7 search API
            library_name: Original library name being searched

        Returns:
            Best matching library ID or None if no good match
        """
        results = search_data.get("results", [])
        if not results:
            return None

        library_name_lower = library_name.lower()

        # Step 1: Check for official library patterns first
        official_patterns = CONTEXT7_OFFICIAL_LIBRARY_PATTERNS.get(
            library_name_lower, []
        )
        if official_patterns:
            for result in results:
                library_id = result.get("id", "")
                if not library_id or not isinstance(library_id, str):
                    continue

                # Check if this matches an official pattern
                for pattern in official_patterns:
                    if pattern in library_id.lower():
                        logger.info(
                            "Selected official library",
                            library=library_name,
                            selected_id=library_id,
                            title=result.get("title"),
                            trust_score=result.get("trust_score"),
                            match_type="official_pattern",
                        )
                        return str(library_id)

        # Step 2: Filter and score all results
        scored_results = []
        for result in results:
            title = result.get("title", "").lower()
            library_id = result.get("id", "")
            description = result.get("description", "").lower()
            trust_score = result.get("trust_score", 0)

            # Skip invalid results
            if not library_id or not isinstance(library_id, str):
                continue

            # Apply denylist filtering
            if self._is_denylisted(library_id):
                logger.debug(
                    "Skipping denylisted library ID",
                    library=library_name,
                    library_id=library_id,
                    title=result.get("title"),
                )
                continue

            # Apply minimum trust score filter
            if trust_score < CONTEXT7_MIN_TRUST_SCORE:
                logger.debug(
                    "Skipping low trust score result",
                    library=library_name,
                    library_id=library_id,
                    title=result.get("title"),
                    trust_score=trust_score,
                )
                continue

            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(
                library_name_lower, title, description, library_id
            )

            scored_results.append(
                {
                    "result": result,
                    "library_id": library_id,
                    "relevance_score": relevance_score,
                    "trust_score": trust_score,
                }
            )

        # Step 3: Sort by relevance score first, then trust score
        scored_results.sort(
            key=lambda x: (x["relevance_score"], x["trust_score"]), reverse=True
        )

        # Step 4: Return the best match if any
        if scored_results:
            best_match = scored_results[0]
            result = best_match["result"]
            logger.info(
                "Selected library by scoring",
                library=library_name,
                selected_id=best_match["library_id"],
                title=result.get("title"),
                trust_score=best_match["trust_score"],
                relevance_score=best_match["relevance_score"],
            )
            return str(best_match["library_id"])

        # No suitable results found
        logger.warning(
            "No suitable library match found after filtering",
            library=library_name,
            total_results=len(results),
            filtered_out=len(results) - len(scored_results),
        )
        return None

    def _is_denylisted(self, library_id: str) -> bool:
        """Check if a library ID matches denylist patterns.

        Args:
            library_id: Context7 library ID to check

        Returns:
            True if denylisted, False otherwise
        """
        library_id_lower = library_id.lower()
        for pattern in CONTEXT7_LIBRARY_DENYLIST_PATTERNS:
            if pattern.lower() in library_id_lower:
                return True
        return False

    def _calculate_relevance_score(
        self, library_name: str, title: str, description: str, library_id: str
    ) -> int:
        """Calculate cumulative relevance score for a library match.

        Scores are additive - multiple conditions can contribute to the final score.
        For example, an exact title match (100) with the library name in the ID (20)
        results in a total score of 120.

        Args:
            library_name: Original library name (lowercase)
            title: Library title (lowercase)
            description: Library description (lowercase)
            library_id: Context7 library ID

        Returns:
            Cumulative relevance score (higher is better)
        """
        score = 0

        # Exact title match is best
        if library_name == title:
            score += 100

        # Title starts with library name
        if title.startswith(library_name):
            score += 50

        # Library name in title
        if library_name in title:
            score += 30

        # Library name in description
        if library_name in description:
            score += 10

        # Library ID contains library name
        if library_name in library_id.lower():
            score += 20

        return score

    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()
        logger.debug("Context7 cache cleared")
