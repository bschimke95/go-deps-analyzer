# Go Dependency Analyzer

A Python tool to analyze Go module dependencies across different branches and projects. This tool helps you understand dependency changes, compare versions, and track Go module updates across your projects.

## Features

- 📊 Analyze Go module dependencies for any project
- 🔄 Compare dependencies between two branches/tags
- 📦 Batch analysis of multiple projects using configuration files
- 📈 Detailed statistics including total, direct, and indirect dependencies
- 🎯 Identify added, removed, and version-changed dependencies
- 🔍 Verbose mode for detailed dependency lists
- 🌳 Works with any Git branch, tag, or commit

## Quick Start

### Prerequisites

- Python 3.7 or higher
- Git installed and accessible in PATH
- Go projects with `go.mod` files

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

#### Compare Two Branches

Compare dependencies between two versions:
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
  # Compare two versions
  - path: /path/to/project1
    branch1: v0.7.0
    branch2: v0.8.0

  # Analyze single branch
  - path: /path/to/project2
    branch1: main

  # Use current branch
  - path: /path/to/project3
```

Run the analysis:
```bash
python3 -m go_deps_analyzer -c config.yaml
```

See the [examples/config.yaml](examples/config.yaml) file for more configuration options.

#### Verbose Output

Get detailed dependency lists:
```bash
python3 -m go_deps_analyzer -p /path/to/project -b v1.0.0 -v
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

### Example 3: Multiple Projects Analysis

Create a `my-projects.yaml`:
```yaml
projects:
  - path: /home/user/projects/api-server
    branch1: v1.0.0
    branch2: v2.0.0
  
  - path: /home/user/projects/worker
    branch1: main
  
  - path: /home/user/projects/scheduler
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

## Configuration File Format

YAML configuration supports multiple projects with flexible branch specifications:

```yaml
projects:
  - path: /absolute/path/to/project1
    branch1: v1.0.0        # First branch/tag to analyze
    branch2: v2.0.0        # (Optional) Second branch for comparison

  - path: /absolute/path/to/project2
    branch1: main          # Analyze single branch

  - path: /absolute/path/to/project3
    # No branches specified = use current branch
```

## How It Works

1. **Git Operations**: Checks out specified branches using Git
2. **Dependency Parsing**: Parses `go.mod` files to extract dependencies
3. **Analysis**: Categorizes dependencies as direct or indirect
4. **Comparison**: When two branches are specified, identifies differences
5. **Output**: Presents results in a clear, readable format

## Troubleshooting

**Git errors**: Ensure the project path is a valid Git repository and specified branches/tags exist.

**Permission errors**: Make sure you have read access to the project directories.

**Go module errors**: Verify that the project has a valid `go.mod` file.

## License

See [LICENSE](LICENSE) file for details.

## Author

**Homayoon Alimohammadi**
- Email: homayoon.alimohammadi@gmail.com
- GitHub: [@HomayoonAlimohammadi](https://github.com/HomayoonAlimohammadi)

## Version

Current version: 1.0.0
