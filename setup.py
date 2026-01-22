"""Setup configuration for VPN server package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vpn-server",
    version="1.0.0",
    author="VPN Server Team",
    description="WireGuard VPN server with bearer token authentication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/vpn-server",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.23",
        "alembic>=1.12.1",
        "pyjwt>=2.8.0",
        "python-multipart>=0.0.6",
        "passlib[bcrypt]>=1.7.4",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "rich>=13.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "cryptography>=41.0.7",
        "email-validator>=2.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "client": [
            "requests>=2.31.0",
            "keyring>=24.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vpn-admin=server.cli.vpn_admin:cli",
            "vpn-client=client.vpn_client.main:cli",
        ],
    },
)
