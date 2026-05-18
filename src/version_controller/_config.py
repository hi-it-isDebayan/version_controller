import os

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_MODULE_DIR, "config", "controller_config.toml")


def load_config() -> dict:
    if tomllib is None or not os.path.isfile(_CONFIG_PATH):
        return {}
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


DEFAULTS = load_config()
