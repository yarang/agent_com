#!/usr/bin/env python3
"""
Token Migration Script

Migrates AGENT_TOKEN from .mcp.json to OS keychain for secure storage.

Security improvements:
1. Removes plaintext tokens from .mcp.json
2. Stores tokens in OS keychain (keyring)
3. Provides environment variable fallback
4. Validates token format before migration

Usage:
    python scripts/migrate_tokens.py [--validate] [--dry-run]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    print("Warning: keyring not installed. Install with: pip install keyring")


# Token validation patterns
VALID_TOKEN_PREFIXES = ["agent_", "sk-", "pk-"]
MIN_TOKEN_LENGTH = 32


class TokenMigrator:
    """Handles migration of tokens from .mcp.json to OS keychain."""

    def __init__(self, mcp_config_path: Optional[Path] = None):
        self.mcp_config_path = mcp_config_path or Path.cwd() / ".mcp.json"
        self.service_name = "agent-comm-mcp"

    def validate_token(self, token: str) -> tuple[bool, str]:
        """
        Validate token format and security requirements.

        Returns:
            (is_valid, error_message)
        """
        if not token:
            return False, "Token is empty"

        # Check for obvious placeholder values
        placeholder_indicators = ["your-", "here", "change", "placeholder", "example"]
        token_lower = token.lower()
        for indicator in placeholder_indicators:
            if indicator in token_lower:
                return False, f"Token contains placeholder indicator: {indicator}"

        # Check minimum length
        if len(token) < MIN_TOKEN_LENGTH:
            return False, f"Token too short (min {MIN_TOKEN_LENGTH} chars)"

        # Check for known prefixes (optional but recommended)
        has_valid_prefix = any(token.startswith(prefix) for prefix in VALID_TOKEN_PREFIXES)
        if not has_valid_prefix:
            print(f"Warning: Token does not start with known prefix: {VALID_TOKEN_PREFIXES}")

        # Check for suspicious patterns
        if " " in token:
            return False, "Token contains whitespace"

        if "\n" in token or "\r" in token or "\t" in token:
            return False, "Token contains control characters"

        return True, ""

    def get_token_from_config(self) -> Optional[str]:
        """Extract AGENT_TOKEN from .mcp.json configuration."""
        if not self.mcp_config_path.exists():
            print(f"Configuration file not found: {self.mcp_config_path}")
            return None

        try:
            with open(self.mcp_config_path, "r") as f:
                config = json.load(f)

            # Navigate to agent-comm server env
            agent_comm = config.get("mcpServers", {}).get("agent-comm", {})
            env = agent_comm.get("env", {})
            token = env.get("AGENT_TOKEN")

            if token:
                return token
            else:
                print("No AGENT_TOKEN found in configuration")
                return None

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration: {e}")
            return None
        except Exception as e:
            print(f"Error reading configuration: {e}")
            return None

    def store_token_in_keyring(self, nickname: str, token: str) -> bool:
        """Store token in OS keychain."""
        if not KEYRING_AVAILABLE:
            print("Keyring not available. Cannot store token in keychain.")
            return False

        try:
            # Use nickname as username for keyring lookup
            keyring.set_password(self.service_name, nickname, token)
            print(f"Token stored in keychain for: {nickname}")
            return True
        except Exception as e:
            print(f"Error storing token in keychain: {e}")
            return False

    def get_token_from_keyring(self, nickname: str) -> Optional[str]:
        """Retrieve token from OS keychain."""
        if not KEYRING_AVAILABLE:
            return None

        try:
            token = keyring.get_password(self.service_name, nickname)
            return token
        except Exception as e:
            print(f"Error retrieving token from keychain: {e}")
            return None

    def remove_token_from_config(self, dry_run: bool = False) -> bool:
        """Remove AGENT_TOKEN from .mcp.json configuration."""
        if not self.mcp_config_path.exists():
            print(f"Configuration file not found: {self.mcp_config_path}")
            return False

        try:
            with open(self.mcp_config_path, "r") as f:
                config = json.load(f)

            # Check if token exists
            agent_comm = config.get("mcpServers", {}).get("agent-comm", {})
            env = agent_comm.get("env", {})
            token = env.get("AGENT_TOKEN")

            if not token:
                print("No AGENT_TOKEN found in configuration")
                return False

            # Get nickname for reference
            nickname = env.get("AGENT_NICKNAME", "unknown")
            print(f"Found token for agent: {nickname}")

            # Remove token from config
            if "AGENT_TOKEN" in env:
                del env["AGENT_TOKEN"]

            # Write back to file
            if not dry_run:
                with open(self.mcp_config_path, "w") as f:
                    json.dump(config, f, indent=2)
                print(f"Token removed from {self.mcp_config_path}")
            else:
                print(f"[DRY RUN] Would remove token from {self.mcp_config_path}")

            return True

        except Exception as e:
            print(f"Error updating configuration: {e}")
            return False

    def migrate(self, dry_run: bool = False) -> bool:
        """
        Perform complete migration flow.

        Returns:
            True if migration successful
        """
        print("=" * 60)
        print("Agent Token Migration Script")
        print("=" * 60)

        # Step 1: Get token from config
        print("\n[Step 1/4] Reading token from configuration...")
        token = self.get_token_from_config()
        if not token:
            print("Migration aborted: No token found in configuration")
            return False

        # Step 2: Validate token
        print("\n[Step 2/4] Validating token format...")
        is_valid, error_msg = self.validate_token(token)
        if not is_valid:
            print(f"Migration aborted: Invalid token - {error_msg}")
            return False
        print("Token validation passed")

        # Get nickname for keyring storage
        with open(self.mcp_config_path, "r") as f:
            config = json.load(f)
        nickname = (
            config.get("mcpServers", {})
            .get("agent-comm", {})
            .get("env", {})
            .get("AGENT_NICKNAME", "default")
        )

        # Step 3: Store in keyring
        print("\n[Step 3/4] Storing token in OS keychain...")
        if not KEYRING_AVAILABLE:
            print("Warning: keyring not available")
            print("Please install: pip install keyring")
            print("\nAlternative: Set AGENT_TOKEN as environment variable")
            print(f"export AGENT_TOKEN='{token}'")
            return False

        if not dry_run:
            stored = self.store_token_in_keyring(nickname, token)
            if not stored:
                print("Migration aborted: Failed to store token in keychain")
                return False
        else:
            print(f"[DRY RUN] Would store token for: {nickname}")

        # Step 4: Remove from config
        print("\n[Step 4/4] Removing token from configuration...")
        removed = self.remove_token_from_config(dry_run=dry_run)
        if not removed:
            print("Warning: Failed to remove token from config")

        print("\n" + "=" * 60)
        if dry_run:
            print("[DRY RUN] Migration simulation complete")
        else:
            print("Migration complete!")
            print(f"\nNext steps:")
            print(f"1. Verify .mcp.json does not contain AGENT_TOKEN")
            print(f"2. Set AGENT_TOKEN environment variable:")
            print(
                f"   export AGENT_TOKEN='$(python -c \"import keyring; print(keyring.get_password('agent-comm-mcp', '{nickname}'))\")'"
            )
            print(f"3. Restart MCP server")
        print("=" * 60)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate AGENT_TOKEN from .mcp.json to OS keychain"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Only validate token, do not migrate"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate migration without making changes"
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to .mcp.json configuration file"
    )

    args = parser.parse_args()

    migrator = TokenMigrator(mcp_config_path=args.config)

    if args.validate:
        print("Validating token...")
        token = migrator.get_token_from_config()
        if token:
            is_valid, error_msg = migrator.validate_token(token)
            if is_valid:
                print("Token is valid")
                sys.exit(0)
            else:
                print(f"Token validation failed: {error_msg}")
                sys.exit(1)
        else:
            print("No token found to validate")
            sys.exit(1)
    else:
        success = migrator.migrate(dry_run=args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
