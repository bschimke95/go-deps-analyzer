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
    formatter.print_section_header(f"Project: {config.path}")

    try:
        git_manager = GitManager(config.path)
        analyzer = DependencyAnalyzer(config.path)
    except (GitError, AnalyzerError) as e:
        logger.error(f"Error initializing project: {e}")
        return

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
        logger.error(f"Failed to checkout {config.branch1}, skipping project")
        return

    actual_branch1 = git_manager.get_current_branch()
    print(f"\nAnalyzing branch: {actual_branch1}")

    try:
        dep_map1 = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        return

    formatter.print_dependency_stats(dep_map1, actual_branch1)

    # Analyze second branch
    if not git_manager.checkout_branch(config.branch2):
        logger.error(f"Failed to checkout {config.branch2}, skipping comparison")
        return

    actual_branch2 = git_manager.get_current_branch()
    print(f"\nAnalyzing branch: {actual_branch2}")

    try:
        dep_map2 = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        return

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
            logger.error(f"Failed to checkout {config.branch1}, skipping project")
            return

    branch = git_manager.get_current_branch()
    print(f"Branch: {branch}")

    try:
        dep_map = analyzer.get_dependencies()
    except AnalyzerError as e:
        logger.error(f"Error analyzing dependencies: {e}")
        return

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

    # Analyze each project
    for project_config in projects:
        try:
            analyze_project(project_config, formatter)
        except Exception as e:
            logger.error(f"Unexpected error analyzing project: {e}", exc_info=True)
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
