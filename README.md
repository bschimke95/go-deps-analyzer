# Go Dependency Analyzer

A Python tool to analyze Go module dependencies across different branches and projects. This tool helps you understand dependency changes, compare versions, and track Go module updates across your projects.

## Features

- 📊 Analyze Go module dependencies for any project
- 🔄 Compare dependencies between two branches, tags, or commits
- 📦 Batch analysis of multiple projects using configuration files
- 🌐 **Support for GitHub repositories** - automatically clone and analyze remote repositories
- 📈 Detailed statistics including total, direct, and indirect dependencies
- 🎯 Identify added, removed, and version-changed dependencies
- 🔍 Verbose mode for detailed dependency lists
- 🌳 Works with any Git branch, tag, or commit reference
- 🔀 **Mix local paths and remote repositories** in the same configuration
- 🧹 Automatic cleanup of temporary directories for cloned repositories
- 🔒 Clear error messages for troubleshooting configuration and network issues
- 📄 **CSV export** - export analysis results to CSV files for further processing

## Quick Start

### Prerequisites

- Python 3.7 or higher
- Git installed and accessible in PATH
- Go projects with `go.mod` files
- Internet connection (for analyzing GitHub repositories)

### Installation

Clone the repository:

```bash
git clone https://github.com/HomayoonAlimohammadi/go-deps-analyzer.git
cd go-deps-analyzer
```

### Basic Usage

#### Analyze a Single Project

Analyze the current branch:
```bash
python3 -m go_deps_analyzer -p /path/to/your/go/project
```

Analyze a specific branch or tag:
```bash
python3 -m go_deps_analyzer -p /path/to/your/go/project -b v1.0.0
```

#### Compare Two Branches or Tags

Compare dependencies between two versions (branches, tags, or commits):
```bash
python3 -m go_deps_analyzer -p /path/to/your/go/project -b v1.0.0 -B v2.0.0
```

This will show you:
- Dependencies added in v2.0.0
- Dependencies removed from v1.0.0
- Dependencies with version changes

#### Batch Analysis with Config File

Create a configuration file (e.g., `config.yaml`):

```yaml
projects:
  # Local path - Compare two versions
  - path: /path/to/project1
    branch1: v0.7.0
    branch2: v0.8.0

  # GitHub repository - Compare two versions
  - repo: https://github.com/user/project.git
    branch1: v1.0.0
    branch2: v2.0.0

  # Local path - Analyze single branch
  - path: /path/to/project2
    branch1: main

  # GitHub repository - Analyze default branch
  - repo: https://github.com/user/another-project.git

  # Mix local and remote projects
  - path: /path/to/project3
```

Run the analysis:
```bash
python3 -m go_deps_analyzer -c config.yaml
```

See the [config.yaml.example](config.yaml.example) file for more configuration options.

#### Verbose Output

Get detailed dependency lists:
```bash
python3 -m go_deps_analyzer -p /path/to/project -b v1.0.0 -v
```

#### CSV Export

Export analysis results to a CSV file:
```bash
python3 -m go_deps_analyzer -c config.yaml -o results.csv
```

The CSV file will contain two tables:
1. **Summary Table**: Shows aggregate statistics (added, removed, changed counts) for each project
2. **Detailed Table**: Lists all dependency changes with old and new versions, sorted alphabetically

You can combine CSV export with verbose console output:
```bash
python3 -m go_deps_analyzer -c config.yaml -v -o results.csv
```

## Usage Examples

### Example 1: Kubernetes Version Comparison

Compare Kubernetes dependencies between versions:
```bash
python3 -m go_deps_analyzer \
  -p /path/to/kubernetes \
  -b v1.33.0 \
  -B v1.34.0 \
  -v
```

### Example 2: Analyze Current Development Branch

Check dependencies on your current working branch:
```bash
python3 -m go_deps_analyzer -p /path/to/your/project
```

### Example 3: Analyze a GitHub Repository

Analyze a public GitHub repository without cloning it manually:
```bash
# Create a simple config
cat > analyze-repo.yaml << EOF
projects:
  - repo: https://github.com/prometheus/prometheus.git
    branch1: v2.45.0
    branch2: v2.46.0
EOF

# Run the analysis
python3 -m go_deps_analyzer -c analyze-repo.yaml -v
```

### Example 4: Mixed Local and Remote Projects

Create a `my-projects.yaml`:
```yaml
projects:
  # Local project
  - path: /home/user/projects/api-server
    branch1: v1.0.0
    branch2: v2.0.0
  
  # GitHub repository
  - repo: https://github.com/user/shared-library.git
    branch1: v1.0.0
    branch2: v2.0.0
  
  # Another local project
  - path: /home/user/projects/worker
    branch1: main
  
  # Another GitHub repository
  - repo: https://github.com/user/common-utils.git
    branch1: v1.5.0
    branch2: v1.6.0
```

Run:
```bash
python3 -m go_deps_analyzer -c my-projects.yaml -v
```

## Command-Line Options

```
Options:
  -h, --help            Show help message and exit
  -v, --verbose         Print detailed dependency lists
  --version             Show program version
  -c, --config CONFIG   Path to configuration file (YAML)
  -p, --project PROJECT Path to a single project to analyze
  -b, --branch BRANCH   Branch to analyze (use with --project)
  -B, --branch2 BRANCH2 Second branch for comparison
  -o, --csv-output PATH Path to CSV file for exporting analysis results
  --log-level LEVEL     Set logging level (DEBUG, INFO, WARNING, ERROR)
```

## Output Format

The tool provides clear, structured output:

