#!/bin/bash
#
# VPN Server Installation Script for Fedora
# This script installs and configures the VPN server with WireGuard and authentication service
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/vpn-server"
CONFIG_DIR="/etc/vpn"
VENV_DIR="$INSTALL_DIR/venv"
LOG_DIR="/var/log/vpn"
DATA_DIR="/var/lib/vpn"

echo -e "${GREEN}=== VPN Server Installation ===${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check if running on Fedora
if [ ! -f /etc/fedora-release ]; then
    echo -e "${YELLOW}Warning: This script is designed for Fedora Linux${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/8] Installing system dependencies...${NC}"
dnf install -y \
    wireguard-tools \
    python3 \
    python3-pip \
    python3-virtualenv \
    git \
    iptables \
    firewalld \
    openssl

echo -e "${GREEN}[2/8] Enabling IP forwarding...${NC}"
# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Make it persistent
cat > /etc/sysctl.d/99-vpn.conf <<EOF
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF

echo -e "${GREEN}[3/8] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/certs"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p /etc/wireguard

echo -e "${GREEN}[4/8] Setting up Python virtual environment...${NC}"
# Create virtual environment
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Copy project files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${GREEN}[5/8] Installing Python dependencies...${NC}"
cd "$PROJECT_ROOT/server"
pip install -r requirements.txt

# Copy server files
cp -r auth_service "$INSTALL_DIR/"
cp -r cli "$INSTALL_DIR/"

# Copy .env.example if .env doesn't exist
if [ ! -f "$CONFIG_DIR/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$CONFIG_DIR/.env"
    echo -e "${YELLOW}Configuration file created at $CONFIG_DIR/.env${NC}"
    echo -e "${YELLOW}Please edit this file with your settings${NC}"

    # Generate a random JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" "$CONFIG_DIR/.env"

    # Update database path
    sed -i "s|DATABASE_URL=sqlite:///vpn.db|DATABASE_URL=sqlite:///$DATA_DIR/vpn.db|" "$CONFIG_DIR/.env"
fi

# Create symlink for .env
ln -sf "$CONFIG_DIR/.env" "$INSTALL_DIR/.env"

echo -e "${GREEN}[6/8] Configuring WireGuard...${NC}"
# Run WireGuard setup script
bash "$SCRIPT_DIR/setup_wireguard.sh"

echo -e "${GREEN}[7/8] Configuring firewall...${NC}"
# Run firewall setup script
bash "$SCRIPT_DIR/setup_firewall.sh"

echo -e "${GREEN}[8/8] Installing systemd services...${NC}"
# Install systemd service
cat > /etc/systemd/system/vpn-auth.service <<EOF
[Unit]
Description=VPN Authentication Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python -m uvicorn auth_service.main:app \\
    --host 0.0.0.0 \\
    --port 8443 \\
    --workers 4
Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=vpn-auth

[Install]
WantedBy=multi-user.target
EOF

# Create CLI wrapper script
cat > /usr/local/bin/vpn-admin <<EOF
#!/bin/bash
source $VENV_DIR/bin/activate
cd $INSTALL_DIR
export PYTHONPATH=$INSTALL_DIR
python -m cli.vpn_admin "\$@"
EOF

chmod +x /usr/local/bin/vpn-admin

# Reload systemd
systemctl daemon-reload

# Enable and start services
systemctl enable wg-quick@wg0
systemctl enable vpn-auth

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Edit the configuration file: $CONFIG_DIR/.env"
echo "2. Start WireGuard: systemctl start wg-quick@wg0"
echo "3. Start VPN auth service: systemctl start vpn-auth"
echo "4. Create an admin user: vpn-admin user add <username> <email>"
echo ""
echo "For SSL/TLS support:"
echo "- Generate or obtain SSL certificates"
echo "- Place them in $CONFIG_DIR/certs/"
echo "- Update TLS settings in $CONFIG_DIR/.env"
echo ""
echo -e "${YELLOW}Remember to configure your firewall and ensure required ports are open${NC}"
