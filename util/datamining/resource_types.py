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
DDS_TYPE_ID = 0x2F7D0004    # DirectDraw Surface texture
PNG_TYPE_ID = 0x00B2D882    # Standard PNG image

# Human-readable labels for known types
RESOURCE_TYPE_LABELS = {
    TUNING_TYPE_ID: "Tuning XML",
    COMBINED_TUNING_TYPE_ID: "CombinedTuning XML",
    STRING_TABLE_TYPE_ID: "String Table (STBL)",
    DDS_TYPE_ID: "DDS Image",
    PNG_TYPE_ID: "PNG Image",
}
