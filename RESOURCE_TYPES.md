# Sims 4 Package Resource Types

Known DBPF resource type IDs for The Sims 4 `.package` files.

Generated from game files using `python datamine.py info`. Cross-referenced with [S4TK BinaryResourceType](https://github.com/sims4toolkit/models).

## Binary Resource Types

These are the 29 binary resource types defined in S4TK, plus additional types observed in game packages.

| Type ID | Abbr | Description |
|---------|------|-------------|
| `0x015A1849` | GEOM | Body/CAS part geometry |
| `0x01661233` | MODL | Object model (geometry) |
| `0x01942E2C` | | Object data |
| `0x01A527DB` | AUD | Audio SNR (voice/dialog) |
| `0x01D0E75D` | | LOD data |
| `0x01D10F34` | MLOD | Object model LODs |
| `0x01EEF63A` | AUD | Audio SNS (effects/music) |
| `0x025ED6F4` | SIMO | Sim outfit |
| `0x02D5DF13` | JAZZ | Animation state machines |
| `0x034AEECB` | CASP | CAS Part data |
| `0x0354796A` | TONE | Skin tone |
| `0x0355E0A6` | BOND | Bone delta |
| `0x03B4C61D` | LITE | Light definition |
| `0x0418FE2A` | CFEN | Fence catalog entry |
| `0x067CAA11` | BGEO | Blend geometry |
| `0x0166038C` | | Package metadata (NameMap) |
| `0x00B2D882` | DST | DDS/DST image (DST5, DST1, ATI2) |
| `0x2F7D0004` | PNG | PNG image |
| `0x220557DA` | STBL | String table (localized text) |
| `0x25796DCA` | | OpenType font |
| `0x276CA4B9` | | TrueType font symbols |
| `0x2A8A5E22` | | Tray item |
| `0x319E4F1D` | COBJ | Object catalog entry |
| `0x3453CF95` | DDS | DDS DXT5 RLE image |
| `0x376840D7` | AVI | Video (SCH1 format) |
| `0x545AC67A` | DATA | SimData (binary tuning companion) |
| `0x62E94D38` | | CombinedTuning XML |
| `0x6B20C4F3` | CLIP | Animation clips |
| `0x8EAF13DE` | RIG | Skeleton/rig |
| `0xAC16FBEC` | | Geometry references (multi-GEOM) |
| `0xB4F762C9` | CFLR | Floor catalog entry |
| `0xB6C8B6A0` | IMG | DDS image (overlays) |
| `0xBA856C78` | IMG | DDS DXT5 RLES image |
| `0xBC4A5044` | | Geometry data |
| `0xBDD82221` | AUEV | Audio event strings |
| `0xC0DB5AE7` | OBJD | Object definition |
| `0xD382BF57` | FTPT | Footprint |
| `0xD3044521` | | Slot data |
| `0xD65DAFF9` | | Region description |
| `0xFF56010C` | | Object catalog set |

## Tuning Resource Types

Individual tuning XML entries use type ID `0x03B33DDF`. The 126 tuning class types (Buff, Career, Trait, etc.) are distinguished by the `c` attribute in the XML, not by type ID.

CombinedTuning (`0x62E94D38`) contains all tuning entries merged into a single resource per package.

## Thumbnail Types

| Type ID | Description |
|---------|-------------|
| `0x3C2A8647` | CAS thumbnails |
| `0x3C1AF1F2` | CAS Part thumbnails |
| `0x5B282D45` | Thumbnails |
| `0x8E71065D` | Thumbnail data |
| `0x9C925813` | Thumbnails |
| `0xCD9DE247` | Thumbnails |

## Animation & Model Types

| Type ID | Description |
|---------|-------------|
| `0xFD04E3BE` | Animation data |
| `0x81CA1A10` | Object data |
| `0xD5F0F921` | Region/lot data |
| `0x033B2B66` | Material data |
| `0x71BDB8A2` | Fashion style preset |
| `0x1B192049` | Audio data |

## UI & Config Types

| Type ID | Abbr | Description |
|---------|------|-------------|
| `0x62ECC59A` | GFX | GFX UI files |
| `0x0333406C` | XML | Font configuration |
| `0x26978421` | | Cursor file |
| `0xC202C770` | XML | Music data file |
| `0xC582D2FB` | XML | XML config |
| `0x4115F9D5` | XML | Sound config |
| `0x99D98089` | XML | Button UI event mapping |
| `0xA576C2E7` | XML | Sound config |
| `0xEA5118B0` | SWB | Effect file |
| `0x1B25A024` | XML | Sound properties |
| `0xE231B3D8` | XML | Object modifiers |
| `0x1A8506C5` | XML | Modal music wrappings |

## Extracting Resources

Use `datamine.py extract-all` to extract resources from game packages:

```bash
# Default: tuning XML, string tables, and images
python datamine.py extract-all /path/to/game -o output/

# Extract everything (smart processing for known types, raw .bin for others)
python datamine.py extract-all /path/to/game -o output/ --types all

# Extract specific types by label or hex ID
python datamine.py extract-all /path/to/game -o output/ --types STBL PNG
python datamine.py extract-all /path/to/game -o output/ --types 0xDEADBEEF
```

Supported `--types` labels: `tuning`, `combinedtuning`, `stbl`, `dds`, `dst`, `png`, `simdata`, `data`, `objd`, `casp`, `cobj`, `jazz`, `clip`, `geom`, `modl`, `rig`.

## References

- [S4TK BinaryResourceType enum](https://github.com/sims4toolkit/models) — 29 binary resource types with verified IDs
- [S4TK TuningResourceType enum](https://github.com/sims4toolkit/models) — 126 individual tuning class type IDs
- [SimsWiki: PackedFileTypes](https://simswiki.info/wiki.php?title=Sims_4:PackedFileTypes)
- [Sims4Tools: Packed File Types](https://github.com/Kuree/Sims4Tools/wiki/Sims-4---Packed-File-Types)
