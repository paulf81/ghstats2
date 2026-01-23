"""Tests for CLI commands."""

from click.testing import CliRunner

from ghstats2.cli import main


class TestCLI:
    """Tests for CLI commands."""

    def test_main_help(self) -> None:
        """Test main help output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "GitHub statistics collector" in result.output

    def test_collect_help(self) -> None:
        """Test collect command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["collect", "--help"])

        assert result.exit_code == 0
        assert "--repo" in result.output
        assert "--dry-run" in result.output

    def test_show_help(self) -> None:
        """Test show command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["show", "--help"])

        assert result.exit_code == 0
        assert "--days" in result.output

    def test_report_help(self) -> None:
        """Test report command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["report", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output

    def test_list_repos_no_config(self) -> None:
        """Test list command with no config."""
        runner = CliRunner()
        result = runner.invoke(main, ["list"])

        # Should handle missing config gracefully
        assert result.exit_code == 0
