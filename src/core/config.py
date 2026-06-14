import platform
from pathlib import Path

import yaml


def load_config():
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config):
    with open(
        "config/settings.yaml",
        "w",
        encoding="utf-8",
    ) as f:
        yaml.safe_dump(
            config,
            f,
            allow_unicode=True,
            sort_keys=False,
        )


def get_platform():
    system = platform.system()
    if system == "Windows":
        return "windows"

    if system == "Linux":
        return "linux"

    raise RuntimeError(f"Nicht unterstütztes System: {system}")
