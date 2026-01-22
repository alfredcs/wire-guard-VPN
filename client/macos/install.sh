#!/bin/bash
#
# VPN Client Installation Script for MacOS
# Installs WireGuard and VPN client CLI tool
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== VPN Client Installation for MacOS ===${NC}"
echo ""

# Check if running on MacOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is for MacOS only${NC}"
    exit 1
fi

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo -e "${GREEN}[1/5] Installing WireGuard...${NC}"
if ! command -v wg &> /dev/null; then
    brew install wireguard-tools
    echo -e "${GREEN}WireGuard installed${NC}"
else
    echo -e "${YELLOW}WireGuard already installed${NC}"
fi

echo -e "${GREEN}[2/5] Installing Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    brew install python@3.11
else
    echo -e "${YELLOW}Python 3 already installed${NC}"
fi

echo -e "${GREEN}[3/5] Installing VPN client...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$(dirname "$SCRIPT_DIR")"

# Create installation directory
INSTALL_DIR="/usr/local/lib/vpn-client"
sudo mkdir -p "$INSTALL_DIR"

# Copy client files
sudo cp -r "$CLIENT_DIR/vpn_client" "$INSTALL_DIR/"
sudo cp "$CLIENT_DIR/requirements.txt" "$INSTALL_DIR/"

# Create virtual environment
echo -e "${GREEN}[4/5] Setting up Python environment...${NC}"
sudo python3 -m venv "$INSTALL_DIR/venv"
sudo "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
sudo "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create CLI wrapper
echo -e "${GREEN}[5/5] Creating CLI command...${NC}"
sudo tee /usr/local/bin/vpn-client > /dev/null <<EOF
#!/bin/bash
export PYTHONPATH="/usr/local/lib/vpn-client:\$PYTHONPATH"
/usr/local/lib/vpn-client/venv/bin/python -m vpn_client.main "\$@"
EOF

sudo chmod +x /usr/local/bin/vpn-client

# Create WireGuard config directory
sudo mkdir -p /usr/local/etc/wireguard

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Usage:"
echo "  vpn-client login <server-url>   - Login to VPN server"
echo "  vpn-client connect              - Connect to VPN"
echo "  vpn-client disconnect           - Disconnect from VPN"
echo "  vpn-client status               - Show connection status"
echo ""
echo "Example:"
echo "  vpn-client login https://vpn.example.com:8443"
echo ""
echo -e "${YELLOW}Note: Some commands require sudo privileges${NC}"
