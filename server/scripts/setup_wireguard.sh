#!/bin/bash
#
# WireGuard Setup Script
# Configures WireGuard interface for VPN server
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
WG_INTERFACE="wg0"
WG_PORT="51820"
WG_ADDRESS="10.0.0.1/24"
WG_CONFIG="/etc/wireguard/$WG_INTERFACE.conf"

echo -e "${GREEN}Setting up WireGuard interface ${WG_INTERFACE}...${NC}"

# Check if WireGuard is installed
if ! command -v wg &> /dev/null; then
    echo -e "${RED}Error: WireGuard tools not found${NC}"
    exit 1
fi

# Generate server keys if they don't exist
if [ ! -f "/etc/wireguard/server_private.key" ]; then
    echo "Generating WireGuard server keys..."
    wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
    chmod 600 /etc/wireguard/server_private.key
    echo -e "${GREEN}Keys generated${NC}"
fi

SERVER_PRIVATE_KEY=$(cat /etc/wireguard/server_private.key)
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)

echo "Server public key: $SERVER_PUBLIC_KEY"

# Detect default network interface
DEFAULT_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
if [ -z "$DEFAULT_INTERFACE" ]; then
    echo -e "${YELLOW}Warning: Could not detect default network interface${NC}"
    DEFAULT_INTERFACE="eth0"
fi

echo "Default network interface: $DEFAULT_INTERFACE"

# Create WireGuard configuration
cat > "$WG_CONFIG" <<EOF
[Interface]
Address = $WG_ADDRESS
ListenPort = $WG_PORT
PrivateKey = $SERVER_PRIVATE_KEY

# Firewall rules
PostUp = iptables -A FORWARD -i %i -j ACCEPT
PostUp = iptables -A FORWARD -o %i -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o $DEFAULT_INTERFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT
PostDown = iptables -D FORWARD -o %i -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o $DEFAULT_INTERFACE -j MASQUERADE

# Peers will be added dynamically by the authentication service
EOF

chmod 600 "$WG_CONFIG"

echo -e "${GREEN}WireGuard configuration created at $WG_CONFIG${NC}"
echo -e "${YELLOW}Note: Peers will be added dynamically by the VPN authentication service${NC}"
echo ""
echo "To start WireGuard: systemctl start wg-quick@$WG_INTERFACE"
echo "To enable on boot: systemctl enable wg-quick@$WG_INTERFACE"
