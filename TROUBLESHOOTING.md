# Troubleshooting Guide

## Common Issues and Solutions

### 1. bcrypt Compatibility Error

**Symptom:**
```
Error: password cannot be longer than 72 bytes, truncate manually if necessary
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Cause:** The server has bcrypt 5.x installed, which is incompatible with passlib 1.7.4.

**Solution:**

Run the fix script on the server:

```bash
sudo bash /path/to/vpn/fix_bcrypt.sh
```

Or manually fix it:

```bash
# Activate the virtual environment
source /opt/vpn-server/venv/bin/activate

# Downgrade bcrypt
pip uninstall -y bcrypt
pip install 'bcrypt>=4.0.0,<5.0.0'

# Verify the fix
pip show bcrypt
```

After fixing, try creating the user again:

```bash
vpn-admin user add admin admin@example.com --admin
```

---

### 2. WireGuard Command Not Found

**Symptom:**
```
wg: command not found
```

**Solution:**

Install WireGuard tools:

```bash
# Fedora/RHEL
sudo dnf install wireguard-tools

# Ubuntu/Debian
sudo apt install wireguard-tools

# Verify installation
wg --version
```

---

### 3. Database Permission Errors

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/var/lib/vpn/vpn.db'
```

**Solution:**

Fix database directory permissions:

```bash
sudo mkdir -p /var/lib/vpn
sudo chown root:root /var/lib/vpn
sudo chmod 755 /var/lib/vpn
```

---

### 4. API Service Won't Start

**Symptom:**
```
systemctl status vpn-auth
● vpn-auth.service - VPN Authentication Service
   Loaded: loaded
   Active: failed
```

**Solution:**

Check the logs:

```bash
sudo journalctl -u vpn-auth -n 50 --no-pager
```

Common causes:
- Missing environment variables in `/etc/vpn/.env`
- Port 8443 already in use
- Database file permissions

Fix:
```bash
# Check environment file
sudo cat /etc/vpn/.env

# Check if port is in use
sudo netstat -tlnp | grep 8443

# Restart service
sudo systemctl restart vpn-auth
```

---

### 5. JWT Secret Key Error

**Symptom:**
```
ValidationError: jwt_secret_key Field required
```

**Solution:**

Generate and set a JWT secret:

```bash
# Generate a secure secret
openssl rand -hex 32

# Edit config
sudo nano /etc/vpn/.env

# Add the line:
JWT_SECRET_KEY=<generated-key-here>

# Restart service
sudo systemctl restart vpn-auth
```

---

### 6. WireGuard Interface Won't Start

**Symptom:**
```
systemctl status wg-quick@wg0
Active: failed
```

**Solution:**

Check WireGuard configuration:

```bash
# Verify config
sudo wg-quick up wg0

# Check kernel module
lsmod | grep wireguard

# Load module if missing
sudo modprobe wireguard

# Check configuration file
sudo cat /etc/wireguard/wg0.conf
```

---

### 7. Client Can't Connect to Server

**Symptom:**
```
vpn-client connect
Error: Connection refused
```

**Solution:**

1. **Check server is running:**
```bash
# On server
curl http://localhost:8443/health
```

2. **Check firewall:**
```bash
# On server
sudo firewall-cmd --list-ports

# Should show:
# 51820/udp 8443/tcp

# If not, add them:
sudo firewall-cmd --permanent --add-port=51820/udp
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload
```

3. **Check cloud provider security groups:**
- Ensure UDP 51820 is open
- Ensure TCP 8443 is open

---

### 8. Token Expired Error

**Symptom:**
```
Error: Token has expired
```

**Solution:**

Refresh your token:

```bash
# On client
vpn-client logout
vpn-client login https://your-server:8443
```

Access tokens expire after 15 minutes by default. This is normal and secure.

---

### 9. Python Module Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**

Reinstall dependencies:

```bash
source /opt/vpn-server/venv/bin/activate
pip install -r /opt/vpn-server/requirements.txt
```

