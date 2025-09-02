"""SSL certificate management utilities."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class SSLCertificateManager:
    """Manages SSL certificate downloading and caching."""

    def __init__(self, cache_dir: str = ".ssl_cache") -> None:
        """Initialize SSL certificate manager.

        Args:
            cache_dir: Directory to cache downloaded certificates
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    async def get_certificate_path(
        self,
        cert_url: str | None = None,
        cert_path: str | None = None,
    ) -> str | None:
        """Get certificate path, downloading if needed.

        Priority order:
        1. cert_path (existing file path)
        2. cert_url (download and cache)
        3. None (no certificate)

        Args:
            cert_url: URL to download certificate from
            cert_path: Path to existing certificate file

        Returns:
            Path to certificate file or None if no certificate configured

        Raises:
            ValueError: If certificate download or validation fails
        """
        # Priority 1: Use existing file path
        if cert_path:
            if not os.path.isfile(cert_path):
                raise ValueError(f"SSL certificate file not found: {cert_path}")
            logger.info("Using existing SSL certificate file", path=cert_path)
            return cert_path

        # Priority 2: Download from URL and cache
        if cert_url:
            return await self._download_and_cache_certificate(cert_url)

        # Priority 3: No certificate
        return None

    async def _download_and_cache_certificate(self, cert_url: str) -> str:
        """Download certificate from URL and cache it.

        Args:
            cert_url: URL to download certificate from

        Returns:
            Path to cached certificate file

        Raises:
            ValueError: If download fails or certificate is invalid
        """
        # Generate cache filename based on URL hash
        url_hash = hashlib.sha256(cert_url.encode()).hexdigest()[:16]
        cache_filename = f"cert_{url_hash}.pem"
        cache_path = self.cache_dir / cache_filename

        # Check if certificate is already cached and valid
        if cache_path.exists():
            if await self._is_certificate_valid(cache_path):
                logger.info(
                    "Using cached SSL certificate",
                    url=cert_url,
                    cache_path=str(cache_path),
                )
                return str(cache_path)
            else:
                logger.info(
                    "Cached certificate invalid, re-downloading",
                    url=cert_url,
                    cache_path=str(cache_path),
                )

        # Download certificate
        logger.info("Downloading SSL certificate", url=cert_url)

        try:
            async with aiohttp.ClientSession() as session:
                # Disable SSL verification for the certificate download itself,
                # as we are bootstrapping trust from a user-provided URL.
                async with session.get(cert_url, ssl=False) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"Failed to download certificate: HTTP {response.status}"
                        )

                    cert_content = await response.text()

                    # Validate certificate format
                    if not self._is_valid_certificate_content(cert_content):
                        raise ValueError(
                            f"Downloaded content is not a valid certificate: {cert_url}"
                        )

                    # Save to cache
                    cache_path.write_text(cert_content)
                    logger.info(
                        "SSL certificate downloaded and cached",
                        url=cert_url,
                        cache_path=str(cache_path),
                    )

                    return str(cache_path)

        except aiohttp.ClientError as e:
            raise ValueError(
                f"Failed to download SSL certificate from {cert_url}: {e}"
            ) from e

    async def _is_certificate_valid(self, cert_path: Path) -> bool:
        """Check if cached certificate is still valid.

        Args:
            cert_path: Path to cached certificate file

        Returns:
            True if certificate exists and appears valid
        """
        if not cert_path.exists():
            return False

        try:
            cert_content = cert_path.read_text()
            return self._is_valid_certificate_content(cert_content)
        except (OSError, UnicodeDecodeError):
            return False

    def _is_valid_certificate_content(self, content: str) -> bool:
        """Validate certificate content format.

        Args:
            content: Certificate content to validate

        Returns:
            True if content appears to be a valid certificate
        """
        content = content.strip()

        # Basic validation: looks like a PEM certificate
        has_begin = "-----BEGIN CERTIFICATE-----" in content
        has_end = "-----END CERTIFICATE-----" in content
        has_content = len(content) > 100  # Certificates are typically much longer

        return has_begin and has_end and has_content
