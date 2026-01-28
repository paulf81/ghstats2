"""Async GitHub Traffic API client."""

import asyncio
from datetime import UTC, datetime
from typing import Self

import httpx

from ghstats2.models import Release, RepoStats, TrafficData


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""


class RateLimitError(GitHubAPIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, reset_at: datetime | None = None):
        """Initialize with reset time.

        Args:
            message: Error message.
            reset_at: When rate limit resets (UTC).
        """
        super().__init__(message)
        self.reset_at = reset_at


class AuthenticationError(GitHubAPIError):
    """Raised for authentication failures."""


class NotFoundError(GitHubAPIError):
    """Raised when repository doesn't exist or no access."""


class GitHubTrafficClient:
    """Async client for GitHub Traffic API.

    Handles authentication, rate limiting, and error recovery.

    Attributes:
        BASE_URL: GitHub API base URL.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, timeout: float = 30.0):
        """Initialize client with authentication token.

        Args:
            token: GitHub personal access token with repo scope.
            timeout: Request timeout in seconds.
        """
        self.token = token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        max_retries: int = 3,
    ) -> dict:
        """Execute request with retry logic.

        Args:
            method: HTTP method.
            path: API endpoint path.
            max_retries: Maximum retry attempts for transient failures.

        Returns:
            JSON response as dictionary.

        Raises:
            RateLimitError: When rate limit is exceeded.
            AuthenticationError: For auth failures.
            NotFoundError: When resource not found.
            GitHubAPIError: For other API errors.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = await self._client.request(method, path)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 401:
                    raise AuthenticationError("Invalid or expired token")

                if response.status_code == 403:
                    # Check if rate limited
                    remaining = response.headers.get("X-RateLimit-Remaining", "1")
                    if remaining == "0":
                        reset_timestamp = int(response.headers.get("X-RateLimit-Reset", "0"))
                        reset_at = datetime.fromtimestamp(reset_timestamp, tz=UTC)
                        raise RateLimitError(
                            f"Rate limit exceeded. Resets at {reset_at.isoformat()}",
                            reset_at=reset_at,
                        )
                    raise AuthenticationError("Access forbidden - check token permissions")

                if response.status_code == 404:
                    raise NotFoundError(f"Repository not found or no access: {path}")

                # Server errors - retry
                if response.status_code >= 500:
                    last_error = GitHubAPIError(
                        f"Server error {response.status_code}: {response.text}"
                    )
                    await asyncio.sleep(2**attempt)
                    continue

                raise GitHubAPIError(f"API error {response.status_code}: {response.text}")

            except httpx.RequestError as e:
                last_error = GitHubAPIError(f"Request failed: {e}")
                await asyncio.sleep(2**attempt)

        raise last_error or GitHubAPIError("Request failed after retries")

    async def get_views(self, owner: str, repo: str) -> TrafficData:
        """Fetch page view traffic for last 14 days.

        Args:
            owner: Repository owner/organization.
            repo: Repository name.

        Returns:
            TrafficData with views breakdown.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}/traffic/views")
        return TrafficData(
            count=data.get("count", 0),
            uniques=data.get("uniques", 0),
            items=data.get("views", []),
        )

    async def get_clones(self, owner: str, repo: str) -> TrafficData:
        """Fetch clone traffic for last 14 days.

        Args:
            owner: Repository owner/organization.
            repo: Repository name.

        Returns:
            TrafficData with clones breakdown.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}/traffic/clones")
        return TrafficData(
            count=data.get("count", 0),
            uniques=data.get("uniques", 0),
            items=data.get("clones", []),
        )

    async def get_repo_stats(self, owner: str, repo: str) -> RepoStats:
        """Fetch repository statistics (forks, stars, etc.).

        Args:
            owner: Repository owner/organization.
            repo: Repository name.

        Returns:
            RepoStats with current counts.
        """
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        return RepoStats(
            forks_count=data.get("forks_count", 0),
            stargazers_count=data.get("stargazers_count", 0),
            watchers_count=data.get("watchers_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
        )

    async def get_releases(self, owner: str, repo: str, per_page: int = 100) -> list[Release]:
        """Fetch releases for a repository.

        Args:
            owner: Repository owner/organization.
            repo: Repository name.
            per_page: Number of releases to fetch (max 100).

        Returns:
            List of Release objects sorted by date (newest first).
        """
        from datetime import date

        data = await self._request("GET", f"/repos/{owner}/{repo}/releases?per_page={per_page}")
        releases = []
        for item in data:
            published = item.get("published_at")
            if published:
                published_date = date.fromisoformat(published[:10])
                releases.append(
                    Release(
                        tag_name=item.get("tag_name", ""),
                        published_at=published_date,
                        name=item.get("name") or "",
                    )
                )
        return releases
