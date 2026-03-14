# Sims 4 Workspace — Specification

This is the authoritative source of truth for system behavior. Code must conform to this spec. Tests must verify spec invariants. When the spec and code disagree, update one or the other — never leave them out of sync.

## 1. Purpose

Provide a complete development environment for creating The Sims 4 mods: compile source into loadable packages, watch for changes during live development, decompile game scripts for reference, and parse game data files for analysis and extraction.

## 2. Development Methodology

### 2.1 Spec-Driven Development

The spec defines what the system does. Development flows from spec to tests to code:

1. **Spec** — Define or update the behavior in this document first
2. **Red** — Write a failing test that asserts the spec's invariants
3. **Green** — Write the minimum code to make the test pass
4. **Refactor** — Clean up while keeping tests green
5. **Verify** — Run `pytest` — all tests must pass before code is complete

When adding a new feature or fixing a bug: update the spec first, then follow Red-Green-Refactor.

### 2.2 Code Review

All changes must be reviewed before pushing:

1. Run `pytest` — all tests must pass
2. Review `git diff` for correctness, style, and unintended changes
3. Only push after confirming changes are correct

## 3. Goals

1. **One-command workflows** — Each development task (compile, dev mode, decompile, cleanup) is a single script invocation with no configuration beyond initial setup.
2. **Dev-prod parity** — Code behavior in dev mode (live file watching) must match compiled mode. The `devmode_parity` setting ensures identical module resolution.
3. **Resilient decompilation** — Multiple decompiler fallbacks (unpyc3 → decompyle3 → pycdc → uncompyle6) maximize successful decompilation. No single decompiler handles all files.
4. **Reusable datamining library** — `util/datamining/` is a general-purpose library for reading `.package` files. It has no knowledge of specific content types and can be used by any consumer.
5. **No real game files in tests** — All tests run with synthetic data. The `mock_settings` fixture provides temporary directories.

## 4. Non-Goals

