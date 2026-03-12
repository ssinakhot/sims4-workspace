# Sims 4 Workspace — Specification

This document describes the behavior of each component in the workspace. It covers the root-level scripts, the `util/` library, the `util/datamining/` package, and the in-game mod scripts. It does **not** cover `extraction/` (separate repo) or `decompile/` output.

## Configuration (`settings.py`)

Copy `settings.py.example` to `settings.py` before first use. The file is gitignored.

### User settings

| Setting | Type | Description |
|---------|------|-------------|
| `creator_name` | `str` | Prefix for mod folder names (`CreatorName_ProjectName`) |
| `mods_folder` | `str` | Path to The Sims 4 Mods directory |
| `game_folder` | `str` | Path to the installed game (needed for decompilation and datamining) |
| `num_threads` | `int` | Thread count for decompilation (default: 10) |
| `decompiler_timeout` | `float` | Per-file decompiler timeout in seconds (default: 30.0) |
| `devmode_parity` | `bool` | When True, compilation mirrors dev mode folder structure |
| `pycharm_pro_folder` | `str` | PyCharm Pro installation path (only for debug setup) |

### Derived settings

All other settings are computed from the above. Key derived paths:

| Setting | Value |
|---------|-------|
| `project_name` | Parent folder name of `settings.py` |
| `src_path` | `{root}/src` |
| `build_path` | `{root}/build` |
| `assets_path` | `{root}/assets` |
| `gameplay_folder_data` | `{game_folder}/Data/Simulation/Gameplay` |
| `gameplay_folder_game` | `{game_folder}/Game/Bin/Python` (Windows) or `{game_folder}/Python` (Mac/Linux) |

### Mod naming

Mods are always placed in `{mods_folder}/{creator_name}_{project_name}/`.

---

## Root-Level Scripts

All scripts follow the same pattern: import `settings`, call util functions in `main()`, and guard with `if __name__ == "__main__"`. This makes them safe to import and testable.

### `compile.py`

Compiles mod source into a distributable `.ts4script` package.

1. Calls `util.compile.compile_src()` — compiles `src/` → `.pyc` via `PyZipFile`, writes `.ts4script` to `build/` and copies to `Mods/{mod_name}/`
2. Calls `util.sync_packages.sync_packages()` — copies `.package` files from `assets/` to the mod folder
3. Calls `util.bundle_build.bundle_build()` — zips build artifacts for distribution

Running `compile.py` also exits dev mode by removing the `Scripts/` folder.

### `decompile.py`

Decompiles game Python bytecode using a multi-threaded worker pool.

**CLI arguments:**
- `--folder` — Decompile zips placed in `decompile/input/`
- `--game` — Decompile the game's Python scripts from `gameplay_folder_data` and `gameplay_folder_game`

**Behavior:**
1. Calls `multiprocessing.freeze_support()` for Windows compatibility
2. Calls `decompile_pre()` to set up the decompiler venv and install dependencies
3. Dispatches to `decompile_zips()` with appropriate source/destination paths
4. Prints decompilation statistics

Output goes to `decompile/output/python/`.

### `devmode.py`

Starts a file watcher for live development with hot reloading.

1. Removes old debug mods from the mod folder
2. Installs the devmode command mod (provides `devmode.reload` cheat)
3. Syncs `.package` files from `assets/`
4. Calls `util.watcher.watcher_create()` — copies `src/` to `Mods/{mod_name}/Scripts/`, then polls for file changes every second on a daemon thread
5. Runs until Ctrl+C

### `cleanup.py`

Removes all build artifacts, mod installations, and debug mods.

1. Calls `debug_teardown()` to remove debug setup
2. Calls `watcher_folder_remove()` to remove the mod folder from Mods
3. Calls `remove_dir()` to delete the build folder

### `sync_packages.py`

Standalone script to copy `.package` files from `assets/` to the mod folder.

### `bundle_build.py`

