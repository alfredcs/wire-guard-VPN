#!/bin/bash
#
# Firewall Setup Script
# Configures firewall rules for VPN server
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
WG_PORT="51820"
API_PORT="8443"

echo -e "${GREEN}Configuring firewall...${NC}"

# Check if firewalld is running
if systemctl is-active --quiet firewalld; then
    echo "Using firewalld..."

    # Allow WireGuard port
    firewall-cmd --permanent --add-port=$WG_PORT/udp
    echo -e "${GREEN}Opened port $WG_PORT/udp for WireGuard${NC}"

    # Allow API port
    firewall-cmd --permanent --add-port=$API_PORT/tcp
    echo -e "${GREEN}Opened port $API_PORT/tcp for API${NC}"

    # Enable masquerading for VPN traffic
    firewall-cmd --permanent --add-masquerade
    echo -e "${GREEN}Enabled masquerading${NC}"

    # Reload firewall
    firewall-cmd --reload
    echo -e "${GREEN}Firewall rules applied${NC}"

else
    echo "firewalld not running, using iptables directly..."

    # Allow WireGuard port
    iptables -A INPUT -p udp --dport $WG_PORT -j ACCEPT
    echo -e "${GREEN}Opened port $WG_PORT/udp for WireGuard${NC}"

    # Allow API port
    iptables -A INPUT -p tcp --dport $API_PORT -j ACCEPT
    echo -e "${GREEN}Opened port $API_PORT/tcp for API${NC}"

    # Save iptables rules
    if command -v iptables-save &> /dev/null; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    fi
fi

echo ""
echo -e "${GREEN}Firewall configuration complete${NC}"
echo ""
echo "Open ports:"
echo "- UDP $WG_PORT: WireGuard VPN"
echo "- TCP $API_PORT: Authentication API"
echo ""
echo -e "${YELLOW}Make sure these ports are also open in your cloud provider's security group/firewall${NC}"
