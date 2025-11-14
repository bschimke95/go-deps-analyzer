"""Data models for dependency analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class DependencyMap:
    """Represents a mapping of module names to their versions."""

    dependencies: Dict[str, List[str]] = field(default_factory=dict)

    def __len__(self) -> int:
        """Return the number of unique dependencies."""
        return len(self.dependencies)

    def get_multi_version_deps(self) -> Dict[str, List[str]]:
        """Return dependencies that have multiple versions."""
        return {
            name: versions
            for name, versions in self.dependencies.items()
            if len(versions) > 1
        }

    def get_dependency_names(self) -> Set[str]:
        """Return a set of all dependency names."""
        return set(self.dependencies.keys())

    def get_versions(self, dep_name: str) -> List[str]:
        """Get versions for a specific dependency."""
        return self.dependencies.get(dep_name, [])


@dataclass
class ComparisonResult:
    """Results from comparing two dependency maps."""

    branch1: str
    branch2: str
    new_deps: Set[str] = field(default_factory=set)
    removed_deps: Set[str] = field(default_factory=set)
    version_changes: Dict[str, Tuple[List[str], List[str]]] = field(
        default_factory=dict
    )
    dep_map1: DependencyMap = field(default_factory=DependencyMap)
    dep_map2: DependencyMap = field(default_factory=DependencyMap)

    def has_changes(self) -> bool:
        """Check if there are any changes between the two branches."""
        return bool(
            self.new_deps or self.removed_deps or self.version_changes
        )


@dataclass
class ProjectConfig:
    """Configuration for a project to analyze."""

    path: str
    branch1: str | None = None
    branch2: str | None = None

    @property
    def is_comparison(self) -> bool:
        """Check if this is a comparison between two branches."""
        return self.branch1 is not None and self.branch2 is not None

    @property
    def is_single_branch(self) -> bool:
        """Check if this analyzes a single branch."""
        return self.branch1 is not None and self.branch2 is None
