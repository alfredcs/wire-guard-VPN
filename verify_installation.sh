#!/bin/bash
#
# Installation Verification Script
# Checks if all components are properly installed
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== VPN Server Installation Verification ===${NC}"
echo ""

# Track results
PASSED=0
FAILED=0
WARNINGS=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2 - File not found: $1"
        ((FAILED++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $2 - Directory not found: $1"
        ((FAILED++))
    fi
}

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2 ($1 found)"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} $2 - $1 not found"
        ((WARNINGS++))
    fi
}

echo "Checking Project Structure..."
check_dir "server/auth_service" "Server auth service directory"
check_dir "server/cli" "Server CLI directory"
check_dir "server/scripts" "Server scripts directory"
check_dir "client/vpn_client" "Client CLI directory"
check_dir "client/macos" "MacOS scripts directory"
check_dir "docs" "Documentation directory"
check_dir "tests" "Tests directory"

echo ""
echo "Checking Core Server Files..."
check_file "server/auth_service/main.py" "FastAPI application"
check_file "server/auth_service/models.py" "Database models"
check_file "server/auth_service/schemas.py" "Pydantic schemas"
check_file "server/auth_service/auth.py" "Authentication module"
check_file "server/auth_service/wireguard.py" "WireGuard manager"
check_file "server/auth_service/config.py" "Configuration module"
check_file "server/auth_service/database.py" "Database module"

echo ""
echo "Checking Server CLI..."
check_file "server/cli/vpn_admin.py" "Server admin CLI"

echo ""
echo "Checking Client Files..."
check_file "client/vpn_client/main.py" "Client CLI main"
check_file "client/vpn_client/auth.py" "Client auth module"
check_file "client/vpn_client/wireguard.py" "Client WireGuard module"
check_file "client/vpn_client/config.py" "Client config module"

echo ""
echo "Checking Installation Scripts..."
check_file "server/scripts/install_server.sh" "Server installation script"
check_file "server/scripts/setup_wireguard.sh" "WireGuard setup script"
check_file "server/scripts/setup_firewall.sh" "Firewall setup script"
check_file "client/macos/install.sh" "MacOS install script"
check_file "client/macos/build_pkg.sh" "PKG builder script"
check_file "client/macos/uninstall.sh" "Uninstall script"

echo ""
echo "Checking Documentation..."
check_file "README.md" "Project README"
check_file "IMPLEMENTATION.md" "Implementation summary"
check_file "docs/ARCHITECTURE.md" "Architecture documentation"
check_file "docs/DEPLOYMENT.md" "Deployment guide"
check_file "docs/API.md" "API documentation"
check_file "docs/SECURITY.md" "Security guide"

echo ""
echo "Checking Configuration Files..."
check_file ".env.example" "Environment template"
check_file ".gitignore" "Git ignore file"
check_file "server/requirements.txt" "Server requirements"
check_file "client/requirements.txt" "Client requirements"
check_file "pytest.ini" "Pytest configuration"
check_file "setup.py" "Setup configuration"

echo ""
echo "Checking Test Suite..."
check_file "tests/conftest.py" "Test fixtures"
check_file "tests/test_auth.py" "Authentication tests"
check_file "tests/test_wireguard.py" "WireGuard tests"
check_file "tests/test_integration.py" "Integration tests"

echo ""
echo "Checking System Dependencies (Optional)..."
check_command "python3" "Python 3"
check_command "wg" "WireGuard tools"
check_command "git" "Git"

echo ""
echo -e "${BLUE}=== Verification Summary ===${NC}"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical components verified!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review and edit .env.example"
    echo "2. Run server installation: sudo ./server/scripts/install_server.sh"
    echo "3. Run client installation: ./client/macos/install.sh"
    echo "4. See DEPLOYMENT.md for detailed instructions"
    exit 0
else
    echo -e "${RED}✗ Some components are missing. Please check the errors above.${NC}"
    exit 1
fi
