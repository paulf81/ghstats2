"""Data collection orchestration."""

import asyncio
from datetime import UTC, date, datetime

from rich.console import Console

from ghstats2.config import RepoConfig, Settings
from ghstats2.github_client import GitHubAPIError, GitHubTrafficClient
from ghstats2.models import TrafficRecord
from ghstats2.storage import StatsStorage

console = Console()


async def collect_repo_stats(
    client: GitHubTrafficClient,
    repo: RepoConfig,
) -> list[TrafficRecord]:
    """Collect all statistics for a single repository.

    Args:
        client: Initialized GitHub client.
        repo: Repository configuration.

    Returns:
        List of TrafficRecord for each day with data.
    """
    records: list[TrafficRecord] = []
    collected_at = datetime.now(UTC).isoformat()

    try:
        # Fetch traffic data in parallel
        views_task = client.get_views(repo.owner, repo.name)
        clones_task = client.get_clones(repo.owner, repo.name)
        stats_task = client.get_repo_stats(repo.owner, repo.name)

        views, clones, stats = await asyncio.gather(views_task, clones_task, stats_task)

        # Build date -> record mapping from views
        date_records: dict[date, TrafficRecord] = {}

        for item in views.items:
            ts = item.get("timestamp", "")
            record_date = date.fromisoformat(ts.split("T")[0])
            date_records[record_date] = TrafficRecord(
                record_date=record_date,
                repo_owner=repo.owner,
                repo_name=repo.name,
                views_total=item.get("count", 0),
                views_unique=item.get("uniques", 0),
                forks_count=stats.forks_count,
                stars_count=stats.stargazers_count,
                collected_at=collected_at,
            )

        # Merge clones data
        for item in clones.items:
            ts = item.get("timestamp", "")
            record_date = date.fromisoformat(ts.split("T")[0])

            if record_date in date_records:
                date_records[record_date].clones_total = item.get("count", 0)
                date_records[record_date].clones_unique = item.get("uniques", 0)
            else:
                date_records[record_date] = TrafficRecord(
                    record_date=record_date,
                    repo_owner=repo.owner,
                    repo_name=repo.name,
                    clones_total=item.get("count", 0),
                    clones_unique=item.get("uniques", 0),
                    forks_count=stats.forks_count,
                    stars_count=stats.stargazers_count,
                    collected_at=collected_at,
                )

        records = list(date_records.values())
        console.print(f"  [green]Collected {len(records)} days of data[/green]")

    except GitHubAPIError as e:
        console.print(f"  [red]Error: {e}[/red]")

    return records


async def collect_all(
    settings: Settings,
    repos: list[RepoConfig] | None = None,
    dry_run: bool = False,
) -> int:
    """Collect statistics for all configured repositories.

    Args:
        settings: Application settings.
        repos: Specific repos to collect (default: all configured).
        dry_run: If True, show what would be collected without storing.

    Returns:
        Total number of records collected.
    """
    if repos is None:
        repos = settings.load_repos()

    if not repos:
        console.print("[yellow]No repositories configured[/yellow]")
        return 0

    console.print(f"\n[bold]Collecting stats for {len(repos)} repositories[/bold]\n")

    if dry_run:
        for repo in repos:
            console.print(f"  Would collect: {repo.owner}/{repo.name}")
        return 0

    if not settings.github_token:
        console.print("[red]Error: GHSTATS_GITHUB_TOKEN not set[/red]")
        console.print("Set environment variable or create .env file")
        return 0

    storage = StatsStorage(settings.data_dir / "stats.parquet")
    all_records: list[TrafficRecord] = []

    async with GitHubTrafficClient(settings.github_token) as client:
        for repo in repos:
            console.print(f"[cyan]{repo.owner}/{repo.name}[/cyan]")
            records = await collect_repo_stats(client, repo)
            all_records.extend(records)

    if all_records:
        count = storage.upsert(all_records)
        output_path = settings.data_dir / "stats.parquet"
        console.print(f"\n[green]Stored {count} records to {output_path}[/green]")
        return count

    console.print("\n[yellow]No new data collected[/yellow]")
    return 0
