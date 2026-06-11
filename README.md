# SBOM Upload Action

[![GitHub release](https://img.shields.io/github/release/scality/sbom-upload.svg)](https://github.com/scality/sbom-upload/releases/latest)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/scality/sbom/blob/main/LICENSE)

A GitHub Action and CLI tool for uploading Software Bill of Materials (SBOM) files to [Dependency Track](https://dependencytrack.org/).

## ✨ Features

- 🚀 **GitHub Action Integration** - Seamless CI/CD pipeline integration
- 📁 **Multiple Upload Methods** - Single SBOMs, batch uploads, or custom hierarchies  
- 🏗️ **Hierarchical Projects** - Create parent/child project relationships
- 🎨 **Auto Hierarchy Generation** - Generate 3-level hierarchies from nested SBOM structures
- 🔄 **Version Management** - Semantic version comparison and latest detection
- 🧪 **Local Testing** - CLI for development and debugging
- 🎯 **Auto-Detection** - Extract project info from SBOM metadata
- 🔐 **Secure** - API key authentication with proper error handling
- 🆔 **Unique Naming** - UUID suffixes prevent project name conflicts

## 🚀 Quick Start

### GitHub Action (Recommended)

```yaml
name: Upload SBOM
on: [push]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: scality/sbom-upload@v1
        with:
          url: 'https://dependency-track.example.com'
          api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
          project-sbom: 'sbom.json'
```

### CLI Usage

```bash
# Set environment variables
export INPUT_URL="https://dependency-track.example.com"
export INPUT_API_KEY="your-api-key"

# Test connection
PYTHONPATH=src python src/main.py test-connection

# Upload single SBOM file
export INPUT_PROJECT_SBOM="sbom.json"
PYTHONPATH=src python src/main.py upload

# Upload SBOM with custom project details (via environment)
export INPUT_PROJECT_SBOM="sbom.json"
export INPUT_PROJECT_NAME="my-app" 
export INPUT_PROJECT_VERSION="1.0.0"
PYTHONPATH=src python src/main.py upload
```

## 📖 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in minutes
- **[Usage Examples](docs/USAGE_EXAMPLES.md)** - Comprehensive examples for GitHub Actions and CLI
- **[Hierarchy Configuration](docs/HIERARCHY_CONFIG.md)** - Advanced project structures
- **[CLI Reference](docs/CLI.md)** - Complete command-line interface documentation

## 🛠️ Installation

### For GitHub Actions
No installation required - just reference the action in your workflow.

### For CLI Development
```bash
git clone https://github.com/scality/sbom-upload.git
cd sbom-upload
pip install -r requirements.txt
```

## 🎯 Use Cases

- **CI/CD Integration** - Automatically upload SBOMs on builds/releases
- **Multi-Service Applications** - Manage complex project hierarchies
- **Security Compliance** - Track dependencies across your organization
- **Version Management** - Maintain accurate version histories
- **Development Workflows** - Test uploads locally before deployment

## 📊 Supported Scenarios

| Scenario | GitHub Action | CLI | Documentation |
|----------|:-------------:|:---:|:-------------:|
| Single SBOM Upload | ✅ | ✅ | [Examples](docs/USAGE_EXAMPLES.md#basic-single-sbom-upload) |
| Multiple SBOMs | ✅ | ✅ | [Examples](docs/USAGE_EXAMPLES.md#multiple-sboms-from-file-list) |
| Nested Projects | ✅ | ✅ | [Examples](docs/USAGE_EXAMPLES.md#advanced-configuration-with-custom-hierarchy) |
| Auto Hierarchy Generation | ✅ | ✅ | [Usage Examples](docs/USAGE_EXAMPLES.md#hierarchy-generation-from-nested-sbom-structure) |
| Custom Hierarchies | ❌ | ✅ | [Hierarchy Config](docs/HIERARCHY_CONFIG.md) |
| Version Detection | ✅ | ✅ | [Usage Examples](docs/USAGE_EXAMPLES.md#with-version-detection) |
| Dry Run Testing | ❌ | ✅ | [CLI Reference](docs/CLI.md) |

## 🔧 Configuration

### GitHub Action Inputs

| Input | Required | Description | Example |
|-------|:--------:|-------------|---------|
| `url` | ✅ | Dependency Track server URL | `https://dt.example.com` |
| `api-key` | ✅ | API key for authentication | `${{ secrets.DT_API_KEY }}` |
| `project-sbom` | ✅* | Path to single SBOM file | `dist/sbom.json` |
| `project-sbom-list` | ✅* | Path to file with SBOM list | `sbom-files.txt` |
| `project-sbom-dir` | ✅* | Directory containing SBOMs | `dist/sboms/` |
| `project-name` | ❌ | Override project name | `my-application` |
| `project-version` | ❌ | Override project version | `1.2.3` |
| `parent-project-name` | ❌ | Parent project name | `main-app` |
| `parent-project-version` | ❌ | Parent project version | `2.0.0` |
| `project-classifier` | ❌ | Project type classifier | `APPLICATION` |
| `parent-project-classifier` | ❌ | Parent project classifier | `APPLICATION` |
| `project-collection-logic` | ❌ | Collection logic for children | `AGGREGATE_DIRECT_CHILDREN` |
| `parent-project-collection-logic` | ❌ | Parent collection logic | `AGGREGATE_DIRECT_CHILDREN` |
| `is-latest` | ❌ | Mark as latest version | `true` |
| `auto-detect-latest` | ❌ | Auto-detect latest flag | `true` |
| `api-timeout` | ❌ | API timeout (seconds) | `300` |
| `dry-run` | ❌ | Validate without uploading | `true` |
| `project-prefix` | ❌ | Prefix for project names | `ci-` |
| `project-suffix` | ❌ | Suffix for project names | `-prod` |
| `project-tags` | ❌ | Comma-separated tags | `production,ci-cd` |
| `delete-on-version-suffix-match` | ❌ | Delete existing leaf project when version matches suffix pattern (default `false`) | `true` |
| `delete-version-suffix-pattern` | ❌ | Case-insensitive regex evaluated against project version when delete is enabled (default `dev`) | `dev$` |

*One of `project-sbom`, `project-sbom-list`, or `project-sbom-dir` is required.

[View all inputs →](docs/USAGE_EXAMPLES.md#environment-variables)

## 🧪 Local Development

```bash
# Start local Dependency Track instance
cd tests
docker-compose up -d

# Test connection
PYTHONPATH=src python src/main.py test-connection

# Upload test SBOM
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
export INPUT_DRY_RUN="true"
PYTHONPATH=src python src/main.py upload
```

## 🏷️ Auto-Tagging & Stale Project Maintenance

Every project created or updated by this tool is automatically tagged with four
canonical prefixed tags:

| Tag | Value |
|-----|-------|
| `name:<n>` | `name.lower().replace("-","_")` |
| `version:<v>` | `version.lower().replace("-","_")` (when set) |
| `parent:<p>` | `parent_name.lower().replace("-","_")` (when set) |
| `lifecycle:<token>` | First match of `alpha`, `beta`, `dev`, `preview`, `rc` in the version string, or `GA` |

User-defined tags are always preserved; only the four managed prefixes are
replaced on subsequent uploads.

### Deactivate stale projects

```bash
# Preview — no changes made
PYTHONPATH=src python3 src/main.py deactivate-stale --dry-run

# Apply with a custom threshold (default: 15 days)
PYTHONPATH=src python3 src/main.py deactivate-stale --days 30
```

Projects are **protected** from deactivation when they carry `lifecycle:GA` or
`keep-active`, or when they have active children (checked via the DT API before
every deactivation attempt, regardless of collection logic).
A project that has never received a BOM (`lastBomImport` is null) is treated as
infinitely stale and will be deactivated unless one of the above protections
applies.

A daily scheduled workflow (`.github/workflows/deactivate-stale-projects.yaml`,
`0 2 * * *` UTC) runs this automatically.  Trigger it manually via
`workflow_dispatch` with the `dry-run` input set to `true` for a safe preview.

### Back-fill tags on existing projects

```bash
# Preview diff (default behaviour)
PYTHONPATH=src python3 src/main.py retag-projects --dry-run

# Apply
PYTHONPATH=src python3 src/main.py retag-projects
```

The one-off remediation workflow (`.github/workflows/retag-projects.yaml`) is
`workflow_dispatch`-only with `dry-run: true` as the safe default.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Dependency Track](https://dependencytrack.org/) - Software composition analysis platform
- [CycloneDX](https://cyclonedx.org/) - SBOM standard specification
- [SPDX](https://spdx.dev/) - Software package data exchange format

## 📞 Support

- 📚 [Documentation](docs/)
- 🐛 [Issues](https://github.com/scality/sbom-upload/issues)
- 💬 [Discussions](https://github.com/scality/sbom-upload/discussions)
