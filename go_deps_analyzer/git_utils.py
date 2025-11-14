"""Git utilities for managing branches and repositories."""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Custom exception for Git-related errors."""

    pass


class GitManager:
    """Manages Git operations for a repository."""

    def __init__(self, project_dir: str):
        """Initialize GitManager.

        Args:
            project_dir: Path to the Git repository.
        """
        self.project_dir = Path(project_dir)
        if not self.project_dir.exists():
            raise GitError(f"Project directory does not exist: {project_dir}")

    def get_current_branch(self) -> str:
        """Get the current Git branch name or tag name.

        Returns:
            The current branch or tag name, or 'N/A' if unable to determine.
        """
        try:
            # First, try to get the branch name
            result = self._run_git_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            )
            branch_or_head = result.strip()

            # If it's HEAD (detached state, likely a tag), try to get the tag name
            if branch_or_head == "HEAD":
                result = self._run_git_command(
                    ["git", "describe", "--tags", "--exact-match"]
                )
                return result.strip()

            return branch_or_head
        except GitError:
            logger.warning(
                f"Unable to determine branch for {self.project_dir}"
            )
            return "N/A"

    def checkout_branch(self, branch: Optional[str] = None) -> bool:
        """Checkout to a specific branch if specified.

        Args:
            branch: Branch name to checkout. If None, no checkout is performed.

        Returns:
            True if checkout was successful or not needed, False otherwise.
        """
        if branch is None:
            return True

        try:
            self._run_git_command(["git", "checkout", branch])
            logger.info(f"Checked out branch '{branch}' in {self.project_dir}")
            return True
        except GitError as e:
            logger.error(f"Error checking out branch '{branch}': {e}")
            return False

    def _run_git_command(self, command: list[str]) -> str:
        """Run a Git command and return its output.

        Args:
            command: Git command as a list of strings.

        Returns:
            Command output as a string.

        Raises:
            GitError: If the command fails.
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {e.stderr.strip()}") from e
