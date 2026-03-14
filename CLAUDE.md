# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**See `SPEC.md` for the authoritative specification** — architecture, invariants, data formats, and design decisions.

## Project Overview

Sims 4 Workspace is a Python-based development environment for creating The Sims 4 mods. It handles compilation, decompilation, dev mode with live file watching, and data mining of game files. The `extraction/` directory is a separate git repo for game data extraction.

## Constraints

- **Python 3.7 only** — use `typing.List` not `list[X]`, no walrus operator (`:=`), no positional-only params (`/`)
- **Spec-driven development** — update SPEC.md first, then write tests, then write code (SPEC.md Section 2.1)
- **TDD Red-Green-Refactor** — write a failing test, make it pass, clean up (SPEC.md Section 2.1)
- **Code review before push** — run `pytest`, review `git diff`, then push (SPEC.md Section 2.2)

## Key Commands

All scripts are run from the project root with `python <script>`.

- **`python compile.py`** — Compile `src/` into a `.ts4script` package
- **`python decompile.py --game`** — Decompile the game's Python scripts
- **`python decompile.py --folder`** — Decompile zips placed in `decompile/input/`
- **`python devmode.py`** — Start dev mode with live file watching
- **`python cleanup.py`** — Remove all build artifacts and mod installations
- **`python datamine.py extract <path>`** — Extract tuning XML from a `.package` file
- **`python datamine.py info <path>`** — Show resource type summary for a `.package` file
- **`pytest`** or **`pytest -v`** — Run the test suite

## Configuration

Copy `settings.py.example` to `settings.py` (gitignored) before first use. Key settings:
- `creator_name` — Used as prefix for mod folder names (`CreatorName_ProjectName`)
- `mods_folder` — Path to The Sims 4 Mods directory
- `game_folder` — Path to installed game (needed for decompilation)
- `num_threads` — Decompilation thread count (default: 10)
- `devmode_parity` — When True, compilation mirrors dev mode structure so behavior matches

## Testing

Tests live in `tests/` and use pytest. The `conftest.py` provides a `mock_settings` fixture that creates temporary directories, so tests don't need a real `settings.py`.

## Licensing

Files originating from the upstream project (by June Hanabi / junebug12851) carry an Apache 2.0 license header — retain those headers on any file that contains or derives from that code. New files written for this fork do not need the Apache header.

## Dev Container

The project supports containerized development via `.devcontainer/`. The container mounts the game files and Mods folder from the host. `.devcontainer/post-create.sh` initializes git submodules and compiles pycdc from source. `.devcontainer/wsl-setup.sh` configures USERPROFILE for WSL environments.
