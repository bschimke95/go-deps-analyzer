"""Data models for dependency analysis."""

import os
from dataclasses import dataclass, field
from pathlib import Path
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
    """Results from comparing two dependency maps.
    
    Attributes:
        branch1: First branch or tag name.
        branch2: Second branch or tag name.
    """

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
        """Check if there are any changes between the two branches or tags."""
        return bool(
            self.new_deps or self.removed_deps or self.version_changes
        )


@dataclass
class ProjectConfig:
    """Configuration for a project to analyze.
    
    Attributes:
        path: Local file system path to the project (mutually exclusive with repo).
        repo: GitHub repository URL (mutually exclusive with path).
        branch1: First branch or tag to analyze.
        branch2: Second branch or tag for comparison (optional).
        src_dir: Subdirectory within repo containing go.mod (only valid with repo).
    """

    path: str | None = None
    repo: str | None = None
    branch1: str | None = None
    branch2: str | None = None
    src_dir: str | None = None

    def __post_init__(self):
        """Validate configuration constraints."""
        # Validate that exactly one of path or repo is provided
        if (self.path is None) == (self.repo is None):
            raise ValueError("Exactly one of 'path' or 'repo' must be provided")
        
        # Validate that src_dir is only used with repo
        if self.src_dir is not None and self.repo is None:
            raise ValueError("'src_dir' can only be used with 'repo', not 'path'")
        
        # Validate that src_dir is a relative path
        if self.src_dir is not None:
            if os.path.isabs(self.src_dir):
                raise ValueError("'src_dir' must be a relative path from repository root")
            if '..' in Path(self.src_dir).parts:
                raise ValueError("'src_dir' cannot contain '..' path traversal")

    @property
    def is_repo_based(self) -> bool:
        """Check if this config uses a GitHub repository."""
        return self.repo is not None

    @property
    def is_comparison(self) -> bool:
        """Check if this is a comparison between two branches or tags."""
        return self.branch1 is not None and self.branch2 is not None

    @property
    def is_single_branch(self) -> bool:
        """Check if this analyzes a single branch or tag."""
        return self.branch1 is not None and self.branch2 is None
