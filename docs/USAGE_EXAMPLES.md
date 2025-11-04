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
          project-name: 'my-application'
          project-version: '1.2.3'
          is-latest: 'true'
```

### Multiple SBOMs from File List

```yaml
- name: Upload Multiple SBOMs
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom-list: 'list-sbom-files.txt'
    project-prefix: 'ci-'
    project-suffix: '-prod'
    project-classifier: 'APPLICATION'
    project-tags: 'production,ci-cd'
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
    parent-project-name: 'microservices-suite'
    parent-project-version: '2.1.0'
    parent-project-classifier: 'APPLICATION'
    parent-project-collection-logic: 'AGGREGATE_DIRECT_CHILDREN'
    project-classifier: 'LIBRARY'
    project-prefix: 'service-'
    auto-detect-latest: 'true'
```

### Dry Run Testing

```yaml
- name: Validate SBOM Upload (Dry Run)
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'dist/sbom.json'
    dry-run: 'true'
    project-description: 'Main application SBOM validation'
```

### Advanced Configuration with Custom Hierarchy

```yaml
- name: Upload with Custom Hierarchy
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom: 'app-sbom.json'
    project-name: 'microservice-app'
    project-classifier: 'APPLICATION'
    parent-project-classifier: 'APPLICATION'
    project-collection-logic: 'AGGREGATE_LATEST_VERSION_CHILDREN'
    parent-project-collection-logic: 'AGGREGATE_LATEST_VERSION_CHILDREN'
    project-description: 'Main application microservice'
    is-latest: 'true'
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
    project-version: ${{ steps.version.outputs.version }}
    is-latest: ${{ github.ref == 'refs/heads/main' }}
```

### Hierarchy Generation from Nested SBOM Structure

For complex projects with nested SBOM structures, use the hierarchy generation feature:

```yaml
- name: Generate and Upload SBOM Hierarchy
  uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    generate_hierarchy: 'true'
    hierarchy_input_dir: 'sbom-artifacts'
    hierarchy_output_file: 'generated-hierarchy.json'
    hierarchy_upload: 'true'
```

This will:
1. Scan the `sbom-artifacts` directory for nested SBOM files
2. Generate a 3-level hierarchy configuration:
   - Level 1: `meta_{name}` (from merged SBOM)
   - Level 2: `{name}_{version}` (from merged SBOM)
   - Level 3: Individual components with UUID suffixes for uniqueness
3. Upload the hierarchy directly to Dependency Track
4. Save the configuration to `generated-hierarchy.json`

**Directory Structure Example:**
```
sbom-artifacts/
├── project_4.0.3_merged_sbom.json
├── project_4.0.3_sbom.json
├── project-base/
│   ├── project_base_4.0.3_merged_sbom.json
│   ├── component1_1.0.0_sbom.json
│   └── component2_2.0.0_sbom.json
└── nginx/
    ├── nginx_4.0.8_merged_sbom.json
    └── component3_3.0.0_sbom.json
```

**Hierarchy Generation Only (without upload):**
```yaml
- name: Generate SBOM Hierarchy Configuration
  uses: scality/sbom-upload@v1
  with:
    generate_hierarchy: 'true'
    hierarchy_input_dir: 'sbom-artifacts'
    hierarchy_output_file: 'hierarchy-config.json'
    hierarchy_upload: 'false'
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

### Generate Hierarchy Configuration

