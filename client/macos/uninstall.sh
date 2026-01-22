#!/bin/bash
#
# VPN Client Uninstall Script for MacOS
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== VPN Client Uninstall ===${NC}"
echo ""

# Check if running on MacOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is for MacOS only${NC}"
    exit 1
fi

# Confirm uninstall
read -p "Are you sure you want to uninstall VPN Client? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled"
    exit 0
fi

echo -e "${GREEN}Disconnecting from VPN...${NC}"
if command -v vpn-client &> /dev/null; then
    vpn-client disconnect 2>/dev/null || true
fi

echo -e "${GREEN}Removing files...${NC}"
sudo rm -rf /usr/local/lib/vpn-client
sudo rm -f /usr/local/bin/vpn-client

echo -e "${GREEN}Removing configuration...${NC}"
rm -rf ~/.vpn-client

echo -e "${GREEN}Removing WireGuard configuration...${NC}"
sudo rm -f /usr/local/etc/wireguard/wg-vpn.conf

echo -e "${GREEN}Clearing keychain entries...${NC}"
security delete-generic-password -s "com.vpn.client" 2>/dev/null || true

echo ""
echo -e "${GREEN}=== Uninstall Complete ===${NC}"
echo ""
echo -e "${YELLOW}Note: WireGuard tools were not removed. To remove them:${NC}"
echo "  brew uninstall wireguard-tools"
