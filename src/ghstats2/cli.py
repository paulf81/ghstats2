"""Command-line interface for ghstats2."""

import asyncio
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from ghstats2.collector import collect_all
from ghstats2.config import get_settings
from ghstats2.storage import StatsStorage

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """GitHub statistics collector for NatLabRockies repositories."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.option("--repo", "-r", multiple=True, help="Specific repo(s) to collect")
@click.option("--dry-run", is_flag=True, help="Show what would be collected")
@click.pass_context
def collect(ctx: click.Context, repo: tuple[str, ...], dry_run: bool) -> None:
    """Collect statistics from GitHub.

    Examples:
        ghstats2 collect                  # All repos
        ghstats2 collect -r floris        # Single repo
        ghstats2 collect --dry-run        # Preview only
    """
    settings = get_settings()
    repos = None

    if repo:
        # Filter to specific repos
        all_repos = settings.load_repos()
        repos = [r for r in all_repos if r.name in repo]
        if not repos:
            console.print(f"[red]No matching repos found for: {repo}[/red]")
            return

    asyncio.run(collect_all(settings, repos=repos, dry_run=dry_run))


@main.command()
@click.option("--repo", "-r", help="Filter by repository name")
@click.option("--days", "-d", default=30, help="Number of days to show")
@click.pass_context
def show(ctx: click.Context, repo: str | None, days: int) -> None:
    """Display statistics in terminal.

    Examples:
        ghstats2 show                     # Last 30 days, all repos
        ghstats2 show -r floris           # Single repo
        ghstats2 show -d 7                # Last 7 days
    """
    settings = get_settings()
    storage = StatsStorage(settings.data_dir / "stats.parquet")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    df = storage.get_stats(repo_name=repo, start_date=start_date, end_date=end_date)

    if df.is_empty():
        console.print("[yellow]No data found. Run 'ghstats2 collect' first.[/yellow]")
        return

    # Create summary table
    table = Table(title=f"Statistics (last {days} days)")
    table.add_column("Repository", style="cyan")
    table.add_column("Views", justify="right")
    table.add_column("Unique Views", justify="right")
    table.add_column("Clones", justify="right")
    table.add_column("Unique Clones", justify="right")
    table.add_column("Stars", justify="right")
    table.add_column("Forks", justify="right")

    # Aggregate by repo
    summary = (
        df.group_by("repo_name")
        .agg(
            [
                df["views_total"].sum().alias("views_total"),
                df["views_unique"].sum().alias("views_unique"),
                df["clones_total"].sum().alias("clones_total"),
                df["clones_unique"].sum().alias("clones_unique"),
                df["stars_count"].last().alias("stars"),
                df["forks_count"].last().alias("forks"),
            ]
        )
        .sort("repo_name")
    )

    for row in summary.iter_rows(named=True):
        table.add_row(
            row["repo_name"],
            str(row["views_total"] or 0),
            str(row["views_unique"] or 0),
            str(row["clones_total"] or 0),
            str(row["clones_unique"] or 0),
            str(row["stars"] or 0),
            str(row["forks"] or 0),
        )

    console.print(table)


async def _fetch_releases(settings, repos: list) -> dict:
    """Fetch releases for all configured repos."""
    from ghstats2.github_client import GitHubTrafficClient
    from ghstats2.models import Release

    releases: dict[str, list[Release]] = {}

    if not settings.github_token:
        return releases

    async with GitHubTrafficClient(settings.github_token) as client:
        for repo in repos:
            try:
                repo_releases = await client.get_releases(repo.owner, repo.name)
                releases[repo.name] = repo_releases
            except Exception:
                # Skip repos where we can't fetch releases
                pass

    return releases


@main.command()
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["html", "csv", "json"]),
    default="html",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--no-releases", is_flag=True, help="Skip fetching release markers")
@click.pass_context
def report(ctx: click.Context, output_format: str, output: str | None, no_releases: bool) -> None:
    """Generate statistics report.

    Examples:
        ghstats2 report                           # HTML dashboard
        ghstats2 report -f csv -o export.csv      # CSV export
        ghstats2 report --no-releases             # Skip release markers
    """
    settings = get_settings()
    storage = StatsStorage(settings.data_dir / "stats.parquet")

    df = storage.read()

    if df.is_empty():
        console.print("[yellow]No data found. Run 'ghstats2 collect' first.[/yellow]")
        return

    if output_format == "csv":
        output_path = output or "reports/stats.csv"
        df.write_csv(output_path)
        console.print(f"[green]Exported to {output_path}[/green]")

    elif output_format == "json":
        output_path = output or "reports/stats.json"
        df.write_json(output_path)
        console.print(f"[green]Exported to {output_path}[/green]")

    else:
        # HTML report
        from ghstats2.report import generate_dashboard

        releases = {}
        if not no_releases:
            repos = settings.load_repos()
            if repos and settings.github_token:
                console.print("[dim]Fetching release data...[/dim]")
                releases = asyncio.run(_fetch_releases(settings, repos))

        output_path = output or "reports/dashboard.html"
        generate_dashboard(df, output_path, releases=releases)
        console.print(f"[green]Generated dashboard at {output_path}[/green]")


@main.command("list")
@click.pass_context
def list_repos(ctx: click.Context) -> None:
    """List configured repositories."""
    settings = get_settings()
    repos = settings.load_repos()

    if not repos:
        console.print("[yellow]No repositories configured in config/repos.yaml[/yellow]")
        return

    table = Table(title="Configured Repositories")
    table.add_column("Owner", style="cyan")
    table.add_column("Repository", style="green")

    for repo in repos:
        table.add_row(repo.owner, repo.name)

    console.print(table)


if __name__ == "__main__":
    main()