---

### 10. Database Migration Issues

**Symptom:**
```
sqlalchemy.exc.OperationalError: no such table: users
```

**Solution:**

Initialize the database:

```bash
source /opt/vpn-server/venv/bin/activate
cd /opt/vpn-server

# Run Python to initialize DB
python3 << 'EOF'
from auth_service.database import init_db
init_db()
print("Database initialized successfully")
EOF
```

---

## Client-Specific Issues

### MacOS Client: Keyring Access Denied

**Symptom:**
```
Error: Access to keychain denied
```

**Solution:**

Grant keychain access:
1. Open "Keychain Access" app
2. Find "com.vpn.client" entries
3. Right-click → Get Info → Access Control
4. Add Python to allowed applications

---

### MacOS Client: WireGuard Config Error

**Symptom:**
```
Error: VPN not configured
```

**Solution:**

```bash
# Check config exists
ls -la /usr/local/etc/wireguard/

# If missing, provision again
vpn-client config update
```

---

## Performance Issues

### Slow VPN Connection

**Causes and Solutions:**

1. **MTU Issues:**
```bash
# On client, adjust MTU
sudo ifconfig utun3 mtu 1420
```

2. **Server Overloaded:**
```bash
# Check server load
top
htop

# Check active connections
sudo wg show
```

3. **Network Issues:**
```bash
# Test latency
ping 10.0.0.1

# Test bandwidth
iperf3 -c 10.0.0.1
```

---

## Debugging Commands

### Server Debugging

```bash
# View all logs
sudo journalctl -u vpn-auth -u wg-quick@wg0 -f

# Check process
ps aux | grep uvicorn

# Check listening ports
sudo netstat -tlnp | grep -E '8443|51820'

# Check WireGuard status
sudo wg show wg0

# List database users
vpn-admin user list

# List active peers
vpn-admin peer list
```

### Client Debugging

```bash
# Check connection status
vpn-client status

# Verify token
vpn-client config show

# Test server connectivity
curl https://your-server:8443/health

# Check WireGuard
wg show

# Check routing
netstat -rn | grep utun
```

---

## Getting Help

If you're still experiencing issues:

1. **Check logs:**
   - Server: `sudo journalctl -u vpn-auth -n 100`
   - WireGuard: `sudo journalctl -u wg-quick@wg0 -n 100`

2. **Verify installation:**
   ```bash
   vpn-admin status
   ```

3. **Test components individually:**
   - Database: Check `/var/lib/vpn/vpn.db` exists
   - API: `curl http://localhost:8443/health`
   - WireGuard: `sudo wg show wg0`

4. **Review documentation:**
   - `docs/DEPLOYMENT.md` - Deployment guide
   - `docs/SECURITY.md` - Security configuration
   - `docs/API.md` - API reference

5. **Report issue:**
   - Include error messages
   - Include relevant logs
   - Include system information (OS, Python version)

---

## Prevention

### Best Practices

1. **Keep backups:**
```bash
# Backup database
sudo cp /var/lib/vpn/vpn.db /var/lib/vpn/vpn.db.backup

# Backup config
sudo cp /etc/vpn/.env /etc/vpn/.env.backup
```

2. **Monitor services:**
```bash
# Set up monitoring
systemctl status vpn-auth wg-quick@wg0
```

3. **Keep updated:**
```bash
# Update system
sudo dnf update

# Update Python packages
source /opt/vpn-server/venv/bin/activate
pip list --outdated
```

4. **Regular testing:**
```bash
# Test from client
vpn-client status
vpn-client connect
```

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| bcrypt error | Run `fix_bcrypt.sh` |
| Service won't start | Check logs with `journalctl` |
| Can't connect | Check firewall ports |
| Token expired | Run `vpn-client login` again |
| No WireGuard | Install `wireguard-tools` |

---

**Last Updated:** 2026-01-22