Standalone script to zip build artifacts into a distributable archive in `build/`.

### `debug_setup.py`

Installs PyCharm Pro remote debugging support.

1. Ensures `pydevd-pycharm` egg is installed via venv
2. Tears down any previous debug setup
3. Installs the debug command mod (provides `pycharm.debug` cheat)
4. Installs the debug egg for code injection

### `debug_teardown.py`

Removes all PyCharm Pro debugging files from the mod folder.

### `datamine.py`

Multi-command CLI tool for extracting and analyzing game `.package` files.

**Subcommands:**

#### `extract <package_path>`
Extracts tuning XML from a single `.package` file.
- `-o, --output` — Output directory for XML files (optional; prints to stdout if omitted)

#### `info <package_path>`
Shows a resource type summary for a `.package` file (counts by type ID with human-readable labels).

#### `extract-all <game_folder>`
Bulk extracts resources from all game packages.
- `-o, --output` (required) — Output directory
- `--types [LABEL|HEX|all]` — Filter resource types (default: tuning + strings + images)

**Default extraction (no `--types`):**
1. Discovers simulation packages (full + delta), deduplicates by instance ID (delta wins)
2. Splits CombinedTuning into individual XML files organized by class: `xml/{ClassName}/{name}.xml`
3. Discovers string packages, merges all STBL entries, writes `strings.json` (hex hash → text)
4. Discovers client packages, extracts PNG/DDS images to `images/{instance_hex}.png`

**`--types` filtering:**
- Accepts labels (`DDS`, `PNG`, `STBL`, `Tuning`, `CombinedTuning`) or hex IDs (`0x2F7D0004`)
- `all` extracts every resource type with smart handling for known types and raw extraction for unknown types
- Unknown hex types are extracted raw to `{TYPE_HEX}/{instance_hex}.bin`

---

## Utility Library (`util/`)

### `util/compile.py`

| Function | Description |
|----------|-------------|
| `compile_slim(src_dir, zf)` | Adds `.py` files to a `PyZipFile`, compiling to `.pyc`. When `devmode_parity` is on, mirrors the `Scripts/` folder structure. |
| `compile_full(src_dir, zf)` | Adds all files (`.py` compiled to `.pyc`, plus non-Python files) to the zip. |
| `compile_src(creator_name, src_dir, build_dir, mods_dir, mod_name)` | Creates the `.ts4script` archive in `build/` and copies it to the mod folder. Clears old builds first. |

### `util/sync_packages.py`

| Function | Description |
|----------|-------------|
| `remove_tl_packages(path)` | Removes all top-level `.package` files from a directory. Returns count removed. |
| `copy_tl_packages(src, dest, file_list_failed)` | Copies top-level `.package` files (excluding `.gitkeep`). Returns count copied. Failed files appended to `file_list_failed`. |
| `sync_packages(assets_path, mods_folder, build_path, creator_name, project_name)` | Removes old packages from mod folder and build, copies fresh ones from assets. |

### `util/bundle_build.py`

| Function | Description |
|----------|-------------|
| `bundle_build(build_path, creator_name, project_name)` | Creates `{creator}_{project}.zip` in `build/` containing all build artifacts. Replaces any existing zip. |

### `util/watcher.py`

| Function | Description |
|----------|-------------|
| `get_scripts_path(creator_name, mods_dir, mod_name)` | Returns the `Scripts/` path inside the mod folder. |
| `exec_cmd(cmd, args)` | Runs a shell command. Returns True on success. |
| `watcher_folder_exists(creator_name, mods_dir, mod_name)` | Checks if the Scripts folder exists. |
| `watcher_folder_remove(creator_name, mods_dir, mod_name)` | Removes the Scripts folder. Falls back to `rmdir` command if `shutil.rmtree` fails. |
| `watcher_create(creator_name, src_dir, mods_dir, mod_name)` | Copies `src/` to `Scripts/`, then spawns a daemon thread that polls for file changes every second and copies modified files. Runs until process exit. |

