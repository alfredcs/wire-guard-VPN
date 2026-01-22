# API Documentation

## Base URL

```
https://vpn.example.com:8443/api/v1
```

## Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### Health Check

#### GET /health

Check if the service is running.

**Authentication**: None required

**Response**:
```json
{
  "message": "Service is healthy",
  "status": "success"
}
```

---

### Authentication

#### POST /api/v1/auth/register

Register a new user account.

**Authentication**: None required

**Request Body**:
```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "username": "string",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Errors**:
- `400`: Username or email already exists
- `422`: Validation error

---

#### POST /api/v1/auth/login

Login and obtain access and refresh tokens.

**Authentication**: None required

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `401`: Incorrect username or password

---

#### POST /api/v1/auth/refresh

Refresh an expired access token using a refresh token.

**Authentication**: None required

**Request Body**:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `401`: Invalid or expired refresh token

---

#### POST /api/v1/auth/logout

Logout and revoke current access token.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "message": "Logged out successfully",
  "status": "success"
}
```

---

#### GET /api/v1/auth/validate

Validate the current access token.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "valid": true,
  "user_id": 1,
  "username": "string",
  "expires_at": "2024-01-01T00:15:00Z"
}
```

**Errors**:
- `401`: Invalid or expired token

---

### VPN Management

#### POST /api/v1/vpn/provision

Provision VPN configuration for the authenticated user.

**Authentication**: Required

**Request Body**:
```json
{
  "device_name": "MacBook Pro"
}
```

**Response** (200 OK):
```json
{
  "interface": {
    "private_key": "yAnz5TF+lXXJte14tji3zlMNq+hd2rYUIgJBgB3fBmk=",
    "address": "10.0.0.2/32",
    "dns": "1.1.1.1,8.8.8.8"
  },
  "peer": {
    "public_key": "HIgo9xNzJMWLKASShiTqIybxZ0U3wGLiUeJ1PKf8ykw=",
    "endpoint": "vpn.example.com:51820",
    "allowed_ips": "0.0.0.0/0,::/0"
  },
  "config_file": "[Interface]\nPrivateKey = ...\n[Peer]\n..."
}
```

**Notes**:
- If user already has an active peer, returns existing configuration
- If user doesn't have a peer, creates a new one

**Errors**:
- `401`: Unauthorized
- `507`: No available IP addresses

---

#### GET /api/v1/vpn/status

Get current VPN connection status for the authenticated user.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "connected": true,
  "assigned_ip": "10.0.0.2/32",
  "last_handshake": "2024-01-01T00:10:00Z",
  "transfer_rx": 1048576,
  "transfer_tx": 524288
}
```

**Notes**:
- `connected`: `false` if user has no active peer
- Statistics based on last recorded values

---

#### DELETE /api/v1/vpn/disconnect

Disconnect from VPN and revoke access.

**Authentication**: Required

**Response** (200 OK):
```json
{
  "message": "Disconnected from VPN successfully",
  "status": "success"
}
```

**Errors**:
- `401`: Unauthorized
- `404`: No active VPN connection found
- `500`: Failed to disconnect

---

### Admin Endpoints

All admin endpoints require admin privileges.

#### GET /api/v1/admin/users

List all users (admin only).

**Authentication**: Required (Admin)

**Response** (200 OK):
```json
{
  "total": 10,
  "users": [
    {
      "id": 1,
      "username": "string",
      "email": "user@example.com",
      "is_active": true,
      "is_admin": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Errors**:
- `401`: Unauthorized
- `403`: Admin access required

---

#### DELETE /api/v1/admin/users/{user_id}

Delete a user (admin only).

**Authentication**: Required (Admin)

**Path Parameters**:
- `user_id` (integer): User ID to delete

**Response** (200 OK):
```json
{
  "message": "User username deleted successfully",
  "status": "success"
}
```

**Errors**:
- `400`: Cannot delete your own account
- `401`: Unauthorized
- `403`: Admin access required
- `404`: User not found

---

#### GET /api/v1/admin/peers

List all active VPN peers (admin only).

**Authentication**: Required (Admin)

**Response** (200 OK):
```json
{
  "total": 5,
  "peers": [
    {
      "id": 1,
      "user_id": 1,
      "username": "string",
      "assigned_ip": "10.0.0.2/32",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "last_handshake": "2024-01-01T00:10:00Z",
      "transfer_rx": 1048576,
      "transfer_tx": 524288
    }
  ]
}
```

**Errors**:
- `401`: Unauthorized
- `403`: Admin access required

---

#### GET /api/v1/admin/status

Get server status (admin only).

**Authentication**: Required (Admin)

**Response** (200 OK):
```json
{
  "status": "running",
  "wireguard_interface": "wg0",
  "active_peers": 5,
  "total_users": 10,
  "uptime": "5 days, 3:24:15"
}
```

**Errors**:
- `401`: Unauthorized
- `403`: Admin access required

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message",
  "detail": "Optional detailed error information",
  "status": "error"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error
- `507 Insufficient Storage`: No available resources

## Rate Limiting

- Default: 60 requests per minute per IP
- Configurable via `RATE_LIMIT_PER_MINUTE` environment variable
- Exceeded rate limit returns `429 Too Many Requests`

## Token Lifecycle

### Access Token
- **Lifetime**: 15 minutes (configurable)
- **Usage**: All authenticated API requests
- **Storage**: Client-side (MacOS Keychain)
- **Refresh**: Using refresh token when expired

### Refresh Token
- **Lifetime**: 7 days (configurable)
- **Usage**: Obtaining new access tokens
- **Storage**: Client-side (MacOS Keychain)
- **Revocation**: On logout or admin action

### Token Structure

JWT tokens contain:
```json
{
  "sub": "1",
  "username": "string",
  "is_admin": false,
  "type": "access",
  "exp": 1704067200,
  "iat": 1704066300,
  "jti": "uuid"
}
```

## Examples

### Complete Authentication Flow

```bash
# 1. Register
curl -X POST https://vpn.example.com:8443/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"user1@example.com","password":"secure123"}'

# 2. Login
curl -X POST https://vpn.example.com:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"secure123"}'

# Response:
# {
#   "access_token": "eyJ0eXAi...",
#   "refresh_token": "eyJ0eXAi...",
#   ...
# }

# 3. Use access token
curl -X POST https://vpn.example.com:8443/api/v1/vpn/provision \
  -H "Authorization: Bearer eyJ0eXAi..." \
  -H "Content-Type: application/json" \
  -d '{}'

# 4. Refresh when expired
curl -X POST https://vpn.example.com:8443/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"eyJ0eXAi..."}'
```

### VPN Provisioning Flow

```bash
# 1. Provision VPN
curl -X POST https://vpn.example.com:8443/api/v1/vpn/provision \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"device_name":"MacBook Pro"}'

# 2. Check status
curl -X GET https://vpn.example.com:8443/api/v1/vpn/status \
  -H "Authorization: Bearer <token>"

# 3. Disconnect
curl -X DELETE https://vpn.example.com:8443/api/v1/vpn/disconnect \
  -H "Authorization: Bearer <token>"
```

## Interactive API Documentation

When the server is running, interactive API documentation is available at:

- **Swagger UI**: `https://vpn.example.com:8443/api/docs`
- **ReDoc**: `https://vpn.example.com:8443/api/redoc`
