# SBOM GitHub Action CLI

A simple, pythonic CLI for testing and uploading SBOMs to Dependency Track.

## Usage

### Prerequisites

Set the required environment variables:
```bash
export INPUT_URL="http://localhost:8081"
export INPUT_API_KEY="your-dependency-track-api-key"
```

### Available Commands

#### Upload SBOMs
Upload SBOMs to Dependency Track with auto-detection based on environment variables:
```bash
# Single SBOM upload
export INPUT_PROJECT_SBOM="sbom.json"
python3 src/main.py upload

# Multiple SBOMs from file list
export INPUT_PROJECT_SBOM_LIST="sbom-files.txt"
python3 src/main.py upload

# Nested hierarchy upload
export INPUT_PROJECT_HIERARCHY_CONFIG="hierarchy.json"
python3 src/main.py upload

# With dry run (validate without uploading)
export INPUT_DRY_RUN="true"
export INPUT_PROJECT_SBOM="sbom.json"
python3 src/main.py upload
```

#### Test Connection
Test connectivity to your Dependency Track instance:
```bash
python3 src/main.py test-connection
```

#### Validate Inputs
Validate all GitHub Action inputs:
```bash
python3 src/main.py validate-inputs
```

#### Help
Get help and see all available commands:
```bash
python3 src/main.py --help
```

## Development

This CLI provides a complete interface for SBOM upload operations:
1. ✅ Input validation - Validates all required environment variables
2. ✅ Connection testing - Tests connectivity to Dependency Track
3. ✅ SBOM upload - Supports multiple upload modes with auto-detection
4. ✅ Project management - Full project hierarchy and configuration support

## Example Environment Setup

For testing with a local Dependency Track instance:

```bash
# Start Dependency Track (from tests/ directory)
cd tests && docker-compose up -d

# Set environment variables
export INPUT_URL="http://localhost:8081"
export INPUT_API_KEY="your-api-key-from-dependency-track"

# Test connection
python3 src/main.py test-connection
```
