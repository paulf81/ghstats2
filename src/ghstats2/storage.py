"""File-based statistics storage using Parquet format."""

from pathlib import Path

import polars as pl

from ghstats2.models import TrafficRecord

STATS_SCHEMA = {
    "date": pl.Date,
    "repo_owner": pl.Utf8,
    "repo_name": pl.Utf8,
    "clones_total": pl.Int64,
    "clones_unique": pl.Int64,
    "views_total": pl.Int64,
    "views_unique": pl.Int64,
    "forks_count": pl.Int64,
    "stars_count": pl.Int64,
    "collected_at": pl.Utf8,
}


class StatsStorage:
    """File-based statistics storage using Parquet format.

    Handles upsert logic to merge new data with existing records,
    deduplicating by (date, repo_owner, repo_name) composite key.

    Attributes:
        data_path: Path to the Parquet file.
    """

    def __init__(self, data_path: Path):
        """Initialize storage with path to data file.

        Args:
            data_path: Path to the Parquet file for storing stats.
        """
        self.data_path = data_path

    def read(self) -> pl.DataFrame:
        """Load existing stats or return empty DataFrame.

        Returns:
            DataFrame with existing statistics or empty DataFrame with schema.
        """
        if not self.data_path.exists():
            return pl.DataFrame(schema=STATS_SCHEMA)

        return pl.read_parquet(self.data_path)

    def write(self, df: pl.DataFrame) -> None:
        """Write DataFrame to Parquet file.

        Args:
            df: DataFrame to write.
        """
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(self.data_path)

    def upsert(self, new_records: list[TrafficRecord]) -> int:
        """Merge new records with existing data.

        Updates existing records by key (date, repo_owner, repo_name)
        or inserts new ones. Returns count of records added/updated.

        Args:
            new_records: List of TrafficRecord to upsert.

        Returns:
            Number of records that were added or updated.
        """
        if not new_records:
            return 0

        # Convert records to DataFrame
        new_data = [r.to_dict() for r in new_records]
        new_df = pl.DataFrame(new_data, schema=STATS_SCHEMA)

        # Load existing data
        existing_df = self.read()

        if existing_df.is_empty():
            self.write(new_df)
            return len(new_records)

        # Key columns for deduplication
        key_cols = ["date", "repo_owner", "repo_name"]

        # Merge: new records take precedence over existing
        # First, filter out existing records that have matching keys in new data
        merged_df = (
            existing_df.join(
                new_df.select(key_cols),
                on=key_cols,
                how="anti",
            )
            .vstack(new_df)
            .sort(["repo_owner", "repo_name", "date"])
        )

        self.write(merged_df)
        return len(new_records)

    def get_stats(
        self,
        repo_name: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pl.DataFrame:
        """Query statistics with optional filters.

        Args:
            repo_name: Filter by repository name.
            start_date: Filter records on or after this date (YYYY-MM-DD).
            end_date: Filter records on or before this date (YYYY-MM-DD).

        Returns:
            Filtered DataFrame of statistics.
        """
        df = self.read()

        if df.is_empty():
            return df

        if repo_name:
            df = df.filter(pl.col("repo_name") == repo_name)

        if start_date:
            df = df.filter(pl.col("date") >= pl.lit(start_date).str.to_date())

        if end_date:
            df = df.filter(pl.col("date") <= pl.lit(end_date).str.to_date())

        return df.sort(["repo_owner", "repo_name", "date"])
