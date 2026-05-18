import os
import tomllib

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_MODULE_DIR, "config", "controller_config.toml")


def load_config() -> dict:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


DEFAULTS = load_config()
