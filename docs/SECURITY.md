# Security Guide

## Overview

This document outlines the security features, best practices, and considerations for the VPN server with bearer token authentication.

## Authentication Security

### Password Security

**Hashing Algorithm**: bcrypt with configurable rounds

```python
# Default: 12 rounds (can be configured)
BCRYPT_ROUNDS=12
```

**Requirements**:
- Minimum 8 characters
- Enforced in Pydantic schemas
- Recommend complexity requirements in production

**Best Practices**:
- Use strong, unique passwords
- Consider password complexity rules
- Implement password expiration policies
- Monitor failed login attempts

### Token Security

#### Access Tokens

- **Algorithm**: HMAC-SHA256 (HS256)
- **Lifetime**: 15 minutes (configurable)
- **Storage**: Client-side in MacOS Keychain
- **Transmission**: HTTPS only
- **Revocation**: Database-backed revocation list

#### Refresh Tokens

- **Lifetime**: 7 days (configurable)
- **Single-use**: Can implement rotation
- **Storage**: Client-side in MacOS Keychain
- **Revocation**: On logout or admin action

#### JWT Structure

```json
{
  "sub": "user_id",
  "username": "string",
  "is_admin": boolean,
  "type": "access|refresh",
  "exp": timestamp,
  "iat": timestamp,
  "jti": "unique_token_id"
}
```

#### JWT Secret Key

**Generation**:
```bash
openssl rand -hex 32
```

**Requirements**:
- Minimum 256 bits (32 bytes)
- Cryptographically random
- Never commit to version control
- Store in environment variables
- Rotate periodically

### Session Management

- **Token Revocation**: Immediate via database flag
- **Logout**: Revokes current access token
- **Admin Revocation**: Admin can revoke any user's tokens
- **Automatic Cleanup**: Expired tokens can be purged

## Network Security

### TLS/SSL Configuration

**Minimum Version**: TLS 1.2 (TLS 1.3 recommended)

**Certificate Options**:
1. **Let's Encrypt** (Recommended for production)
2. **Commercial CA** certificate
3. **Self-signed** (Testing only)

**Configuration**:
```bash
TLS_ENABLED=true
TLS_CERT_PATH=/etc/vpn/certs/cert.pem
TLS_KEY_PATH=/etc/vpn/certs/key.pem
```

**Certificate Renewal**:
- Let's Encrypt: Auto-renewal with certbot
- Manual renewal: Every 90 days recommended
- Monitor expiration dates

### VPN Encryption

**WireGuard Security**:
- **Key Exchange**: Noise_IK handshake
- **Encryption**: ChaCha20-Poly1305
- **Authentication**: Curve25519 for DH
- **Hash**: BLAKE2s

**Perfect Forward Secrecy**: Optional preshared keys

**Key Rotation**: Generate new keys periodically

### Firewall Configuration

**Required Open Ports**:
- UDP 51820: WireGuard VPN traffic
- TCP 8443: API traffic (HTTPS)

**Firewall Rules**:
```bash
# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow WireGuard
iptables -A INPUT -p udp --dport 51820 -j ACCEPT

# Allow API
iptables -A INPUT -p tcp --dport 8443 -j ACCEPT

# Drop everything else
iptables -A INPUT -j DROP
```

**NAT Configuration**:
```bash
# Enable forwarding
sysctl -w net.ipv4.ip_forward=1

# NAT for VPN traffic
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE
```

## API Security

### Input Validation

**Pydantic Schemas**: All API inputs validated

**Example**:
```python
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
```

**SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

### Rate Limiting

**Configuration**:
```bash
RATE_LIMIT_PER_MINUTE=60
```

**Implementation**: Per-IP rate limiting

**Recommendations**:
- Adjust based on expected traffic
- Implement per-user rate limiting
- Use Redis for distributed rate limiting
- Monitor for abuse patterns

### CORS Configuration

**Development**:
```python
allow_origins=["*"]  # Allow all origins
```

**Production**:
```python
allow_origins=["https://yourdomain.com"]  # Specific origins only
```

### Security Headers

**Recommended Headers**:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

## Key Management

### Server Keys

**WireGuard Server Keys**:
- Location: `/etc/wireguard/`
- Permissions: `600` (root only)
- Backup: Encrypted backups only
- Rotation: Coordinate with all clients

**JWT Secret**:
- Location: Environment variables / `.env` file
- Permissions: `600` (root only)
- Rotation: Invalidates all tokens
- Backup: Encrypted backups only

### Client Keys

**Generation**: Per-user, on-demand

**Storage**:
- Server: Database (encrypted at rest recommended)
- Client: Local config file with restrictive permissions

**Transmission**: Once, over HTTPS

**Revocation**: Remove peer from WireGuard

## Access Control

### User Roles

**Regular User**:
- Register account
- Login/logout
- Provision VPN
- View own status
- Disconnect own VPN

**Admin User**:
- All regular user permissions
- List all users
- Delete users
- View all peers
- Remove peers
- View server status
- Generate tokens for users

### Authorization

**Implementation**: Role-based access control (RBAC)

