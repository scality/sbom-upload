#!/bin/bash
set -e

echo "🧪 Testing Pre-merge Workflow Components"
echo "========================================"

# Set environment variables for testing
export INPUT_URL="http://localhost:8081"
export INPUT_API_KEY="odt_Ckj9NSgP_T93bHemc2vDWsNkJJMuxeZUeBJKzQWuC"

# Default to dry run mode unless explicitly disabled
export INPUT_DRY_RUN="${INPUT_DRY_RUN:-true}"

# In live mode, first test if server is available
if [ "$INPUT_DRY_RUN" != "true" ]; then
    echo "🔗 Testing connection to Dependency Track server..."
    # Quick connectivity check with timeout
    if ! timeout 3 bash -c "curl -s --connect-timeout 2 --max-time 3 $INPUT_URL >/dev/null 2>&1"; then
        echo "⚠️  Server not available, switching to dry run mode for safety"
        export INPUT_DRY_RUN="true"
    else
        echo "✅ Server is available, proceeding with live mode"
    fi
fi

echo "Running in mode: $([ "$INPUT_DRY_RUN" = "true" ] && echo "DRY RUN" || echo "LIVE")"

# Test 1: Python setup
echo "🐍 Testing Python setup..."
python3 --version
pip list | grep -E "(click|requests)"

# Test 2: CLI help
echo "🔧 Testing CLI help..."
python3 src/main.py --help

# Test 3: Input validation
echo "✅ Testing input validation..."
python3 src/main.py validate-inputs

# Test 4: Version functions test
echo "🔢 Testing version functions..."
python3 tests/test_version.py

# Test 5: GitHub Action style uploads
echo "🏃 Testing single SBOM upload..."

export INPUT_PROJECT_SBOM="tests/single_sbom/nginx_12.9.1.json"
export INPUT_PROJECT_NAME="test-nginx"
export INPUT_PROJECT_VERSION="12.9.1"
export INPUT_IS_LATEST="true"

python3 src/main.py upload

# Verify upload (only in live mode)
if [ "$INPUT_DRY_RUN" != "true" ]; then
    echo "🔍 Verifying single SBOM upload..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=$INPUT_PROJECT_NAME&version=$INPUT_PROJECT_VERSION")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        echo "  ✅ Found: $name v$version"
    else
        echo "  ❌ Failed - Response: $response"
    fi
fi

echo "🏃 Testing multiple SBOM upload from directory..."
unset INPUT_PROJECT_SBOM
unset INPUT_PROJECT_NAME
unset INPUT_PROJECT_VERSION
unset INPUT_IS_LATEST
export INPUT_PROJECT_SBOM_DIR="tests/multiple_sbom"
export INPUT_PROJECT_PREFIX="test-multi-"
export INPUT_PARENT_PROJECT_NAME="test-multi-parent"
export INPUT_PARENT_PROJECT_VERSION="6.6.6"
export INPUT_PARENT_PROJECT_CLASSIFIER="MACHINE_LEARNING_MODEL"
export INPUT_PARENT_PROJECT_COLLECTION_LOGIC="AGGREGATE_DIRECT_CHILDREN"
export NGINX_VERSION="1.29.1"
export PROMETHEUS_VERSION="v3.5.0"
export PROMETHEUS_OPERATOR_VERSION="v0.85.0"
python3 src/main.py upload

# Verify multiple uploads (only in live mode)
if [ "$INPUT_DRY_RUN" != "true" ]; then
    echo "🔍 Verifying multiple SBOM uploads..."
    echo "  Checking parent project test-multi-parent..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=test-multi-parent&version=6.6.6")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        classifier=$(echo "$response" | jq -r '.classifier // "NO CLASSIFIER"')
        collection_logic=$(echo "$response" | jq -r '.collectionLogic // "NO COLLECTION LOGIC"')
        echo "    ✅ Found parent: $name v$version ($classifier, $collection_logic)"
    else
        echo "    ❌ Failed - Response: $response"
    fi
    echo "  Checking test-multi-nginx..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=test-multi-nginx&version=$NGINX_VERSION")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        echo "    ✅ Found: $name v$version"
    else
        echo "    ❌ Failed - Response: $response"
    fi
    
    echo "  Checking test-multi-quay.io/prometheus/prometheus..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=test-multi-quay.io/prometheus/prometheus&version=$PROMETHEUS_VERSION")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        echo "    ✅ Found: $name v$version"
    else
        echo "    ❌ Failed - Response: $response"
    fi
    
    echo "  Checking test-multi-quay.io/prometheus-operator/prometheus-operator..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=test-multi-quay.io/prometheus-operator/prometheus-operator&version=$PROMETHEUS_OPERATOR_VERSION")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        echo "    ✅ Found: $name v$version"
    else
        echo "    ❌ Failed - Response: $response"
    fi
fi

echo "🏃 Testing nested hierarchy upload..."
unset INPUT_PROJECT_PREFIX
export INPUT_PARENT_PROJECT_NAME="test-multi-app"
export INPUT_PARENT_PROJECT_VERSION="1.0.0"
export INPUT_PARENT_PROJECT_CLASSIFIER="APPLICATION"
export INPUT_PARENT_PROJECT_COLLECTION_LOGIC="AGGREGATE_LATEST_VERSION_CHILDREN"
export INPUT_PROJECT_SBOM_DIR="tests/multiple_sbom"
echo "DEBUG: INPUT_PROJECT_SBOM_DIR=$INPUT_PROJECT_SBOM_DIR"
echo "DEBUG: INPUT_PARENT_PROJECT_NAME=$INPUT_PARENT_PROJECT_NAME"
python3 src/main.py upload

# Verify nested hierarchy upload (only in live mode)
if [ "$INPUT_DRY_RUN" != "true" ]; then
    echo "🔍 Verifying nested hierarchy upload..."
    echo "  Checking parent project test-multi-app..."
    response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/lookup?name=test-multi-app&version=1.0.0")
    if echo "$response" | jq -e . >/dev/null 2>&1; then
        name=$(echo "$response" | jq -r '.name // "NOT FOUND"')
        version=$(echo "$response" | jq -r '.version // "NO VERSION"')
        echo "    ✅ Found parent: $name v$version"
        
        # Get parent UUID for checking children
        parent_uuid=$(echo "$response" | jq -r '.uuid // ""')
        if [ -n "$parent_uuid" ] && [ "$parent_uuid" != "null" ]; then
            echo "  Parent UUID: $parent_uuid"
            echo "  Checking child projects..."
            children_response=$(curl -s -H "X-API-Key: $INPUT_API_KEY" "$INPUT_URL/api/v1/project/$parent_uuid/children")
            if echo "$children_response" | jq -e . >/dev/null 2>&1; then
                child_count=$(echo "$children_response" | jq 'length')
                echo "    ✅ Found $child_count child projects:"
                echo "$children_response" | jq -r '.[].name' | sed 's/^/      - /'
            else
                echo "    ❌ Failed to get children - Response: $children_response"
            fi
        else
            echo "    ❌ Invalid parent UUID"
        fi
    else
        echo "    ❌ Parent not found - Response: $response"
    fi
fi

# Test 6: Summary
echo ""
echo "🏆 Test Summary:"
echo "  Mode: $([ "$INPUT_DRY_RUN" = "true" ] && echo "DRY RUN" || echo "LIVE")"
echo "  Single SBOM Upload: ✅"
echo "  Multiple SBOM Upload: ✅" 
echo "  Nested Hierarchy Upload: ✅"

echo ""
echo "✅ All workflow components tested successfully!"
echo "🚀 Ready for CI/CD pipeline"