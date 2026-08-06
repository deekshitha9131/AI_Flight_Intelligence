"""Task discovery.

Celery's built-in `autodiscover_tasks()` only imports a single submodule
per package by default (named `tasks` — e.g. `app.workers.sync_tasks.tasks`),
which fits a project with exactly one task file per app. This project's
queue-packages (`sync_tasks/`, `classification_tasks/`, etc.) are
expected to hold multiple task files over time — Gmail sync, contact
aggregation, and thread-memory refresh might all eventually live under
`sync_tasks/` as separate modules, for instance. Celery's default
discovery would silently miss every file except one literally named
`tasks.py`.

`discover_tasks` instead imports every non-package submodule of each
listed package. A new task file dropped into `sync_tasks/` is
registered automatically the next time a worker process starts — no
edit to app/core/celery_app.py required, which is the actual point of
"discovery" as opposed to a manual import list.
"""

import importlib
import pkgutil

import structlog

logger = structlog.get_logger(__name__)


def discover_tasks(package_names: list[str]) -> None:
    """Import every submodule of each given package, registering any
    `@celery_app.task`-decorated functions found inside as a side effect
    of the import.
    """
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