### `util/decompile.py`

| Function | Description |
|----------|-------------|
| `decompile_pre()` | Sets up a venv and installs decompiler packages (`decompyle3`, `uncompyle6`). |
| `decompile_zips(src_dirs, dst_dir)` | Extracts `.pyc` from zips in `src_dirs`, runs multi-threaded decompilation to `dst_dir`. |
| `decompile_worker(src_file, dest_path)` | Tries decompilers in order: unpyc3 → decompyle3 → pycdc → uncompyle6. Each gets `decompiler_timeout` seconds. Writes stub on total failure. |
| `streaming_decompile(cmd, args, dest_path)` | Runs a decompiler as subprocess, streams output to file. Detects runaway indentation (>200 levels) and kills the process. |
| `stdout_decompile(cmd, args, dest_path)` | Runs a decompiler, captures stdout, writes to file on success. |
| `print_progress(stats, total, success)` | Prints `.` or `X` progress indicator. |
| `print_summary(stats)` | Prints per-zip decompilation statistics. |
| `decompile_print_totals()` | Prints aggregate totals across all zips. |

### `util/debug.py`

| Function | Description |
|----------|-------------|
| `install_debug_mod(mod_src, mods_dir, mod_name, mod_folder_name)` | Packages a Python file as a `.ts4script` and installs it in the mod folder. |
| `debug_install_egg(egg_path, mods_dir, dest_name, mod_folder_name)` | Packages a PyCharm debug egg + ctypes as a `.ts4script`. |
| `remove_debug_mods(mods_dir, mod_folder_name)` | Removes all `.ts4script` files from the debug mod folder. |
| `debug_teardown(mods_dir, mod_folder_name)` | Removes the entire debug mod folder. |
| `debug_ensure_pycharm_debug_package_installed()` | Installs `pydevd-pycharm` via venv if not present. |

### `util/path.py`

| Function | Description |
|----------|-------------|
| `get_rel_path(path, common_base)` | Returns path relative to a base directory. |
| `get_file_stem(file)` | Returns filename without extension. |
| `replace_extension(file, new_ext)` | Replaces a file's extension. |
| `get_default_executable_extension()` | Returns `.exe` on Windows, empty string elsewhere. |
| `get_sys_path()` | Returns `sys.executable` absolute path. |
| `get_sys_folder()` | Returns the directory containing `sys.executable`. |
| `get_sys_scripts_folder()` | Returns the `bin/` or `Scripts/` folder for the Python installation. |
| `get_full_filepath(folder, base_name)` | Finds a file by base name, trying with platform extensions. |
| `ensure_path_created(path)` | Creates directory tree if it doesn't exist. |
| `remove_dir(path)` | Recursively removes a directory (no-op if missing). |
| `remove_file(path)` | Removes a file (no-op if missing). |

### `util/time.py`

| Function | Description |
|----------|-------------|
| `get_time()` | Returns current datetime. |
| `get_minutes(time_end, time_start)` | Returns elapsed minutes between two datetimes. |
| `get_hours(minutes)` | Returns whole hours from minutes. |
| `get_minutes_remain(minutes)` | Returns remaining minutes after removing whole hours. |
| `get_time_str(minutes)` | Formats minutes as `Hh Mm` string. |

### `util/exec.py`

| Function | Description |
|----------|-------------|
| `exec_cli(package, args, **kwargs)` | Runs a CLI tool as subprocess. Resolves the command by checking: direct file path → `python3` special case → console script in Scripts folder → `python -m` fallback. Returns `(success, result)`. |

### `util/venv.py`

| Function | Description |
|----------|-------------|
| `Venv(virtual_dir)` | Manages a virtual environment at the given path. |
| `.install_virtual_env()` | Creates the venv if it doesn't exist. |
| `.is_venv()` | Returns True if currently running inside this venv. |
| `.restart_under_venv()` | Re-launches the current script under the venv's Python. |
| `.install(package)` | Installs a pip package into the venv. |
| `.run()` | Orchestrator: creates venv, restarts under it if needed. |

