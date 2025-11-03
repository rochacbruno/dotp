"""Configuration management for DOTP."""

import os
import tomllib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from xdg_base_dirs import xdg_config_home


@dataclass
class Config:
    """Application configuration."""

    vault_path: Optional[Path] = None
    close_on_copy: bool = False
    clipboard_command: str = "wl-copy"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file.

        Args:
            config_path: Path to config file, defaults to XDG_CONFIG_HOME/dotp/config.toml

        Returns:
            Config instance with loaded settings
        """
        if config_path is None:
            config_path = xdg_config_home() / "dotp" / "config.toml"

        config = cls()

        if config_path.exists():
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            if "vault_path" in data:
                config.vault_path = Path(data["vault_path"])
            if "close_on_copy" in data:
                config.close_on_copy = data["close_on_copy"]
            if "clipboard_command" in data:
                config.clipboard_command = data["clipboard_command"]

        return config


def get_default_vault_path(custom_path: Optional[Path] = None) -> Path:
    """Get the default vault path based on config and arguments.

    Lookup order:
    1. Custom path argument
    2. DOTP_VAULT environment variable
    3. Config file vault_path
    4. Local directory .vault.dotp
    5. XDG_CONFIG_HOME/dotp/.vault.dotp

    Args:
        custom_path: Optional custom vault path

    Returns:
        Path to use for the vault
    """
    if custom_path:
        return custom_path

    # Check DOTP_VAULT environment variable
    env_vault = os.environ.get("DOTP_VAULT")
    if env_vault:
        return Path(env_vault)

    config = Config.load()
    if config.vault_path:
        return config.vault_path

    local_vault = Path(".vault.dotp")
    if local_vault.exists():
        return local_vault

    return xdg_config_home() / "dotp" / ".vault.dotp"
