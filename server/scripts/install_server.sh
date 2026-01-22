#!/bin/bash
#
# VPN Server Installation Script for Fedora and Ubuntu/Debian
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

# Detect distribution
DISTRO="unknown"
if [ -f /etc/fedora-release ]; then
    DISTRO="fedora"
    echo -e "${GREEN}Detected: Fedora Linux${NC}"
elif [ -f /etc/debian_version ]; then
    # Check if it's Ubuntu or Debian
    if grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        DISTRO="ubuntu"
        echo -e "${GREEN}Detected: Ubuntu Linux${NC}"
    else
        DISTRO="debian"
        echo -e "${GREEN}Detected: Debian Linux${NC}"
    fi
elif [ -f /etc/redhat-release ]; then
    DISTRO="rhel"
    echo -e "${GREEN}Detected: RHEL/CentOS Linux${NC}"
else
    echo -e "${YELLOW}Warning: Unknown distribution. This script supports Fedora, Ubuntu, and Debian.${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/9] Installing system dependencies...${NC}"

# Install packages based on distribution
case "$DISTRO" in
    fedora|rhel)
        dnf install -y \
            wireguard-tools \
            python3 \
            python3-pip \
            python3-virtualenv \
            git \
            iptables \
            firewalld \
            openssl
        ;;
    ubuntu|debian)
        # Update package lists
        apt-get update

        # Install packages
        apt-get install -y \
            wireguard \
            wireguard-tools \
            python3 \
            python3-pip \
            python3-venv \
            git \
            iptables \
            openssl

        # Install ufw if not present (Ubuntu default firewall)
        if ! command -v ufw &> /dev/null; then
            apt-get install -y ufw
        fi
        ;;
    *)
        echo -e "${YELLOW}Attempting to install packages using available package manager...${NC}"
        if command -v dnf &> /dev/null; then
            dnf install -y wireguard-tools python3 python3-pip python3-virtualenv git iptables openssl
        elif command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y wireguard wireguard-tools python3 python3-pip python3-venv git iptables openssl
        elif command -v yum &> /dev/null; then
            yum install -y wireguard-tools python3 python3-pip git iptables openssl
        else
            echo -e "${RED}Error: No supported package manager found${NC}"
            exit 1
        fi
        ;;
esac

# Export DISTRO for child scripts
export DISTRO

echo -e "${GREEN}[2/9] Enabling IP forwarding...${NC}"
# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Make it persistent
cat > /etc/sysctl.d/99-vpn.conf <<EOF
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF

echo -e "${GREEN}[3/9] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/certs"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p /etc/wireguard

echo -e "${GREEN}[4/9] Setting up Python virtual environment...${NC}"
# Create virtual environment
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Copy project files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${GREEN}[5/9] Installing Python dependencies...${NC}"
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

echo -e "${GREEN}[6/9] Generating SSL certificates...${NC}"
# Generate SSL certificates if they don't exist
SSL_CERT="$CONFIG_DIR/certs/cert.pem"
SSL_KEY="$CONFIG_DIR/certs/key.pem"

if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "Generating self-signed SSL certificate..."

    # Get server hostname/IP for certificate
    SERVER_NAME="${VPN_SERVER_NAME:-$(hostname -f 2>/dev/null || hostname)}"

    # Generate self-signed certificate valid for 365 days
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$SSL_KEY" \
        -out "$SSL_CERT" \
        -sha256 -days 365 -nodes \
        -subj "/CN=$SERVER_NAME" \
        -addext "subjectAltName=DNS:$SERVER_NAME,DNS:localhost,IP:127.0.0.1"

    chmod 600 "$SSL_KEY"
    chmod 644 "$SSL_CERT"

    echo -e "${GREEN}SSL certificate generated for: $SERVER_NAME${NC}"
    echo -e "${YELLOW}Note: This is a self-signed certificate. For production, use a proper CA-signed certificate.${NC}"
else
    echo -e "${GREEN}SSL certificates already exist, skipping generation${NC}"
fi

echo -e "${GREEN}[7/9] Configuring WireGuard...${NC}"
# Run WireGuard setup script
bash "$SCRIPT_DIR/setup_wireguard.sh"

echo -e "${GREEN}[8/9] Configuring firewall...${NC}"
# Run firewall setup script
bash "$SCRIPT_DIR/setup_firewall.sh"

echo -e "${GREEN}[9/9] Installing systemd services...${NC}"
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
    --workers 4 \\
    --ssl-keyfile=$CONFIG_DIR/certs/key.pem \\
    --ssl-certfile=$CONFIG_DIR/certs/cert.pem
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
echo "SSL/TLS:"
echo "- Self-signed certificate generated at $CONFIG_DIR/certs/"
echo "- Server runs HTTPS on port 8443"
echo "- For production, replace with CA-signed certificates (e.g., Let's Encrypt)"
echo "- Clients can use --insecure flag for self-signed certs"
echo ""
echo -e "${YELLOW}Remember to configure your firewall and ensure required ports are open${NC}"
