# VPN Server Architecture

## Overview

This document describes the architecture of the VPN server with bearer token authentication.

## System Components

### 1. WireGuard VPN Server

**Purpose**: Provides the VPN tunnel infrastructure

**Technology**: WireGuard kernel module on Linux

**Key Features**:
- High-performance, modern VPN protocol
- Minimal attack surface
- Peer-to-peer encryption
- Dynamic peer management

**Configuration**:
- Interface: `wg0`
- Port: `51820/udp`
- Network: `10.0.0.0/24`
- Server IP: `10.0.0.1`

### 2. Authentication Service

**Purpose**: Manages user authentication and VPN provisioning

**Technology**: Python FastAPI application

**Components**:
- **REST API**: HTTP endpoints for authentication and VPN management
- **JWT Token System**: Bearer token-based authentication
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **WireGuard Manager**: Python wrapper for WireGuard operations

**Key Features**:
- JWT-based authentication with refresh tokens
- Dynamic peer provisioning
- User and token management
- Audit logging
- Rate limiting

### 3. Server CLI Tool

**Purpose**: Administrative interface for server management

**Technology**: Python Click application

**Capabilities**:
- User management (create, delete, list, reset password)
- Token management (generate, revoke, list)
- Peer management (list, remove)
- Server status monitoring
- Log viewing

### 4. MacOS Client

**Purpose**: Client-side VPN connection management

**Technology**: Python CLI application

**Components**:
- **CLI Tool**: Command-line interface for VPN operations
- **Auth Client**: HTTP client for server authentication
- **WireGuard Client**: Interface with MacOS WireGuard tools
- **Keychain Integration**: Secure token storage

## Data Flow

### Authentication Flow

```
1. User → Client CLI: login <server-url>
2. Client CLI → Auth API: POST /api/v1/auth/login
3. Auth API → Database: Verify credentials
4. Auth API → Client CLI: Return access + refresh tokens
5. Client CLI → MacOS Keychain: Store tokens securely
```

### VPN Provisioning Flow

```
1. User → Client CLI: connect
2. Client CLI → Auth API: POST /api/v1/vpn/provision (with bearer token)
3. Auth API: Validate token
4. Auth API → WireGuard Manager: Generate keys, allocate IP
5. WireGuard Manager → WireGuard: Add peer
6. Auth API → Database: Store peer info
7. Auth API → Client CLI: Return WireGuard config
8. Client CLI → WireGuard: Write config and connect
```

### Token Refresh Flow

```
1. Client CLI → Auth API: Request with expired access token
2. Auth API → Client CLI: 401 Unauthorized
3. Client CLI → Auth API: POST /api/v1/auth/refresh (with refresh token)
4. Auth API → Database: Validate refresh token
5. Auth API → Client CLI: Return new access token
6. Client CLI → MacOS Keychain: Update access token
7. Client CLI → Auth API: Retry original request
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `hashed_password`: bcrypt hashed password
- `is_active`: Account status
- `is_admin`: Admin flag
- `created_at`, `updated_at`: Timestamps

### Tokens Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `token_type`: 'access' or 'refresh'
- `jti`: JWT ID (unique)
- `is_revoked`: Revocation flag
- `expires_at`: Expiration timestamp
- `ip_address`, `user_agent`: Client info

### Peers Table
- `id`: Primary key
- `user_id`: Foreign key to users
- `public_key`: WireGuard public key
- `private_key`: WireGuard private key (encrypted)
- `preshared_key`: Optional PSK
- `assigned_ip`: Client IP address
- `is_active`: Peer status
- `last_handshake`: Last connection time
- `transfer_rx`, `transfer_tx`: Data transfer statistics

### Audit Logs Table
- `id`: Primary key
- `user_id`: Foreign key to users (nullable)
- `action`: Action type
- `resource_type`, `resource_id`: Target resource
- `details`: Additional information
- `ip_address`, `user_agent`: Client info
- `status`: 'success' or 'failure'
- `created_at`: Timestamp

## Security Architecture

### Authentication Security

1. **Password Storage**: bcrypt with configurable rounds
2. **Token Security**:
   - Short-lived access tokens (15 minutes)
   - Long-lived refresh tokens (7 days)
   - JWT with HMAC-SHA256 signatures
   - Stored with revocation capability
3. **API Security**:
   - HTTPS/TLS encryption
   - Bearer token authentication
   - Rate limiting
   - Input validation with Pydantic

### Network Security

1. **VPN Encryption**: WireGuard's ChaCha20-Poly1305
2. **API Encryption**: TLS 1.3
3. **Firewall**:
   - Only required ports open (51820/udp, 8443/tcp)
   - iptables rules for forwarding
   - NAT masquerading for VPN traffic

### Key Management

1. **Server Keys**: Generated on installation, stored in /etc/wireguard
2. **Client Keys**: Generated per-user, transmitted once
3. **JWT Secret**: Random 256-bit key, stored in environment
4. **Token Storage**: MacOS Keychain on client side

## Scalability Considerations

### Current Architecture
- Single server deployment
- SQLite database (can migrate to PostgreSQL)
- 4 worker processes for API
- Support for ~250 concurrent connections per /24 network

### Scaling Options

1. **Vertical Scaling**:
   - Increase API workers
   - Upgrade server resources
   - Expand IP address space

2. **Horizontal Scaling**:
   - Multiple WireGuard servers with load balancing
   - Shared PostgreSQL database
   - Redis for session management
   - Separate auth and VPN infrastructure

3. **Database Scaling**:
   - Migrate to PostgreSQL
   - Read replicas for queries
   - Connection pooling

## Monitoring and Observability

### Logging
- Structured JSON logging
- systemd journal integration
- Audit log for security events

### Metrics
- API request rates
- Authentication success/failure rates
- Active peer count
- Data transfer statistics
- Token lifecycle events

### Health Checks
- `/health` endpoint for API
- WireGuard interface status
- Database connectivity

## Deployment Architecture

### Production Deployment
```
Internet
    ↓
Firewall (UDP 51820, TCP 8443)
    ↓
Fedora Server
    ├── WireGuard (wg0 interface)
    ├── FastAPI (uvicorn + 4 workers)
    ├── SQLite/PostgreSQL
    └── systemd services
```

### High Availability Deployment
```
Internet
    ↓
Load Balancer (HAProxy/Nginx)
    ↓
┌─────────────┬─────────────┐
│  Server 1   │  Server 2   │
│  WireGuard  │  WireGuard  │
│  Auth API   │  Auth API   │
└─────────────┴─────────────┘
         ↓
    PostgreSQL
    (Primary + Replica)
```

## Technology Stack Summary

### Server
- **OS**: Fedora Linux
- **VPN**: WireGuard
- **API Framework**: FastAPI
- **Web Server**: uvicorn
- **Database**: SQLite (default) / PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: PyJWT
- **Password Hashing**: passlib with bcrypt

### Client
- **OS**: MacOS (M2/Apple Silicon)
- **VPN Client**: WireGuard tools
- **CLI Framework**: Click
- **HTTP Client**: requests
- **Secure Storage**: keyring (MacOS Keychain)

## Future Enhancements

1. **Multi-factor Authentication**: TOTP support
2. **Web Dashboard**: Web-based management interface
3. **Mobile Clients**: iOS and Android applications
4. **Certificate-based Authentication**: Alternative to passwords
5. **Advanced Analytics**: Real-time monitoring dashboard
6. **Automatic Backups**: Database and configuration backups
7. **IPv6 Support**: Full IPv6 tunneling
8. **Multiple Networks**: Support for multiple VPN networks
