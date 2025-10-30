# Pre-merge Workflow Documentation

## 🎯 Overview

The pre-merge workflow (`/.github/workflows/pre-merge.yaml`) provides comprehensive testing for the SBOM Upload Action before code changes are merged. It tests all upload scenarios using the official Dependency Track Docker setup.

## 🧪 Test Scenarios Covered

### 1. **Single SBOM Upload**
- Tests unified `upload` command with single SBOM
- Verifies project creation from SBOM metadata
- Validates latest flag management

### 2. **Multiple SBOM Upload (Directory Mode)**
- Tests unified `upload` command with directory input
- Creates parent-child project relationships
- Processes multiple SBOMs from a directory

### 3. **Custom Hierarchy Upload**
- Tests unified `upload` command with hierarchy configuration
- Uses `tests/hierarchy-example.json` configuration
- Creates complex multi-level project structures

### 4. **GitHub Action Style Uploads**
- Tests the main `upload` command used by GitHub Actions
- Tests both single SBOM and multiple SBOM scenarios
- Validates environment variable handling

### 5. **Version Management**
- Tests semantic version comparison functions
- Validates latest flag logic
- Tests version sorting capabilities

## 🏗️ Infrastructure Setup

### **Dependency Track Stack**
```yaml
services:
  postgres:       # PostgreSQL 17 database
  apiserver:      # Dependency Track API server v4.13.2
```

### **Network Configuration**
- Uses host networking for simplified CI access
- API server accessible on `localhost:8080`
- Database connection via localhost:5432

### **Resource Allocation**
```yaml
memory:
  limits: 4096m
  reservations: 2048m
```

## 🔐 Authentication Strategy

### **Real API Key Creation**
The workflow now creates a **real API key** in Dependency Track:

1. **Wait for DT Initialization** - Ensures API is fully ready
2. **Admin Login** - Uses default admin/admin credentials  
3. **Team Creation** - Creates "Automation" team with proper permissions
4. **API Key Generation** - Creates real API key via DT API
5. **Permission Assignment** - Grants `BOM_UPLOAD`, `PROJECT_CREATION_UPLOAD`, `PORTFOLIO_MANAGEMENT`

### **Setup Script Process**
```bash
scripts/setup-ci.sh:
1. Wait for API response (up to 5 minutes)
2. Login with admin/admin credentials  
3. Extract JWT token from login response
4. Create automation team via PUT /api/v1/team
5. Extract team UUID from response
6. Create API key via PUT /api/v1/team/{uuid}/key
7. Save real API key to /tmp/api_key.txt
```

### **Why Real Keys?**
1. **Actual Testing** - Tests real authentication and authorization
2. **Full Coverage** - Validates complete upload workflows
3. **Latest Flag Testing** - Tests version management with real projects  
4. **Integration Validation** - Ensures API compatibility

## 📋 Test Matrix

| Test Type | Command | Mode | Expected Result |
|-----------|---------|------|----------------|
| CLI Help | `--help` | Normal | ✅ Shows usage |
| Input Validation | `validate-inputs` | Normal | ✅ Validates env vars |
| Connection Test | `test-connection` | Real API Key | ✅ Authentication success |
| Single Upload | `upload` (single SBOM) | Real Upload | ✅ Project created + SBOM uploaded |
| Directory Upload | `upload` (directory) | Real Upload | ✅ Parent/child structure created |
| Hierarchy Upload | `upload` (hierarchy config) | Real Upload | ✅ Complex hierarchy created |
| GitHub Action Upload | `upload` | Real API Key | ✅ Environment variable handling |
| Version Functions | `test_version.py` | Normal | ✅ All tests pass |
| Latest Flag Logic | All uploads | Real Upload | ✅ Version comparison + flag management |
| End-to-End Suite | `test-e2e.sh` | Mixed | ✅ Component + integration tests |

## 🎛️ Workflow Configuration

### **Triggers**
```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

### **Timeout**
```yaml
timeout-minutes: 25
```

### **Key Steps**
1. **Setup** - Python 3.13, dependencies, PostgreSQL service
2. **Start DT** - Launch Dependency Track with Docker Compose
3. **Wait** - Ensure API is responding (up to 10 minutes)
4. **Test** - Run all upload scenarios
5. **Cleanup** - Stop containers, remove volumes

## 🐛 Debugging

### **If Tests Fail**
The workflow includes debug steps:
```yaml
- name: Check Docker Logs (Debug)
  if: failure()
  run: |
    echo "🔍 Dependency Track logs:"
    docker-compose logs apiserver --tail=100
```

### **Local Testing**
Run workflow components locally:
```bash
# Test all components
./test-workflow.sh

# Test specific scenarios
export INPUT_URL="http://localhost:8080"
export INPUT_API_KEY="your-real-api-key"
export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
python3 src/main.py upload
```

## 🚀 Benefits

### **Quality Assurance**
- ✅ Validates all upload methods work correctly
- ✅ Tests error handling and edge cases  
- ✅ Ensures backward compatibility

### **Confidence**
- ✅ Catches regressions before merge
- ✅ Validates against real Dependency Track instance
- ✅ Tests both CLI and GitHub Action interfaces

### **Documentation**
- ✅ Serves as executable documentation
- ✅ Shows proper usage patterns
- ✅ Validates example configurations

## 🔧 Customization

### **For Different DT Versions**
```yaml
apiserver:
  image: dependencytrack/apiserver:4.11.4  # Change version
```

### **For Real API Keys**
Replace the mock key section with real authentication:
```yaml
- name: Setup Real API Key
  run: |
    # Use your organization's DT setup script
    ./scripts/setup-production-key.sh
    echo "API_KEY=$(cat api_key.txt)" >> $GITHUB_ENV
```

### **For Additional Tests**
Add new test steps:
```yaml
- name: Test Custom Scenario
  run: |
    export INPUT_URL="http://localhost:8080"
    export INPUT_API_KEY="$(cat api_key.txt)"
    python3 src/main.py your-custom-command
```

## 📊 Success Criteria

The workflow passes when:
1. ✅ All CLI commands execute without errors
2. ✅ Dry run uploads complete successfully  
3. ✅ Version functions work correctly
4. ✅ Input validation passes
5. ✅ Mock authentication failures are handled gracefully
6. ✅ End-to-end test suite completes

## 🔮 Future Enhancements

- **Integration Tests** - Add tests with real API keys in secure environments
- **Performance Testing** - Measure upload times and resource usage
- **Compatibility Matrix** - Test against multiple Dependency Track versions
- **Security Scanning** - Validate SBOM content and dependencies
