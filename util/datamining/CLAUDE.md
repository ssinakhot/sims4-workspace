# util/datamining — Sims 4 Package Parsing Library

General-purpose library for reading The Sims 4 `.package` files (DBPF v2.0).

## Module Overview

| Module | Purpose |
|--------|---------|
| `package_reader.py` | DBPF v2.0 container reader — parses 96-byte header, resource index, extracts resources |
| `package_discovery.py` | Game folder scanner — discovers simulation, client, string, and all packages with full-before-delta ordering |
| `combined_tuning.py` | CombinedTuning XML parser with `<g>` shared reference table resolution |
| `binary_tuning.py` | Binary DATA format decoder — converts compiled CombinedTuning to XML string |
| `tuning_splitter.py` | Splits CombinedTuning into standalone XML entries with all `<r>` references inlined |
| `string_table.py` | STBL binary format parser for localized strings |
| `image_decoder.py` | DST5/DST3/DST1 (DDS variant) → PNG image decoder |
| `refpack.py` | EA RefPack/QFS decompression (used for large compressed resources) |
| `resource_types.py` | Resource type ID constants, human-readable labels, and `--types` CLI label resolution |
| `tuning_parser.py` | Single-file tuning XML parser (for individual tuning resources, not CombinedTuning) |

## Key Concepts

### Package File Types

The game uses two builds of simulation packages per pack:

- **Full builds** (`SimulationFullBuild0.package`) — Original pack data, in the pack's own directory
- **Delta builds** (`SimulationDeltaBuild0.package`) — Patches that add or update tuning entries

Delta builds live in two locations:
- Base game: `Data/Simulation/SimulationDeltaBuild0.package`
- Packs: `Delta/EPxx/SimulationDeltaBuild0.package` (also GP, SP, FP)

**Delta builds override full builds.** When the same tuning instance ID appears in both, the delta version is the current one. Consumers must search both and deduplicate by instance ID, keeping the delta version.

### CombinedTuning Formats

CombinedTuning (resource type `0x62E94D38`) exists in two formats:

1. **XML** — Used by base game full build. Starts with `<?xml` or `<combined>`.
2. **Binary DATA** — Used by all other packages (EP/GP/SP/FP full builds and all delta builds). Starts with magic bytes `DATA`.

Use `is_binary_combined_tuning(data)` to detect, then `decode_combined_tuning(data)` to convert binary to XML. Both produce equivalent XML that `CombinedTuningParser` can parse.

### CombinedTuning XML Structure

```xml
<combined>
  <g s="merged">
    <!-- Shared value table: indexed by x attribute -->
    <E x="0">MAJOR</E>
    <E x="1">Skill_Mental</E>
    <T x="2">True</T>
  </g>
  <R>
    <I c="Skill" i="statistic" m="statistics.skill" n="statistic_Skill_AdultMajor_Logic" s="16703">
      <r n="skill_level_type" x="0" />     <!-- resolves to "MAJOR" -->
      <T n="stat_name">0x3645CBC1</T>      <!-- STBL hash -->
      <T n="icon">2f7d0004:00000000:1c4b4b0d6f9b4aec</T>
      <L n="tags">
        <r x="1" />                         <!-- resolves to "Skill_Mental" -->
      </L>
    </I>
  </R>
</combined>
```

Key elements:
- `<g>` — Shared value table. Each child has an `x` attribute (index).
- `<r x="...">` — Reference to a shared value by index. Must be resolved before reading.
- `<I>` — Tuning entry with attributes: `c` (class), `i` (tuning type), `n` (name), `s` (instance ID), `m` (module path).
- `<T>` — Scalar value (text, hash, resource key).
- `<E>` — Enum value.
- `<L>` — List of values.

### Binary DATA Format

**Detection:** Decompressed resource starts with `DATA` (4 bytes).

**Header:** magic (`DATA`), version (`0x100` or `0x101`), table header offset, table count, schema offset, schema count. Little-endian byte order.

**Table structure (7 fixed tables encoding packed XML):**