### `util/injector.py`

| Function | Description |
|----------|-------------|
| `inject(target_function, new_function)` | Wraps `target_function` so that `new_function(target_function, *args, **kwargs)` is called instead. Preserves the original name. |
| `inject_to(target_object, target_function_name)` | Decorator that replaces a named method on an object with an injected version. |
| `is_injectable(target_function, new_function)` | Checks if `new_function` has a compatible signature (one extra arg for the original). |

### `util/type_hints.py`

Generates Python type stubs from decompiled game code and protobuf definitions. Upstream legacy code with complex protobuf reflection. Requires decompiled game files and `protoc` binary.

### `util/process_module.py`

Shared multiprocessing state for decompilation workers: `stats`, `total_stats`, `failed_files`.

---

## Data Mining Library (`util/datamining/`)

### `package_reader.py` — DBPF v2.0 Reader

Parses Sims 4 `.package` files (96-byte header, resource index with type/group/instance keys).

| Class/Function | Description |
|----------------|-------------|
| `ResourceKey` | Identifies a resource by `(type_id, group, instance)`. Property `is_tuning` checks for tuning type. |
| `IndexEntry` | Index record with offset, file/mem sizes, compression flag. Property `is_compressed` checks flag and size mismatch. |
| `PackageReader` | Main reader. `read()` parses header and index. `extract_resource()` decompresses (RefPack or zlib). `extract_by_type()`, `extract_tuning_entries()`, `extract_combined_tuning_entries()`, `extract_string_table_entries()` filter by type. |

### `combined_tuning.py` — CombinedTuning Parser

Parses CombinedTuning XML with shared reference table resolution.

| Class/Function | Description |
|----------------|-------------|
| `CombinedTuningParser(xml)` | Parses XML, builds ref table from `<g>`. Iterable over `TuningElement`s. Methods: `by_class()`, `by_module()`, `by_tuning_type()`, `find_by_name()`, `find_by_instance_id()`. |
| `TuningElement` | Wrapper around an `<I>` element. Properties: `cls`, `name`, `instance_id`, `module`, `tuning_type`. Methods: `get_value()`, `get_enum()`, `get_bool()`, `get_list()`, `get_child_element()`, `to_dict()`. All `<r>` references are resolved transparently. |

### `binary_tuning.py` — Binary DATA Decoder

Decodes compiled binary CombinedTuning (EP/GP/SP/FP packs) into XML string.

| Function | Description |
|----------|-------------|
| `is_binary_combined_tuning(data)` | Returns True if data starts with `DATA` magic. |
| `decode_combined_tuning(data)` | Converts binary DATA format to CombinedTuning XML string. |
| `BinaryDecoder` | Low-level binary reader with typed read methods. |

### `tuning_splitter.py` — CombinedTuning Splitter

Splits a CombinedTuning resource into standalone XML entries.

| Function | Description |
|----------|-------------|
| `split_combined_tuning(data)` | Takes raw bytes (XML or binary DATA), resolves all `<r>` references, returns `List[SplitEntry]`. Each entry has `cls`, `name`, `instance_id`, `module`, `element_tag`, `xml`. |

### `tuning_parser.py` — Individual Tuning Parser

Parses standalone tuning XML (single `<I>` elements, not CombinedTuning).

| Class | Description |
|-------|-------------|
| `TuningFile` | Dataclass: `instance_id`, `tuning_type`, `name`, `cls`, `xml`, `references`. |
| `TuningParser` | Static methods: `parse(xml)` → `TuningFile`, `parse_multiple(xml_list)` → `List[TuningFile]` (skips invalid). |

### `string_table.py` — STBL Parser

Parses Sims 4 string table binary format.

