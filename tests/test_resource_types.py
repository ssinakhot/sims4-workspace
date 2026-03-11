import pytest

from util.datamining.resource_types import (
    TUNING_TYPE_ID,
    COMBINED_TUNING_TYPE_ID,
    STRING_TABLE_TYPE_ID,
    DDS_TYPE_ID,
    PNG_TYPE_ID,
    RESOURCE_TYPE_BY_LABEL,
    resolve_type_filter,
)


class TestResolveTypeFilter:
    def test_hex_with_prefix(self):
        assert resolve_type_filter("0x00B2D882") == DDS_TYPE_ID

    def test_hex_without_prefix(self):
        assert resolve_type_filter("00B2D882") == DDS_TYPE_ID

    def test_hex_lowercase(self):
        assert resolve_type_filter("0x00b2d882") == DDS_TYPE_ID

    def test_hex_png(self):
        assert resolve_type_filter("0x2F7D0004") == PNG_TYPE_ID

    def test_label_dds(self):
        assert resolve_type_filter("DDS") == DDS_TYPE_ID

    def test_label_case_insensitive(self):
        assert resolve_type_filter("dds") == DDS_TYPE_ID
        assert resolve_type_filter("Dds") == DDS_TYPE_ID

    def test_label_stbl(self):
        assert resolve_type_filter("STBL") == STRING_TABLE_TYPE_ID

    def test_label_png(self):
        assert resolve_type_filter("PNG") == PNG_TYPE_ID

    def test_label_tuning(self):
        assert resolve_type_filter("Tuning") == TUNING_TYPE_ID

    def test_label_combined_tuning(self):
        assert resolve_type_filter("CombinedTuning") == COMBINED_TUNING_TYPE_ID

    def test_label_with_underscore(self):
        assert resolve_type_filter("combined_tuning") == COMBINED_TUNING_TYPE_ID

    def test_label_with_hyphen(self):
        assert resolve_type_filter("combined-tuning") == COMBINED_TUNING_TYPE_ID

    def test_whitespace_stripped(self):
        assert resolve_type_filter("  PNG  ") == PNG_TYPE_ID

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError, match="Unknown resource type"):
            resolve_type_filter("FooBar")

    def test_short_string_not_hex(self):
        # "abc" is only 3 chars, so it won't be treated as hex
        with pytest.raises(ValueError, match="Unknown resource type"):
            resolve_type_filter("abc")


class TestResourceTypeByLabel:
    def test_all_known_types_have_labels(self):
        """Every constant should be reachable via label lookup."""
        assert TUNING_TYPE_ID in RESOURCE_TYPE_BY_LABEL.values()
        assert COMBINED_TUNING_TYPE_ID in RESOURCE_TYPE_BY_LABEL.values()
        assert STRING_TABLE_TYPE_ID in RESOURCE_TYPE_BY_LABEL.values()
        assert DDS_TYPE_ID in RESOURCE_TYPE_BY_LABEL.values()
        assert PNG_TYPE_ID in RESOURCE_TYPE_BY_LABEL.values()
