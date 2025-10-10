"""Context7 provider for fetching official library documentation via REST API."""

from __future__ import annotations

from typing import Any

import structlog

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

        Uses intelligent selection to prefer Python libraries over other languages.

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

        # Strategy: Use Context7's ranking and trust score, but validate relevance
        # Context7 already provides good ranking based on search query

        for result in results:
            title = result.get("title", "").lower()
            library_id = result.get("id", "")
            description = result.get("description", "").lower()

            # Skip results with None library_id
            if not library_id or not isinstance(library_id, str):
                continue

            # Look for exact or close matches in title
            if (
                library_name_lower == title
                or library_name_lower in title
                or title.startswith(library_name_lower)
            ):
                logger.info(
                    "Selected library by title relevance",
                    library=library_name,
                    selected_id=library_id,
                    title=result.get("title"),
                    trust_score=result.get("trust_score"),
                )
                return str(library_id)

            # Look for matches in description if title doesn't match
            if library_name_lower in description:
                logger.info(
                    "Selected library by description relevance",
                    library=library_name,
                    selected_id=library_id,
                    title=result.get("title"),
                    trust_score=result.get("trust_score"),
                )
                return str(library_id)

        # If no clear match found, return the first result (Context7's top recommendation)
        # This trusts Context7's ranking algorithm
        if results:
            first_result = results[0]
            library_id = first_result.get("id")
            if library_id and isinstance(library_id, str):
                logger.info(
                    "Selected top-ranked library from Context7",
                    library=library_name,
                    selected_id=library_id,
                    title=first_result.get("title"),
                    trust_score=first_result.get("trust_score"),
                )
                return str(library_id)

        # No suitable results found
        logger.warning(
            "No suitable library match found",
            library=library_name,
            available_results=[r.get("title") for r in results[:3]],
        )
        return None

    def clear_cache(self) -> None:
        """Clear the session cache."""
        self._session_cache.clear()
        logger.debug("Context7 cache cleared")
