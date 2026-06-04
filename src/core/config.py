import yaml


def load_config():
    with open(
        "config/settings.yaml",
        "r",
        encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)
    
import yaml
