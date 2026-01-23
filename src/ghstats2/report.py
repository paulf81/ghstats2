"""HTML dashboard generation with Plotly charts."""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

HTML_TEMPLATE = """<!DOCTYPE html>
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
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart {{
            width: 100%;
            height: 400px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GitHub Stats Dashboard</h1>
        <p>Generated: {generated_at}</p>
    </div>

    <div class="cards">
        <div class="card">
            <h3>Total Views</h3>
            <div class="value">{total_views:,}</div>
        </div>
        <div class="card">
            <h3>Unique Views</h3>
            <div class="value">{unique_views:,}</div>
        </div>
        <div class="card">
            <h3>Total Clones</h3>
            <div class="value">{total_clones:,}</div>
        </div>
        <div class="card">
            <h3>Unique Clones</h3>
            <div class="value">{unique_clones:,}</div>
        </div>
    </div>

    <div class="charts">
        <div class="chart-container">
            <div id="views-chart" class="chart"></div>
        </div>
        <div class="chart-container">
            <div id="clones-chart" class="chart"></div>
        </div>
        <div class="chart-container">
            <div id="comparison-chart" class="chart"></div>
        </div>
    </div>

    <script>
        // Views time series
        var viewsData = {views_data};
        Plotly.newPlot('views-chart', viewsData, {{
            title: 'Daily Views by Repository',
            xaxis: {{ title: 'Date' }},
            yaxis: {{ title: 'Views' }},
            hovermode: 'x unified'
        }});

        // Clones time series
        var clonesData = {clones_data};
        Plotly.newPlot('clones-chart', clonesData, {{
            title: 'Daily Clones by Repository',
            xaxis: {{ title: 'Date' }},
            yaxis: {{ title: 'Clones' }},
            hovermode: 'x unified'
        }});

        // Comparison bar chart
        var comparisonData = {comparison_data};
        Plotly.newPlot('comparison-chart', comparisonData, {{
            title: 'Repository Comparison (Total)',
            barmode: 'group',
            xaxis: {{ title: 'Repository' }},
            yaxis: {{ title: 'Count' }}
        }});
    </script>
</body>
</html>
"""


def generate_dashboard(df: pl.DataFrame, output_path: str | Path) -> None:
    """Generate HTML dashboard from statistics DataFrame.

    Args:
        df: Statistics DataFrame with columns: date, repo_name, views_total, etc.
        output_path: Path to write HTML file.
    """
    import json

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate totals
    total_views = df["views_total"].sum() or 0
    unique_views = df["views_unique"].sum() or 0
    total_clones = df["clones_total"].sum() or 0
    unique_clones = df["clones_unique"].sum() or 0

    # Prepare time series data for Plotly
    repos = df["repo_name"].unique().sort().to_list()

    views_traces = []
    clones_traces = []

    for repo in repos:
        repo_df = df.filter(pl.col("repo_name") == repo).sort("date")
        dates = repo_df["date"].cast(pl.Utf8).to_list()
        views = repo_df["views_unique"].fill_null(0).to_list()
        clones = repo_df["clones_unique"].fill_null(0).to_list()

        views_traces.append(
            {
                "x": dates,
                "y": views,
                "type": "scatter",
                "mode": "lines+markers",
                "name": repo,
            }
        )

        clones_traces.append(
            {
                "x": dates,
                "y": clones,
                "type": "scatter",
                "mode": "lines+markers",
                "name": repo,
            }
        )

    # Comparison bar chart data
    summary = (
        df.group_by("repo_name")
        .agg(
            [
                pl.col("views_total").sum().alias("views"),
                pl.col("clones_total").sum().alias("clones"),
            ]
        )
        .sort("repo_name")
    )

    comparison_data = [
        {
            "x": summary["repo_name"].to_list(),
            "y": summary["views"].fill_null(0).to_list(),
            "type": "bar",
            "name": "Views",
        },
        {
            "x": summary["repo_name"].to_list(),
            "y": summary["clones"].fill_null(0).to_list(),
            "type": "bar",
            "name": "Clones",
        },
    ]

    # Generate HTML
    html = HTML_TEMPLATE.format(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        total_views=total_views,
        unique_views=unique_views,
        total_clones=total_clones,
        unique_clones=unique_clones,
        views_data=json.dumps(views_traces),
        clones_data=json.dumps(clones_traces),
        comparison_data=json.dumps(comparison_data),
    )

    output_path.write_text(html)
