"""
Known DBPF resource type IDs for The Sims 4 .package files.
"""

# Tuning XML — individual tuning entries
TUNING_TYPE_ID = 0x03B33DDF

# CombinedTuning XML — single blob containing all tuning <I> elements
COMBINED_TUNING_TYPE_ID = 0x62E94D38

# String Table (STBL) — localized string lookups
STRING_TABLE_TYPE_ID = 0x220557DA

# Image resources
# Per S4TK and verified against game files:
#   0x00B2D882 = DDS/DST image (S4TK: "DstImage") — data starts with "DDS "
#   0x2F7D0004 = PNG image (S4TK: "PngImage") — data starts with "\x89PNG"
DDS_TYPE_ID = 0x00B2D882    # DDS/DST image (DirectDraw Surface, may be DST-shuffled)
PNG_TYPE_ID = 0x2F7D0004    # Standard PNG image

# Human-readable labels for all known types (from S4TK BinaryResourceType enum)
RESOURCE_TYPE_LABELS = {
    # Binary resource types
    0x02D5DF13: "AnimationStateMachine (JAZZ)",
    0x034AEECB: "CasPart (CASP)",
    0x3C1AF1F2: "CasPartThumbnail",
    0xEAA32ADD: "CasPreset",
    COMBINED_TUNING_TYPE_ID: "CombinedTuning",
    DDS_TYPE_ID: "DstImage (DDS)",
    0xD382BF57: "Footprint (FTPT)",
    0x03B4C61D: "Light (LITE)",
    0x01661233: "Model (MODL)",
    0x01D10F34: "ModelLod (MLOD)",
    0x0166038C: "NameMap",
    0x319E4F1D: "ObjectCatalog (COBJ)",
    0xFF56010C: "ObjectCatalogSet",
    0xC0DB5AE7: "ObjectDefinition (OBJD)",
    0x25796DCA: "OpenTypeFont",
    PNG_TYPE_ID: "PngImage",
    0xD65DAFF9: "RegionDescription",
    0xAC16FBEC: "RegionMap",
    0x3453CF95: "Rle2Image",
    0xBA856C78: "RlesImage",
    0x8EAF13DE: "Rig",
    0x545AC67A: "SimData (DATA)",
    0x025ED6F4: "SimInfo (SIMO)",
    0xD3044521: "Slot",
    STRING_TABLE_TYPE_ID: "StringTable (STBL)",
    TUNING_TYPE_ID: "Tuning XML",
    0x2A8A5E22: "TrayItem",
    0x276CA4B9: "TrueTypeFont",
    # Additional types observed in game packages
    0x01A527DB: "Audio SNR (voice)",
    0x01EEF63A: "Audio SNS (effects)",
    0x6B20C4F3: "AnimationClip (CLIP)",
    0x067CAA11: "BlendGeometry (BGEO)",
    0x015A1849: "BodyGeometry (GEOM)",
    0x0355E0A6: "BoneDelta (BOND)",
    0xB4F762C9: "FloorCatalog (CFLR)",
    0x0418FE2A: "FenceCatalog (CFEN)",
    0xBDD82221: "AudioEvent (AUEV)",
    0x0354796A: "SkinTone (TONE)",
    0x376840D7: "Video (SCH1)",
    0x62ECC59A: "GFX",
    0x0333406C: "FontConfig (XML)",
    0xB6C8B6A0: "DdsOverlay",
    0x3C2A8647: "Thumbnail (CAS)",
    0x5B282D45: "Thumbnail",
    0xCD9DE247: "Thumbnail",
    0x9C925813: "Thumbnail",
    0xBC4A5044: "GeometryData",
}

# Short labels for --types CLI filter (case-insensitive lookup)
RESOURCE_TYPE_BY_LABEL = {
    "tuning": TUNING_TYPE_ID,
    "combinedtuning": COMBINED_TUNING_TYPE_ID,
    "stbl": STRING_TABLE_TYPE_ID,
    "dds": DDS_TYPE_ID,
    "dst": DDS_TYPE_ID,
    "png": PNG_TYPE_ID,
    "simdata": 0x545AC67A,
    "data": 0x545AC67A,
    "objd": 0xC0DB5AE7,
    "casp": 0x034AEECB,
    "cobj": 0x319E4F1D,
    "jazz": 0x02D5DF13,
    "clip": 0x6B20C4F3,
    "geom": 0x015A1849,
    "modl": 0x01661233,
    "rig": 0x8EAF13DE,
}


def resolve_type_filter(name):
    # type: (str) -> int
    """Resolve a resource type name or hex ID to a numeric type ID.

    Accepts:
      - Hex IDs: '0x2F7D0004' or '2F7D0004'
      - Labels: 'DDS', 'STBL', 'CombinedTuning' (case-insensitive)

    Raises ValueError if the name cannot be resolved.
    """
    # Try hex first
    stripped = name.strip()
    try:
        if stripped.lower().startswith("0x"):
            return int(stripped, 16)
        # If it looks like a hex string (all hex chars, >= 4 chars), parse it
        if len(stripped) >= 4 and all(c in "0123456789abcdefABCDEF" for c in stripped):
            return int(stripped, 16)
    except ValueError:
        pass

    # Try label lookup (case-insensitive, no spaces/underscores)
    normalized = stripped.lower().replace("_", "").replace(" ", "").replace("-", "")
    type_id = RESOURCE_TYPE_BY_LABEL.get(normalized)
    if type_id is not None:
        return type_id

    raise ValueError(
        "Unknown resource type: {!r}. Use a hex ID (0x2F7D0004) or label ({}).".format(
            name, ", ".join(sorted(RESOURCE_TYPE_BY_LABEL.keys()))
        )
    )
