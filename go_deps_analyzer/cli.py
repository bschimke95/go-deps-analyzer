"""Command-line interface for the Go dependency analyzer."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from . import __version__
from .analyzer import AnalyzerError, DependencyAnalyzer
from .config import Config, ConfigError
from .csv_exporter import CSVExportError, CSVExporter, get_project_name
from .git_utils import GitError, GitManager
from .models import ProjectConfig
from .output import OutputFormatter
from .repo_manager import RepositoryError, RepositoryManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_argparser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser.

    Returns:
        Configured ArgumentParser object.
    """
    parser = argparse.ArgumentParser(
        description="Analyze Go module dependencies across branches and projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze using a config file
  %(prog)s -c config.yaml

  # Analyze a single project on current branch
  %(prog)s -p /path/to/project

  # Analyze a single project on a specific branch
  %(prog)s -p /path/to/project -b v1.0.0

  # Compare two branches
  %(prog)s -p /path/to/project -b v1.0.0 -B v2.0.0

  # Verbose output
  %(prog)s -c config.yaml -v

  # Export results to CSV
  %(prog)s -c config.yaml -o results.csv

  # Export with verbose console output
  %(prog)s -c config.yaml -v -o results.csv
        """,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed dependency lists",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file (YAML)",
    )
    parser.add_argument(
        "-p",
        "--project",
        type=str,
        help="Path to a single project to analyze",
    )
    parser.add_argument(
        "-b",
        "--branch",
        type=str,
        help="Branch or tag to analyze (use with --project)",
    )
    parser.add_argument(
        "-B",
        "--branch2",
        type=str,
        help="Second branch or tag for comparison (use with --project and --branch)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "-o",
        "--csv-output",
        type=str,
        help="Path to CSV file for exporting analysis results",
    )

    return parser


def analyze_project(
    config: ProjectConfig,
    formatter: OutputFormatter,
    project_name: str = "",
) -> None:
    """Analyze a single project based on its configuration.

    Args:
        config: Project configuration.
        formatter: Output formatter for displaying results.
        project_name: Name of the project for CSV export.
    """
    if config.is_repo_based:
        # Use repository manager for remote repos
        try:
            repo_manager = RepositoryManager(config.repo)
            with repo_manager:
                local_path = str(repo_manager.temp_dir)
                _perform_analysis(local_path, config, formatter, project_name)
        except RepositoryError as e:
            logger.error(f"Repository error for '{config.repo}': {e}")
            raise
    else:
        # Use path directly for local projects
        _perform_analysis(config.path, config, formatter, project_name)


def _perform_analysis(
    local_path: str,
    config: ProjectConfig,
    formatter: OutputFormatter,
    project_name: str = "",
) -> None:
    """Perform the actual analysis on a local path.

    Args:
        local_path: Local file system path to analyze.
        config: Project configuration.
        formatter: Output formatter for displaying results.
        project_name: Name of the project for CSV export.
    """
    # Combine with src_dir if specified
    analysis_path = local_path
    if config.src_dir:
        analysis_path = str(Path(local_path) / config.src_dir)
        
        # Validate that the combined path exists
        if not Path(analysis_path).exists():
            raise AnalyzerError(
                f"Source directory not found: {config.src_dir} "
                f"(full path: {analysis_path})"
            )
    
    # Display project header with source type
    if config.is_repo_based:
        if config.src_dir:
            project_label = f"Project: {config.repo} (src: {config.src_dir})"
        else:
            project_label = f"Project: {config.repo}"
    else:
        project_label = f"Project: {local_path}"
    
    formatter.print_section_header(project_label)

    try:
        git_manager = GitManager(local_path)  # Still use repo root for git operations
        analyzer = DependencyAnalyzer(analysis_path)  # Use src_dir for analysis
    except (GitError, AnalyzerError) as e:
        if config.is_repo_based:
            logger.error(f"Error initializing repository project '{config.repo}': {e}")
        else:
            logger.error(f"Error initializing local project '{config.path}': {e}")
        raise

    # Comparison mode: analyze two branches
    if config.is_comparison:
        _analyze_comparison_mode(config, git_manager, analyzer, formatter, project_name)

    # Single branch mode
    else:
        _analyze_single_mode(config, git_manager, analyzer, formatter)

    print(f"\n{'=' * 80}\n")


def _analyze_comparison_mode(
    config: ProjectConfig,
    git_manager: GitManager,
    analyzer: DependencyAnalyzer,
    formatter: OutputFormatter,
    project_name: str = "",
) -> None:
    """Analyze two branches for comparison.

    Args:
        config: Project configuration.
        git_manager: Git manager instance.
        analyzer: Dependency analyzer instance.
        formatter: Output formatter.
        project_name: Name of the project for CSV export.
    """
    # Analyze first branch
    if not git_manager.checkout_branch(config.branch1):
        error_msg = f"Failed to checkout {config.branch1}, skipping project"
        logger.error(error_msg)
        raise GitError(error_msg)

    actual_branch1 = git_manager.get_current_branch()
    print(f"\nAnalyzing branch: {actual_branch1}")

    try:
        dep_map1 = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        raise

    formatter.print_dependency_stats(dep_map1, actual_branch1)

    # Analyze second branch
    if not git_manager.checkout_branch(config.branch2):
        error_msg = f"Failed to checkout {config.branch2}, skipping comparison"
        logger.error(error_msg)
        raise GitError(error_msg)

    actual_branch2 = git_manager.get_current_branch()
    print(f"\nAnalyzing branch: {actual_branch2}")

    try:
        dep_map2 = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        raise

    formatter.print_dependency_stats(dep_map2, actual_branch2)

    # Compare the two branches
    result = DependencyAnalyzer.compare_dependencies(
        dep_map1, dep_map2, actual_branch1, actual_branch2
    )
    formatter.print_comparison_results(result, project_name)


def _analyze_single_mode(
    config: ProjectConfig,
    git_manager: GitManager,
    analyzer: DependencyAnalyzer,
    formatter: OutputFormatter,
) -> None:
    """Analyze a single branch.

    Args:
        config: Project configuration.
        git_manager: Git manager instance.
        analyzer: Dependency analyzer instance.
        formatter: Output formatter.
    """
    if config.branch1:
        if not git_manager.checkout_branch(config.branch1):
            error_msg = f"Failed to checkout {config.branch1}, skipping project"
            logger.error(error_msg)
            raise GitError(error_msg)

    branch = git_manager.get_current_branch()
    print(f"Branch: {branch}")

    try:
        dep_map = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        raise

    formatter.print_dependency_stats(dep_map, branch)


def main(argv: List[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = setup_argparser()
    args = parser.parse_args(argv)

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create CSV exporter if output path is provided
    # Use a temporary file that will be moved to final location only on success
    csv_exporter = None
    temp_csv_path = None
    if args.csv_output:
        try:
            import tempfile
            # Create temporary file in the same directory as the target
            target_path = Path(args.csv_output)
            temp_fd, temp_csv_path = tempfile.mkstemp(
                suffix='.csv.tmp',
                dir=target_path.parent if target_path.parent.exists() else None,
                prefix='.tmp_'
            )
            import os
            os.close(temp_fd)  # Close the file descriptor, CSVExporter will open it
            csv_exporter = CSVExporter(temp_csv_path)
        except CSVExportError as e:
            logger.error(f"Failed to initialize CSV export: {e}")
            if temp_csv_path and Path(temp_csv_path).exists():
                Path(temp_csv_path).unlink()
            return 1

    # Create output formatter
    formatter = OutputFormatter(verbose=args.verbose, csv_exporter=csv_exporter)

    # Determine project configurations
    projects: List[ProjectConfig] = []

    if args.config:
        try:
            projects = Config.load_from_file(args.config)
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
            return 1
    elif args.project:
        projects = [
            ProjectConfig(
                path=args.project,
                branch1=args.branch,
                branch2=args.branch2,
            )
        ]
    else:
        parser.print_help()
        return 1

    if not projects:
        logger.error("No projects configured for analysis")
        return 1

    # Track repository managers for cleanup
    repo_managers: List[RepositoryManager] = []
    has_errors = False

    try:
        # Write CSV summary header if exporter is available
        if csv_exporter:
            csv_exporter.write_summary_header()

        # Analyze each project
        for project_config in projects:
            try:
                # Extract project name for CSV export
                project_name = get_project_name(project_config) if csv_exporter else ""
                analyze_project(project_config, formatter, project_name)
            except (RepositoryError, GitError, AnalyzerError) as e:
                # Log the error with project context
                project_id = project_config.repo if project_config.is_repo_based else project_config.path
                logger.error(f"Error analyzing project '{project_id}': {e}")
                has_errors = True
                # Abort processing on first error as per requirement 4.3
                break
            except Exception as e:
                project_id = project_config.repo if project_config.is_repo_based else project_config.path
                logger.error(f"Unexpected error analyzing project '{project_id}': {e}", exc_info=True)
                has_errors = True
                # Abort processing on first error
                break

        # Write total summary row and detail table if CSV export is enabled
        if csv_exporter and not has_errors:
            # Write total summary row
            if hasattr(csv_exporter, '_totals'):
                csv_exporter.write_total_summary_row(
                    csv_exporter._totals['unique_deps_v1'],
                    csv_exporter._totals['unique_deps_v2'],
                    csv_exporter._totals['added'],
                    csv_exporter._totals['removed'],
                    csv_exporter._totals['changed']
                )
            
            csv_exporter.write_blank_separator()
            csv_exporter.write_detail_header()
            
            # Write all collected detail rows
            if hasattr(csv_exporter, '_detail_rows'):
                for project_name, module_name, change_type, old_versions, new_versions in csv_exporter._detail_rows:
                    csv_exporter.write_detail_row(
                        project_name, module_name, change_type, old_versions, new_versions
                    )
    finally:
        # Close CSV exporter
        if csv_exporter:
            try:
                csv_exporter.close()
            except CSVExportError as e:
                logger.error(f"Error closing CSV file: {e}")
                has_errors = True
            
            # Move temp file to final location on success, or delete it on failure
            if temp_csv_path:
                temp_path = Path(temp_csv_path)
                final_path = Path(args.csv_output)
                
                if has_errors:
                    # Delete temporary file on failure
                    try:
                        if temp_path.exists():
                            temp_path.unlink()
                            logger.info(f"Removed temporary CSV file due to errors")
                    except Exception as e:
                        logger.error(f"Failed to delete temporary CSV file: {e}")
                else:
                    # Move temporary file to final location on success
                    try:
                        import shutil
                        shutil.move(str(temp_path), str(final_path))
                        logger.info(f"CSV export completed: {args.csv_output}")
                    except Exception as e:
                        logger.error(f"Failed to move CSV file to final location: {e}")
                        has_errors = True
                        # Try to clean up temp file
                        if temp_path.exists():
                            temp_path.unlink()

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
