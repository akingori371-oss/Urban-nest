#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


# This launcher lives in plots/plots while the Django project package (config)
# is its sibling in plots/. Keep it runnable from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Run administrative tasks."""
    test_command = sys.argv[1:2] == ["test"]
    explicit_settings = any(
        argument == "--settings" or argument.startswith("--settings=")
        for argument in sys.argv[2:]
    )
    if test_command and not explicit_settings:
        # Never route the default test command to the configured development DB.
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

