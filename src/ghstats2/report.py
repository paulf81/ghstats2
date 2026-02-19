"""HTML dashboard generation with Plotly charts."""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from ghstats2.models import Release


def _build_charts(
    df: pl.DataFrame,
    repos: list[str],
    suffix: str,
    title_prefix: str,
    releases: dict[str, list[Release]],
    min_date: pl.Date | None,
    max_date: pl.Date | None,
) -> tuple[str, str]:
    """Build chart HTML containers and JavaScript for a dataset.

    Args:
        df: DataFrame with date, repo_name, views_unique, clones_unique columns.
        repos: List of repository names.
        suffix: Suffix for element IDs (e.g., "daily", "weekly", "monthly").
        title_prefix: Prefix for chart titles (e.g., "Daily", "Weekly", "Monthly").
        releases: Dict mapping repo_name to list of Release objects.
        min_date: Minimum date for release filtering.
        max_date: Maximum date for release filtering.

    Returns:
        Tuple of (charts_html, charts_js).
    """
    import json

    charts_html = ""
    charts_js = ""

    for repo in repos:
        safe_id = repo.replace("-", "_").replace(".", "_")
        charts_html += f"""
        <div class="repo-charts">
            <h2 class="repo-title">{repo}</h2>
            <div class="charts-row">
                <div class="chart-container">
                    <div id="views-{safe_id}-{suffix}" class="chart"></div>
                </div>
                <div class="chart-container">
                    <div id="clones-{safe_id}-{suffix}" class="chart"></div>
                </div>
            </div>
        </div>
        """

        repo_df = df.filter(pl.col("repo_name") == repo).sort("date")
        dates = repo_df["date"].cast(pl.Utf8).to_list()
        views_unique = repo_df["views_unique"].fill_null(0).to_list()
        clones_unique = repo_df["clones_unique"].fill_null(0).to_list()

        views_trace = [
            {
                "x": dates,
                "y": views_unique,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Unique Views",
                "line": {"color": "#636EFA"},
            }
        ]

        clones_trace = [
            {
                "x": dates,
                "y": clones_unique,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Unique Clones",
                "line": {"color": "#EF553B"},
            }
        ]

        # Build release markers (shapes and annotations) for this repo
        repo_releases = releases.get(repo, [])
        shapes = []
        annotations = []

        for release in repo_releases:
            release_date = release.published_at
            if min_date and max_date and min_date <= release_date <= max_date:
                date_str = release_date.isoformat()
                shapes.append(
                    {
                        "type": "line",
                        "x0": date_str,
                        "x1": date_str,
                        "y0": 0,
                        "y1": 1,
                        "yref": "paper",
                        "line": {"color": "#888", "width": 1, "dash": "dash"},
                    }
                )
                annotations.append(
                    {
                        "x": date_str,
                        "y": 1,
                        "yref": "paper",
                        "text": release.tag_name,
                        "showarrow": False,
                        "font": {"size": 10, "color": "#666"},
                        "yanchor": "bottom",
                        "textangle": -45,
                    }
                )

        views_layout = {
            "title": f"{title_prefix} Views",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Unique Views"},
            "margin": {"t": 40, "r": 20},
            "shapes": shapes,
            "annotations": annotations,
        }

        clones_layout = {
            "title": f"{title_prefix} Clones",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Unique Clones"},
            "margin": {"t": 40, "r": 20},
            "shapes": shapes,
            "annotations": annotations,
        }

        views_trace_json = json.dumps(views_trace)
        views_layout_json = json.dumps(views_layout)
        clones_trace_json = json.dumps(clones_trace)
        clones_layout_json = json.dumps(clones_layout)
        charts_js += f"""
        Plotly.newPlot('views-{safe_id}-{suffix}', {views_trace_json}, {views_layout_json});
        Plotly.newPlot('clones-{safe_id}-{suffix}', {clones_trace_json}, {clones_layout_json});
        """

    return charts_html, charts_js