| Table | Purpose | Schema | Row fields |
|-------|---------|--------|------------|
| 0 | Document metadata | Yes (20B) | first_element, top_element, element_count, string_table |
| 1 | XML nodes | Yes (12B) | text (string index), attrs (offset), children (offset) |
| 2 | XML attributes | Yes (8B) | name (string index), value (string index) |
| 3 | Node references | No | Offset to child node in table 1 |
| 4 | Attribute references | No | Offset to attribute in table 2 |
| 5 | String references | No | Offset to null-terminated string in character data |
| 6 | Character data | No | Raw UTF-8 characters |

**Implementation notes:**
- Schema matching: primary match by absolute offset position; fallback by `schema_size == row_size` (needed for EP01)
- `Character` data type (code 1): raw byte value, not UTF-8 (bytes > 0x7F are valid)
- `RELOFFSET_NULL` (`-0x80000000`): sentinel for null relative offsets — skip when resolving
- Reference: format ported from S4TK (MIT-licensed) TypeScript implementation at `@s4tk/models`

### Compression

Resources may be compressed with:

| Compression Type | Magic Bytes | Notes |
|-----------------|-------------|-------|
| zlib (`0x5A42`) | Standard zlib header | Common for smaller resources |
| RefPack (`0xFFFF`) | `0x10FB` or `0x50FB` | EA's proprietary LZ compression. Used for large resources like STBL and CombinedTuning. |

`PackageReader.extract_resource()` handles decompression automatically.

### String Tables

Localized strings are in `Strings_ENG_US.package` files (resource type `0x220557DA`). English locale uses group ID `0x00000000`. String tables exist in both pack directories and `Delta/` directories — search both for complete coverage.

**STBL binary format:**
- Header (21 bytes): magic `STBL`, version (uint16), compressed flag, num_entries (uint64), reserved (2 bytes), string data length (uint32)
- Entries: key_hash (uint32), flags (1 byte), string_length (uint16), UTF-8 string data

### Icon Resources

Icons referenced in tuning are resource keys in `type:group:instance` format (e.g., `2f7d0004:00000000:1c4b4b0d6f9b4aec`):

| Resource Type | Format | Description |
|--------------|--------|-------------|
| `0x2F7D0004` | DDS | DirectDraw Surface (texture) |
| `0x00B2D882` | PNG | Standard PNG image |

Icons are in `Client*Build*.package` files (both full and delta builds). `image_decoder.py` handles DDS-to-PNG conversion.

### Package Discovery

`package_discovery.py` provides functions to find game packages organized by category:

- `discover_simulation_packages(game_folder)` → `List[Tuple[str, str]]` — Simulation packages (full + delta), ordered full-before-delta for deduplication. Returns `(absolute_path, relative_path)` tuples.
- `discover_string_packages(game_folder)` → `List[str]` — All `Strings_ENG_US.package` files.
- `discover_client_packages(game_folder)` → `List[Tuple[str, str]]` — Client packages (full + delta), ordered full-before-delta.
- `discover_all_packages(game_folder)` → `List[Tuple[str, str]]` — Every `.package` file in the game folder tree.

### Tuning Splitter

`tuning_splitter.py` splits a CombinedTuning resource into standalone XML entries:

- `split_combined_tuning(data: bytes) -> List[SplitEntry]` — Takes raw CombinedTuning bytes (XML or binary DATA), resolves all `<r>` references from the `<g>` shared table, and returns individual entries.
- Each `SplitEntry` has: `cls` (tuning class), `name` (instance name), `instance_id`, `module`, `element_tag` (`"I"` or `"M"`), `xml` (standalone XML string).
- References are deep-copied and inlined recursively, so each output entry is fully self-contained.

### Resource Type Resolution

`resource_types.py` provides label-based lookup for the `--types` CLI filter:

- `resolve_type_filter(name)` — Accepts hex IDs (`"0x2F7D0004"`) or labels (`"DDS"`, `"STBL"`, `"CombinedTuning"`). Case-insensitive, strips underscores/hyphens/spaces.
- `RESOURCE_TYPE_BY_LABEL` — Maps 16 common labels to type IDs (tuning, combinedtuning, stbl, dds, dst, png, simdata, data, objd, casp, cobj, jazz, clip, geom, modl, rig).
- `RESOURCE_TYPE_LABELS` — Maps 47 known type IDs to human-readable names for display.

## Python 3.7 Compatibility

All code must be Python 3.7 compatible. Use `typing.List`, `typing.Dict`, `typing.Tuple` etc. — not `list[X]`, `dict[X, Y]`.
