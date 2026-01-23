"""Tests for storage module."""

from datetime import date
from pathlib import Path

import polars as pl

from ghstats2.models import TrafficRecord
from ghstats2.storage import StatsStorage


class TestStatsStorage:
    """Tests for StatsStorage class."""

    def test_read_empty(self, temp_data_dir: Path) -> None:
        """Test reading from non-existent file returns empty DataFrame."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")
        df = storage.read()

        assert df.is_empty()
        assert "date" in df.columns

    def test_write_and_read(self, temp_data_dir: Path, sample_dataframe: pl.DataFrame) -> None:
        """Test writing and reading data."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")

        storage.write(sample_dataframe)
        df = storage.read()

        assert len(df) == 2
        assert df["repo_name"][0] == "floris"

    def test_upsert_new_records(
        self, temp_data_dir: Path, sample_records: list[TrafficRecord]
    ) -> None:
        """Test upserting new records into empty storage."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")

        count = storage.upsert(sample_records)

        assert count == 3
        df = storage.read()
        assert len(df) == 3

    def test_upsert_updates_existing(self, temp_data_dir: Path) -> None:
        """Test that upsert updates existing records by key."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")

        # Insert initial record
        initial = [
            TrafficRecord(
                record_date=date(2024, 1, 1),
                repo_owner="NatLabRockies",
                repo_name="floris",
                views_total=100,
                views_unique=50,
            )
        ]
        storage.upsert(initial)

        # Upsert with updated value (same key)
        updated = [
            TrafficRecord(
                record_date=date(2024, 1, 1),
                repo_owner="NatLabRockies",
                repo_name="floris",
                views_total=200,
                views_unique=80,
            )
        ]
        storage.upsert(updated)

        df = storage.read()
        assert len(df) == 1
        assert df["views_total"][0] == 200

    def test_upsert_empty_list(self, temp_data_dir: Path) -> None:
        """Test upserting empty list returns 0."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")

        count = storage.upsert([])

        assert count == 0

    def test_get_stats_with_filters(
        self, temp_data_dir: Path, sample_records: list[TrafficRecord]
    ) -> None:
        """Test filtering stats by repo and date."""
        storage = StatsStorage(temp_data_dir / "stats.parquet")
        storage.upsert(sample_records)

        # Filter by repo
        df = storage.get_stats(repo_name="floris")
        assert len(df) == 2
        assert df["repo_name"].to_list() == ["floris", "floris"]

        # Filter by date range
        df = storage.get_stats(start_date="2024-01-02")
        assert len(df) == 1
