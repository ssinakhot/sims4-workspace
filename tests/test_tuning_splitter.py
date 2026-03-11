import pytest

from util.datamining.tuning_splitter import split_combined_tuning, SplitEntry


# CombinedTuning with shared <g> reference table
COMBINED_WITH_REFS = b"""\
<?xml version="1.0" encoding="utf-8"?>
<combined>
  <g s="merged">
    <E x="0">MAJOR</E>
    <E x="1">Skill_Mental</E>
    <T x="2">True</T>
    <L x="3">
      <T>Creative</T>
      <T>Cooking</T>
    </L>
  </g>
  <R>
    <I c="Skill" i="statistic" m="statistics.skill" n="skill_Cooking" s="16700">
      <r n="skill_level_type" x="0" />
      <T n="stat_name">0x1234ABCD</T>
      <r n="tags" x="3" />
    </I>
    <I c="Skill" i="statistic" m="statistics.skill" n="skill_Logic" s="16701">
      <r n="skill_level_type" x="0" />
      <T n="stat_name">0xAAAABBBB</T>
      <L n="tags">
        <r x="1" />
      </L>
    </I>
    <I c="Career" i="career" m="careers.career_tuning" n="career_Astronaut" s="25000">
      <T n="career_name">0xCCCCDDDD</T>
    </I>
  </R>
</combined>
"""

# Simple format without <g> (used in tests)
SIMPLE_FORMAT = b"""\
<?xml version="1.0" encoding="utf-8"?>
<M n="combined" s="0">
  <I c="Trait" i="trait" m="traits.traits" n="trait_Gloomy" s="32427">
    <T n="display_name">0xABCDE</T>
  </I>
</M>
"""

# Module-level tuning (<M> entries)
WITH_MODULE_TUNING = b"""\
<?xml version="1.0" encoding="utf-8"?>
<combined>
  <g s="merged">
    <T x="0">SomeValue</T>
  </g>
  <R>
    <I c="Skill" i="statistic" m="statistics.skill" n="skill_Cooking" s="16700">
      <T n="stat_name">0x1234ABCD</T>
    </I>
    <M n="objects.collection_manager" s="99999">
      <U n="COLLECTION_GARDENING">
        <r n="ref_field" x="0" />
      </U>
    </M>
  </R>
</combined>
"""

# Nested references (ref inside a resolved ref)
NESTED_REFS = b"""\
<?xml version="1.0" encoding="utf-8"?>
<combined>
  <g s="merged">
    <T x="0">inner_value</T>
    <U x="1">
      <r n="nested" x="0" />
    </U>
  </g>
  <R>
    <I c="Test" i="test" m="test.module" n="test_Entry" s="1">
      <r n="wrapper" x="1" />
    </I>
  </R>
</combined>
"""


class TestSplitCombinedTuning:
    def test_basic_split(self):
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        assert len(entries) == 3

    def test_entry_attributes(self):
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        cooking = next(e for e in entries if e.name == "skill_Cooking")
        assert cooking.cls == "Skill"
        assert cooking.instance_id == "16700"
        assert cooking.module == "statistics.skill"
        assert cooking.element_tag == "I"

    def test_reference_resolved_in_xml(self):
        """References like <r x="0"/> should be replaced with actual content."""
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        cooking = next(e for e in entries if e.name == "skill_Cooking")
        # The <r n="skill_level_type" x="0"/> should be resolved to <E n="skill_level_type">MAJOR</E>
        assert "MAJOR" in cooking.xml
        assert "<r " not in cooking.xml  # no unresolved references

    def test_list_reference_resolved(self):
        """<r x="3"/> referencing a list should be inlined."""
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        cooking = next(e for e in entries if e.name == "skill_Cooking")
        assert "Creative" in cooking.xml
        assert "Cooking" in cooking.xml

    def test_ref_inside_list_resolved(self):
        """<r> inside an <L> should be resolved."""
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        logic = next(e for e in entries if e.name == "skill_Logic")
        assert "Skill_Mental" in logic.xml
        assert "<r " not in logic.xml

    def test_simple_format(self):
        """Simple <M> root format (no <g> table)."""
        entries = split_combined_tuning(SIMPLE_FORMAT)
        assert len(entries) == 1
        assert entries[0].cls == "Trait"
        assert entries[0].name == "trait_Gloomy"
        assert "0xABCDE" in entries[0].xml

    def test_module_tuning(self):
        """<M> elements with s attribute are extracted as module tuning."""
        entries = split_combined_tuning(WITH_MODULE_TUNING)
        modules = [e for e in entries if e.element_tag == "M"]
        assert len(modules) == 1
        assert modules[0].name == "objects.collection_manager"
        assert modules[0].instance_id == "99999"

    def test_module_tuning_refs_resolved(self):
        """References inside <M> entries should also be resolved."""
        entries = split_combined_tuning(WITH_MODULE_TUNING)
        module = next(e for e in entries if e.element_tag == "M")
        assert "SomeValue" in module.xml
        assert "<r " not in module.xml

    def test_nested_references(self):
        """References that themselves contain references should be fully resolved."""
        entries = split_combined_tuning(NESTED_REFS)
        assert len(entries) == 1
        entry = entries[0]
        assert "inner_value" in entry.xml
        assert "<r " not in entry.xml

    def test_no_mutation_of_original(self):
        """Splitting should not modify the ref table entries (deep copy)."""
        # Split twice — second time should produce identical results
        entries1 = split_combined_tuning(COMBINED_WITH_REFS)
        entries2 = split_combined_tuning(COMBINED_WITH_REFS)
        for e1, e2 in zip(entries1, entries2):
            assert e1.xml == e2.xml

    def test_field_name_preserved(self):
        """The n attribute from <r> should transfer to the resolved element."""
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        cooking = next(e for e in entries if e.name == "skill_Cooking")
        # <r n="skill_level_type" x="0"/> → <E n="skill_level_type">MAJOR</E>
        assert 'n="skill_level_type"' in cooking.xml

    def test_career_no_refs(self):
        """Entries without references should still work fine."""
        entries = split_combined_tuning(COMBINED_WITH_REFS)
        career = next(e for e in entries if e.name == "career_Astronaut")
        assert career.cls == "Career"
        assert "0xCCCCDDDD" in career.xml