```
=== Project: metrics-server (/path/to/metrics-server) ===

Branch: v0.7.0
  Total dependencies: 45
  Direct dependencies: 12
  Indirect dependencies: 33

Branch: v0.8.0
  Total dependencies: 48
  Direct dependencies: 13
  Indirect dependencies: 35

Comparison (v0.7.0 → v0.8.0):
  Added dependencies: 4
  Removed dependencies: 1
  Version changes: 8
```

With `-v` flag, you'll also see the complete list of dependencies and their versions.

## CSV Export Format

When using the `-o` or `--csv-output` flag, the tool generates a CSV file with two tables:

### Summary Table

The summary table provides an overview of changes across all projects:

| Column | Description |
|--------|-------------|
| Project | Name of the project (extracted from repo URL or path) |
| Branch 1 | First branch/tag being compared |
| Branch 2 | Second branch/tag being compared |
| Added | Number of dependencies added |
| Removed | Number of dependencies removed |
| Changed | Number of dependencies with version changes |

The summary table includes a **TOTAL** row at the end that sums up all counts across all projects.

### Detailed Table

The detailed table lists all dependency changes:

| Column | Description |
|--------|-------------|
| Project | Name of the project |
| Module | Go module name |
| Change Type | One of: `added`, `removed`, or `changed` |
| Old Versions | Semicolon-separated list of versions (empty for added dependencies) |
| New Versions | Semicolon-separated list of versions (empty for removed dependencies) |

**Notes:**
- Dependencies are sorted alphabetically by module name within each project
- Multiple versions are joined with semicolons (e.g., `v1.0.0;v1.1.0;v1.2.0`)
- The CSV file uses UTF-8 encoding and follows RFC 4180 standard
- Special characters (commas, quotes, newlines) are automatically escaped

### Example CSV Output

```csv
Project,Branch 1,Branch 2,Added,Removed,Changed
kubernetes,v1.33.0,v1.34.0,17,139,86
etcd,v3.6.2,v3.6.2,0,0,0
TOTAL,,,17,139,86

Project,Module,Change Type,Old Versions,New Versions
kubernetes,github.com/google/uuid,changed,v1.1.2;v1.6.0,v1.1.1;v1.6.0
kubernetes,github.com/new/package,added,,v1.0.0
kubernetes,github.com/old/package,removed,v2.0.0,
etcd,go.etcd.io/etcd,changed,v3.5.0,v3.6.0
```

## Configuration File Format

YAML configuration supports multiple projects with flexible branch specifications. You can use either local paths or GitHub repositories:

```yaml
projects:
  # Local path-based project
  - path: /absolute/path/to/project1
    branch1: v1.0.0        # First branch, tag, or commit to analyze
    branch2: v2.0.0        # (Optional) Second branch, tag, or commit for comparison

  # GitHub repository-based project
  - repo: https://github.com/user/project.git
    branch1: v1.0.0        # First branch, tag, or commit to analyze
    branch2: v2.0.0        # (Optional) Second branch, tag, or commit for comparison

  # Local path - single branch or tag
  - path: /absolute/path/to/project2
    branch1: main          # Analyze single branch or tag

  # GitHub repository - default branch
  - repo: https://github.com/user/another-project.git
    # No branches specified = use default branch

  # You can mix local and remote projects in the same config
```

**Important**: Each project must have exactly one of `path` or `repo`, not both.

### Working with Subdirectories

Some repositories contain multiple Go projects in subdirectories rather than at the repository root. For these cases, use the `src_dir` option to specify the path from the repository root to the directory containing the `go.mod` file.

**Key Points:**
- `src_dir` is only valid with `repo` (not `path`)
- For local paths, simply point the `path` directly to the directory containing `go.mod`
- `src_dir` must be a relative path from the repository root
- Path traversal (`../`) is not allowed

**Example Configuration:**

```yaml
projects:
  # Repository with Go project in a subdirectory
  - repo: https://github.com/user/monorepo.git
    src_dir: services/api
    branch1: v1.0.0
    branch2: v2.0.0
  
  # Repository with nested Go project
  - repo: https://github.com/kubernetes/kubernetes.git
    src_dir: staging/src/k8s.io/api
    branch1: v1.33.0
    branch2: v1.34.0
```

**Real-World Example:**

The Kubernetes repository contains multiple Go modules in the `staging/src/k8s.io/` directory. To analyze the `api` module:

```bash
# Create a config file
cat > k8s-api-analysis.yaml << EOF
projects:
  - repo: https://github.com/kubernetes/kubernetes.git
    src_dir: staging/src/k8s.io/api
    branch1: v1.33.0
    branch2: v1.34.0
EOF

# Run the analysis
python3 -m go_deps_analyzer -c k8s-api-analysis.yaml -v
```

The tool will clone the Kubernetes repository, navigate to the `staging/src/k8s.io/api` subdirectory, analyze the dependencies there, and clean up afterward.

### Example: Analyzing Kubernetes

```bash
# Create a config file
cat > kubernetes-analysis.yaml << EOF
projects:
  - repo: https://github.com/kubernetes/kubernetes.git
    branch1: v1.33.0
    branch2: v1.34.0
EOF

# Run the analysis
python3 -m go_deps_analyzer -c kubernetes-analysis.yaml -v
```

The tool will automatically clone Kubernetes, analyze both versions, and clean up afterward.

## License

See [LICENSE](LICENSE) file for details.

## Author

**Homayoon Alimohammadi**
- Email: homayoon.alimohammadi@gmail.com
- GitHub: [@HomayoonAlimohammadi](https://github.com/HomayoonAlimohammadi)

## Version

Current version: 1.0.0