```bash
# Generate hierarchy JSON from nested SBOM directory structure
python3 src/main.py generate-hierarchy -i tests/project

# Save generated hierarchy to file
python3 src/main.py generate-hierarchy -i tests/project -o project-hierarchy.json

# Generate and upload directly to Dependency Track (recommended)
python3 src/main.py generate-hierarchy -i tests/project --upload

# Use generated hierarchy for upload (alternative method)
export INPUT_PROJECT_HIERARCHY_CONFIG="project-hierarchy.json"
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
INPUT_API_TIMEOUT                   # API timeout in seconds (default: 300)
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

### Timeout Errors
```
❌ Upload failed: Failed to create project X: Project creation failed: No response
❌ API request timed out after 300 seconds
```
**What's happening**: The API request is taking longer than the configured timeout period. This commonly occurs with:
- Slow network connections
- Large SBOM files
- Heavy server load
- Project creation with many dependencies

**Solutions**:
1. **Increase the timeout** (recommended for large projects):
   ```yaml
   - uses: scality/sbom-upload@v1
     with:
       api-timeout: 300  # 5 minutes
   ```

2. **For CLI usage**, set the environment variable:
   ```bash
   export INPUT_API_TIMEOUT=300
   python3 src/main.py upload
   ```

3. **Check server performance**: Verify your Dependency Track instance isn't overloaded

4. **Split large uploads**: Break up multiple SBOM uploads into separate jobs if possible

**Default timeout**: 300 seconds (5 minutes)  
**Recommended for large projects**: 300-600 seconds (5-10 minutes)

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

## 🏗️ Automatic Hierarchy Generation

The action can automatically generate hierarchy configurations from nested directory structures containing SBOM files.

### Supported Directory Structure

```
project-root/
├── project_1.0.0_merged_sbom.json          # Top-level metapp
├── component-a/
│   ├── component_a_1.2.0_merged_sbom.json  # Child application  
│   ├── service1_1.0.0_sbom.json            # Leaf component
│   └── service2_1.1.0_sbom.json            # Leaf component
└── component-b/
    ├── component_b_2.0.0_merged_sbom.json  # Child application
    ├── api_2.0.0_sbom.json                 # Leaf component
    └── ui_1.5.0_sbom.json                  # Leaf component
```

### Naming Convention Requirements

For automatic detection to work, SBOM files must follow these naming patterns:

- **Merged SBOMs** (applications with children): `name_version_merged_sbom.json`
- **Leaf SBOMs** (individual components): `name_version_sbom.json`

### Hierarchy Generation Rules

1. **Top-level metapps**: Created from `*_merged_sbom.json` files in the root directory
2. **Child applications**: Created from `*_merged_sbom.json` files in subdirectories  
3. **Leaf components**: Created from `*_sbom.json` files (non-merged) in any directory
4. **Collection logic**: 
   - Metapps: `AGGREGATE_LATEST_VERSION_CHILDREN`
   - Child applications: `AGGREGATE_DIRECT_CHILDREN`
   - Leaf components: `NONE`

### Example Usage

```bash
# Generate hierarchy from project test structure
python3 src/main.py generate-hierarchy -i tests/project

# Generate and upload directly (recommended - avoids configuration errors)
python3 src/main.py generate-hierarchy -i tests/project --upload

# Alternative: Save to file and use for upload
python3 src/main.py generate-hierarchy -i tests/project -o project-hierarchy.json
export INPUT_PROJECT_HIERARCHY_CONFIG="project-hierarchy.json"
python3 src/main.py upload
```

### Generated Configuration Example

```json
{
  "project": {
    "version": "4.0.3",
    "collection_logic": "AGGREGATE_LATEST_VERSION_CHILDREN",
    "classifier": "APPLICATION",
    "tags": ["project", "metapp"],
    "sbom_file": "project/project_4.0.3_merged_sbom.json",
    "children": [
      {
        "name": "project_base", 
        "version": "4.0.3",
        "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
        "classifier": "APPLICATION",
        "tags": ["project_base"],
        "sbom_file": "project/project-base/project_base_4.0.3_merged_sbom.json",
        "children": [
          {
            "name": "postgres",
            "version": "17.4-alpine3.21",
            "collection_logic": "NONE", 
            "classifier": "APPLICATION",
            "tags": ["postgres"],
            "sbom_file": "project/project-base/postgres_17.4-alpine3.21_sbom.json"
          }
        ]
      }
    ]
  }
}
```
