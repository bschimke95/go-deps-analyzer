"""Command-line interface for the Go dependency analyzer."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from . import __version__
from .analyzer import AnalyzerError, DependencyAnalyzer
from .config import Config, ConfigError
from .cross_config_stats import (
    CrossConfigAnalyzer,
    CSVParseError,
    OutputFormatter as CrossConfigOutputFormatter,
)
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
  
  # Cross-configuration statistics
  %(prog)s cross-config-stats --configs config1.yaml config2.yaml --csv-dir ./output
        """,
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add cross-config-stats subcommand
    cross_config_parser = subparsers.add_parser(
        'cross-config-stats',
        help='Analyze dependencies across multiple configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two configurations
  %(prog)s --configs config1.yaml config2.yaml --csv-dir ./output
  
  # Output to CSV file
  %(prog)s --configs config1.yaml config2.yaml --csv-dir ./output --output stats.csv --format csv
  
  # Output to JSON file
  %(prog)s --configs config1.yaml config2.yaml --csv-dir ./output --output stats.json --format json
  
  # Output to text file
  %(prog)s --configs config1.yaml config2.yaml --csv-dir ./output --output stats.txt --format text
        """
    )
    
    cross_config_parser.add_argument(
        '--configs',
        nargs='+',
        required=True,
        help='Paths to configuration YAML files to compare'
    )
    
    cross_config_parser.add_argument(
        '--csv-dir',
        required=True,
        help='Directory containing CSV output files'
    )
    
    cross_config_parser.add_argument(
        '--output',
        help='Path to output file (if not specified, prints to stdout)'
    )
    
    cross_config_parser.add_argument(
        '--format',
        choices=['text', 'json', 'csv'],
        default='text',
        help='Output format (default: text)'
    )
    
    cross_config_parser.add_argument(
        '--log-level',
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )
    
    # Regular command arguments (when no subcommand is used)
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
        _analyze_single_mode(config, git_manager, analyzer, formatter, project_name)

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
    project_name: str = "",
) -> None:
    """Analyze a single branch.

    Args:
        config: Project configuration.
        git_manager: Git manager instance.
        analyzer: Dependency analyzer instance.
        formatter: Output formatter.
        project_name: Name of the project for CSV export.
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

    formatter.print_dependency_stats(dep_map, branch, project_name)


def handle_cross_config_stats(args) -> int:
    """Handle the cross-config-stats subcommand.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Create analyzer
        analyzer = CrossConfigAnalyzer(args.configs, args.csv_dir)
        
        # Run analysis
        logger.info("Loading configurations...")
        stats = analyzer.analyze()
        
        # Format output
        if args.format == 'json':
            output = CrossConfigOutputFormatter.format_json(stats)
        elif args.format == 'csv':
            output = CrossConfigOutputFormatter.format_csv(stats)
        else:
            output = CrossConfigOutputFormatter.format_text(stats)
        
        # Write to file or stdout
        if args.output:
            CrossConfigOutputFormatter.write_to_file(output, args.output)
            logger.info(f"Results written to {args.output}")
        else:
            print(output)
        
        return 0
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except CSVParseError as e:
        logger.error(f"CSV parsing error: {e}")
        return 1
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


def main(argv: List[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = setup_argparser()
    args = parser.parse_args(argv)
    
    # Handle cross-config-stats subcommand
    if args.command == 'cross-config-stats':
        return handle_cross_config_stats(args)

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
        # Determine if we're in comparison mode or single-branch mode
        is_comparison_mode = any(p.is_comparison for p in projects)
        
        # Write CSV summary header if exporter is available and in comparison mode
        if csv_exporter and is_comparison_mode:
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

        # Write total summary row and detail table if CSV export is enabled and in comparison mode
        if csv_exporter and not has_errors and is_comparison_mode:
            # Write total summary row
            if hasattr(csv_exporter, '_totals'):
                # Convert sets to counts for unique modules
                unique_v1_count = len(csv_exporter._totals['unique_deps_v1'])
                unique_v2_count = len(csv_exporter._totals['unique_deps_v2'])
                csv_exporter.write_total_summary_row(
                    unique_v1_count,
                    unique_v2_count,
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
        
        # Write aggregated single-branch dependencies if in single-branch mode
        if csv_exporter and not has_errors and not is_comparison_mode:
            if hasattr(csv_exporter, '_single_branch_mode') and hasattr(csv_exporter, '_aggregated_deps'):
                from .csv_exporter import analyze_version_differences
                
                # Compute statistics
                unique_modules = len(csv_exporter._aggregated_deps)
                (modules_with_multiple_major, modules_with_multiple_minor, 
                 modules_with_multiple_patch, total_module_versions) = analyze_version_differences(
                    csv_exporter._aggregated_deps
                )
                
                # Write summary statistics
                csv_exporter.write_single_branch_summary_header()
                csv_exporter.write_single_branch_summary_row("Unique Modules", unique_modules)
                csv_exporter.write_single_branch_summary_row("Total Module Versions", total_module_versions)
                csv_exporter.write_single_branch_summary_row("Modules with Multiple Major Versions", modules_with_multiple_major)
                csv_exporter.write_single_branch_summary_row("Modules with Multiple Minor Versions", modules_with_multiple_minor)
                csv_exporter.write_single_branch_summary_row("Modules with Multiple Patch Versions", modules_with_multiple_patch)
                
                # Write blank separator
                csv_exporter.write_blank_separator()
                
                # Write dependency details
                csv_exporter.write_single_branch_header()
                # Sort by module name and write each entry
                for module_name in sorted(csv_exporter._aggregated_deps.keys()):
                    versions = sorted(csv_exporter._aggregated_deps[module_name])
                    csv_exporter.write_single_branch_row(module_name, versions)
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
