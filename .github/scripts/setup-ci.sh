#!/bin/bash
# Script to setup Dependency Track with admin password change and API key creation

set -e

BASE_URL="http://localhost:8081"
ADMIN_USER="admin"
OLD_ADMIN_PASS="admin"
NEW_ADMIN_PASS="admin123!"

echo "🔧 Setting up Dependency Track for CI tests..."

# Function to wait for API
wait_for_api() {
    echo "⏳ Waiting for Dependency Track API..."
    for i in {1..60}; do
        if curl -f "$BASE_URL/api/version" >/dev/null 2>&1; then
            echo "✅ API version endpoint responding"
            break
        fi
        echo "Waiting for API... ($i/60)"
        sleep 5
    done
    
    # Now wait for auth endpoints to be ready
    echo "⏳ Waiting for authentication endpoints..."
    for i in {1..20}; do
        # Try to access an auth endpoint to see if it returns proper responses
        AUTH_TEST=$(curl -s -X POST \
            -d "username=test&password=test" \
            "$BASE_URL/api/v1/user/login" \
            -w "HTTPSTATUS:%{http_code}")
        
        HTTP_STATUS=$(echo $AUTH_TEST | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        RESPONSE_BODY=$(echo $AUTH_TEST | sed -e 's/HTTPSTATUS:.*//g')
        
        # If we get 401 (unauthorized) or FORCE_PASSWORD_CHANGE, that means auth endpoints are working
        if [ "$HTTP_STATUS" -eq 401 ] || echo "$RESPONSE_BODY" | grep -q "FORCE_PASSWORD_CHANGE"; then
            echo "✅ Authentication endpoints are ready (HTTP $HTTP_STATUS)"
            return 0
        elif [ "$HTTP_STATUS" -eq 405 ]; then
            echo "Auth endpoints not ready yet... ($i/20)"
            sleep 5
        else
            echo "Checking auth endpoints... ($i/20) - Status: $HTTP_STATUS"
            sleep 5
        fi
    done
    
    echo "❌ Authentication endpoints failed to become ready"
    return 1
}

# Function to change admin password
change_admin_password() {
    echo "🔐 Changing default admin password..."
    
    # First check if we can login with the new password (already changed)
    echo "🔍 Checking if password was already changed..."
    TEST_LOGIN=$(curl -s -X POST \
        -d "username=$ADMIN_USER&password=$NEW_ADMIN_PASS" \
        "$BASE_URL/api/v1/user/login" \
        -w "HTTPSTATUS:%{http_code}")
    
    TEST_STATUS=$(echo $TEST_LOGIN | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$TEST_STATUS" -eq 200 ]; then
        echo "✅ Password already changed, no action needed"
        return 0
    fi
    
    # Try to change the password using form data
    echo "🔐 Attempting to change admin password..."
    PASSWORD_CHANGE_RESPONSE=$(curl -s -X POST \
        -d "username=$ADMIN_USER&password=$OLD_ADMIN_PASS&newPassword=$NEW_ADMIN_PASS&confirmPassword=$NEW_ADMIN_PASS" \
        "$BASE_URL/api/v1/user/forceChangePassword" \
        -w "HTTPSTATUS:%{http_code}")
    
    HTTP_STATUS=$(echo $PASSWORD_CHANGE_RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    RESPONSE_BODY=$(echo $PASSWORD_CHANGE_RESPONSE | sed -e 's/HTTPSTATUS:.*//g')
    
    echo "🔍 Password change response: HTTP $HTTP_STATUS"
    
    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo "✅ Admin password changed successfully"
        return 0
    elif [ "$HTTP_STATUS" -eq 304 ]; then
        echo "ℹ️  Password already changed (304)"
        return 0
    elif [ "$HTTP_STATUS" -eq 400 ]; then
        echo "ℹ️  Password might already be changed (400)"
        return 0
    elif [ "$HTTP_STATUS" -eq 405 ]; then
        echo "❌ Method not allowed - auth endpoints may not be ready"
        echo "Response: $RESPONSE_BODY"
        return 1
    else
        echo "❌ Failed to change password. Status: $HTTP_STATUS"
        echo "Response: $RESPONSE_BODY"
        # Don't fail here - password might already be changed
        return 0
    fi
}

# Function to login and get JWT token
login_admin() {
    echo "🔐 Logging in as admin..." >&2
    
    # Try with new password first, then old password
    for password in "$NEW_ADMIN_PASS" "$OLD_ADMIN_PASS"; do
        echo "🔑 Trying password..." >&2
        
        LOGIN_RESPONSE=$(curl -s -X POST \
            -d "username=$ADMIN_USER&password=$password" \
            "$BASE_URL/api/v1/user/login" \
            -w "HTTPSTATUS:%{http_code}")
        
        HTTP_STATUS=$(echo $LOGIN_RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        RESPONSE_BODY=$(echo $LOGIN_RESPONSE | sed -e 's/HTTPSTATUS:.*//g')
        
        if [ "$HTTP_STATUS" -eq 200 ]; then
            # The JWT token is returned directly in the response body
            JWT_TOKEN=$(echo "$RESPONSE_BODY" | tr -d '\n')
            
            if [ -n "$JWT_TOKEN" ]; then
                echo "✅ Login successful with password" >&2
                echo "Bearer $JWT_TOKEN"
                return 0
            fi
        else
            echo "🔍 Login attempt failed with status: $HTTP_STATUS" >&2
        fi
    done
    
    echo "❌ Failed to login with any password" >&2
    return 1
}

# Function to configure Dependency Track settings
configure_dependency_track() {
    local auth_header="$1"
    echo "⚙️ Configuring Dependency Track settings..."
    
    # Disable BOM format validation
    echo "🔧 Disabling BOM format validation..."
    CONFIG_RESPONSE=$(curl -s -X POST \
        -H "Authorization: $auth_header" \
        -H "Content-Type: application/json" \
        -d '{"groupName":"artifact","propertyName":"bom.validation.mode","propertyValue":"DISABLED"}' \
        "$BASE_URL/api/v1/configProperty" \
        -w "HTTPSTATUS:%{http_code}")
    
    CONFIG_STATUS=$(echo $CONFIG_RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    CONFIG_BODY=$(echo $CONFIG_RESPONSE | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$CONFIG_STATUS" -eq 200 ] || [ "$CONFIG_STATUS" -eq 201 ]; then
        echo "✅ BOM format validation disabled"
    else
        echo "⚠️  Failed to disable BOM validation. Status: $CONFIG_STATUS"
        echo "Response: $CONFIG_BODY"
        # Don't fail the setup for this - it's not critical
    fi
    
    return 0
}

# Function to create team and API key
create_api_key() {
    local auth_header="$1"
    echo "🔑 Creating API key..."
    
    # Check if Administrators team already exists
    echo "🔍 Looking for existing Administrators team..."
    EXISTING_TEAMS=$(curl -s -H "Authorization: $auth_header" "$BASE_URL/api/v1/team")
    
    # Get the UUID of the first Administrators team (simple approach)
    TEAM_UUID=$(echo "$EXISTING_TEAMS" | grep -o '"uuid":"[^"]*","name":"Administrators"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$TEAM_UUID" ]; then
        # Look for any team with Administrators in the name
        TEAM_UUID=$(echo "$EXISTING_TEAMS" | grep -B 5 '"name":"Administrators"' | grep -o '"uuid":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi
    
    if [ -n "$TEAM_UUID" ]; then
        echo "✅ Found existing Administrators team with UUID: $TEAM_UUID"
    else
        echo "❌ No Administrators team found"
        return 1
    fi
    
    # Grant additional permissions to the team if needed
    echo "🛡️ Ensuring team has required permissions..."
    for permission in "PROJECT_CREATION_UPLOAD" "PORTFOLIO_MANAGEMENT" "BOM_UPLOAD"; do
        PERM_RESPONSE=$(curl -s -X POST \
            -H "Authorization: $auth_header" \
            "$BASE_URL/api/v1/permission/$permission/team/$TEAM_UUID" \
            -w "HTTPSTATUS:%{http_code}")
        
        PERM_STATUS=$(echo $PERM_RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        if [ "$PERM_STATUS" -eq 200 ] || [ "$PERM_STATUS" -eq 204 ]; then
            echo "✅ Permission granted: $permission"
        else
            echo "⚠️  Permission $permission: $PERM_STATUS"
        fi
    done
    
    # Create API key for the team
    echo "🗝️ Creating API key for team..."
    API_KEY_RESPONSE=$(curl -s -X PUT \
        -H "Authorization: $auth_header" \
        -H "Content-Type: application/json" \
        -d '{"comment":"CI/CD Administrators Key"}' \
        "$BASE_URL/api/v1/team/$TEAM_UUID/key" \
        -w "HTTPSTATUS:%{http_code}")
    
    API_KEY_HTTP_STATUS=$(echo $API_KEY_RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    API_KEY_BODY=$(echo $API_KEY_RESPONSE | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$API_KEY_HTTP_STATUS" -eq 201 ] || [ "$API_KEY_HTTP_STATUS" -eq 200 ]; then
        # Extract the key from the JSON response
        API_KEY=$(echo "$API_KEY_BODY" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$API_KEY" ]; then
            echo "✅ API Key created: $API_KEY"
            echo "$API_KEY" > /tmp/api_key.txt
            return 0
        else
            echo "❌ Could not extract API key from response"
            echo "Response: $API_KEY_BODY"
            return 1
        fi
    else
        echo "❌ Failed to create API key. Status: $API_KEY_HTTP_STATUS"
        echo "Response: $API_KEY_BODY"
        return 1
    fi
}

# Main setup
if wait_for_api; then
    # Give extra time for full initialization
    echo "⏳ Waiting for full initialization..."
    sleep 60
    
    # Change default admin password
    if change_admin_password; then
        echo "✅ Password change completed"
    else
        echo "❌ Failed to change admin password"
        exit 1
    fi
    
    # Login and get auth token
    echo "🔐 Starting login process..."
    AUTH_TOKEN=$(login_admin)
    LOGIN_STATUS=$?
    
    if [ $LOGIN_STATUS -eq 0 ] && [ -n "$AUTH_TOKEN" ]; then
        echo "🎯 Using auth token for API operations..."
        
        # Configure Dependency Track settings
        configure_dependency_track "$AUTH_TOKEN"
        
        # Create API key
        if create_api_key "$AUTH_TOKEN"; then
            echo "✅ Setup complete!"
            echo "🔑 API Key saved to /tmp/api_key.txt"
            API_KEY_CONTENT=$(cat /tmp/api_key.txt)
            echo "📋 API Key: $API_KEY_CONTENT"
            # Also export to current shell environment for immediate use
            export INPUT_URL="$BASE_URL"
            export INPUT_API_KEY="$API_KEY_CONTENT"
            echo "🌍 API key exported to environment"
        else
            echo "❌ Failed to create API key"
            exit 1
        fi
    else
        echo "❌ Failed to login to Dependency Track"
        echo "🔍 Login status: $LOGIN_STATUS, Token: '$AUTH_TOKEN'"
        exit 1
    fi
else
    echo "❌ Failed to setup Dependency Track"
    exit 1
fi
