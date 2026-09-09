# RUNNER.

A small retro platformer built with Python and Pygame.

## Requirements

- Python 3.8 or newer
- Internet connection on the first launch, to install Pygame
- Windows or Linux

Python's standard libraries are used for all other imports.

## Installation and Running

Download or clone the project, then run the platform-specific launcher from the game folder.

### Windows

Double-click:

```text
run_game.bat
```

Or run it from Command Prompt:

```bat
py run_game.py
```

### Linux

Make the launcher executable once:

```bash
chmod +x run_game.sh
```

Then run:

```bash
./run_game.sh
```

Alternatively:

```bash
python3 run_game.py
```

## Automatic Setup

`run_game.py` automatically:

1. Detects Windows or Linux.
2. Creates a `.venv` folder beside the game files.
3. Installs Pygame inside that virtual environment.
4. Runs `main.py` using the same virtual environment every time.

The project structure will look like this after the first launch:

```text
runner/
├── main.py
├── run_game.py
├── run_game.bat
├── run_game.sh
└── .venv/
```

The `.venv` folder should not be deleted while using the game. It can be recreated automatically if removed.

## Controls

### Main Menu

- `W` / `Up Arrow`: Move up
- `S` / `Down Arrow`: Move down
- `Enter` / `Space`: Select
- `Escape`: Go back

### Gameplay

- `A` / `Left Arrow`: Move left
- `D` / `Right Arrow`: Move right
- `Space` / `Up Arrow`: Jump
- `Left Shift`: Run
- `R`: Restart
- `Escape`: Return to the main menu

Controls can be changed in the Options menu.

## Saved Data

The game automatically creates `data.json` in the game folder to store the best completion time.

## Troubleshooting

If Python is not installed:

- Windows: install Python from [python.org](https://www.python.org/downloads/)
- Linux:

```bash
sudo apt install python3 python3-venv
```

If Pygame installation fails, verify that Python and internet access are available, then run the launcher again.