"""
SPIDER — Config Loader
Loads and provides access to settings.yaml with encryption support.
"""
import os
import yaml
from pathlib import Path
from loguru import logger

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "settings.yaml"


def load_config() -> dict:
    """Load configuration from settings.yaml."""
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve relative paths to absolute
    _resolve_paths(config, ROOT_DIR)
    return config


def save_config(config: dict) -> None:
    """Save updated config back to settings.yaml."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    logger.info("Config saved.")


def _resolve_paths(config: dict, root: Path) -> None:
    """Convert relative paths in config to absolute paths."""
    path_keys = {
        ("memory", "db_path"),
        ("resume", "default_path"),
        ("logging", "log_file"),
    }
    for section, key in path_keys:
        if section in config and key in config[section]:
            val = config[section][key]
            if val and not os.path.isabs(val):
                config[section][key] = str(root / val)


# Global config singleton
CONFIG = load_config()
