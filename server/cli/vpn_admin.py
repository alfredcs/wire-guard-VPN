#!/usr/bin/env python3
"""VPN Server Administration CLI Tool."""

import click
import sys
import os
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_service.config import settings
from auth_service.database import SessionLocal, init_db
from auth_service.models import User, Token, Peer
from auth_service.auth import AuthService
from auth_service.wireguard import WireGuardManager

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """VPN Server Administration Tool.

    Manage users, tokens, peers, and monitor VPN server status.
    """
    pass


# ============================================================================
# User Management Commands
# ============================================================================

@cli.group()
def user():
    """User management commands."""
    pass


@user.command("add")
@click.argument("username")
@click.argument("email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="User password")
@click.option("--admin", is_flag=True, help="Make user an administrator")
def user_add(username: str, email: str, password: str, admin: bool):
    """Add a new user."""
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            console.print("[red]Error: Username or email already exists[/red]")
            sys.exit(1)

        # Create user
        hashed_password = AuthService.hash_password(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        console.print(f"[green]✓[/green] User created successfully")
        console.print(f"  ID: {user.id}")
        console.print(f"  Username: {user.username}")
        console.print(f"  Email: {user.email}")
        console.print(f"  Admin: {user.is_admin}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@user.command("remove")
@click.argument("username")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def user_remove(username: str, force: bool):
    """Remove a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User '{username}' not found[/red]")
            sys.exit(1)

        if not force:
            if not click.confirm(f"Are you sure you want to remove user '{username}'?"):
                console.print("Cancelled")
                return

        # Remove peers
        peers = db.query(Peer).filter(Peer.user_id == user.id, Peer.is_active == True).all()
        for peer in peers:
            try:
                WireGuardManager.remove_peer(db, peer)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to remove peer {peer.id}: {e}[/yellow]")

        # Delete user
        db.delete(user)
        db.commit()

        console.print(f"[green]✓[/green] User '{username}' removed successfully")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@user.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def user_list(output_json: bool):
    """List all users."""
    db = SessionLocal()
    try:
        users = db.query(User).all()

        if output_json:
            import json
            data = [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "is_active": u.is_active,
                    "is_admin": u.is_admin,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
            print(json.dumps(data, indent=2))
        else:
            table = Table(title="VPN Users")
            table.add_column("ID", style="cyan")
            table.add_column("Username", style="green")
            table.add_column("Email", style="blue")
            table.add_column("Active", style="yellow")
            table.add_column("Admin", style="magenta")
            table.add_column("Created", style="white")

            for u in users:
                table.add_row(
                    str(u.id),
                    u.username,
                    u.email,
                    "✓" if u.is_active else "✗",
                    "✓" if u.is_admin else "✗",
                    u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A"
                )

            console.print(table)
            console.print(f"\nTotal users: {len(users)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@user.command("reset-password")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="New password")
def user_reset_password(username: str, password: str):
    """Reset user password."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User '{username}' not found[/red]")
            sys.exit(1)

        user.hashed_password = AuthService.hash_password(password)
        db.commit()

        console.print(f"[green]✓[/green] Password reset successfully for user '{username}'")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


# ============================================================================
# Token Management Commands
# ============================================================================

@cli.group()
def token():
    """Token management commands."""
    pass


@token.command("generate")
@click.argument("username")
@click.option("--expires", type=int, help="Token expiration in minutes (default: 15)")
def token_generate(username: str, expires: int):
    """Generate a bearer token for a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User '{username}' not found[/red]")
            sys.exit(1)

        if not user.is_active:
            console.print(f"[red]Error: User '{username}' is inactive[/red]")
            sys.exit(1)

        # Generate tokens
        expires_delta = timedelta(minutes=expires) if expires else None
        access_token, access_jti, access_expires = AuthService.create_access_token(
            user.id, user.username, user.is_admin, expires_delta
        )
        refresh_token, refresh_jti, refresh_expires = AuthService.create_refresh_token(
            user.id, user.username
        )

        # Save tokens
        AuthService.save_token(db, user.id, "access", access_jti, access_expires)
        AuthService.save_token(db, user.id, "refresh", refresh_jti, refresh_expires)

        console.print(f"[green]✓[/green] Tokens generated for user '{username}'")
        console.print(f"\n[bold]Access Token:[/bold]")
        console.print(f"{access_token}")
        console.print(f"\n[bold]Refresh Token:[/bold]")
        console.print(f"{refresh_token}")
        console.print(f"\n[dim]Access token expires: {access_expires}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@token.command("revoke")
@click.argument("token_id", type=int)
def token_revoke(token_id: int):
    """Revoke a token by ID."""
    db = SessionLocal()
    try:
        token = db.query(Token).filter(Token.id == token_id).first()
        if not token:
            console.print(f"[red]Error: Token ID {token_id} not found[/red]")
            sys.exit(1)

        token.is_revoked = True
        token.revoked_at = datetime.utcnow()
        db.commit()

        console.print(f"[green]✓[/green] Token {token_id} revoked successfully")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@token.command("list")
@click.argument("username")
@click.option("--active-only", is_flag=True, help="Show only active tokens")
def token_list(username: str, active_only: bool):
    """List tokens for a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            console.print(f"[red]Error: User '{username}' not found[/red]")
            sys.exit(1)

        query = db.query(Token).filter(Token.user_id == user.id)
        if active_only:
            query = query.filter(Token.is_revoked == False)

        tokens = query.all()

        table = Table(title=f"Tokens for {username}")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("JTI", style="blue")
        table.add_column("Expires", style="yellow")
        table.add_column("Revoked", style="red")
        table.add_column("Created", style="white")

        for t in tokens:
            table.add_row(
                str(t.id),
                t.token_type,
                t.jti[:8] + "...",
                t.expires_at.strftime("%Y-%m-%d %H:%M") if t.expires_at else "N/A",
                "✓" if t.is_revoked else "✗",
                t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "N/A"
            )

        console.print(table)
        console.print(f"\nTotal tokens: {len(tokens)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


# ============================================================================
# Peer Management Commands
# ============================================================================

@cli.group()
def peer():
    """Peer management commands."""
    pass


@peer.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def peer_list(output_json: bool):
    """List all active peers."""
    db = SessionLocal()
    try:
        peers = db.query(Peer).filter(Peer.is_active == True).all()

        if output_json:
            import json
            data = []
            for p in peers:
                user = db.query(User).filter(User.id == p.user_id).first()
                data.append({
                    "id": p.id,
                    "user_id": p.user_id,
                    "username": user.username if user else None,
                    "assigned_ip": p.assigned_ip,
                    "public_key": p.public_key,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                })
            print(json.dumps(data, indent=2))
        else:
            table = Table(title="Active VPN Peers")
            table.add_column("ID", style="cyan")
            table.add_column("User", style="green")
            table.add_column("IP", style="blue")
            table.add_column("Public Key", style="yellow")
            table.add_column("Created", style="white")

            for p in peers:
                user = db.query(User).filter(User.id == p.user_id).first()
                table.add_row(
                    str(p.id),
                    user.username if user else f"ID:{p.user_id}",
                    p.assigned_ip,
                    p.public_key[:16] + "...",
                    p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "N/A"
                )

            console.print(table)
            console.print(f"\nTotal active peers: {len(peers)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@peer.command("remove")
@click.argument("peer_id", type=int)
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def peer_remove(peer_id: int, force: bool):
    """Remove a peer."""
    db = SessionLocal()
    try:
        peer = db.query(Peer).filter(Peer.id == peer_id).first()
        if not peer:
            console.print(f"[red]Error: Peer ID {peer_id} not found[/red]")
            sys.exit(1)

        if not force:
            if not click.confirm(f"Are you sure you want to remove peer {peer_id}?"):
                console.print("Cancelled")
                return

        WireGuardManager.remove_peer(db, peer)
        console.print(f"[green]✓[/green] Peer {peer_id} removed successfully")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


# ============================================================================
# Status Commands
# ============================================================================

@cli.command()
def status():
    """Show VPN server status."""
    db = SessionLocal()
    try:
        # Get database stats
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_peers = db.query(Peer).filter(Peer.is_active == True).count()

        # Get WireGuard status
        try:
            wg_status = WireGuardManager.get_interface_status()
            wg_running = True
        except Exception as e:
            wg_status = None
            wg_running = False

        console.print("[bold]VPN Server Status[/bold]\n")
        console.print(f"Database: [green]Connected[/green]")
        console.print(f"WireGuard Interface: {'[green]Running[/green]' if wg_running else '[red]Not Running[/red]'}")
        console.print(f"Interface Name: {settings.wg_interface}")
        console.print(f"Interface Address: {settings.wg_address}")
        console.print(f"Listen Port: {settings.wg_port}")
        console.print(f"\n[bold]Statistics[/bold]")
        console.print(f"Total Users: {total_users}")
        console.print(f"Active Users: {active_users}")
        console.print(f"Active Peers: {total_peers}")

        if wg_status and "peers" in wg_status:
            console.print(f"WireGuard Peers: {len(wg_status['peers'])}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        db.close()


@cli.command()
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
def logs(lines: int):
    """View server logs."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", "vpn-auth", "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True
        )
        console.print(result.stdout)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Note: This command requires systemd and appropriate permissions[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    # Initialize database
    init_db()
    cli()
