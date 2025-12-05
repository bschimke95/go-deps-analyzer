"""Cross-configuration dependency statistics analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class OverlapStats:
    """Overlap statistics between two configurations.
    
    Attributes:
        config1: Name of the first configuration.
        config2: Name of the second configuration.
        shared_count: Number of dependencies shared between both configurations.
        config1_only: Number of dependencies unique to config1.
        config2_only: Number of dependencies unique to config2.
        overlap_percentage: Percentage of overlap (shared / union * 100).
    """
    
    config1: str
    config2: str
    shared_count: int
    config1_only: int
    config2_only: int
    overlap_percentage: float


@dataclass
class ConfigDependencySet:
    """Dependency set for a single configuration.
    
    Attributes:
        config_name: Name of the configuration.
        config_path: Path to the configuration YAML file.
        csv_path: Path to the CSV file containing dependency data.
        dependencies: Set of unique dependency module names.
        dependency_versions: Dict mapping module names to sets of versions.
        project_count: Number of projects in this configuration.
    """
    
    config_name: str
    config_path: str
    csv_path: str
    dependencies: Set[str] = field(default_factory=set)
    dependency_versions: Dict[str, Set[str]] = field(default_factory=dict)
    project_count: int = 0


@dataclass
class VersionDifferenceStats:
    """Statistics about version differences for a module across configurations.
    
    Attributes:
        module: Module name.
        versions: Set of all versions across configurations.
        version_count: Number of different versions.
        has_patch_diff: True if versions differ only in patch level.
        has_minor_diff: True if versions differ in minor level.
        has_major_diff: True if versions differ in major level.
    """
    
    module: str
    versions: Set[str] = field(default_factory=set)
    version_count: int = 0
    has_patch_diff: bool = False
    has_minor_diff: bool = False
    has_major_diff: bool = False


@dataclass
class CrossConfigStats:
    """Statistics computed across multiple configurations.
    
    Attributes:
        config_names: List of configuration names being analyzed.
        unique_counts: Mapping of config name to unique dependency count.
        shared_dependencies: Set of (module, version) tuples present in all configurations.
        config_specific: Mapping of config name to its unique (module, version) tuples.
        pairwise_overlap: Mapping of config pairs to their overlap statistics.
        total_unique_across_all: Total number of unique (module, version) pairs across all configs.
        version_differences: Dict mapping modules to their version difference stats.
        modules_with_patch_diff: Number of modules with only patch-level differences.
        modules_with_minor_diff: Number of modules with minor-level differences.
        modules_with_major_diff: Number of modules with major-level differences.
    """
    
    config_names: List[str] = field(default_factory=list)
    unique_counts: Dict[str, int] = field(default_factory=dict)
    shared_dependencies: Set[Tuple[str, str]] = field(default_factory=set)
    config_specific: Dict[str, Set[Tuple[str, str]]] = field(default_factory=dict)
    pairwise_overlap: Dict[Tuple[str, str], OverlapStats] = field(default_factory=dict)
    total_unique_across_all: int = 0
    version_differences: Dict[str, VersionDifferenceStats] = field(default_factory=dict)
    modules_with_patch_diff: int = 0
    modules_with_minor_diff: int = 0
    modules_with_major_diff: int = 0



import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CSVParseError(Exception):
    """Custom exception for CSV parsing errors."""
    pass


class CSVDependencyParser:
    """Parses CSV files to extract dependency information."""
    
    @staticmethod
    def parse_csv(csv_path: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """Parse CSV and return dependency module names and their versions.
        
        Args:
            csv_path: Path to the CSV file to parse.
            
        Returns:
            Tuple of (set of module names, dict mapping module names to version sets).
            
        Raises:
            CSVParseError: If the CSV file cannot be parsed.
            FileNotFoundError: If the CSV file doesn't exist.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        dependencies = set()
        dependency_versions = {}
        in_detail_section = False
        is_single_branch_format = False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                
                for row_num, row in enumerate(reader, start=1):
                    # Skip empty rows
                    if not row or all(cell.strip() == '' for cell in row):
                        continue
                    
                    # Check for single-branch format header (Module, Versions)
                    if row_num == 1 and len(row) == 2 and row[0].strip().lower() == 'module' and row[1].strip().lower() == 'versions':
                        is_single_branch_format = True
                        continue
                    
                    # Parse single-branch format
                    if is_single_branch_format and len(row) >= 2:
                        module_name = row[0].strip()
                        versions_str = row[1].strip()
                        
                        if module_name:
                            # Normalize module name
                            normalized = CSVDependencyParser._normalize_module_name(module_name)
                            dependencies.add(normalized)
                            
                            # Parse versions (semicolon-separated)
                            if versions_str:
                                versions = set(v.strip() for v in versions_str.split(';') if v.strip())
                                if normalized not in dependency_versions:
                                    dependency_versions[normalized] = set()
                                dependency_versions[normalized].update(versions)
                        continue
                    
                    # Check if we've reached the detail section (comparison format)
                    if CSVDependencyParser._is_detail_section(row):
                        in_detail_section = True
                        continue
                    
                    # Parse dependency rows in detail section (comparison format)
                    if in_detail_section and len(row) >= 5:
                        # Row format: Project, Module, Change Type, Old Versions, New Versions
                        module_name = row[1].strip()
                        change_type = row[2].strip().lower()
                        new_versions_str = row[4].strip()
                        
                        if module_name:
                            # Normalize module name
                            normalized = CSVDependencyParser._normalize_module_name(module_name)
                            dependencies.add(normalized)
                            
                            # Extract versions - use "New Versions" for added/changed, "Old Versions" for removed
                            if change_type == 'removed':
                                versions_str = row[3].strip()
                            else:
                                versions_str = new_versions_str
                            
                            # Parse versions (semicolon-separated)
                            if versions_str:
                                versions = set(v.strip() for v in versions_str.split(';') if v.strip())
                                if normalized not in dependency_versions:
                                    dependency_versions[normalized] = set()
                                dependency_versions[normalized].update(versions)
            
            logger.info(f"Extracted {len(dependencies)} unique dependencies from {csv_path}")
            return dependencies, dependency_versions
            
        except csv.Error as e:
            raise CSVParseError(f"Error parsing CSV at line {row_num}: {e}") from e
        except Exception as e:
            raise CSVParseError(f"Unexpected error parsing CSV: {e}") from e
    
    @staticmethod
    def _is_detail_section(row: List[str]) -> bool:
        """Check if we've reached the detailed table section.
        
        The detail section starts with a header row containing:
        "Project", "Module", "Change Type", "Old Versions", "New Versions"
        
        Args:
            row: CSV row to check.
            
        Returns:
            True if this is the detail section header.
        """
        if len(row) < 3:
            return False
        
        # Check for the characteristic header
        return (row[0].strip().lower() == 'project' and 
                row[1].strip().lower() == 'module' and
                row[2].strip().lower() == 'change type')
    
    @staticmethod
    def _normalize_module_name(module_name: str) -> str:
        """Normalize module name by removing version information.
        
        Module names may contain version info like:
        - github.com/foo/bar v1.2.3
        - github.com/foo/bar@v1.2.3
        
        We want just: github.com/foo/bar
        
        Args:
            module_name: Raw module name from CSV.
            
        Returns:
            Normalized module name without version.
        """
        # Remove everything after space (version separator)
        if ' ' in module_name:
            module_name = module_name.split(' ')[0]
        
        # Remove everything after @ (alternative version separator)
        if '@' in module_name:
            module_name = module_name.split('@')[0]
        
        return module_name.strip()



