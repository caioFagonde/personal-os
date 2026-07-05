"""Root pytest conftest.

Service directories use hyphenated names (services/connector-service) which are
not importable as Python packages. Root-level contract tests import them as
underscored packages (services.connector_service.app.providers). This shim
registers an import alias for every service directory so those imports resolve
without duplicating code or adding symlinks (which break on Windows checkouts).
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICES_DIR = ROOT / "services"


def _ensure_namespace(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = []  # mark as package
        sys.modules[name] = module
    return module


def _alias_package(alias: str, directory: Path) -> None:
    """Register `alias` (dotted) as a package rooted at `directory`."""
    if alias in sys.modules or not directory.is_dir():
        return
    init = directory / "__init__.py"
    if init.exists():
        spec = importlib.util.spec_from_file_location(
            alias, init, submodule_search_locations=[str(directory)]
        )
    else:
        spec = importlib.util.spec_from_loader(alias, loader=None, is_package=True)
        if spec is not None:
            spec.submodule_search_locations = [str(directory)]  # type: ignore[misc]
    if spec is None:
        return
    module = importlib.util.module_from_spec(spec)
    module.__path__ = [str(directory)]
    sys.modules[alias] = module
    if spec.loader is not None:
        spec.loader.exec_module(module)


_services_pkg = _ensure_namespace("services")
if SERVICES_DIR.is_dir():
    for service_dir in sorted(SERVICES_DIR.iterdir()):
        if not service_dir.is_dir():
            continue
        alias = f"services.{service_dir.name.replace('-', '_')}"
        _alias_package(alias, service_dir)
        _alias_package(f"{alias}.app", service_dir / "app")
        if str(service_dir) not in _services_pkg.__path__:
            _services_pkg.__path__.append(str(service_dir))
