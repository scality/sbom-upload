# SBOM Upload Action - Usage Examples

This document provides comprehensive examples for using the SBOM Upload Action both as a GitHub Action and via CLI.

## 🎯 GitHub Action Usage

### Basic Single SBOM Upload

```yaml
name: Upload SBOM to Dependency Track
on:
  push:
    branches: [main]

jobs:
  upload-sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Upload SBOM
        uses: scality/sbom-upload@v1
        with:
          url: 'https://dependency-track.example.com'
          api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
          project-sbom: 'sbom.json'
          project_name: 'my-application'
          project_version: '1.2.3'
          is_latest: 'true'
```

### Multiple SBOMs from File List

```yaml
- name: Upload Multiple SBOMs
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom-list: 'list-sbom-files.txt'
    project_prefix: 'ci-'
    project_suffix: '-prod'
    project_classifier: 'APPLICATION'
    project_tags: 'production,ci-cd'
```

Where `sbom-files.txt` contains:
```
frontend/sbom.json
backend/sbom.json
database/sbom.json
```

### Directory Upload with Parent Project Configuration

```yaml
- name: Upload Directory as Child Projects
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom-dir: 'dist/sboms/'
    parent_project_name: 'microservices-suite'
    parent_project_version: '2.1.0'
    parent_project_classifier: 'APPLICATION'
    parent_project_collection_logic: 'AGGREGATE_DIRECT_CHILDREN'
    project_classifier: 'LIBRARY'
    project_prefix: 'service-'
    auto_detect_latest: 'true'
```

### Dry Run Testing

```yaml
- name: Validate SBOM Upload (Dry Run)
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'dist/sbom.json'
    dry_run: 'true'
    project_description: 'Main application SBOM validation'
```

### Advanced Configuration with Custom Hierarchy

```yaml
- name: Upload with Custom Hierarchy
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'app-sbom.json'
    project_name: 'microservice-app'
    project_classifier: 'APPLICATION'
    parent_project_classifier: 'APPLICATION'
    project_collection_logic: 'AGGREGATE_LATEST_VERSION_CHILDREN'
    parent_project_collection_logic: 'AGGREGATE_LATEST_VERSION_CHILDREN'
    project_description: 'Main application microservice'
    is_latest: 'true'
```

### With Version Detection

```yaml
- name: Get Version from Git
  id: version
  run: echo "version=$(git describe --tags --abbrev=0 || echo 'dev')" >> $GITHUB_OUTPUT

- name: Upload SBOM with Auto Version
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'dist/sbom.json'
    project_version: ${{ steps.version.outputs.version }}
    is_latest: ${{ github.ref == 'refs/heads/main' }}
```

## 🖥️ CLI Usage

### Installation & Setup

```bash
# Clone the repository
git clone https://github.com/scality/sbom-upload.git
cd sbom-upload

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export INPUT_URL="https://dependency-track.example.com"
export INPUT_API_KEY="your-api-key-here"
```

### Test Connection

```bash
# Verify connection to Dependency Track
python3 src/main.py test-connection
```

### Single SBOM Upload

```bash
# Upload a single SBOM file
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
export INPUT_PROJECT_NAME="nginx"
export INPUT_PROJECT_VERSION="12.9.1"
python3 src/main.py upload
```

### Auto Upload (Project name/version from SBOM metadata)

```bash
# Let the tool extract project info from SBOM metadata
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
python3 src/main.py upload
```

### Multiple SBOMs from File List

```bash
# Upload multiple SBOMs listed in a file
export INPUT_PROJECT_SBOM_LIST="sbom-files.txt"
export INPUT_PROJECT_PREFIX="ci-"
export INPUT_PROJECT_SUFFIX="-prod"
python3 src/main.py upload
```

### Directory Upload (Multiple Child Projects)

```bash
# Upload all SBOMs in a directory as child projects
export INPUT_PROJECT_SBOM_DIR="tests/multiple_sbom/"
export INPUT_PARENT_PROJECT_NAME="my-application"
export INPUT_PARENT_PROJECT_VERSION="2.1.0"
python3 src/main.py upload
```

### Hierarchy Configuration Upload

```bash
# Upload using a JSON hierarchy configuration file
export INPUT_PROJECT_HIERARCHY_CONFIG="tests/hierarchy-example.json"
python3 src/main.py upload
```

### Dry Run Testing

```bash
# Test upload without actually sending to server
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
export INPUT_DRY_RUN="true"
python3 src/main.py upload
```

### Show Existing Hierarchy

```bash
# View current project structure in Dependency Track web interface
# Navigate to your configured URL to see uploaded projects
echo "Check your Dependency Track instance at $INPUT_URL"
```

### Dry Run Mode (Already Updated Above)

The dry run functionality is demonstrated in the earlier examples using `INPUT_DRY_RUN="true"`.

## 📁 File Structure Examples

### SBOM List File (`sbom-files.txt`)
```
frontend/dist/sbom.json
backend/build/sbom.json
mobile-app/release/sbom.json
shared-lib/target/sbom.json
```

