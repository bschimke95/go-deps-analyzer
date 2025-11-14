"""Go Module Dependency Analyzer.

A tool to analyze Go module dependencies across different branches and projects.
"""

__version__ = "1.0.0"
__author__ = "Homayoon Alimohammadi"
__email__ = "homayoon.alimohammadi@gmail.com"

from .analyzer import DependencyAnalyzer
from .git_utils import GitManager
from .models import DependencyMap, ComparisonResult

__all__ = [
    "DependencyAnalyzer",
    "GitManager",
    "DependencyMap",
    "ComparisonResult",
]
