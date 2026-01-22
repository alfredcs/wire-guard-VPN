"""Client authentication module."""

import requests
import keyring
from typing import Optional, Tuple
import logging

from .config import config, KEYCHAIN_SERVICE, KEYCHAIN_ACCESS_TOKEN, KEYCHAIN_REFRESH_TOKEN

logger = logging.getLogger(__name__)


class AuthClient:
    """Authentication client for VPN service."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = True  # Enable SSL verification in production

    def login(self, username: str, password: str) -> Tuple[str, str]:
        """Login and get tokens.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            Exception: If login fails
        """
        try:
            response = self.session.post(
                f"{self.server_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]

            # Store tokens in keychain
            keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCESS_TOKEN, access_token)
            keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_REFRESH_TOKEN, refresh_token)

            # Store server URL
            config.set("server_url", self.server_url)
            config.set("username", username)

            logger.info(f"Login successful for user: {username}")
            return access_token, refresh_token

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Invalid username or password")
            raise Exception(f"Login failed: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {str(e)}")

    def logout(self):
        """Logout and clear tokens."""
        try:
            access_token = self.get_access_token()
            if access_token:
                # Call logout endpoint
                try:
                    self.session.post(
                        f"{self.server_url}/api/v1/auth/logout",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    )
                except Exception as e:
                    logger.warning(f"Failed to call logout endpoint: {e}")

            # Clear tokens from keychain
            try:
                keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCESS_TOKEN)
            except keyring.errors.PasswordDeleteError:
                pass

            try:
                keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_REFRESH_TOKEN)
            except keyring.errors.PasswordDeleteError:
                pass

            # Clear config
            config.clear()

            logger.info("Logout successful")

        except Exception as e:
            logger.error(f"Logout error: {e}")
            raise

    def refresh_access_token(self) -> str:
        """Refresh access token using refresh token.

        Returns:
            New access token

        Raises:
            Exception: If refresh fails
        """
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            raise Exception("No refresh token found. Please login again.")

        try:
            response = self.session.post(
                f"{self.server_url}/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            access_token = data["access_token"]

            # Update access token in keychain
            keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCESS_TOKEN, access_token)

            logger.info("Access token refreshed successfully")
            return access_token

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Refresh token expired, need to login again
                self.logout()
                raise Exception("Session expired. Please login again.")
            raise Exception(f"Token refresh failed: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {str(e)}")

    def get_access_token(self) -> Optional[str]:
        """Get access token from keychain."""
        try:
            return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCESS_TOKEN)
        except Exception:
            return None

    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token from keychain."""
        try:
            return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_REFRESH_TOKEN)
        except Exception:
            return None

    def validate_token(self) -> bool:
        """Validate current access token.

        Returns:
            True if token is valid, False otherwise
        """
        access_token = self.get_access_token()
        if not access_token:
            return False

        try:
            response = self.session.get(
                f"{self.server_url}/api/v1/auth/validate",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated request with automatic token refresh.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            Exception: If request fails
        """
        access_token = self.get_access_token()
        if not access_token:
            raise Exception("Not logged in. Please login first.")

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"
        kwargs["headers"] = headers

        url = f"{self.server_url}{endpoint}"

        try:
            response = self.session.request(method, url, timeout=10, **kwargs)

            # If token expired, try to refresh
            if response.status_code == 401:
                logger.info("Access token expired, refreshing...")
                access_token = self.refresh_access_token()
                headers["Authorization"] = f"Bearer {access_token}"
                kwargs["headers"] = headers
                response = self.session.request(method, url, timeout=10, **kwargs)

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