| Class | Description |
|-------|-------------|
| `StringTable` | Dict-like container mapping `int` hash → `str`. Methods: `get()`, `__contains__()`, `__getitem__()`, `__len__()`. |
| `StringTableReader` | Static methods: `parse(data)` → `StringTable`, `merge(tables)` → `StringTable`. |

### `image_decoder.py` — Image Decoder

Decodes EA's shuffled DDS formats (DST1/DST3/DST5) to standard DDS, with optional PNG conversion.

| Function | Description |
|----------|-------------|
| `decode_image(data)` | Detects DDS magic and FourCC. Unshuffles DST→DXT block data. Returns standard DDS or passthrough for non-DDS. |
| `decode_image_to_png(data)` | Decodes image and converts to PNG bytes via Pillow. |

### `refpack.py` — RefPack Decompression

EA's proprietary LZ compression used in DBPF packages.

| Function | Description |
|----------|-------------|
| `is_refpack(data)` | Checks for `0x10FB` or `0x50FB` magic at offset 0 or 4. |
| `decompress(data)` | Decompresses RefPack data. Handles 3-byte and 4-byte size headers, all control code types (2/3/4/1-byte + stop codes). |

### `package_discovery.py` — Game Folder Scanner

Discovers `.package` files in the game folder, organized by category.

| Function | Description |
|----------|-------------|
| `discover_simulation_packages(game_folder)` | Returns `List[Tuple[str, str]]` of simulation packages (absolute path, relative path). Full builds ordered before deltas for deduplication. |
| `discover_string_packages(game_folder)` | Returns `List[str]` of all `Strings_ENG_US.package` paths. |
| `discover_client_packages(game_folder)` | Returns `List[Tuple[str, str]]` of client packages. Full before delta. |
| `discover_all_packages(game_folder)` | Returns every `.package` file in the game folder tree. |

### `resource_types.py` — Resource Type Constants

| Item | Description |
|------|-------------|
| `TUNING_TYPE_ID` | `0x03B33DDF` |
| `COMBINED_TUNING_TYPE_ID` | `0x62E94D38` |
| `STRING_TABLE_TYPE_ID` | `0x220557DA` |
| `DDS_TYPE_ID` | `0x2F7D0004` |
| `PNG_TYPE_ID` | `0x00B2D882` |
| `RESOURCE_TYPE_LABELS` | Maps 47 type IDs → human-readable names |
| `RESOURCE_TYPE_BY_LABEL` | Maps 16 labels → type IDs (case-insensitive lookup) |
| `resolve_type_filter(name)` | Resolves a label or hex string to a type ID. |

---

## In-Game Mod Scripts (`game_mods/`)

These scripts run inside the Sims 4 engine (Python 3.7). They are packaged as `.ts4script` files and installed to the Mods folder.

### `devmode_cmd.py`

Registers the `devmode.reload` cheat command (CommandType.Live).

- `devmode.reload` — Reloads all Python files in the `Scripts/` folder
- `devmode.reload path.to.module` — Reloads a specific module or folder

Uses `sims4.reload.reload_file()` for hot reloading during gameplay.

### `debug_cmd.py`

Registers the `pycharm.debug` cheat command for PyCharm Pro remote debugging. Connects to localhost:5678 debug server.

---

## File Formats

### `.ts4script`

A zip archive containing compiled `.pyc` files. The Sims 4 engine loads these from the Mods folder at startup.

### `.package` (DBPF v2.0)

Binary container with 96-byte header and resource index. Resources identified by `(type_id, group, instance)`. See `util/datamining/` documentation for format details.

### STBL (String Table)

21-byte header (`STBL` magic, version, entry count, string data length) followed by entries (key hash uint32, flags byte, string length uint16, UTF-8 data).

### RefPack

EA's LZ compression identified by `0x10FB`/`0x50FB` magic. Variable-length control codes for back-references and literal runs. See `refpack.py` docstring for control code format.
