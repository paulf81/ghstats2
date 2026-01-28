"""Data models for ghstats2."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime


@dataclass
class TrafficRecord:
    """Single day's traffic data for one repository.

    Attributes:
        record_date: The date of the record.
        repo_owner: GitHub organization/owner (e.g., "NatLabRockies").
        repo_name: Repository name (e.g., "floris").
        clones_total: Total number of clones.
        clones_unique: Unique cloners (IP-based).
        views_total: Total page views.
        views_unique: Unique visitors.
        forks_count: Cumulative fork count (from repo API).
        stars_count: Cumulative star count (from repo API).
        collected_at: When this data was collected (ISO format).
    """

    record_date: date
    repo_owner: str
    repo_name: str
    clones_total: int | None = None
    clones_unique: int | None = None
    views_total: int | None = None
    views_unique: int | None = None
    forks_count: int | None = None
    stars_count: int | None = None
    collected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame creation.

        Returns:
            Dictionary representation of the record.
        """
        return {
            "date": self.record_date,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "clones_total": self.clones_total,
            "clones_unique": self.clones_unique,
            "views_total": self.views_total,
            "views_unique": self.views_unique,
            "forks_count": self.forks_count,
            "stars_count": self.stars_count,
            "collected_at": self.collected_at,
        }


@dataclass
class TrafficData:
    """Traffic data from GitHub API for a time period.

    Attributes:
        count: Total count over the period.
        uniques: Unique visitors/cloners over the period.
        items: Daily breakdown of traffic.
    """

    count: int
    uniques: int
    items: list[dict]


@dataclass
class RepoStats:
    """Repository statistics from GitHub API.

    Attributes:
        forks_count: Number of forks.
        stargazers_count: Number of stars.
        watchers_count: Number of watchers.
        open_issues_count: Number of open issues.
    """

    forks_count: int
    stargazers_count: int
    watchers_count: int
    open_issues_count: int


@dataclass
class Release:
    """GitHub release information.

    Attributes:
        tag_name: Release version tag (e.g., "v1.0.0").
        published_at: When the release was published.
        name: Release title (may be empty).
    """

    tag_name: str
    published_at: date
    name: str = ""
