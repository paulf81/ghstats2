"""Shared test fixtures."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from ghstats2.models import TrafficRecord


@pytest.fixture
def sample_records() -> list[TrafficRecord]:
    """Sample traffic records for testing."""
    return [
        TrafficRecord(
            record_date=date(2024, 1, 1),
            repo_owner="NatLabRockies",
            repo_name="floris",
            views_total=100,
            views_unique=50,
            clones_total=10,
            clones_unique=5,
            forks_count=20,
            stars_count=100,
        ),
        TrafficRecord(
            record_date=date(2024, 1, 2),
            repo_owner="NatLabRockies",
            repo_name="floris",
            views_total=150,
            views_unique=60,
            clones_total=15,
            clones_unique=8,
            forks_count=20,
            stars_count=101,
        ),
        TrafficRecord(
            record_date=date(2024, 1, 1),
            repo_owner="NatLabRockies",
            repo_name="flasc",
            views_total=50,
            views_unique=25,
            clones_total=5,
            clones_unique=3,
            forks_count=10,
            stars_count=50,
        ),
    ]


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Temporary directory for test data files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Sample DataFrame for testing."""
    return pl.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "repo_owner": ["NatLabRockies", "NatLabRockies"],
            "repo_name": ["floris", "floris"],
            "clones_total": [10, 15],
            "clones_unique": [5, 8],
            "views_total": [100, 150],
            "views_unique": [50, 60],
            "forks_count": [20, 20],
            "stars_count": [100, 101],
            "collected_at": ["2024-01-01T12:00:00Z", "2024-01-02T12:00:00Z"],
        }
    )
