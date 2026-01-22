#!/bin/bash
#
# Fix bcrypt compatibility issue
# Run this script to downgrade bcrypt to a compatible version
#

set -e

echo "Fixing bcrypt compatibility issue..."
echo ""

# Check if running in the correct directory
if [ ! -f "/opt/vpn-server/venv/bin/activate" ]; then
    echo "Error: VPN server installation not found at /opt/vpn-server"
    echo "This script should be run on the VPN server after installation"
    exit 1
fi

# Activate virtual environment
source /opt/vpn-server/venv/bin/activate

# Check current bcrypt version
echo "Current bcrypt version:"
pip show bcrypt | grep Version || echo "bcrypt not installed"
echo ""

# Uninstall bcrypt 5.x if present
echo "Removing incompatible bcrypt version..."
pip uninstall -y bcrypt 2>/dev/null || true

# Install compatible bcrypt 4.x
echo "Installing compatible bcrypt 4.x..."
pip install 'bcrypt>=4.0.0,<5.0.0'

echo ""
echo "New bcrypt version:"
pip show bcrypt | grep Version

echo ""
echo "✓ Fix applied successfully!"
echo ""
echo "You can now run: vpn-admin user add admin admin@example.com --admin"
