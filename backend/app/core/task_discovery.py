import importlib
import pkgutil

import structlog

logger = structlog.get_logger(__name__)


def discover_tasks(package_names: list[str]) -> None:

    for package_name in package_names:
        package = importlib.import_module(package_name)

        if not hasattr(package, "__path__"):
            logger.warning(
                "task_discovery_skipped_non_package",
                package=package_name,
            )
            continue

        for _finder, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if is_pkg:
                continue
            full_module_name = f"{package_name}.{module_name}"
            importlib.import_module(full_module_name)
            logger.debug("task_discovery_imported_module", module=full_module_name)