**Middleware**: JWT token validation + role check

**Example**:
```python
async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

## Audit Logging

### Logged Events

**Authentication**:
- User registration
- Login attempts (success/failure)
- Logout
- Token refresh
- Token revocation

**VPN Operations**:
- VPN provisioning
- VPN disconnection
- Peer creation/removal

**Administrative**:
- User creation/deletion
- Admin actions on other users

### Log Format

```python
{
    "user_id": 1,
    "action": "user_login",
    "resource_type": "user",
    "resource_id": "1",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "status": "success",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### Log Security

- **Storage**: Append-only
- **Retention**: 90 days minimum
- **Protection**: Read-only for non-root
- **Monitoring**: Alert on suspicious patterns

## Threat Mitigation

### Brute Force Attacks

**Mitigation**:
- Rate limiting on login endpoint
- Account lockout after N failed attempts
- CAPTCHA for suspicious activity
- Monitor failed login patterns

### Token Theft

**Mitigation**:
- Short-lived access tokens
- HTTPS-only transmission
- Secure client-side storage (Keychain)
- Token revocation capability
- IP-based token validation (optional)

### Man-in-the-Middle (MITM)

**Mitigation**:
- Mandatory TLS/SSL
- Certificate pinning (optional)
- HSTS headers
- Certificate transparency monitoring

### Denial of Service (DoS)

**Mitigation**:
- Rate limiting
- Connection limits
- Firewall rules
- Resource monitoring
- Load balancing (if available)

### Privilege Escalation

**Mitigation**:
- Principle of least privilege
- Role-based access control
- Admin action logging
- Regular permission audits

### Data Breaches

**Mitigation**:
- Password hashing (bcrypt)
- Database encryption at rest (optional)
- Encrypted backups
- Limited data collection
- Regular security audits

## Client Security

### MacOS Client

**Token Storage**: MacOS Keychain

**Configuration Storage**: `~/.vpn-client/` with `600` permissions

**WireGuard Config**: `/usr/local/etc/wireguard/` with `600` permissions

**Security Features**:
- Automatic token refresh
- Secure credential storage
- TLS certificate validation
- No password caching

## Security Best Practices

### Deployment

1. **Use HTTPS/TLS**: Never run in production without TLS
2. **Strong JWT Secret**: 256-bit random key
3. **Firewall**: Only required ports open
4. **Updates**: Keep system and packages updated
5. **Monitoring**: Set up logging and alerting
6. **Backups**: Encrypted backups of database and keys
7. **Limited Access**: Minimal sudo/root access

### Configuration

1. **Environment Variables**: Never hardcode secrets
2. **File Permissions**: Restrictive permissions on configs
3. **Database**: Use PostgreSQL in production with SSL
4. **Rate Limits**: Adjust based on expected load
5. **Token Expiry**: Balance security vs. usability

### Operations

1. **Regular Audits**: Review logs for suspicious activity
2. **User Management**: Remove inactive users
3. **Token Cleanup**: Purge expired/revoked tokens
4. **Key Rotation**: Periodic key rotation schedule
5. **Incident Response**: Have a plan for security incidents

### Monitoring

1. **Failed Logins**: Alert on repeated failures
2. **Admin Actions**: Log and review all admin operations
3. **Unusual Traffic**: Monitor for suspicious patterns
4. **Resource Usage**: Track API and VPN usage
5. **Certificate Expiry**: Monitor SSL certificate expiration

## Compliance Considerations

### Data Privacy

- **Minimal Collection**: Only collect necessary data
- **Data Retention**: Define retention policies
- **User Rights**: Implement data deletion on request
- **Encryption**: Encrypt sensitive data at rest

### GDPR (if applicable)

- Right to access
- Right to deletion
- Data portability
- Consent management
- Breach notification procedures

## Security Checklist

### Pre-Deployment

- [ ] Generate strong JWT secret
- [ ] Configure TLS/SSL with valid certificate
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Set strong bcrypt rounds
- [ ] Review CORS settings
- [ ] Set up audit logging
- [ ] Configure secure database connection
- [ ] Set restrictive file permissions
- [ ] Disable debug mode

### Post-Deployment

- [ ] Create initial admin user with strong password
- [ ] Test authentication flow
- [ ] Verify TLS/SSL configuration
- [ ] Test rate limiting
- [ ] Review initial logs
- [ ] Set up monitoring and alerts
- [ ] Schedule regular backups
- [ ] Document security procedures
- [ ] Plan incident response
- [ ] Schedule security audits

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Update system packages monthly
- [ ] Review user access quarterly
- [ ] Rotate JWT secret annually
- [ ] Security audit annually
- [ ] Test backups monthly
- [ ] Review and update firewall rules
- [ ] Monitor certificate expiration
- [ ] Clean up expired tokens
- [ ] Review API access patterns

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **Do Not** create a public GitHub issue
2. Email security contact directly
3. Provide detailed description
4. Allow reasonable time for response
5. Coordinate disclosure timing

## References

- [WireGuard Security](https://www.wireguard.com/formal-verification/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/)
