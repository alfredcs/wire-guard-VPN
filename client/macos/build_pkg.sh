#!/bin/bash
#
# Build MacOS PKG Installer
# Creates a .pkg installer for the VPN client
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Building VPN Client PKG ===${NC}"
echo ""

# Check if running on MacOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script must be run on MacOS${NC}"
    exit 1
fi

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"
PKG_ROOT="$BUILD_DIR/root"

# Version
VERSION="1.0.0"

echo -e "${GREEN}[1/4] Creating build directories...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$PKG_ROOT/usr/local/lib/vpn-client"
mkdir -p "$PKG_ROOT/usr/local/bin"

echo -e "${GREEN}[2/4] Copying files...${NC}"
# Copy client files
cp -r "$CLIENT_DIR/vpn_client" "$PKG_ROOT/usr/local/lib/vpn-client/"
cp "$CLIENT_DIR/requirements.txt" "$PKG_ROOT/usr/local/lib/vpn-client/"

# Create CLI wrapper
cat > "$PKG_ROOT/usr/local/bin/vpn-client" <<'EOF'
#!/bin/bash
source /usr/local/lib/vpn-client/venv/bin/activate
python -m vpn_client.main "$@"
EOF

chmod +x "$PKG_ROOT/usr/local/bin/vpn-client"

# Create postinstall script
mkdir -p "$BUILD_DIR/scripts"
cat > "$BUILD_DIR/scripts/postinstall" <<'EOF'
#!/bin/bash

# Create virtual environment
python3 -m venv /usr/local/lib/vpn-client/venv
/usr/local/lib/vpn-client/venv/bin/pip install --upgrade pip
/usr/local/lib/vpn-client/venv/bin/pip install -r /usr/local/lib/vpn-client/requirements.txt

# Create WireGuard config directory
mkdir -p /usr/local/etc/wireguard

# Install WireGuard if not already installed
if ! command -v wg &> /dev/null; then
    echo "Please install WireGuard tools: brew install wireguard-tools"
fi

echo "VPN Client installed successfully"
exit 0
EOF

chmod +x "$BUILD_DIR/scripts/postinstall"

echo -e "${GREEN}[3/4] Building package...${NC}"
pkgbuild \
    --root "$PKG_ROOT" \
    --scripts "$BUILD_DIR/scripts" \
    --identifier "com.vpn.client" \
    --version "$VERSION" \
    --install-location "/" \
    "$BUILD_DIR/vpn-client-$VERSION.pkg"

echo -e "${GREEN}[4/4] Creating product archive...${NC}"
productbuild \
    --package "$BUILD_DIR/vpn-client-$VERSION.pkg" \
    "$SCRIPT_DIR/vpn-client-installer.pkg"

# Clean up
rm -rf "$BUILD_DIR"

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo ""
echo "Installer package created: $SCRIPT_DIR/vpn-client-installer.pkg"
echo ""
echo "To install:"
echo "  sudo installer -pkg vpn-client-installer.pkg -target /"
echo ""
echo -e "${YELLOW}Note: For distribution, you may want to sign the package with:${NC}"
echo "  productsign --sign 'Developer ID Installer' vpn-client-installer.pkg vpn-client-installer-signed.pkg"
