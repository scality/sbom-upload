# Quick Start Examples

## 🚀 GitHub Action (Recommended)

### 1. Simple SBOM Upload
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

### 2. Multiple SBOMs
```yaml
- uses: scality/sbom-upload@v1
  with:
    url: ${{ vars.DEPENDENCY_TRACK_URL }}
    api-key: ${{ secrets.DEPENDENCY_TRACK_API_KEY }}
    project-sbom-list: 'sbom-files.txt'  # File containing list of SBOM paths
    project_prefix: 'myapp-'
    is_latest: 'true'
```

## 🖥️ CLI Usage

### 1. Test Connection
```bash
export INPUT_URL="https://dependency-track.example.com"
export INPUT_API_KEY="your-api-key"
python3 src/main.py test-connection
```

### 2. Upload Single SBOM
```bash
export INPUT_PROJECT_SBOM="sbom.json"
python3 src/main.py upload
```

### 3. Upload Multiple SBOMs as Child Projects
```bash
export INPUT_PROJECT_SBOM_DIR="dist/"
export INPUT_PARENT_PROJECT_NAME="my-app"
export INPUT_PARENT_PROJECT_VERSION="1.0.0"
python3 src/main.py upload
```

### 4. GitHub Action Simulation (Local Testing)
```bash
INPUT_URL="https://your-dt.com" \
INPUT_API_KEY="your-key" \
INPUT_PROJECT_SBOM="sbom.json" \
python3 src/main.py upload
```

## 📁 Required Files

**For GitHub Action:**
- `sbom.json` (or your SBOM file)
- GitHub secrets: `DEPENDENCY_TRACK_API_KEY`

**For multiple SBOMs:**
- `sbom-files.txt`:
  ```
  frontend/sbom.json
  backend/sbom.json
  mobile/sbom.json
  ```

**For custom hierarchies:**
- `hierarchy.json`:
  ```json
  {
    "my-app": {
      "version": "1.0.0",
      "children": [
        {"name": "frontend", "sbom_path": "frontend/sbom.json"},
        {"name": "backend", "sbom_path": "backend/sbom.json"}
      ]
    }
  }
  ```

## 🎯 Common Patterns

### Release Pipeline
```yaml
on:
  release:
    types: [published]

jobs:
  upload-sbom:
    steps:
      - uses: scality/sbom-upload@v1
        with:
          project_version: ${{ github.event.release.tag_name }}
          is_latest: 'true'
```

### Multi-Environment
```yaml
- name: Upload to Staging
  if: github.ref == 'refs/heads/develop'
  uses: scality/sbom-upload@v1
  with:
    project_suffix: '-staging'
    
- name: Upload to Production  
  if: github.ref == 'refs/heads/main'
  uses: scality/sbom-upload@v1
  with:
    project_suffix: '-prod'
    is_latest: 'true'
```
