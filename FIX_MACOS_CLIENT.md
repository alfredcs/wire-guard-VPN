# Fix for macOS Client ModuleNotFoundError

## Problem
The `vpn-client` command fails with:
```
ModuleNotFoundError: No module named 'vpn_client'
```

## Quick Fix (Option A)

Edit the wrapper script at `/usr/local/bin/vpn-client`:

```bash
sudo nano /usr/local/bin/vpn-client
```

Change the content to:
```bash
#!/bin/bash
export PYTHONPATH="/usr/local/lib/vpn-client:$PYTHONPATH"
/usr/local/lib/vpn-client/venv/bin/python -m vpn_client.main "$@"
```

Save and test:
```bash
vpn-client login https://infs.cavatar.info:8443
```

## Better Fix (Option B) - Reinstall

Run the uninstall script first:
```bash
cd /path/to/wire-guard-VPN/client/macos
sudo ./uninstall.sh
```

Then reinstall using the updated install script (which now includes the fix):
```bash
sudo ./install.sh
```

## Verify Installation

After applying either fix, verify it works:
```bash
vpn-client --version
vpn-client --help
```