- Runtime mod framework (this is a build tool, not a mod API)
- GUI or web interface
- Supporting Python versions other than 3.7
- Extracting specific game content types (that is `extraction/`'s job)

## 5. Constraints

- **Python 3.7 only** — The Sims 4 engine embeds Python 3.7. All code must be compatible.
  - No `list[X]`, `dict[X, Y]`, `tuple[X]` type hints — use `typing.List`, `typing.Dict`, `typing.Tuple`
  - No walrus operator (`:=`), no `dataclasses.field(kw_only=...)`, no positional-only params (`/`)
  - No `importlib.resources` features added after 3.7
- **Upstream compatibility** — Files from the upstream project (junebug12851) carry Apache 2.0 headers. Retain them.

---

## 6. Compilation

### 11.1 Behavior

`compile.py` produces a `.ts4script` file (a zip of `.pyc` files) that the Sims 4 engine loads at startup.

**Invariants:**
- Output is always `build/{creator}_{project}.ts4script`
- A copy is placed in `{mods_folder}/{creator}_{project}/`
- Old `.ts4script` files in `build/` are removed before writing
- `.package` files from `assets/` are synced to the mod folder
- A distribution zip is created in `build/`
- If dev mode is active (Scripts/ folder exists), compilation removes it

### 11.2 Compilation Modes

| Mode | Setting | Behavior |
|------|---------|----------|
| Slim (default) | `devmode_parity=False` | Compiles `.py` → `.pyc` at zip root. Standard Python import resolution. |
| Parity | `devmode_parity=True` | Mirrors the `Scripts/` folder structure inside the zip so module paths match dev mode exactly. |
| Full | *(not exposed via settings)* | Includes non-Python files alongside `.pyc` files. |

### 9.3 Asset Sync

`sync_packages()` copies top-level `.package` files from `assets/` to the mod folder. `.gitkeep` files are skipped. Only top-level files are copied (no recursion into subdirectories).

### 6.4 Bundle

`bundle_build()` creates `{creator}_{project}.zip` in `build/` containing all build artifacts. Replaces any existing zip.

---

## 7. Dev Mode

### 11.1 Behavior

`devmode.py` enables live development by copying source files to the game's Mods folder and watching for changes.

**Invariants:**
- Source files are copied to `{mods_folder}/{creator}_{project}/Scripts/`
- A daemon thread polls for changes every 1 second
- Modified files are copied immediately on detection
- The devmode command mod is installed (provides `devmode.reload` cheat)
- `.package` assets are synced
- Process runs until Ctrl+C

### 11.2 In-Game Reload

The `devmode.reload` cheat command (CommandType.Live) is registered by `game_mods/devmode_cmd.py`:

| Command | Behavior |
|---------|----------|
| `devmode.reload` | Reloads all `.py` files in `Scripts/` |
| `devmode.reload path.to.module` | Reloads a specific module file or folder |

Uses `sims4.reload.reload_file()` for hot reloading.

### 9.3 Dev Mode ↔ Compile Interaction

Running `compile.py` while dev mode is active removes the `Scripts/` folder, effectively exiting dev mode. This prevents conflicts between compiled and live-loaded code.

---

## 8. Decompilation

### 11.1 Behavior

`decompile.py` decompiles the game's compiled Python bytecode (`.pyc`) into readable source.

**Modes:**
- `--game` — Decompiles game scripts from `gameplay_folder_data` and `gameplay_folder_game`
- `--folder` — Decompiles zips placed in `decompile/input/`

**Output:** `decompile/output/python/`

### 11.2 Decompiler Fallback Chain

Each `.pyc` file is attempted with decompilers in sequence. The first successful result is kept:

1. **unpyc3** — Fast, handles most standard files
2. **decompyle3** — Good coverage, installed via venv
3. **pycdc** — C++ decompiler (compiled from submodule), handles some edge cases
4. **uncompyle6** — Broadest compatibility, installed via venv

Each decompiler gets `decompiler_timeout` seconds per file (default: 30s).

### 9.3 Failure Handling

- If all decompilers fail, a stub file is written with a comment indicating failure
- Runaway indentation (>200 levels) is detected and the decompiler process is killed
- Progress is printed as `.` (success) or `X` (failure), wrapping at 80 columns
- Per-zip and aggregate statistics are printed at completion

### 9.4 Environment Setup

`decompile_pre()` creates a virtual environment and installs decompiler packages (`decompyle3`, `uncompyle6`). The venv is created once and reused.

---

## 9. Data Mining Library (`util/datamining/`)

A general-purpose library for reading The Sims 4 `.package` files. Has no knowledge of specific content types — it provides the building blocks that consumers (like `extraction/`) use.

### 11.1 Package Reading

**DBPF v2.0 format:**
- 96-byte header with magic (`DBPF`), version, index entry count, index offset/size
- Resource index with per-entry type/group/instance keys, offset, sizes, compression flag
- Index flags can mark type/group/instance fields as constant across all entries

**Invariants:**
- `PackageReader.read()` raises `ValueError` if magic is not `DBPF` or file is too small
- `extract_resource()` automatically decompresses: RefPack first, then zlib, then zlib with 4-byte header skip
- `extract_by_type()` filters entries by type ID
- `is_compressed` is True only when the compressed flag is set AND file_size differs from mem_size

### 11.2 CombinedTuning

CombinedTuning (resource type `0x62E94D38`) contains all tuning for a game package in one resource.

**Two formats:**
- **XML** (base game full build) — Standard XML with `<g>` shared reference table and `<r>` references
- **Binary DATA** (all other packages) — 7-table binary encoding, detected by `DATA` magic

**Invariants:**
- `is_binary_combined_tuning(data)` correctly detects binary vs XML format
- `decode_combined_tuning(data)` produces XML equivalent to the XML format
- `CombinedTuningParser` resolves all `<r>` references transparently
- `TuningElement` methods (`get_value`, `get_list`, `get_bool`, etc.) work identically regardless of source format
- `split_combined_tuning(data)` accepts either format, resolves references, and returns self-contained XML entries

### 9.3 String Tables

STBL binary format (resource type `0x220557DA`):
- 21-byte header: magic `STBL`, version (uint16), compressed flag (1 byte), num_entries (uint64), reserved (2 bytes), string data length (uint32)
- Entries: key_hash (uint32), flags (1 byte), string_length (uint16), UTF-8 data

**Invariants:**
- `StringTableReader.parse()` raises `ValueError` for invalid magic or truncated data
- `StringTableReader.merge()` combines multiple tables; later tables override earlier entries with the same key
- `StringTable.get()` returns None for missing keys (does not raise)

### 9.4 Image Decoding

EA uses custom "DST" DDS variants with shuffled block data:

| Format | Block Size | Shuffling |
|--------|-----------|-----------|
| DST1 | 8 bytes | Split into [all endpoints][all indices] |
| DST3 | 16 bytes | Same layout as DST5 |
| DST5 | 16 bytes | Regions reordered: [alpha_ep, color_ep, alpha_idx, color_idx] |

**Invariants:**
- `decode_image()` returns data unchanged for non-DDS input or standard DXT formats
- DST FourCC is replaced with corresponding DXT FourCC in the header
- Block data is unshuffled to standard DXT interleaved layout
- `decode_image_to_png()` produces valid PNG bytes via Pillow

### 9.5 RefPack Decompression

EA's proprietary LZ compression identified by `0x10FB` or `0x50FB` magic.

**Invariants:**
- `is_refpack()` detects magic at offset 0 or offset 4 (compressed size prefix variant)
- `decompress()` raises `ValueError` for invalid magic or truncated data
- Output is truncated to the declared decompressed size
- All control code types are handled: 2-byte (short copy), 3-byte (medium copy), 4-byte (long copy), 1-byte (literals only), stop codes (0xFC-0xFF)

### 9.6 Package Discovery

Discovers `.package` files in the game folder organized by category.

**Invariants:**
- Full builds are always ordered before delta builds in returned lists (enables deduplication by processing in order)
- Simulation packages include base game + all pack directories (EP, GP, SP, FP) + Delta directories
- String packages include all `Strings_ENG_US.package` files across all pack directories
- Client packages include `Client*Build*.package` from both pack directories and Delta directories

### 9.7 Resource Type Resolution

`resolve_type_filter(name)` accepts:
- Hex IDs with or without `0x` prefix (e.g., `"0x2F7D0004"`, `"2F7D0004"`)
- Human-readable labels (e.g., `"DDS"`, `"STBL"`, `"CombinedTuning"`)
- Case-insensitive, strips underscores/hyphens/spaces

Raises `ValueError` for unknown labels.

---

## 10. Debugging Support

### 11.1 PyCharm Pro Debug Setup

`debug_setup.py` installs remote debugging support:

1. Installs `pydevd-pycharm` egg via venv
2. Packages the debug command mod as `.ts4script`
3. Packages the debug egg + ctypes as `.ts4script`

The `pycharm.debug` cheat connects to localhost:5678.

### 11.2 Teardown

`debug_teardown.py` removes the entire debug mod folder from the Mods directory.

---

## 11. Configuration

### 11.1 Settings

Copy `settings.py.example` to `settings.py` (gitignored) before first use.

**User-configurable:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `creator_name` | str | — | Prefix for mod folder names |
| `mods_folder` | str | — | Path to Sims 4 Mods directory |
| `game_folder` | str | — | Path to game installation |
| `num_threads` | int | 10 | Decompilation thread count |
| `decompiler_timeout` | float | 30.0 | Per-file decompiler timeout (seconds) |
| `devmode_parity` | bool | True | Mirror dev mode folder structure in compilation |

**Derived (do not modify):**
- `project_name` — Parent folder name of `settings.py`
- `src_path` — `{root}/src`
- `build_path` — `{root}/build`
- `assets_path` — `{root}/assets`
- `gameplay_folder_data` — `{game_folder}/Data/Simulation/Gameplay`
- `gameplay_folder_game` — `{game_folder}/Game/Bin/Python` (Windows) or `{game_folder}/Python` (Mac/Linux)

### 11.2 Mod Naming

All mods are placed in `{mods_folder}/{creator_name}_{project_name}/`. The `project_name` defaults to the repository folder name.

---

## 12. Cleanup

`cleanup.py` removes all workspace artifacts:

1. Removes debug mod folder from Mods
2. Removes `Scripts/` folder from Mods (exits dev mode)
3. Deletes `build/` directory

**Invariant:** After cleanup, the Mods folder contains no trace of the workspace project.

---

## 13. Script Pattern

All root-level scripts follow the same structure:

```python
import settings
from util.some_module import some_function

def main():
    some_function(settings.param1, settings.param2)

if __name__ == "__main__":
    main()
```

**Invariants:**
- Every script is safe to import without side effects (guarded by `__name__` check)
- Every script defines a `main()` function that can be called programmatically
- Settings are imported at module level; util functions do not import settings themselves

---

## 14. File Formats

### 14.1 `.ts4script`

A zip archive containing compiled `.pyc` files. The Sims 4 engine scans the Mods folder for `.ts4script` files at startup and loads them as Python packages.

### 14.2 `.package` (DBPF v2.0)

Binary container with 96-byte header and resource index. Resources identified by `(type_id, group, instance)` tuples. See section 9.1 for format details.

### 14.3 STBL (String Table)

Binary format for localized strings. See section 9.3 for format details.

### 14.4 RefPack

EA's LZ compression. See section 9.5 for format details.

### 14.5 DST (Shuffled DDS)

EA's DDS variant with rearranged block data. See section 9.4 for format details.

---

## 15. Error Handling

| Scenario | Behavior |
|----------|----------|
| `settings.py` missing | Import error at script startup (expected — user must create it) |
| Source directory empty | Compilation produces empty `.ts4script` (valid zip with no entries) |
| Invalid DBPF magic | `PackageReader.read()` raises `ValueError` |
| File too small for header | `PackageReader.read()` raises `ValueError` |
| Decompression failure | `extract_resource()` raises `ValueError` after trying RefPack and zlib |
| All decompilers fail | Stub file written with failure comment |
| Invalid STBL magic | `StringTableReader.parse()` raises `ValueError` |
| Invalid RefPack magic | `decompress()` raises `ValueError` |

