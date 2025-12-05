"""Output formatting and display utilities."""

from typing import TYPE_CHECKING

from .models import ComparisonResult, DependencyMap

if TYPE_CHECKING:
    from .csv_exporter import CSVExporter


class OutputFormatter:
    """Formats and displays analysis results."""

    def __init__(self, verbose: bool = False, csv_exporter: "CSVExporter | None" = None):
        """Initialize OutputFormatter.

        Args:
            verbose: Whether to display detailed output.
            csv_exporter: Optional CSV exporter for writing results to CSV.
        """
        self.verbose = verbose
        self.csv_exporter = csv_exporter

    def print_section_header(self, title: str, char: str = "=") -> None:
        """Print a formatted section header.

        Args:
            title: The title text.
            char: The character to use for the border.
        """
        print(f"\n{char * 80}")
        print(title)
        print(f"{char * 80}")

    def print_subsection_header(self, title: str) -> None:
        """Print a formatted subsection header.

        Args:
            title: The title text.
        """
        print(f"\n--- {title} ---")

    def print_dependency_stats(
        self, dep_map: DependencyMap, branch_name: str = "", project_name: str = ""
    ) -> None:
        """Print dependency statistics.

        Args:
            dep_map: The dependency map to analyze.
            branch_name: Optional branch name for context.
            project_name: Optional project name for CSV export.
        """
        multi_version_deps = dep_map.get_multi_version_deps()

        if branch_name:
            self.print_subsection_header(f"Statistics for branch: {branch_name}")
        print(f"Total unique dependencies: {len(dep_map)}")
        print(
            f"Dependencies with multiple versions: {len(multi_version_deps)}"
        )

        if self.verbose:
            self._print_all_dependencies(dep_map)

        # Write to CSV if exporter is available and in single-branch mode
        if self.csv_exporter and project_name:
            self._write_single_branch_to_csv(dep_map, project_name)

    def print_comparison_results(self, result: ComparisonResult, project_name: str = "") -> None:
        """Print comparison results between two branches.

        Args:
            result: The comparison result to display.
            project_name: Name of the project being analyzed.
        """
        print("\n" + "-" * 60)
        print(
            f"\nComparing dependencies between branches: "
            f"'{result.branch1}' -> '{result.branch2}'"
        )

        # New dependencies
        print(f"\nNew dependencies added in '{result.branch2}': {len(result.new_deps)}")
        if self.verbose:
            self._print_dependency_list(
                result.new_deps, result.dep_map2, prefix="+"
            )

        # Removed dependencies
        print(
            f"\nDependencies removed in '{result.branch2}': {len(result.removed_deps)}"
        )
        if self.verbose:
            self._print_dependency_list(
                result.removed_deps, result.dep_map1, prefix="-"
            )

        # Version changes
        print(
            f"\nDependencies with version changes: {len(result.version_changes)}"
        )
        if self.verbose and result.version_changes:
            self._print_version_changes(result)

        # Write to CSV if exporter is available
        if self.csv_exporter and project_name:
            self._write_to_csv(result, project_name)

    def _print_all_dependencies(self, dep_map: DependencyMap) -> None:
        """Print all dependencies with their version counts.

        Args:
            dep_map: The dependency map to display.
        """
        if not dep_map.dependencies:
            return

        print("\nAll dependencies with version counts:")
        sorted_deps = sorted(
            dep_map.dependencies.items(),
            key=lambda x: (-len(x[1]), x[0]),
        )
        for name, versions in sorted_deps:
            version_text = "version" if len(versions) == 1 else "versions"
            print(f"  {name}: {len(versions)} {version_text}")
            print(f"     ↳ {versions}")

    def _print_dependency_list(
        self,
        deps: set,
        dep_map: DependencyMap,
        prefix: str = "",
    ) -> None:
        """Print a list of dependencies with their versions.

        Args:
            deps: Set of dependency names.
            dep_map: Dependency map containing version information.
            prefix: Optional prefix for each line (e.g., '+' or '-').
        """
        if not deps:
            print("  (none)")
            return

        print()
        for dep in sorted(deps):
            versions = dep_map.get_versions(dep)
            print(f"  {prefix} {dep} {versions}")

    def _print_version_changes(self, result: ComparisonResult) -> None:
        """Print version changes for dependencies.

        Args:
            result: The comparison result containing version changes.
        """
        print()
        for dep, (old_versions, new_versions) in sorted(
            result.version_changes.items()
        ):
            print(f"  ~ {dep}")
            print(f"      {result.branch1}: {old_versions}")
            print(f"      {result.branch2}: {new_versions}")

    def _write_to_csv(self, result: ComparisonResult, project_name: str) -> None:
        """Write comparison results to CSV.

        Args:
            result: The comparison result to write.
            project_name: Name of the project.
        """
        if not self.csv_exporter:
            return

        # Write summary row with branch information
        added_count = len(result.new_deps)
        removed_count = len(result.removed_deps)
        changed_count = len(result.version_changes)
        unique_deps_v1 = len(result.dep_map1)
        unique_deps_v2 = len(result.dep_map2)
        
        self.csv_exporter.write_summary_row(
            project_name, result.branch1, result.branch2, 
            unique_deps_v1, unique_deps_v2,
            added_count, removed_count, changed_count
        )

        # Track totals for summary row
        if not hasattr(self.csv_exporter, '_totals'):
            self.csv_exporter._totals = {
                'added': 0, 
                'removed': 0, 
                'changed': 0,
                'unique_deps_v1': set(),  # Track unique modules across all projects
                'unique_deps_v2': set()   # Track unique modules across all projects
            }
        
        self.csv_exporter._totals['added'] += added_count
        self.csv_exporter._totals['removed'] += removed_count
        self.csv_exporter._totals['changed'] += changed_count
        # Add unique modules to sets instead of summing counts
        self.csv_exporter._totals['unique_deps_v1'].update(result.dep_map1.dependencies.keys())
        self.csv_exporter._totals['unique_deps_v2'].update(result.dep_map2.dependencies.keys())

        # Store detail rows for later writing (will be written after all projects)
        if not hasattr(self.csv_exporter, '_detail_rows'):
            self.csv_exporter._detail_rows = []

        # Collect all detail rows for sorting
        detail_rows = []

        # Added dependencies
        for dep in result.new_deps:
            new_versions = result.dep_map2.get_versions(dep)
            detail_rows.append((project_name, dep, "added", [], new_versions))

        # Removed dependencies
        for dep in result.removed_deps:
            old_versions = result.dep_map1.get_versions(dep)
            detail_rows.append((project_name, dep, "removed", old_versions, []))

        # Changed dependencies
        for dep, (old_versions, new_versions) in result.version_changes.items():
            detail_rows.append((project_name, dep, "changed", old_versions, new_versions))

        # Sort alphabetically by module name
        detail_rows.sort(key=lambda x: x[1])

        # Store for later writing
        self.csv_exporter._detail_rows.extend(detail_rows)

    def _write_single_branch_to_csv(self, dep_map: DependencyMap, project_name: str) -> None:
        """Collect single-branch dependency data for later aggregation.

        Args:
            dep_map: The dependency map to collect.
            project_name: Name of the project.
        """
        if not self.csv_exporter:
            return

        # Mark that we're in single-branch mode
        if not hasattr(self.csv_exporter, '_single_branch_mode'):
            self.csv_exporter._single_branch_mode = True
            self.csv_exporter._aggregated_deps = {}

        # Aggregate dependencies across all projects
        for module_name, versions in dep_map.dependencies.items():
            if module_name not in self.csv_exporter._aggregated_deps:
                self.csv_exporter._aggregated_deps[module_name] = set()
            self.csv_exporter._aggregated_deps[module_name].update(versions)
