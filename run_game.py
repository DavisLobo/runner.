import os
import subprocess
import sys
import venv
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent
VENV_DIR = GAME_DIR / ".venv"

if os.name == "nt":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"


def main():
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)

    try:
        subprocess.run(
            [str(VENV_PYTHON), "-c", "import pygame"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("Installing pygame...")
        subprocess.check_call([
            str(VENV_PYTHON),
            "-m",
            "pip",
            "install",
            "pygame",
        ])

    print("Starting game...")
    os.chdir(GAME_DIR)

    if os.name == "nt":
        subprocess.call([str(VENV_PYTHON), "main.py"])
    else:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), "main.py"])


if __name__ == "__main__":
    main()