# Deployment Guide

## Prerequisites

### Server Requirements
- **Operating System**: Fedora Linux (or RHEL-based distribution)
- **RAM**: Minimum 1GB, recommended 2GB+
- **CPU**: 1 core minimum, 2+ cores recommended
- **Disk**: 10GB minimum
- **Network**: Public IP address, open UDP/TCP ports
- **Access**: Root or sudo privileges

### Client Requirements
- **Operating System**: MacOS (tested on M2/Apple Silicon)
- **Python**: 3.11 or higher
- **WireGuard**: wireguard-tools package
- **Homebrew**: For package management

## Server Installation

### 1. Prepare Server

```bash
# Update system
sudo dnf update -y

# Install git
sudo dnf install -y git

# Clone repository
git clone <repository-url>
cd vpn
```

### 2. Run Installation Script

```bash
# Make scripts executable
chmod +x server/scripts/*.sh

# Run installation
sudo ./server/scripts/install_server.sh
```

The installation script will:
- Install system dependencies (WireGuard, Python, etc.)
- Enable IP forwarding
- Set up Python virtual environment
- Install Python packages
- Configure WireGuard interface
- Set up firewall rules
- Create systemd services
- Generate initial configuration

### 3. Configure Server

Edit the configuration file:

```bash
sudo nano /etc/vpn/.env
```

Important settings to configure:

```bash
# Generate a secure JWT secret
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database (use PostgreSQL for production)
DATABASE_URL=sqlite:////var/lib/vpn/vpn.db
# DATABASE_URL=postgresql://user:password@localhost/vpn_db

# WireGuard settings
WG_INTERFACE=wg0
WG_PORT=51820
WG_ADDRESS=10.0.0.1/24

# API settings
API_PORT=8443

# TLS settings (recommended for production)
TLS_ENABLED=true
TLS_CERT_PATH=/etc/vpn/certs/cert.pem
TLS_KEY_PATH=/etc/vpn/certs/key.pem
```

### 4. Set Up TLS/SSL (Recommended)

#### Option A: Let's Encrypt

```bash
# Install certbot
sudo dnf install -y certbot

# Get certificate
sudo certbot certonly --standalone -d vpn.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/vpn.yourdomain.com/fullchain.pem /etc/vpn/certs/cert.pem
sudo cp /etc/letsencrypt/live/vpn.yourdomain.com/privkey.pem /etc/vpn/certs/key.pem
```

#### Option B: Self-Signed Certificate (Testing Only)

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/vpn/certs/key.pem \
  -out /etc/vpn/certs/cert.pem
```

### 5. Start Services

```bash
# Start WireGuard
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0

# Start authentication service
sudo systemctl start vpn-auth
sudo systemctl enable vpn-auth

# Check status
sudo systemctl status wg-quick@wg0
sudo systemctl status vpn-auth
```

### 6. Create Admin User

```bash
# Create first admin user
vpn-admin user add admin admin@example.com --admin

# Generate token for testing
vpn-admin token generate admin
```

### 7. Verify Installation

```bash
# Check server status
vpn-admin status

# Check WireGuard
sudo wg show

# Check API (replace with your token)
curl -H "Authorization: Bearer <token>" https://localhost:8443/health
```

### 8. Configure Firewall

Ensure your cloud provider's security group allows:
- **UDP 51820**: WireGuard VPN
- **TCP 8443**: Authentication API

Example for AWS Security Group:
```
Type        Protocol    Port Range    Source
Custom UDP  UDP         51820         0.0.0.0/0
Custom TCP  TCP         8443          0.0.0.0/0
```

## Client Installation (MacOS)

### 1. Install from Source

```bash
# Clone repository
git clone <repository-url>
cd vpn

# Make install script executable
chmod +x client/macos/install.sh

# Run installation
./client/macos/install.sh
```

### 2. Install from Package (if available)

```bash
# Download package
curl -O https://example.com/vpn-client-installer.pkg

# Install
sudo installer -pkg vpn-client-installer.pkg -target /
```

### 3. Verify Installation

```bash
# Check if installed
vpn-client --version

# Check WireGuard
wg --version
```

## Client Usage

### First-Time Setup

```bash
# Login to VPN server
vpn-client login https://vpn.yourdomain.com:8443

# Enter username and password when prompted

# Connect to VPN
vpn-client connect

