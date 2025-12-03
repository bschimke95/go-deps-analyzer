"""Configuration management for the analyzer."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from .models import ProjectConfig

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


class Config:
    """Manages configuration for the analyzer."""

    @staticmethod
    def load_from_file(config_path: str) -> List[ProjectConfig]:
        """Load project configurations from a YAML file.

        Args:
            config_path: Path to the configuration file.

        Returns:
            List of ProjectConfig objects.

        Raises:
            ConfigError: If the configuration file is invalid.
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict) or "projects" not in data:
                raise ConfigError(
                    "Invalid configuration: must contain 'projects' key"
                )

            return [
                Config._parse_project_config(proj)
                for proj in data["projects"]
            ]
        except yaml.YAMLError as e:
            raise ConfigError(f"Error parsing YAML: {e}") from e

    @staticmethod
    def _parse_project_config(
        proj_data: Union[str, Dict[str, Any]]
    ) -> ProjectConfig:
        """Parse a project configuration entry.

        Args:
            proj_data: Project configuration data (string or dict).

        Returns:
            ProjectConfig object.

        Raises:
            ConfigError: If the configuration is invalid.
        """
        # Legacy format: string means path
        if isinstance(proj_data, str):
            return ProjectConfig(path=proj_data)

        if not isinstance(proj_data, dict):
            raise ConfigError(
                "Invalid project configuration format: must be a string or dictionary"
            )

        # Define valid configuration keys
        valid_keys = {"path", "repo", "branch1", "branch2", "src_dir"}
        
        # Check for unknown keys
        unknown_keys = set(proj_data.keys()) - valid_keys
        if unknown_keys:
            error_msg = (
                f"Unknown configuration key(s): {', '.join(sorted(unknown_keys))}. "
                f"Valid keys are: {', '.join(sorted(valid_keys))}"
            )
            
            # Provide helpful hint for common mistake
            if "src-dir" in unknown_keys:
                error_msg += ". Note: use 'src_dir' (underscore) not 'src-dir' (hyphen)"
            
            raise ConfigError(error_msg)

        # Extract fields
        path = proj_data.get("path")
        repo = proj_data.get("repo")
        branch1 = proj_data.get("branch1")
        branch2 = proj_data.get("branch2")
        src_dir = proj_data.get("src_dir")

        # Validation happens in ProjectConfig.__post_init__
        try:
            return ProjectConfig(
                path=path,
                repo=repo,
                branch1=branch1,
                branch2=branch2,
                src_dir=src_dir,
            )
        except ValueError as e:
            raise ConfigError(f"Invalid project configuration: {e}") from e

    @staticmethod
    def parse_legacy_format(
        proj_entry: Union[str, tuple]
    ) -> ProjectConfig:
        """Parse legacy configuration format.

        Args:
            proj_entry: Project entry in old format (string or tuple).

        Returns:
            ProjectConfig object.
        """
        if isinstance(proj_entry, tuple):
            proj_dir = proj_entry[0]
            branch1 = proj_entry[1] if len(proj_entry) > 1 else None
            branch2 = proj_entry[2] if len(proj_entry) > 2 else None
        else:
            proj_dir = proj_entry
            branch1 = None
            branch2 = None

        return ProjectConfig(path=proj_dir, branch1=branch1, branch2=branch2)
