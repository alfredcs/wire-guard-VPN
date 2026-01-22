# VPN Server with Bearer Token Authentication

Production-ready WireGuard VPN server with Python-based bearer token authentication for MacOS M2 clients.

## Features

- **Secure Authentication**: JWT-based bearer token authentication
- **WireGuard VPN**: High-performance, modern VPN protocol
- **REST API**: Full-featured API for VPN management
- **CLI Tools**: Server admin and client CLI tools
- **MacOS Support**: Native support for MacOS M2 (Apple Silicon)
- **Production Ready**: Systemd integration, logging, monitoring

## Architecture

### Server Components
- **WireGuard VPN Server**: Kernel-based VPN on Fedora
- **Authentication Service**: FastAPI REST API with JWT tokens
- **Admin CLI**: Python CLI tool for server management
- **Database**: SQLite/PostgreSQL for user and token storage

### Client Components
- **MacOS Client CLI**: Python-based client for MacOS
- **WireGuard Client**: Native WireGuard for MacOS
- **Keychain Integration**: Secure token storage in MacOS Keychain

## Quick Start

### Server Installation (Fedora)

```bash
# Clone repository
git clone <repository-url>
cd vpn

# Run server installation script
sudo ./server/scripts/install_server.sh

# Create admin user
vpn-admin user add admin admin@example.com

# Generate token
vpn-admin token generate admin
```

### Client Installation (MacOS M2)

```bash
# Build client package
cd client/macos
./build_pkg.sh

# Install package
sudo installer -pkg vpn-client.pkg -target /

# Login to VPN server
vpn-client login https://vpn.example.com:8443

# Connect to VPN
vpn-client connect
```

## Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)
- [Security Guide](docs/SECURITY.md)

## Server CLI Commands

```bash
# User Management
vpn-admin user add <username> <email>
vpn-admin user remove <username>
vpn-admin user list

# Token Management
vpn-admin token generate <username>
vpn-admin token revoke <token_id>
vpn-admin token list <username>

# Peer Management
vpn-admin peer list
vpn-admin peer remove <peer_id>

# Status
vpn-admin status
vpn-admin logs
```

## Client CLI Commands

```bash
# Authentication
vpn-client login <server_url>
vpn-client logout

# Connection
vpn-client connect
vpn-client disconnect
vpn-client status

# Configuration
vpn-client config update
```

## API Endpoints

```
POST   /api/v1/auth/register      # Register new user
POST   /api/v1/auth/login         # Login and get bearer token
POST   /api/v1/auth/refresh       # Refresh access token
POST   /api/v1/auth/logout        # Revoke token
GET    /api/v1/auth/validate      # Validate token

POST   /api/v1/vpn/provision      # Get WireGuard configuration
GET    /api/v1/vpn/status         # Get connection status
DELETE /api/v1/vpn/disconnect     # Revoke VPN access

GET    /api/v1/admin/users        # List users (admin only)
DELETE /api/v1/admin/users/:id    # Delete user (admin only)
GET    /api/v1/admin/peers        # List active peers (admin only)
```

## Requirements

### Server
- Fedora Linux (or compatible RHEL-based distribution)
- Python 3.11+
- WireGuard kernel module
- Root or sudo access

### Client
- MacOS (tested on M2/Apple Silicon)
- Python 3.11+
- WireGuard-tools

## Security Features

- JWT-based authentication with short-lived tokens
- TLS/SSL for API communication
- bcrypt password hashing
- Rate limiting and brute force protection
- Audit logging
- Token revocation
- Secure key management
- Input validation

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

For issues and questions, please see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
