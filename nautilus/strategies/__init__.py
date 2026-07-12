import importlib
import pkgutil
from pathlib import Path

from nautilus_trader.trading.strategy import Strategy


def discover_strategies() -> list[dict]:
    strategies = []
    package_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f".{module_info.name}", __package__)
        except Exception as e:
            print(f"[strategies] Failed to import {module_info.name}: {e}")
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, "config_schema"):
                try:
                    schema = attr.config_schema()
                    if isinstance(schema, dict) and "name" in schema:
                        strategies.append(schema)
                except Exception as e:
                    print(f"[strategies] config_schema error on {attr_name}: {e}")
    print(f"[strategies] Discovered: {[s['name'] for s in strategies]}")
    return strategies


def get_strategy_cls(name: str) -> tuple[type, type]:
    package_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f".{module_info.name}", __package__)
        config_cls = None
        strategy_cls = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, "config_schema"):
                schema = attr.config_schema()
                if schema.get("name") == name:
                    config_cls = attr
            if isinstance(attr, type) and issubclass(attr, Strategy) and attr is not Strategy:
                strategy_cls = attr
        if config_cls is not None and strategy_cls is not None:
            return config_cls, strategy_cls
        if config_cls is not None:
            raise ValueError(
                f"Strategy '{name}': found config class but no Strategy subclass in module"
            )
    raise ValueError(f"Strategy '{name}' not found")
