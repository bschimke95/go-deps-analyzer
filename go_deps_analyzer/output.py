"""Output formatting and display utilities."""


from .models import ComparisonResult, DependencyMap


class OutputFormatter:
    """Formats and displays analysis results."""

    def __init__(self, verbose: bool = False):
        """Initialize OutputFormatter.

        Args:
            verbose: Whether to display detailed output.
        """
        self.verbose = verbose

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
        self, dep_map: DependencyMap, branch_name: str = ""
    ) -> None:
        """Print dependency statistics.

        Args:
            dep_map: The dependency map to analyze.
            branch_name: Optional branch name for context.
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

    def print_comparison_results(self, result: ComparisonResult) -> None:
        """Print comparison results between two branches.

        Args:
            result: The comparison result to display.
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
