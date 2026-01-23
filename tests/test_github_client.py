"""Tests for GitHub client."""

import pytest
import respx
from httpx import Response

from ghstats2.github_client import (
    AuthenticationError,
    GitHubTrafficClient,
    NotFoundError,
    RateLimitError,
)


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    with respx.mock(base_url="https://api.github.com") as respx_mock:
        yield respx_mock


class TestGitHubTrafficClient:
    """Tests for GitHubTrafficClient class."""

    @pytest.mark.asyncio
    async def test_get_views_success(self, mock_github_api) -> None:
        """Test successful views fetch."""
        mock_github_api.get("/repos/NatLabRockies/floris/traffic/views").mock(
            return_value=Response(
                200,
                json={
                    "count": 1000,
                    "uniques": 200,
                    "views": [
                        {"timestamp": "2024-01-01T00:00:00Z", "count": 100, "uniques": 50},
                        {"timestamp": "2024-01-02T00:00:00Z", "count": 150, "uniques": 60},
                    ],
                },
            )
        )

        async with GitHubTrafficClient(token="test_token") as client:
            result = await client.get_views("NatLabRockies", "floris")

        assert result.count == 1000
        assert result.uniques == 200
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_get_clones_success(self, mock_github_api) -> None:
        """Test successful clones fetch."""
        mock_github_api.get("/repos/NatLabRockies/floris/traffic/clones").mock(
            return_value=Response(
                200,
                json={
                    "count": 100,
                    "uniques": 50,
                    "clones": [
                        {"timestamp": "2024-01-01T00:00:00Z", "count": 10, "uniques": 5},
                    ],
                },
            )
        )

        async with GitHubTrafficClient(token="test_token") as client:
            result = await client.get_clones("NatLabRockies", "floris")

        assert result.count == 100
        assert result.uniques == 50
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_get_repo_stats_success(self, mock_github_api) -> None:
        """Test successful repo stats fetch."""
        mock_github_api.get("/repos/NatLabRockies/floris").mock(
            return_value=Response(
                200,
                json={
                    "forks_count": 25,
                    "stargazers_count": 150,
                    "watchers_count": 150,
                    "open_issues_count": 10,
                },
            )
        )

        async with GitHubTrafficClient(token="test_token") as client:
            result = await client.get_repo_stats("NatLabRockies", "floris")

        assert result.forks_count == 25
        assert result.stargazers_count == 150

    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_github_api) -> None:
        """Test authentication error handling."""
        mock_github_api.get("/repos/NatLabRockies/floris/traffic/views").mock(
            return_value=Response(401, json={"message": "Bad credentials"})
        )

        async with GitHubTrafficClient(token="bad_token") as client:
            with pytest.raises(AuthenticationError):
                await client.get_views("NatLabRockies", "floris")

    @pytest.mark.asyncio
    async def test_not_found_error(self, mock_github_api) -> None:
        """Test not found error handling."""
        mock_github_api.get("/repos/NatLabRockies/nonexistent/traffic/views").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )

        async with GitHubTrafficClient(token="test_token") as client:
            with pytest.raises(NotFoundError):
                await client.get_views("NatLabRockies", "nonexistent")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_github_api) -> None:
        """Test rate limit error handling."""
        mock_github_api.get("/repos/NatLabRockies/floris/traffic/views").mock(
            return_value=Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "1704067200",
                },
                json={"message": "API rate limit exceeded"},
            )
        )

        async with GitHubTrafficClient(token="test_token") as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client.get_views("NatLabRockies", "floris")

            assert exc_info.value.reset_at is not None
