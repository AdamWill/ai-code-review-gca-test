"""CI/CD Documentation Provider for fetching official CI/CD documentation."""

from __future__ import annotations

import aiohttp
import structlog

from context_generator.models import CIDocsConfig

logger = structlog.get_logger(__name__)


class CIDocsProvider:
    """Provider for fetching official CI/CD documentation."""

    # Mapping of CI systems to their official documentation URLs
    CI_DOCS_URLS = {
        "gitlab-ci": {
            "yaml": "https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/yaml/_index.md",
            "variables": "https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/variables/_index.md",
            "jobs": "https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/jobs/_index.md",
            "pipelines": "https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/pipelines/_index.md",
        },
        "github-actions": {
            "workflow-syntax": "https://raw.githubusercontent.com/github/docs/refs/heads/main/data/reusables/actions/workflow-basic-example-and-explanation.md",
            "variables": "https://raw.githubusercontent.com/github/docs/refs/heads/main/data/reusables/actions/environment-variables.md",
            "secrets": "https://raw.githubusercontent.com/github/docs/refs/heads/main/data/reusables/actions/encrypted-secrets.md",
        },
    }

    def __init__(self, config: CIDocsConfig) -> None:
        """Initialize the CI docs provider.

        Args:
            config: Configuration for the provider
        """
        self.config = config

    async def fetch_ci_documentation(self, ci_system: str) -> dict[str, str]:
        """Fetch official documentation for a CI system.

        Args:
            ci_system: The CI system name (e.g., 'gitlab-ci', 'github-actions')

        Returns:
            Dictionary mapping doc types to their content

        Raises:
            ValueError: If CI system is not supported
            aiohttp.ClientError: If HTTP request fails
        """
        if ci_system not in self.CI_DOCS_URLS:
            raise ValueError(f"Unsupported CI system: {ci_system}")

        urls = self.CI_DOCS_URLS[ci_system]
        docs = {}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as session:
            for doc_type, url in urls.items():
                try:
                    logger.info(
                        f"Fetching {ci_system} {doc_type} documentation from {url}"
                    )
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            if len(content) <= self.config.max_content_length:
                                docs[doc_type] = content
                                logger.info(
                                    f"Successfully fetched {doc_type} docs ({len(content)} chars)"
                                )
                            else:
                                # Truncate content instead of discarding it
                                truncated_content = content[
                                    : self.config.max_content_length
                                ]
                                docs[doc_type] = truncated_content
                                logger.warning(
                                    f"Content truncated for {doc_type}: {len(content)} chars -> {len(truncated_content)} chars"
                                )
                        else:
                            logger.warning(
                                f"Failed to fetch {doc_type}: HTTP {response.status}"
                            )
                except aiohttp.ClientError as e:
                    logger.error(f"HTTP client error fetching {doc_type} docs: {e}")
                except TimeoutError:
                    logger.error(f"Timeout fetching {doc_type} docs")
                except Exception:
                    logger.error(f"Unexpected error fetching {doc_type} docs")

        return docs

    def get_supported_ci_systems(self) -> list[str]:
        """Get list of supported CI systems.

        Returns:
            List of supported CI system names
        """
        return list(self.CI_DOCS_URLS.keys())

    def get_doc_types_for_ci_system(self, ci_system: str) -> list[str]:
        """Get available documentation types for a CI system.

        Args:
            ci_system: The CI system name

        Returns:
            List of available documentation types

        Raises:
            ValueError: If CI system is not supported
        """
        if ci_system not in self.CI_DOCS_URLS:
            raise ValueError(f"Unsupported CI system: {ci_system}")

        return list(self.CI_DOCS_URLS[ci_system].keys())
