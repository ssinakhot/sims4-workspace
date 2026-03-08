# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sims 4 Workspace is a Python-based development environment for creating The Sims 4 mods. It handles decompilation of the game's Python bytecode, compilation/packaging of mod scripts into `.ts4script` format, and provides a dev mode with live file watching for hot reloading during development. It also includes data-mining tools for parsing Sims 4 `.package` files and extracting tuning XML.

**Python 3.7 only.** The Sims 4 engine embeds Python 3.7, so all code in this project must be compatible with Python 3.7. This means:
- No `list[X]`, `dict[X, Y]`, or `tuple[X]` in type hints — use `typing.List`, `typing.Dict`, `typing.Tuple`, etc.
- No walrus operator (`:=`), no `dataclasses.field(kw_only=...)`, no positional-only params (`/`).
- No `importlib.resources` features added after 3.7.

## Key Commands

All scripts are run from the project root with `python <script>`.

- **`python compile.py`** — Compile `src/` into a `.ts4script` package, copy to `build/` and the game's Mods folder. Also runs sync_packages and bundle_build automatically. Exits dev mode if active.
- **`python decompile.py --game`** — Decompile the game's Python scripts (multi-threaded, uses multiple decompiler fallbacks). Output goes to `decompile/output/python/`.
- **`python decompile.py --folder`** — Decompile zips placed in `decompile/input/`.
- **`python devmode.py`** — Start dev mode: watches `src/` for changes and auto-copies to the game's Mods folder. Runs until Ctrl+C. No compilation needed in this mode; use the in-game cheat `devmode.reload [path.to.module]` to reload live.
- **`python cleanup.py`** — Remove all build artifacts, mod installations, and debug mods.
- **`python sync_packages.py`** — Copy `.package` files from `assets/` to the mod folder.
- **`python bundle_build.py`** — Zip build artifacts for distribution.
- **`python debug_setup.py`** / **`python debug_teardown.py`** — Install/remove PyCharm Pro debugging support.
- **`python datamine.py extract <path>`** — Extract tuning XML from a `.package` file.
- **`python datamine.py info <path>`** — Show resource type summary for a `.package` file.
- **`pytest`** or **`pytest -v`** — Run the test suite.

## Configuration

Copy `settings.py.example` to `settings.py` (gitignored) before first use. Key settings:
- `creator_name` — Used as prefix for mod folder names (`CreatorName_ProjectName`)
- `mods_folder` — Path to The Sims 4 Mods directory
- `game_folder` — Path to installed game (needed for decompilation)
- `num_threads` — Decompilation thread count (default: 10)
- `devmode_parity` — When True, compilation mirrors dev mode structure so behavior matches

## Architecture

### Directory Layout

- `src/` — Mod source code (user writes code here)
- `build/` — Compiled `.ts4script` output (generated)
- `assets/` — `.package` files to include with the mod
- `util/` — Core library modules used by the top-level scripts
- `util/datamining/` — Package for parsing `.package` files and tuning XML
- `game_mods/` — In-game mod scripts loaded by the Sims 4 engine (devmode_cmd.py, debug_cmd.py)
- `tests/` — pytest-based test suite
- `decompile/input/` — Drop zips here for `decompile.py --folder`
- `decompile/output/python/` — Decompiled game code (base, core, generated, simulation); used for IDE autocomplete
- `pycdc/`, `unpyc37/` — Git submodules for decompiler tools

### Script Pattern

All root-level scripts follow the same pattern: import settings and util functions, define a `main()` function, and use an `if __name__ == "__main__":` guard. This makes them safe to import and testable.

### Compilation Flow

1. `compile.py` calls `util/compile.py:compile_src()` which uses `PyZipFile` to compile `.py` → `.pyc` and package into a `.ts4script` (zip) archive
2. Then calls `util/sync_packages.py:sync_packages()` and `util/bundle_build.py:bundle_build()`
3. The archive is placed in `build/` and copied to `Mods/CreatorName_ProjectName/`
4. When `devmode_parity` is on, the zip structure mirrors how files appear in dev mode's `Scripts/` folder

### Dev Mode (Watcher)

`devmode.py` → `util/watcher.py:watcher_create()` — copies `src/` to `Mods/CreatorName_ProjectName/Scripts/`, then polls for file changes every second on a daemon thread, copying modified files in real time. Running `compile.py` exits dev mode by removing the `Scripts/` folder.

### Decompilation

`util/decompile.py` runs a multi-threaded worker pool that tries decompilers in sequence: unpyc3 → decompyle3 → pycdc → uncompyle6. Each file gets `decompiler_timeout` seconds per attempt. Dependencies are installed into an auto-created venv via `util/venv.py`.

### Data Mining

`util/datamining/package_reader.py` parses DBPF v2.0 `.package` files (96-byte header, resource index with type/group/instance keys). `util/datamining/tuning_parser.py` parses the extracted tuning XML into structured `TuningFile` objects. Key resource type: `0x03B33DDF` = Tuning XML.

### Mod Naming Convention

Mods are always named `{creator_name}_{project_name}` where `project_name` defaults to the repository folder name.

## Testing

Tests live in `tests/` and use pytest. Run with `pytest` or `pytest -v` from the project root. The `conftest.py` provides a `mock_settings` fixture that creates temporary directories, so tests don't need a real `settings.py`.

## Licensing

Files originating from the upstream project (by June Hanabi / junebug12851) carry an Apache 2.0 license header — retain those headers on any file that contains or derives from that code. New files written for this fork do not need the Apache header.

## Dev Container

The project supports containerized development via `.devcontainer/`. The container mounts the game files and Mods folder from the host. `.devcontainer/post-create.sh` initializes git submodules and compiles pycdc from source. `.devcontainer/wsl-setup.sh` configures USERPROFILE for WSL environments. VSCode is configured with Pylance and autocomplete paths pointing to decompiled game code.