from .config import Config, ConfigError
from .models import ProjectConfig


class ConfigurationLoader:
    """Loads and manages multiple configuration files."""
    
    @staticmethod
    def load_configurations(config_paths: List[str]) -> Dict[str, List[ProjectConfig]]:
        """Load multiple configuration files.
        
        Args:
            config_paths: List of paths to configuration YAML files.
            
        Returns:
            Dictionary mapping config names to their project configurations.
            
        Raises:
            ConfigError: If any configuration file fails to load.
        """
        configurations = {}
        errors = []
        
        for config_path in config_paths:
            try:
                # Derive config name from filename (without extension)
                config_name = Path(config_path).stem
                
                # Load the configuration using existing Config class
                projects = Config.load_from_file(config_path)
                
                configurations[config_name] = projects
                logger.info(f"Loaded configuration '{config_name}' with {len(projects)} projects")
                
            except ConfigError as e:
                error_msg = f"Failed to load configuration from {config_path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
            except FileNotFoundError:
                error_msg = f"Configuration file not found: {config_path}"
                logger.error(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Unexpected error loading {config_path}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # If any errors occurred, raise with all error messages
        if errors:
            raise ConfigError(f"Failed to load {len(errors)} configuration(s):\n" + "\n".join(errors))
        
        if not configurations:
            raise ConfigError("No configurations were successfully loaded")
        
        return configurations



class DependencyExtractor:
    """Extracts dependencies from CSV files for configurations."""
    
    def __init__(self, csv_dir: str):
        """Initialize with directory containing CSV files.
        
        Args:
            csv_dir: Directory path where CSV files are located.
        """
        self.csv_dir = Path(csv_dir)
        if not self.csv_dir.exists():
            raise ValueError(f"CSV directory does not exist: {csv_dir}")
    
    def extract_all(self, configurations: Dict[str, List[ProjectConfig]]) -> Dict[str, ConfigDependencySet]:
        """Extract dependencies for all configurations.
        
        Args:
            configurations: Dictionary mapping config names to project lists.
            
        Returns:
            Dictionary mapping config names to their ConfigDependencySet.
        """
        dependency_sets = {}
        
        for config_name, projects in configurations.items():
            try:
                dep_set = self._extract_for_config(config_name, projects)
                dependency_sets[config_name] = dep_set
                logger.info(f"Extracted {len(dep_set.dependencies)} dependencies for '{config_name}'")
            except FileNotFoundError as e:
                logger.warning(f"Skipping '{config_name}': {e}")
            except CSVParseError as e:
                logger.warning(f"Error parsing CSV for '{config_name}': {e}")
        
        if not dependency_sets:
            raise ValueError("No dependencies could be extracted from any configuration")
        
        return dependency_sets
    
    def _extract_for_config(self, config_name: str, projects: List[ProjectConfig]) -> ConfigDependencySet:
        """Extract dependencies for a single configuration.
        
        Args:
            config_name: Name of the configuration.
            projects: List of projects in this configuration.
            
        Returns:
            ConfigDependencySet with extracted dependencies.
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist.
            CSVParseError: If CSV parsing fails.
        """
        # Construct expected CSV path: {config_name}.csv
        csv_path = self.csv_dir / f"{config_name}.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Parse CSV to extract dependencies and versions
        dependencies, dependency_versions = CSVDependencyParser.parse_csv(str(csv_path))
        
        # Create ConfigDependencySet
        return ConfigDependencySet(
            config_name=config_name,
            config_path="",  # Not needed for this use case
            csv_path=str(csv_path),
            dependencies=dependencies,
            dependency_versions=dependency_versions,
            project_count=len(projects)
        )



from itertools import combinations
import re


class VersionAnalyzer:
    """Analyzes semantic version differences."""
    
    @staticmethod
    def parse_semver(version: str) -> Tuple[int, int, int]:
        """Parse semantic version string into (major, minor, patch).
        
        Args:
            version: Version string (e.g., "v1.2.3", "1.2.3").
            
        Returns:
            Tuple of (major, minor, patch) as integers, or (0, 0, 0) if parsing fails.
        """
        # Remove 'v' prefix if present
        version = version.lstrip('v')
        
        # Try to extract major.minor.patch
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        # Try major.minor
        match = re.match(r'^(\d+)\.(\d+)', version)
        if match:
            return (int(match.group(1)), int(match.group(2)), 0)
        
        # Try just major
        match = re.match(r'^(\d+)', version)
        if match:
            return (int(match.group(1)), 0, 0)
        
        return (0, 0, 0)
    
    @staticmethod
    def analyze_version_differences(versions: Set[str]) -> Tuple[bool, bool, bool]:
        """Analyze what level of version differences exist.
        
        Args:
            versions: Set of version strings.
            
        Returns:
            Tuple of (has_patch_diff, has_minor_diff, has_major_diff).
        """
        if len(versions) <= 1:
            return (False, False, False)
        
        parsed_versions = [VersionAnalyzer.parse_semver(v) for v in versions]
        
        # Extract unique major, minor, patch values
        majors = set(v[0] for v in parsed_versions)
        minors = set(v[1] for v in parsed_versions)
        patches = set(v[2] for v in parsed_versions)
        
        has_major_diff = len(majors) > 1
        has_minor_diff = len(minors) > 1
        has_patch_diff = len(patches) > 1
        
        return (has_patch_diff, has_minor_diff, has_major_diff)


class StatsComputer:
    """Computes statistical metrics on dependency sets."""
    
    @staticmethod
    def compute_unique_counts(dep_sets: Dict[str, Set[str]]) -> Dict[str, int]:
        """Count unique dependencies for each configuration.
        
        Args:
            dep_sets: Dictionary mapping config names to dependency sets.
            
        Returns:
            Dictionary mapping config names to their unique dependency counts.
        """
        return {config_name: len(deps) for config_name, deps in dep_sets.items()}
    
    @staticmethod
    def compute_shared_dependencies(
        dep_sets: Dict[str, ConfigDependencySet]
    ) -> Set[Tuple[str, str]]:
        """Find dependencies with same versions present in all configurations.
        
        Args:
            dep_sets: Dictionary mapping config names to ConfigDependencySet objects.
            
        Returns:
            Set of (module, version) tuples present in all configurations.
        """
        if not dep_sets:
            return set()
        
        # Build sets of (module, version) tuples for each config
        config_module_versions = {}
        for config_name, dep_set in dep_sets.items():
            module_versions = set()
            for module, versions in dep_set.dependency_versions.items():
                for version in versions:
                    module_versions.add((module, version))
            config_module_versions[config_name] = module_versions
        
        # Compute intersection of all sets
        all_sets = list(config_module_versions.values())
        if len(all_sets) == 1:
            return all_sets[0].copy()
        
        shared = all_sets[0].copy()
        for dep_set in all_sets[1:]:
            shared &= dep_set
        
        return shared
    
    @staticmethod
    def compute_config_specific(
        dep_sets: Dict[str, ConfigDependencySet]
    ) -> Dict[str, Set[Tuple[str, str]]]:
        """Find dependencies with versions unique to each configuration.
        
        Args:
            dep_sets: Dictionary mapping config names to ConfigDependencySet objects.
            
        Returns:
            Dictionary mapping config names to their unique (module, version) tuples.
        """
        # Build sets of (module, version) tuples for each config
        config_module_versions = {}
        for config_name, dep_set in dep_sets.items():
            module_versions = set()
            for module, versions in dep_set.dependency_versions.items():
                for version in versions:
                    module_versions.add((module, version))
            config_module_versions[config_name] = module_versions
        
        config_specific = {}
        for config_name, deps in config_module_versions.items():
            # Get union of all other configurations
            other_deps = set()
            for other_name, other_set in config_module_versions.items():
                if other_name != config_name:
                    other_deps |= other_set
            
            # Unique deps are those not in any other config
            unique = deps - other_deps
            config_specific[config_name] = unique
        
        return config_specific
    
    @staticmethod
    def compute_version_differences(
        dep_sets: Dict[str, ConfigDependencySet]
    ) -> Dict[str, VersionDifferenceStats]:
        """Analyze version differences for modules across configurations.
        
        Args:
            dep_sets: Dictionary mapping config names to ConfigDependencySet objects.
            
        Returns:
            Dictionary mapping module names to their version difference statistics.
        """
        # Collect all versions for each module across all configs
        module_all_versions = {}
        for dep_set in dep_sets.values():
            for module, versions in dep_set.dependency_versions.items():
                if module not in module_all_versions:
                    module_all_versions[module] = set()
                module_all_versions[module].update(versions)
        
        # Analyze version differences for modules that appear in multiple configs
        version_diffs = {}
        for module, versions in module_all_versions.items():
            if len(versions) > 1:
                has_patch, has_minor, has_major = VersionAnalyzer.analyze_version_differences(versions)
                version_diffs[module] = VersionDifferenceStats(
                    module=module,
                    versions=versions,
                    version_count=len(versions),
                    has_patch_diff=has_patch,
                    has_minor_diff=has_minor,
                    has_major_diff=has_major
                )
        
        return version_diffs
    
    @staticmethod
    def compute_pairwise_overlap(
        dep_sets: Dict[str, ConfigDependencySet]
    ) -> Dict[Tuple[str, str], OverlapStats]:
        """Calculate overlap percentage for each pair of configurations.
        
        Args:
            dep_sets: Dictionary mapping config names to ConfigDependencySet objects.
            
        Returns:
            Dictionary mapping config pairs to their overlap statistics.
        """
        # Build sets of (module, version) tuples for each config
        config_module_versions = {}
        for config_name, dep_set in dep_sets.items():
            module_versions = set()
            for module, versions in dep_set.dependency_versions.items():
                for version in versions:
                    module_versions.add((module, version))
            config_module_versions[config_name] = module_versions
        
        pairwise = {}
        
        # Generate all unique pairs
        config_names = list(dep_sets.keys())
        for config1, config2 in combinations(config_names, 2):
            set1 = config_module_versions[config1]
            set2 = config_module_versions[config2]
            
            # Calculate statistics
            shared = set1 & set2
            union = set1 | set2
            config1_only = set1 - set2
            config2_only = set2 - set1
            
            # Calculate overlap percentage
            overlap_pct = (len(shared) / len(union) * 100) if union else 0.0
            
            stats = OverlapStats(
                config1=config1,
                config2=config2,
                shared_count=len(shared),
                config1_only=len(config1_only),
                config2_only=len(config2_only),
                overlap_percentage=overlap_pct
            )
            
            pairwise[(config1, config2)] = stats
        
        return pairwise
    
    @staticmethod
    def compute_all_statistics(dep_sets: Dict[str, ConfigDependencySet]) -> CrossConfigStats:
        """Compute all statistics for the given dependency sets.
        
        Args:
            dep_sets: Dictionary mapping config names to ConfigDependencySet objects.
            
        Returns:
            CrossConfigStats object with all computed statistics.
        """
        # Build module-version sets for each config
        config_module_versions = {}
        for config_name, dep_set in dep_sets.items():
            module_versions = set()
            for module, versions in dep_set.dependency_versions.items():
                for version in versions:
                    module_versions.add((module, version))
            config_module_versions[config_name] = module_versions
        
        # Compute unique counts (number of module-version pairs)
        unique_counts = {name: len(mvs) for name, mvs in config_module_versions.items()}
        
        # Compute shared dependencies (module-version pairs in all configs)
        shared_deps = StatsComputer.compute_shared_dependencies(dep_sets)
        
        # Compute config-specific dependencies
        config_specific = StatsComputer.compute_config_specific(dep_sets)
        
        # Compute pairwise overlap
        pairwise = StatsComputer.compute_pairwise_overlap(dep_sets)
        
        # Calculate total unique module-version pairs across all configs
        all_module_versions = set()
        for mvs in config_module_versions.values():
            all_module_versions |= mvs
        
        # Analyze version differences across configurations
        version_differences = StatsComputer.compute_version_differences(dep_sets)
        
        # Count modules by difference type
        modules_with_patch_diff = sum(1 for vd in version_differences.values() 
                                      if vd.has_patch_diff and not vd.has_minor_diff and not vd.has_major_diff)
        modules_with_minor_diff = sum(1 for vd in version_differences.values() 
                                      if vd.has_minor_diff and not vd.has_major_diff)
        modules_with_major_diff = sum(1 for vd in version_differences.values() 
                                      if vd.has_major_diff)
        
        return CrossConfigStats(
            config_names=list(dep_sets.keys()),
            unique_counts=unique_counts,
            shared_dependencies=shared_deps,
            config_specific=config_specific,
            pairwise_overlap=pairwise,
            total_unique_across_all=len(all_module_versions),
            version_differences=version_differences,
            modules_with_patch_diff=modules_with_patch_diff,
            modules_with_minor_diff=modules_with_minor_diff,
            modules_with_major_diff=modules_with_major_diff
        )



class CrossConfigAnalyzer:
    """Main orchestrator for cross-configuration dependency analysis."""
    
    def __init__(self, config_paths: List[str], csv_dir: str):
        """Initialize the analyzer.
        
        Args:
            config_paths: List of paths to configuration YAML files.
            csv_dir: Directory containing CSV output files.
        """
        self.config_paths = config_paths
        self.csv_dir = csv_dir
        self.configurations = {}
        self.dependency_sets = {}
    
    def load_configurations(self) -> Dict[str, List[ProjectConfig]]:
        """Load all configuration files.
        
        Returns:
            Dictionary mapping config names to their project configurations.
            
        Raises:
            ConfigError: If configuration loading fails.
        """
        self.configurations = ConfigurationLoader.load_configurations(self.config_paths)
        return self.configurations
    
    def extract_dependencies(self) -> Dict[str, ConfigDependencySet]:
        """Extract dependencies from CSV files for all configurations.
        
        Returns:
            Dictionary mapping config names to their ConfigDependencySet.
            
        Raises:
            ValueError: If no dependencies could be extracted.
        """
        if not self.configurations:
            raise ValueError("No configurations loaded. Call load_configurations() first.")
        
        extractor = DependencyExtractor(self.csv_dir)
        self.dependency_sets = extractor.extract_all(self.configurations)
        return self.dependency_sets
    
    def compute_statistics(self) -> CrossConfigStats:
        """Compute all statistics across configurations.
        
        Returns:
            CrossConfigStats object with all computed statistics.
            
        Raises:
            ValueError: If no dependency sets are available.
        """
        if not self.dependency_sets:
            raise ValueError("No dependency sets available. Call extract_dependencies() first.")
        
        return StatsComputer.compute_all_statistics(self.dependency_sets)
    
    def analyze(self) -> CrossConfigStats:
        """Run the complete analysis workflow.
        
        This is a convenience method that runs all steps in sequence:
        1. Load configurations
        2. Extract dependencies
        3. Compute statistics
        
        Returns:
            CrossConfigStats object with all computed statistics.
        """
        self.load_configurations()
        self.extract_dependencies()
        return self.compute_statistics()



import json


class OutputFormatter:
    """Formats statistics for display or export."""
    
    @staticmethod
    def format_csv(stats: CrossConfigStats) -> str:
        """Format statistics as CSV.
        
        Args:
            stats: CrossConfigStats object to format.
            
        Returns:
            CSV formatted string.
        """
        lines = []
        
        # Summary table
        lines.append("Configuration,Unique Dependencies,Shared Dependencies,Config-Specific Dependencies")
        for config_name in sorted(stats.config_names):
            unique_count = stats.unique_counts[config_name]
            config_specific_count = len(stats.config_specific.get(config_name, set()))
            lines.append(f"{config_name},{unique_count},{len(stats.shared_dependencies)},{config_specific_count}")
        
        # Total row
        lines.append(f"TOTAL,{stats.total_unique_across_all},{len(stats.shared_dependencies)},")
        
        # Blank separator
        lines.append("")
        
        # Version difference statistics
        lines.append("Version Difference Type,Count")
        lines.append(f"Modules with Patch-level differences only,{stats.modules_with_patch_diff}")
        lines.append(f"Modules with Minor-level differences,{stats.modules_with_minor_diff}")
        lines.append(f"Modules with Major-level differences,{stats.modules_with_major_diff}")
        lines.append(f"Total modules with version differences,{len(stats.version_differences)}")
        
        # Blank separator
        lines.append("")
        
        # Modules with multiple versions (sorted by version count, descending)
        lines.append("Module,Version Count,Versions")
        sorted_version_diffs = sorted(
            stats.version_differences.items(),
            key=lambda x: x[1].version_count,
            reverse=True
        )
        for module, vd in sorted_version_diffs:
            versions_str = ";".join(sorted(vd.versions))
            lines.append(f"{module},{vd.version_count},{versions_str}")
        
        # Blank separator
        lines.append("")
        
        # Pairwise overlap table
        if len(stats.config_names) > 1:
            lines.append("Config 1,Config 2,Shared Count,Config 1 Only,Config 2 Only,Overlap %")
            for (config1, config2), overlap in sorted(stats.pairwise_overlap.items()):
                lines.append(f"{config1},{config2},{overlap.shared_count},{overlap.config1_only},{overlap.config2_only},{overlap.overlap_percentage:.2f}")
            
            # Blank separator
            lines.append("")
        
        # Shared dependencies detail
        lines.append("Dependency Type,Configuration,Module,Version")
        for module, version in sorted(stats.shared_dependencies):
            lines.append(f"Shared,ALL,{module},{version}")
        
        # Configuration-specific dependencies
        for config_name in sorted(stats.config_names):
            specific = stats.config_specific.get(config_name, set())
            for module, version in sorted(specific):
                lines.append(f"Config-Specific,{config_name},{module},{version}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_text(stats: CrossConfigStats) -> str:
        """Format statistics as human-readable text.
        
        Args:
            stats: CrossConfigStats object to format.
            
        Returns:
            Formatted text string.
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("CROSS-CONFIGURATION DEPENDENCY ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary section
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Configurations analyzed: {len(stats.config_names)}")
        lines.append(f"Total unique dependencies across all: {stats.total_unique_across_all}")
        lines.append(f"Shared dependencies (in all configs): {len(stats.shared_dependencies)}")
        lines.append("")
        lines.append("VERSION DIFFERENCES")
        lines.append(f"  Modules with patch-level differences only: {stats.modules_with_patch_diff}")
        lines.append(f"  Modules with minor-level differences: {stats.modules_with_minor_diff}")
        lines.append(f"  Modules with major-level differences: {stats.modules_with_major_diff}")
        lines.append(f"  Total modules with version differences: {len(stats.version_differences)}")
        lines.append("")
        
        # Unique counts per configuration
        lines.append("UNIQUE DEPENDENCY COUNTS PER CONFIGURATION")
        lines.append("-" * 80)
        for config_name in sorted(stats.config_names):
            count = stats.unique_counts[config_name]
            lines.append(f"  {config_name}: {count}")
        lines.append("")
        
        # Modules with multiple versions
        lines.append("MODULES WITH MULTIPLE VERSIONS (sorted by version count)")
        lines.append("-" * 80)
        sorted_version_diffs = sorted(
            stats.version_differences.items(),
            key=lambda x: x[1].version_count,
            reverse=True
        )
        # Show top 20 to keep output manageable
        for module, vd in sorted_version_diffs[:20]:
            versions_list = ", ".join(sorted(vd.versions))
            lines.append(f"  {module} ({vd.version_count} versions): {versions_list}")
        
        if len(sorted_version_diffs) > 20:
            lines.append(f"  ... and {len(sorted_version_diffs) - 20} more modules with version differences")
        lines.append("")
        
        # Shared dependencies
        lines.append("SHARED DEPENDENCIES (same module and version in all configurations)")
        lines.append("-" * 80)
        if stats.shared_dependencies:
            for module, version in sorted(stats.shared_dependencies):
                lines.append(f"  {module} @ {version}")
        else:
            lines.append("  (none)")
        lines.append("")
        
        # Configuration-specific dependencies
        lines.append("CONFIGURATION-SPECIFIC DEPENDENCIES")
        lines.append("-" * 80)
        for config_name in sorted(stats.config_names):
            specific = stats.config_specific.get(config_name, set())
            lines.append(f"\n{config_name} ({len(specific)} unique):")
            if specific:
                for module, version in sorted(specific):
                    lines.append(f"  {module} @ {version}")
            else:
                lines.append("  (all dependencies are shared)")
        lines.append("")
        
        # Pairwise overlap
        if len(stats.config_names) > 1:
            lines.append("PAIRWISE OVERLAP STATISTICS")
            lines.append("-" * 80)
            for (config1, config2), overlap in sorted(stats.pairwise_overlap.items()):
                lines.append(f"\n{config1} vs {config2}:")
                lines.append(f"  Shared: {overlap.shared_count}")
                lines.append(f"  Only in {config1}: {overlap.config1_only}")
                lines.append(f"  Only in {config2}: {overlap.config2_only}")
                lines.append(f"  Overlap: {overlap.overlap_percentage:.2f}%")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_json(stats: CrossConfigStats) -> str:
        """Format statistics as JSON.
        
        Args:
            stats: CrossConfigStats object to format.
            
        Returns:
            JSON string.
        """
        # Convert sets of tuples to sorted lists of dicts for JSON serialization
        shared_deps_list = [
            {"module": module, "version": version}
            for module, version in sorted(stats.shared_dependencies)
        ]
        
        config_specific_dict = {}
        for name, deps in stats.config_specific.items():
            config_specific_dict[name] = [
                {"module": module, "version": version}
                for module, version in sorted(deps)
            ]
        
        # Version differences
        version_diffs_list = []
        for module, vd in sorted(stats.version_differences.items()):
            version_diffs_list.append({
                "module": module,
                "versions": sorted(vd.versions),
                "version_count": vd.version_count,
                "has_patch_diff": vd.has_patch_diff,
                "has_minor_diff": vd.has_minor_diff,
                "has_major_diff": vd.has_major_diff
            })
        
        data = {
            "config_names": stats.config_names,
            "total_unique_across_all": stats.total_unique_across_all,
            "unique_counts": stats.unique_counts,
            "shared_dependencies": shared_deps_list,
            "shared_count": len(stats.shared_dependencies),
            "config_specific": config_specific_dict,
            "version_difference_summary": {
                "modules_with_patch_diff": stats.modules_with_patch_diff,
                "modules_with_minor_diff": stats.modules_with_minor_diff,
                "modules_with_major_diff": stats.modules_with_major_diff,
                "total_modules_with_differences": len(stats.version_differences)
            },
            "version_differences": version_diffs_list,
            "pairwise_overlap": [
                {
                    "config1": overlap.config1,
                    "config2": overlap.config2,
                    "shared_count": overlap.shared_count,
                    "config1_only": overlap.config1_only,
                    "config2_only": overlap.config2_only,
                    "overlap_percentage": round(overlap.overlap_percentage, 2)
                }
                for overlap in stats.pairwise_overlap.values()
            ]
        }
        
        return json.dumps(data, indent=2)
    
    @staticmethod
    def write_to_file(content: str, output_path: str) -> None:
        """Write formatted output to a file.
        
        Args:
            content: Content to write.
            output_path: Path to output file.
            
        Raises:
            IOError: If file writing fails.
        """
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Output written to {output_path}")
        except Exception as e:
            raise IOError(f"Failed to write output to {output_path}: {e}") from e