# Check status
vpn-client status
```

### Daily Usage

```bash
# Connect
vpn-client connect

# Disconnect
vpn-client disconnect

# Check status
vpn-client status
```

## Production Deployment Checklist

### Security
- [ ] Use strong JWT secret (256-bit random)
- [ ] Enable TLS/SSL with valid certificate
- [ ] Use strong passwords for all users
- [ ] Configure firewall properly
- [ ] Keep system and packages updated
- [ ] Set up rate limiting if needed
- [ ] Review and adjust bcrypt rounds

### Performance
- [ ] Adjust API workers based on load
- [ ] Monitor system resources
- [ ] Set up log rotation
- [ ] Consider PostgreSQL for high load
- [ ] Optimize database queries

### Monitoring
- [ ] Set up log aggregation
- [ ] Configure alerts for failures
- [ ] Monitor disk space
- [ ] Track active connections
- [ ] Monitor authentication failures

### Backup
- [ ] Back up database regularly
- [ ] Back up /etc/vpn directory
- [ ] Back up WireGuard keys
- [ ] Test restore procedures
- [ ] Document recovery procedures

### Maintenance
- [ ] Regular security updates
- [ ] Token cleanup (expired/revoked)
- [ ] Peer cleanup (inactive)
- [ ] Log rotation
- [ ] Certificate renewal

## Troubleshooting

### Server Issues

#### Service won't start

```bash
# Check logs
sudo journalctl -u vpn-auth -n 50
sudo journalctl -u wg-quick@wg0 -n 50

# Check configuration
vpn-admin status

# Verify database
ls -l /var/lib/vpn/vpn.db
```

#### WireGuard interface not working

```bash
# Check if module is loaded
lsmod | grep wireguard

# Check interface
sudo wg show

# Restart WireGuard
sudo systemctl restart wg-quick@wg0
```

#### API not responding

```bash
# Check if running
sudo systemctl status vpn-auth

# Check if port is open
sudo netstat -tlnp | grep 8443

# Test locally
curl https://localhost:8443/health -k
```

### Client Issues

#### Cannot connect to server

```bash
# Check if server is reachable
ping vpn.yourdomain.com

# Test API connection
curl https://vpn.yourdomain.com:8443/health

# Check DNS resolution
nslookup vpn.yourdomain.com
```

#### Authentication fails

```bash
# Verify credentials
vpn-client login https://vpn.yourdomain.com:8443

# Check token in keychain
security find-generic-password -s com.vpn.client

# Clear and re-login
vpn-client logout
vpn-client login https://vpn.yourdomain.com:8443
```

#### VPN won't connect

```bash
# Check if WireGuard is installed
wg --version

# Check configuration
cat /usr/local/etc/wireguard/wg-vpn.conf

# Check logs
sudo wg-quick up /usr/local/etc/wireguard/wg-vpn.conf

# Update configuration
vpn-client config update
```

## Upgrading

### Server Upgrade

```bash
# Stop services
sudo systemctl stop vpn-auth

# Backup database
sudo cp /var/lib/vpn/vpn.db /var/lib/vpn/vpn.db.backup

# Pull updates
cd /path/to/vpn
git pull

# Update dependencies
source /opt/vpn-server/venv/bin/activate
pip install -r server/requirements.txt --upgrade

# Copy updated files
sudo cp -r server/auth_service /opt/vpn-server/
sudo cp -r server/cli /opt/vpn-server/

# Restart services
sudo systemctl start vpn-auth
```

### Client Upgrade

```bash
# Re-run installation script
./client/macos/install.sh
```

## Uninstallation

### Server

```bash
# Stop services
sudo systemctl stop vpn-auth
sudo systemctl stop wg-quick@wg0

# Disable services
sudo systemctl disable vpn-auth
sudo systemctl disable wg-quick@wg0

# Remove files
sudo rm -rf /opt/vpn-server
sudo rm -rf /etc/vpn
sudo rm -rf /var/lib/vpn
sudo rm -f /usr/local/bin/vpn-admin
sudo rm -f /etc/systemd/system/vpn-auth.service

# Reload systemd
sudo systemctl daemon-reload
```

### Client (MacOS)

```bash
# Run uninstall script
./client/macos/uninstall.sh
```

## Support

For issues and questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review logs: `sudo journalctl -u vpn-auth`
- Check GitHub issues
- Contact support
