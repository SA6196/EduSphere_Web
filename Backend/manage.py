#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edusphere.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists() and sys.executable.lower() != str(venv_python).lower():
            import subprocess
            res = subprocess.run([str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:])
            sys.exit(res.returncode)
        raise ImportError(
            "Django is not installed. Activate the virtual environment and "
            "run: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
