"""Command-line interface for the Go dependency analyzer."""

import argparse
import logging
import sys
from typing import List

from . import __version__
from .analyzer import AnalyzerError, DependencyAnalyzer
from .config import Config, ConfigError
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
        help="Branch to analyze (use with --project)",
    )
    parser.add_argument(
        "-B",
        "--branch2",
        type=str,
        help="Second branch for comparison (use with --project and --branch)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    return parser


def analyze_project(
    config: ProjectConfig,
    formatter: OutputFormatter,
) -> None:
    """Analyze a single project based on its configuration.

    Args:
        config: Project configuration.
        formatter: Output formatter for displaying results.
    """
    if config.is_repo_based:
        # Use repository manager for remote repos
        try:
            repo_manager = RepositoryManager(config.repo)
            with repo_manager:
                local_path = str(repo_manager.temp_dir)
                _perform_analysis(local_path, config, formatter)
        except RepositoryError as e:
            logger.error(f"Repository error for '{config.repo}': {e}")
            raise
    else:
        # Use path directly for local projects
        _perform_analysis(config.path, config, formatter)


def _perform_analysis(
    local_path: str,
    config: ProjectConfig,
    formatter: OutputFormatter,
) -> None:
    """Perform the actual analysis on a local path.

    Args:
        local_path: Local file system path to analyze.
        config: Project configuration.
        formatter: Output formatter for displaying results.
    """
    # Display project header with source type
    if config.is_repo_based:
        project_label = f"Project: {config.repo} (cloned to {local_path})"
    else:
        project_label = f"Project: {local_path}"
    
    formatter.print_section_header(project_label)

    try:
        git_manager = GitManager(local_path)
        analyzer = DependencyAnalyzer(local_path)
    except (GitError, AnalyzerError) as e:
        if config.is_repo_based:
            logger.error(f"Error initializing repository project '{config.repo}': {e}")
        else:
            logger.error(f"Error initializing local project '{config.path}': {e}")
        raise

    # Comparison mode: analyze two branches
    if config.is_comparison:
        _analyze_comparison_mode(config, git_manager, analyzer, formatter)

    # Single branch mode
    else:
        _analyze_single_mode(config, git_manager, analyzer, formatter)

    print(f"\n{'=' * 80}\n")


def _analyze_comparison_mode(
    config: ProjectConfig,
    git_manager: GitManager,
    analyzer: DependencyAnalyzer,
    formatter: OutputFormatter,
) -> None:
    """Analyze two branches for comparison.

    Args:
        config: Project configuration.
        git_manager: Git manager instance.
        analyzer: Dependency analyzer instance.
        formatter: Output formatter.
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
    formatter.print_comparison_results(result)


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

    # Create output formatter
    formatter = OutputFormatter(verbose=args.verbose)

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
        # Analyze each project
        for project_config in projects:
            try:
                analyze_project(project_config, formatter)
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
    finally:
        # Cleanup is handled by context managers in analyze_project
        pass

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