### Hierarchy Configuration (`hierarchy.json`)
```json
{
  "enterprise-platform": {
    "version": "3.0.0",
    "classifier": "APPLICATION",
    "collection_logic": "AGGREGATE_LATEST_VERSION_CHILDREN",
    "description": "Main enterprise platform",
    "children": [
      {
        "name": "web-frontend",
        "sbom_path": "frontend/sbom.json",
        "classifier": "APPLICATION"
      },
      {
        "name": "api-backend", 
        "sbom_path": "backend/sbom.json",
        "classifier": "APPLICATION"
      },
      {
        "name": "shared-components",
        "version": "1.5.0",
        "classifier": "LIBRARY",
        "children": [
          {
            "name": "auth-service",
            "sbom_path": "auth/sbom.json"
          },
          {
            "name": "logging-service", 
            "sbom_path": "logging/sbom.json"
          }
        ]
      }
    ]
  }
}
```

## 🔧 Environment Variables

When using as a GitHub Action, these environment variables are automatically set:

```bash
INPUT_URL                           # Dependency Track server URL
INPUT_API_KEY                       # API key for authentication
INPUT_PROJECT_SBOM                  # Path to single SBOM file
INPUT_PROJECT_SBOM_LIST            # Path to file containing SBOM list
INPUT_PROJECT_NAME                  # Project name override
INPUT_PROJECT_VERSION               # Project version override
INPUT_PROJECT_DESCRIPTION           # Project description
INPUT_PROJECT_PREFIX                # Prefix for project names
INPUT_PROJECT_SUFFIX                # Suffix for project names
INPUT_PROJECT_CLASSIFIER            # Project classifier (APPLICATION, LIBRARY, etc.)
INPUT_PROJECT_COLLECTION_LOGIC      # How child projects are aggregated
INPUT_PROJECT_TAGS                  # Comma-separated tags
INPUT_IS_LATEST                     # Mark as latest version (true/false)
```

## 🎯 Use Case Examples

### 1. CI/CD Pipeline with Multiple Services
```yaml
# .github/workflows/sbom-upload.yml
name: Upload SBOMs
on:
  release:
    types: [published]

jobs:
  upload-sboms:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [frontend, backend, mobile]
    steps:
      - uses: actions/checkout@v4
      
      - name: Upload ${{ matrix.service }} SBOM
        uses: scality/sbom-upload@v1
        with:
          url: ${{ vars.DEPENDENCY_TRACK_URL }}
          api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
          project-sbom: '${{ matrix.service }}/dist/sbom.json'
          project_name: 'myapp-${{ matrix.service }}'
          project_version: ${{ github.event.release.tag_name }}
          is_latest: 'true'
```

### 2. Development vs Production Environments
```yaml
- name: Upload to Dev Environment
  if: github.ref == 'refs/heads/develop'
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEV_DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEV_DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'sbom.json'
    project_suffix: '-dev'
    is_latest: 'false'

- name: Upload to Production
  if: github.ref == 'refs/heads/main'
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.PROD_DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.PROD_DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'sbom.json'
    project_suffix: '-prod'
    is_latest: 'true'
```

### 3. Local Development Testing
```bash
#!/bin/bash
# test-upload.sh - Local testing script

set -e

echo "🧪 Testing SBOM Upload Action Locally"

# Test connection
echo "📡 Testing connection..."
python3 src/main.py test-connection

# Validate inputs
echo "✅ Validating inputs..."  
python3 src/main.py validate-inputs

# Upload test SBOM
echo "📤 Uploading test SBOM..."
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
export INPUT_DRY_RUN="true"
python3 src/main.py upload

echo "✅ All tests passed!"
```

## 📊 Version Checking Features

The action now includes advanced version checking capabilities:

```bash
# CLI: Check if a version would be latest
python3 -c "
from src.domain.version import is_latest_version
existing = ['1.0.0', '1.1.0', '2.0.0']
new = '2.1.0'
print(f'Version {new} would be latest: {is_latest_version(new, existing + [new])}')
"

# CLI: Find latest among versions
python3 -c "
from src.domain.version import get_latest_version
versions = ['1.0.0', '2.0.0-beta', '1.5.0', '2.0.0']
print(f'Latest version: {get_latest_version(versions)}')
"
```

## 🚨 Common Issues & Solutions

### Authentication Errors
```
❌ 403 Forbidden: Check API key permissions
```
**Solution**: Ensure API key has `BOM_UPLOAD` and `PROJECT_CREATION_UPLOAD` permissions.

### Connection Issues
```
❌ Failed to connect to Dependency Track API
```
**Solutions**:
- Verify URL format: `https://your-domain.com` (without `/api/v1`)
- Check network connectivity
- Validate SSL certificates

### File Not Found
```
❌ SBOM file not found: sbom.json
```
**Solutions**:
- Use absolute paths or paths relative to workspace root
- Verify file exists in repository
- Check file permissions

### Invalid Configuration
```
❌ Invalid collection logic: INVALID_VALUE
```
**Solution**: Use valid values: `NONE`, `AGGREGATE_LATEST_VERSION_CHILDREN`, `AGGREGATE_ALL_VERSION_CHILDREN`