def generate_dashboard(
    df: pl.DataFrame,
    output_path: str | Path,
    releases: dict[str, list[Release]] | None = None,
) -> None:
    """Generate HTML dashboard from statistics DataFrame.

    Args:
        df: Statistics DataFrame with columns: date, repo_name, views_total, etc.
        output_path: Path to write HTML file.
        releases: Optional dict mapping repo_name to list of Release objects.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    releases = releases or {}
    repos = df["repo_name"].unique().sort().to_list()

    # Get date range from data for filtering releases
    min_date = df["date"].min()
    max_date = df["date"].max()

    # Calculate per-repo summaries
    summary = (
        df.group_by("repo_name")
        .agg(
            [
                pl.col("views_total").sum().alias("views_total"),
                pl.col("views_unique").sum().alias("views_unique"),
                pl.col("clones_total").sum().alias("clones_total"),
                pl.col("clones_unique").sum().alias("clones_unique"),
            ]
        )
        .sort("repo_name")
    )

    # Build per-repo cards HTML
    cards_html = ""
    for repo in repos:
        repo_stats = summary.filter(pl.col("repo_name") == repo)
        views_total = repo_stats["views_total"][0] or 0
        views_unique = repo_stats["views_unique"][0] or 0
        clones_total = repo_stats["clones_total"][0] or 0
        clones_unique = repo_stats["clones_unique"][0] or 0

        cards_html += f"""
        <div class="repo-section">
            <h2 class="repo-title">{repo}</h2>
            <div class="cards">
                <div class="card">
                    <h3>Total Views</h3>
                    <div class="value">{views_total:,}</div>
                </div>
                <div class="card">
                    <h3>Unique Views</h3>
                    <div class="value">{views_unique:,}</div>
                </div>
                <div class="card">
                    <h3>Total Clones</h3>
                    <div class="value">{clones_total:,}</div>
                </div>
                <div class="card">
                    <h3>Unique Clones</h3>
                    <div class="value">{clones_unique:,}</div>
                </div>
            </div>
        </div>
        """

    # Build daily charts
    daily_charts_html, daily_charts_js = _build_charts(
        df, repos, "daily", "Daily", releases, min_date, max_date
    )

    # Build weekly aggregated data and charts
    weekly_df = (
        df.with_columns(pl.col("date").dt.truncate("1w").alias("date"))
        .group_by(["date", "repo_name"])
        .agg(
            [
                pl.col("views_unique").sum(),
                pl.col("clones_unique").sum(),
            ]
        )
    )
    weekly_charts_html, weekly_charts_js = _build_charts(
        weekly_df, repos, "weekly", "Weekly", releases, min_date, max_date
    )

    # Build monthly aggregated data and charts
    monthly_df = (
        df.with_columns(pl.col("date").dt.truncate("1mo").alias("date"))
        .group_by(["date", "repo_name"])
        .agg(
            [
                pl.col("views_unique").sum(),
                pl.col("clones_unique").sum(),
            ]
        )
    )
    monthly_charts_html, monthly_charts_js = _build_charts(
        monthly_df, repos, "monthly", "Monthly", releases, min_date, max_date
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Stats Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #333;
            margin-bottom: 5px;
        }}
        .header p {{
            color: #666;
            font-size: 14px;
        }}
        .repo-section {{
            margin-bottom: 30px;
        }}
        .repo-title {{
            color: #333;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
            margin-bottom: 15px;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 8px 0;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .repo-charts {{
            margin-bottom: 40px;
        }}
        .charts-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart {{
            width: 100%;
            height: 300px;
        }}
        @media (max-width: 900px) {{
            .cards {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .charts-row {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GitHub Stats Dashboard</h1>
        <p>NatLabRockies Wind Energy Repositories</p>
        <p>Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}</p>
    </div>

    {cards_html}

    <h1 style="margin-top: 40px; color: #333;">Daily Totals</h1>

    {daily_charts_html}

    <h1 style="margin-top: 40px; color: #333;">Weekly Totals</h1>

    {weekly_charts_html}

    <h1 style="margin-top: 40px; color: #333;">Monthly Totals</h1>

    {monthly_charts_html}

    <script>
        {daily_charts_js}
        {weekly_charts_js}
        {monthly_charts_js}
    </script>
</body>
</html>
"""

    output_path.write_text(html)
