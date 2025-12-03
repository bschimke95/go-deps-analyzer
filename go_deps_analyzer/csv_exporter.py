"""CSV export functionality for dependency analysis results."""

import csv
import logging
from pathlib import Path
from typing import List

from .models import ProjectConfig

logger = logging.getLogger(__name__)


class CSVExportError(Exception):
    """Custom exception for CSV export errors."""

    pass


class CSVExporter:
    """Handles CSV export of dependency analysis results."""

    def __init__(self, output_path: str):
        """Initialize CSVExporter with output file path.

        Args:
            output_path: Path where the CSV file will be written.

        Raises:
            CSVExportError: If the output path is invalid or file cannot be created.
        """
        self.output_path = Path(output_path)
        self.file_handle = None
        self.csv_writer = None
        self._summary_written = False
        self._detail_header_written = False

        try:
            # Create parent directories if they don't exist
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Open file with UTF-8 encoding
            self.file_handle = open(
                self.output_path, "w", newline="", encoding="utf-8"
            )
            self.csv_writer = csv.writer(self.file_handle)
            logger.info(f"CSV export initialized: {self.output_path}")
        except (OSError, IOError) as e:
            error_msg = f"Failed to create CSV file at {output_path}: {e}"
            logger.error(error_msg)
            raise CSVExportError(error_msg) from e

    def write_summary_header(self) -> None:
        """Write summary table header."""
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        # Write summary table header
        self.csv_writer.writerow([
            "Project", "Branch 1", "Branch 2", 
            "Unique Deps V1", "Unique Deps V2",
            "Added", "Removed", "Changed"
        ])
        self._summary_written = True

    def write_summary_row(
        self, 
        project_name: str, 
        branch1: str, 
        branch2: str, 
        unique_deps_v1: int,
        unique_deps_v2: int,
        added: int, 
        removed: int, 
        changed: int
    ) -> None:
        """Write a row to the summary table.

        Args:
            project_name: Name of the project.
            branch1: Name of the first branch for this project.
            branch2: Name of the second branch for this project.
            unique_deps_v1: Number of unique dependencies in version 1.
            unique_deps_v2: Number of unique dependencies in version 2.
            added: Count of added dependencies.
            removed: Count of removed dependencies.
            changed: Count of changed dependencies.
        """
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        self.csv_writer.writerow([
            project_name, branch1, branch2, 
            unique_deps_v1, unique_deps_v2,
            added, removed, changed
        ])

    def write_total_summary_row(
        self, 
        total_unique_deps_v1: int,
        total_unique_deps_v2: int,
        total_added: int, 
        total_removed: int, 
        total_changed: int
    ) -> None:
        """Write a total summary row.

        Args:
            total_unique_deps_v1: Total unique dependencies in version 1 across all projects.
            total_unique_deps_v2: Total unique dependencies in version 2 across all projects.
            total_added: Total count of added dependencies across all projects.
            total_removed: Total count of removed dependencies across all projects.
            total_changed: Total count of changed dependencies across all projects.
        """
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        self.csv_writer.writerow([
            "TOTAL", "", "", 
            total_unique_deps_v1, total_unique_deps_v2,
            total_added, total_removed, total_changed
        ])

    def write_blank_separator(self) -> None:
        """Write a blank row separator."""
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        self.csv_writer.writerow([])

    def write_detail_header(self) -> None:
        """Write detailed table header."""
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        if not self._detail_header_written:
            self.csv_writer.writerow(
                ["Project", "Module", "Change Type", "Old Versions", "New Versions"]
            )
            self._detail_header_written = True

    def write_detail_row(
        self,
        project_name: str,
        module_name: str,
        change_type: str,
        old_versions: List[str],
        new_versions: List[str],
    ) -> None:
        """Write a row to the detailed table.

        Args:
            project_name: Name of the project.
            module_name: Name of the module/dependency.
            change_type: Type of change (added, removed, changed).
            old_versions: List of old versions (empty for added).
            new_versions: List of new versions (empty for removed).
        """
        if not self.csv_writer:
            raise CSVExportError("CSV writer not initialized")

        # Join versions with semicolons
        old_versions_str = ";".join(old_versions) if old_versions else ""
        new_versions_str = ";".join(new_versions) if new_versions else ""

        self.csv_writer.writerow(
            [project_name, module_name, change_type, old_versions_str, new_versions_str]
        )

    def close(self) -> None:
        """Close the CSV file and flush all data."""
        if self.file_handle:
            try:
                self.file_handle.close()
                logger.info(f"CSV export completed: {self.output_path}")
            except Exception as e:
                logger.error(f"Error closing CSV file: {e}")
                raise CSVExportError(f"Failed to close CSV file: {e}") from e


def get_project_name(config: ProjectConfig) -> str:
    """Extract project name from ProjectConfig.

    Args:
        config: Project configuration object.

    Returns:
        Project name extracted from repo URL or local path.
    """
    if config.is_repo_based:
        # Extract from URL: https://github.com/org/repo.git -> repo
        repo_url = config.repo.rstrip("/")
        project_name = repo_url.split("/")[-1]
        # Remove .git suffix if present
        if project_name.endswith(".git"):
            project_name = project_name[:-4]
        return project_name
    else:
        # Extract from path: /path/to/project -> project
        return Path(config.path).name
