#!/bin/bash
#
# Firewall Setup Script
# Configures firewall rules for VPN server
# Supports: firewalld (Fedora/RHEL), ufw (Ubuntu/Debian), and iptables (fallback)
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

# Detect which firewall system to use
FIREWALL_TYPE="iptables"  # Default fallback

if systemctl is-active --quiet firewalld 2>/dev/null; then
    FIREWALL_TYPE="firewalld"
elif command -v ufw &> /dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
    FIREWALL_TYPE="ufw"
elif command -v ufw &> /dev/null; then
    # ufw exists but may not be active - use it on Ubuntu/Debian
    if [ -f /etc/debian_version ]; then
        FIREWALL_TYPE="ufw"
    fi
fi

echo "Detected firewall: $FIREWALL_TYPE"

case "$FIREWALL_TYPE" in
    firewalld)
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
        ;;

    ufw)
        echo "Using ufw (Uncomplicated Firewall)..."

        # Enable ufw if not already enabled (non-interactive)
        if ! ufw status | grep -q "Status: active"; then
            echo -e "${YELLOW}Enabling ufw...${NC}"
            # Allow SSH first to prevent lockout
            ufw allow ssh
            ufw --force enable
        fi

        # Allow WireGuard port
        ufw allow $WG_PORT/udp
        echo -e "${GREEN}Opened port $WG_PORT/udp for WireGuard${NC}"

        # Allow API port
        ufw allow $API_PORT/tcp
        echo -e "${GREEN}Opened port $API_PORT/tcp for API${NC}"

        # Enable IP forwarding in ufw
        # Check if already configured
        if ! grep -q "^DEFAULT_FORWARD_POLICY=\"ACCEPT\"" /etc/default/ufw 2>/dev/null; then
            sed -i 's/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
            echo -e "${GREEN}Enabled forwarding policy in ufw${NC}"
        fi

        # Add NAT rules for masquerading if not already present
        UFW_BEFORE_RULES="/etc/ufw/before.rules"
        if ! grep -q "# WireGuard NAT rules" "$UFW_BEFORE_RULES" 2>/dev/null; then
            # Detect default interface
            DEFAULT_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
            if [ -z "$DEFAULT_INTERFACE" ]; then
                DEFAULT_INTERFACE="eth0"
            fi

            # Add NAT rules at the beginning of the file
            cat > /tmp/ufw_nat_rules.tmp <<EOF
# WireGuard NAT rules
*nat
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -s 10.0.0.0/24 -o $DEFAULT_INTERFACE -j MASQUERADE
COMMIT

EOF
            # Prepend NAT rules to before.rules
            cat /tmp/ufw_nat_rules.tmp "$UFW_BEFORE_RULES" > /tmp/before.rules.new
            mv /tmp/before.rules.new "$UFW_BEFORE_RULES"
            rm -f /tmp/ufw_nat_rules.tmp
            echo -e "${GREEN}Added NAT masquerading rules to ufw${NC}"
        fi

        # Reload ufw
        ufw reload
        echo -e "${GREEN}Firewall rules applied${NC}"
        ;;

    iptables)
        echo "Using iptables directly..."

        # Allow WireGuard port
        iptables -A INPUT -p udp --dport $WG_PORT -j ACCEPT
        echo -e "${GREEN}Opened port $WG_PORT/udp for WireGuard${NC}"

        # Allow API port
        iptables -A INPUT -p tcp --dport $API_PORT -j ACCEPT
        echo -e "${GREEN}Opened port $API_PORT/tcp for API${NC}"

        # Save iptables rules
        if command -v iptables-save &> /dev/null; then
            mkdir -p /etc/iptables
            iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
            echo -e "${GREEN}Saved iptables rules${NC}"
        fi

        # For Ubuntu/Debian, install iptables-persistent for rule persistence
        if [ -f /etc/debian_version ]; then
            if ! dpkg -l | grep -q iptables-persistent; then
                echo -e "${YELLOW}Installing iptables-persistent for rule persistence...${NC}"
                DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
            fi
        fi
        ;;
esac

echo ""
echo -e "${GREEN}Firewall configuration complete${NC}"
echo ""
echo "Open ports:"
echo "- UDP $WG_PORT: WireGuard VPN"
echo "- TCP $API_PORT: Authentication API"
echo ""
echo -e "${YELLOW}Make sure these ports are also open in your cloud provider's security group/firewall${NC}"
