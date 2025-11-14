"""Core dependency analysis functionality."""

import logging
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .models import ComparisonResult, DependencyMap

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Custom exception for analyzer-related errors."""

    pass


class DependencyAnalyzer:
    """Analyzes Go module dependencies."""

    def __init__(self, project_dir: str):
        """Initialize DependencyAnalyzer.

        Args:
            project_dir: Path to the Go project.
        """
        self.project_dir = Path(project_dir)
        if not self.project_dir.exists():
            raise AnalyzerError(
                f"Project directory does not exist: {project_dir}"
            )

    def get_dependencies(self) -> DependencyMap:
        """Run `go mod graph` and return a dependency map.

        Returns:
            DependencyMap containing module names and their versions.

        Raises:
            AnalyzerError: If `go mod graph` fails.
        """
        try:
            result = subprocess.run(
                ["go", "mod", "graph"],
                cwd=self.project_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise AnalyzerError(
                f"Error running `go mod graph`: {e.stderr.strip()}"
            ) from e

        dep_map: Dict[str, Set[str]] = defaultdict(set)

        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) != 2:
                continue

            for mod in parts:
                if "@" not in mod:
                    # Root module might not have a version
                    dep_map[mod].add("")
                    continue
                name, version = mod.split("@", 1)
                dep_map[name].add(version)

        # Convert to sorted lists
        dependencies = {k: sorted(v) for k, v in sorted(dep_map.items())}
        return DependencyMap(dependencies=dependencies)

    @staticmethod
    def compare_dependencies(
        dep_map1: DependencyMap,
        dep_map2: DependencyMap,
        branch1: str,
        branch2: str,
    ) -> ComparisonResult:
        """Compare two dependency maps.

        Args:
            dep_map1: First dependency map (base).
            dep_map2: Second dependency map (comparison).
            branch1: Name of the first branch.
            branch2: Name of the second branch.

        Returns:
            ComparisonResult containing the differences.
        """
        deps1 = dep_map1.get_dependency_names()
        deps2 = dep_map2.get_dependency_names()

        new_deps = deps2 - deps1
        removed_deps = deps1 - deps2

        # Check for version changes in common dependencies
        common_deps = deps1 & deps2
        version_changes: Dict[str, Tuple[List[str], List[str]]] = {}

        for dep in common_deps:
            v1 = set(dep_map1.get_versions(dep))
            v2 = set(dep_map2.get_versions(dep))
            if v1 != v2:
                version_changes[dep] = (
                    dep_map1.get_versions(dep),
                    dep_map2.get_versions(dep),
                )

        return ComparisonResult(
            branch1=branch1,
            branch2=branch2,
            new_deps=new_deps,
            removed_deps=removed_deps,
            version_changes=version_changes,
            dep_map1=dep_map1,
            dep_map2=dep_map2,
        )
