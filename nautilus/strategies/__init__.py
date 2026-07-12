import importlib
import pkgutil
from pathlib import Path


def discover_strategies() -> list[dict]:
    strategies = []
    package_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f".{module_info.name}", __package__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, "config_schema"):
                schema = attr.config_schema()
                if isinstance(schema, dict) and "name" in schema:
                    strategies.append(schema)
    return strategies
