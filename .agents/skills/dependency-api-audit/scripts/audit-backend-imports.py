"""Import every backend package to catch missing or incompatible dependencies."""
from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path


PACKAGES = ["agent", "api", "config", "eval", "ingestion", "mcp_server", "retrieval", "store"]


def main() -> None:
    sys.path.insert(0, str(Path.cwd()))
    modules: set[str] = set()
    for package_name in PACKAGES:
        package = importlib.import_module(package_name)
        modules.add(package_name)
        if hasattr(package, "__path__"):
            modules.update(
                module.name
                for module in pkgutil.walk_packages(
                    package.__path__, package.__name__ + "."
                )
            )

    for module_name in sorted(modules):
        importlib.import_module(module_name)

    print(f"Imported {len(modules)} backend modules")


if __name__ == "__main__":
    main()
