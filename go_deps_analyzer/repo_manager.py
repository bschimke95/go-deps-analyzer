"""Repository management for cloning and cleaning up GitHub repositories."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Custom exception for repository management errors."""

    pass


class RepositoryManager:
    """Manages GitHub repository cloning and cleanup."""

    def __init__(self, repo_url: str):
        """Initialize with a GitHub repository URL.

        Args:
            repo_url: GitHub repository URL to clone.
        """
        self.repo_url = repo_url
        self.temp_dir: Optional[Path] = None

    def clone(self) -> str:
        """Clone the repository and return the local path.

        Returns:
            Path to the cloned repository as a string.

        Raises:
            RepositoryError: If cloning fails.
        """
        try:
            # Create temporary directory with recognizable prefix
            temp_dir_str = tempfile.mkdtemp(prefix="go-deps-analyzer-")
            self.temp_dir = Path(temp_dir_str)
            logger.info(f"Created temporary directory: {self.temp_dir}")

            # Execute git clone without depth limit to get all tags and branches
            # Note: We don't use --depth 1 because it doesn't fetch tags,
            # which are commonly used for version references
            logger.info(f"Cloning repository: {self.repo_url}")
            result = subprocess.run(
                ["git", "clone", self.repo_url, str(self.temp_dir)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            logger.info(f"Successfully cloned repository to {self.temp_dir}")
            return str(self.temp_dir)

        except subprocess.TimeoutExpired as e:
            self._cleanup_on_error()
            raise RepositoryError(
                f"Failed to clone repository '{self.repo_url}': operation timed out after 5 minutes"
            ) from e
        except subprocess.CalledProcessError as e:
            self._cleanup_on_error()
            error_msg = e.stderr.strip() if e.stderr else str(e)
            
            # Provide more specific error messages based on common failure patterns
            if "could not resolve host" in error_msg.lower() or "network" in error_msg.lower():
                raise RepositoryError(
                    f"Failed to clone repository '{self.repo_url}': network unreachable (check internet connection)"
                ) from e
            elif "repository not found" in error_msg.lower() or "not found" in error_msg.lower():
                raise RepositoryError(
                    f"Failed to clone repository '{self.repo_url}': repository not found or inaccessible"
                ) from e
            elif "authentication" in error_msg.lower() or "permission denied" in error_msg.lower():
                raise RepositoryError(
                    f"Failed to clone repository '{self.repo_url}': authentication required. "
                    f"Private repositories are currently not supported, please use the 'path' key instead"
                ) from e
            else:
                raise RepositoryError(
                    f"Failed to clone repository '{self.repo_url}': {error_msg}"
                ) from e
        except Exception as e:
            self._cleanup_on_error()
            raise RepositoryError(
                f"Unexpected error cloning repository '{self.repo_url}': {e}"
            ) from e

    def cleanup(self):
        """Remove the cloned repository directory.

        This method attempts to clean up the temporary directory and logs
        any errors that occur, but does not raise exceptions.
        """
        if self.temp_dir is None:
            return

        try:
            if self.temp_dir.exists():
                logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
                logger.info(f"Successfully removed temporary directory: {self.temp_dir}")
            self.temp_dir = None
        except Exception as e:
            logger.error(f"Failed to clean up temporary directory {self.temp_dir}: {e}")
            # Don't raise exception during cleanup

    def _cleanup_on_error(self):
        """Clean up temporary directory after an error during cloning."""
        if self.temp_dir is not None and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
            except Exception as e:
                logger.error(f"Failed to clean up after error: {e}")

    def __enter__(self):
        """Context manager entry: clone repository.

        Returns:
            The RepositoryManager instance.
        """
        self.clone()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: cleanup repository.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.

        Returns:
            False to propagate any exception that occurred.
        """
        self.cleanup()
        return False
