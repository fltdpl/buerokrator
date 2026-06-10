from pathlib import Path
import yaml
import platform


def load_config():
    with open(
        "config/settings.yaml",
        "r",
        encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)
    

def get_platform():

    system = platform.system()

    if system == "Windows":
        return "windows"

    if system == "Linux":
        return "linux"

    raise RuntimeError(
        f"Nicht unterstütztes System: {system}"
    )
