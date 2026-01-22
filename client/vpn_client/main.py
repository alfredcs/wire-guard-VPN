#!/usr/bin/env python3
"""VPN Client CLI Tool."""

import click
import sys
import logging
from rich.console import Console
from rich.table import Table
from getpass import getpass

from . import __version__
from .config import config
from .auth import AuthClient
from .wireguard import WireGuardClient

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_auth_client() -> AuthClient:
    """Get authenticated client.

    Returns:
        AuthClient instance

    Raises:
        Exception: If not logged in
    """
    server_url = config.get("server_url")
    if not server_url:
        console.print("[red]Error: Not logged in. Please run 'vpn-client login' first.[/red]")
        sys.exit(1)

    return AuthClient(server_url)


@click.group()
@click.version_option(version=__version__)
def cli():
    """VPN Client CLI Tool.

    Connect to VPN server with bearer token authentication.
    """
    pass


@cli.command()
@click.argument("server_url")
@click.option("--username", "-u", help="Username")
@click.option("--password", "-p", help="Password (not recommended, will prompt if not provided)")
def login(server_url: str, username: str, password: str):
    """Login to VPN server."""
    try:
        # Get username if not provided
        if not username:
            username = click.prompt("Username")

        # Get password if not provided
        if not password:
            password = getpass("Password: ")

        # Create auth client and login
        auth_client = AuthClient(server_url)
        access_token, refresh_token = auth_client.login(username, password)

        console.print(f"[green]✓[/green] Login successful")
        console.print(f"  Server: {server_url}")
        console.print(f"  Username: {username}")
        console.print(f"\nUse 'vpn-client connect' to connect to VPN")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def logout():
    """Logout and clear credentials."""
    try:
        # Disconnect if connected
        if WireGuardClient.is_connected():
            console.print("Disconnecting from VPN...")
            WireGuardClient.disconnect()

        # Remove config
        WireGuardClient.remove_config()

        # Logout
        auth_client = get_auth_client()
        auth_client.logout()

        console.print("[green]✓[/green] Logout successful")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def connect():
    """Connect to VPN."""
    try:
        # Check if already connected
        if WireGuardClient.is_connected():
            console.print("[yellow]Already connected to VPN[/yellow]")
            return

        # Get auth client
        auth_client = get_auth_client()

        # Provision VPN if config doesn't exist
        from pathlib import Path
        from .config import WG_CONFIG_FILE

        if not WG_CONFIG_FILE.exists():
            console.print("Provisioning VPN configuration...")

            # Get VPN config from server
            response = auth_client.make_authenticated_request(
                "POST",
                "/api/v1/vpn/provision",
                json={}
            )

            data = response.json()
            config_content = data["config_file"]

            # Write config
            WireGuardClient.write_config(config_content)
            console.print("[green]✓[/green] Configuration provisioned")

        # Connect
        console.print("Connecting to VPN...")
        WireGuardClient.connect()
        console.print("[green]✓[/green] Connected to VPN")

        # Show status
        status = WireGuardClient.get_status()
        if status:
            console.print(f"\n[bold]Connection Details:[/bold]")
            if status.get("interface"):
                console.print(f"  Interface: {status['interface']}")
            if status.get("endpoint"):
                console.print(f"  Endpoint: {status['endpoint']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def disconnect():
    """Disconnect from VPN."""
    try:
        if not WireGuardClient.is_connected():
            console.print("[yellow]Not connected to VPN[/yellow]")
            return

        console.print("Disconnecting from VPN...")
        WireGuardClient.disconnect()
        console.print("[green]✓[/green] Disconnected from VPN")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def status():
    """Show VPN connection status."""
    try:
        # Check if logged in
        server_url = config.get("server_url")
        username = config.get("username")

        console.print("[bold]VPN Client Status[/bold]\n")

        if server_url:
            console.print(f"Server: {server_url}")
            console.print(f"Username: {username}")

            # Check if token is valid
            auth_client = AuthClient(server_url)
            if auth_client.validate_token():
                console.print("Authentication: [green]Valid[/green]")
            else:
                console.print("Authentication: [red]Invalid[/red]")
        else:
            console.print("Status: [red]Not logged in[/red]")
            return

        # Check VPN connection
        if WireGuardClient.is_connected():
            console.print("VPN: [green]Connected[/green]\n")

            # Get detailed status
            status = WireGuardClient.get_status()
            if status:
                console.print("[bold]Connection Details:[/bold]")
                if status.get("interface"):
                    console.print(f"  Interface: {status['interface']}")
                if status.get("endpoint"):
                    console.print(f"  Endpoint: {status['endpoint']}")
                if status.get("latest_handshake"):
                    console.print(f"  Latest Handshake: {status['latest_handshake']}")
                if status.get("transfer"):
                    console.print(f"  Transfer: {status['transfer']}")

            # Get status from server
            try:
                response = auth_client.make_authenticated_request(
                    "GET",
                    "/api/v1/vpn/status"
                )
                server_status = response.json()

                console.print(f"\n[bold]Server Status:[/bold]")
                console.print(f"  Connected: {'Yes' if server_status.get('connected') else 'No'}")
                if server_status.get("assigned_ip"):
                    console.print(f"  Assigned IP: {server_status['assigned_ip']}")

            except Exception as e:
                logger.warning(f"Failed to get server status: {e}")

        else:
            console.print("VPN: [red]Not connected[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.group()
def config_cmd():
    """Configuration management."""
    pass


@config_cmd.command("update")
def config_update():
    """Update VPN configuration from server."""
    try:
        # Check if connected
        if WireGuardClient.is_connected():
            console.print("[yellow]Please disconnect before updating configuration[/yellow]")
            sys.exit(1)

        auth_client = get_auth_client()

        console.print("Fetching new configuration from server...")

        # Get new config
        response = auth_client.make_authenticated_request(
            "POST",
            "/api/v1/vpn/provision",
            json={}
        )

        data = response.json()
        config_content = data["config_file"]

        # Write config
        WireGuardClient.write_config(config_content)

        console.print("[green]✓[/green] Configuration updated successfully")
        console.print("Use 'vpn-client connect' to connect with new configuration")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@config_cmd.command("show")
def config_show():
    """Show current configuration."""
    try:
        server_url = config.get("server_url")
        username = config.get("username")

        if not server_url:
            console.print("[yellow]Not configured[/yellow]")
            return

        table = Table(title="VPN Client Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Server URL", server_url)
        table.add_row("Username", username or "N/A")
        table.add_row("Config File", str(WG_CONFIG_FILE))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Add config subcommands to main CLI
cli.add_command(config_cmd, name="config")


if __name__ == "__main__":
    cli()
