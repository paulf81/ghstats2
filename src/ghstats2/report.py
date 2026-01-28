"""HTML dashboard generation with Plotly charts."""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from ghstats2.models import Release


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
    import json

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

    # Build per-repo chart containers
    charts_html = ""
    for repo in repos:
        safe_id = repo.replace("-", "_").replace(".", "_")
        charts_html += f"""
        <div class="repo-charts">
            <h2 class="repo-title">{repo}</h2>
            <div class="charts-row">
                <div class="chart-container">
                    <div id="views-{safe_id}" class="chart"></div>
                </div>
                <div class="chart-container">
                    <div id="clones-{safe_id}" class="chart"></div>
                </div>
            </div>
        </div>
        """

    # Build per-repo chart JavaScript
    charts_js = ""
    for repo in repos:
        safe_id = repo.replace("-", "_").replace(".", "_")
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
            # Only show releases within the data range
            if min_date and max_date and min_date <= release_date <= max_date:
                date_str = release_date.isoformat()
                # Vertical line shape
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
                # Annotation at top
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
            "title": "Daily Views",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Unique Views"},
            "margin": {"t": 40, "r": 20},
            "shapes": shapes,
            "annotations": annotations,
        }

        clones_layout = {
            "title": "Daily Clones",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Unique Clones"},
            "margin": {"t": 40, "r": 20},
            "shapes": shapes,
            "annotations": annotations,
        }

        charts_js += f"""
        Plotly.newPlot('views-{safe_id}', {json.dumps(views_trace)}, {json.dumps(views_layout)});

        Plotly.newPlot('clones-{safe_id}', {json.dumps(clones_trace)}, {json.dumps(clones_layout)});
        """

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

    <h1 style="margin-top: 40px; color: #333;">Time Series</h1>

    {charts_html}

    <script>
        {charts_js}
    </script>
</body>
</html>
"""

    output_path.write_text(html)
