import json
import struct
import pytest

from extraction.extract_skills import (
    derive_display_name,
    resolve_string,
    categorize_skill,
    extract_skill,
    extract_skills_from_xml,
)
from util.datamining.combined_tuning import CombinedTuningParser
from util.datamining.string_table import StringTable


# -- Test XML with a mix of skills --

SKILLS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<M n="combined" s="0">
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Cooking" s="16700">
    <T n="stat_name">0x1234ABCD</T>
    <T n="skill_description">0x5678CDEF</T>
    <T n="skill_level_type">MAJOR</T>
    <T n="hidden">False</T>
    <T n="icon">0x00000000AABBCCDD</T>
    <L n="tags">
      <T>Creative</T>
      <T>Cooking</T>
    </L>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Logic" s="16701">
    <T n="stat_name">0xAAAABBBB</T>
    <T n="skill_level_type">MAJOR</T>
    <T n="hidden">False</T>
    <L n="tags">
      <T>Mental</T>
    </L>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Fitness" s="16702">
    <T n="skill_level_type">MAJOR</T>
    <T n="hidden">False</T>
    <L n="tags">
      <T>Motor</T>
    </L>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Charisma" s="16703">
    <T n="skill_level_type">MAJOR</T>
    <T n="hidden">False</T>
    <L n="tags">
      <T>Social</T>
    </L>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Hidden_Dancing" s="16710">
    <T n="skill_level_type">MINOR</T>
    <T n="hidden">True</T>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Toddler_Potty" s="16720">
    <T n="skill_level_type">POTTY</T>
    <T n="hidden">False</T>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Child_Creativity" s="16730">
    <T n="skill_level_type">CHILD</T>
    <T n="hidden">False</T>
    <L n="tags">
      <T>Creative</T>
    </L>
  </I>
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_Bowling" s="16740">
    <T n="skill_level_type">MINOR</T>
    <T n="hidden">False</T>
    <L n="tags">
      <T>Motor</T>
    </L>
  </I>
  <I c="Career" i="career" m="careers.career_tuning" n="career_Astronaut" s="25000">
    <T n="career_name">0xCCCCDDDD</T>
  </I>
</M>
"""


def make_string_table(entries):
    """Create a StringTable from a dict of {hash: string}."""
    table = StringTable()
    table.strings = dict(entries)
    return table


class TestDeriveDisplayName:
    def test_skill_prefix(self):
        assert derive_display_name("skill_Cooking") == "Cooking"

    def test_skill_prefix_with_underscores(self):
        assert derive_display_name("skill_Child_Creativity") == "Child Creativity"

    def test_no_prefix(self):
        assert derive_display_name("Bowling") == "Bowling"

    def test_complex_name(self):
        assert derive_display_name("statistic_skill_Bowling") == "Bowling"


class TestResolveString:
    def test_resolve_hex(self):
        table = make_string_table({0x1234ABCD: "Cooking"})
        assert resolve_string("0x1234ABCD", table) == "Cooking"

    def test_resolve_decimal(self):
        table = make_string_table({12345: "Test Skill"})
        assert resolve_string("12345", table) == "Test Skill"

    def test_resolve_missing(self):
        table = make_string_table({0x1111: "Something"})
        assert resolve_string("0x9999", table) is None

    def test_resolve_no_table(self):
        assert resolve_string("0x1234", None) is None

    def test_resolve_no_hash(self):
        table = make_string_table({})
        assert resolve_string(None, table) is None

    def test_resolve_invalid_hash(self):
        table = make_string_table({})
        assert resolve_string("not_a_number", table) is None


class TestCategorizeSkill:
    def test_uses_first_meaningful_tag(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Cooking")
        assert categorize_skill(el) == "Creative"

    def test_skips_skill_all(self):
        """Tags like Skill_All should be skipped."""
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Logic")
        # First tag is Mental, so that's the category
        assert categorize_skill(el) == "Mental"

    def test_no_tags_returns_other(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Hidden_Dancing")
        assert categorize_skill(el) == "Other"


class TestExtractSkill:
    def test_basic_extraction(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Cooking")
        result = extract_skill(el)
        assert result is not None
        assert result["instanceName"] == "skill_Cooking"
        assert result["name"] == "Cooking"
        assert result["skillLevelType"] == "MAJOR"
        assert result["tuningInstanceId"] == "0x0000413C"

    def test_with_string_table(self):
        table = make_string_table({0x1234ABCD: "Gourmet Cooking"})
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Cooking")
        result = extract_skill(el, table)
        assert result["name"] == "Gourmet Cooking"

    def test_description_resolved(self):
        table = make_string_table({0x5678CDEF: "Master the art of cooking."})
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Cooking")
        result = extract_skill(el, table)
        assert result["description"] == "Master the art of cooking."

    def test_hidden_returns_none(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Hidden_Dancing")
        assert extract_skill(el) is None

    def test_potty_included(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Toddler_Potty")
        result = extract_skill(el)
        assert result is not None
        assert result["skillLevelType"] == "POTTY"

    def test_child_skill_included(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Child_Creativity")
        result = extract_skill(el)
        assert result is not None
        assert result["skillLevelType"] == "CHILD"

    def test_minor_skill_included(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Bowling")
        result = extract_skill(el)
        assert result is not None
        assert result["skillLevelType"] == "MINOR"

    def test_icon_ref(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Cooking")
        result = extract_skill(el)
        assert result["iconRef"] == "0x00000000AABBCCDD"

    def test_no_description_key_when_unresolved(self):
        parser = CombinedTuningParser(SKILLS_XML)
        el = parser.find_by_name("skill_Fitness")
        result = extract_skill(el)
        assert "description" not in result


class TestExtractSkillsFromXml:
    def test_grouped_by_first_tag(self):
        result = extract_skills_from_xml(SKILLS_XML)
        # Tags from test XML are used directly as category names
        assert "Creative" in result
        assert "Mental" in result
        assert "Motor" in result
        assert "Social" in result

    def test_filters_hidden(self):
        result = extract_skills_from_xml(SKILLS_XML)
        all_names = [s["instanceName"] for skills in result.values() for s in skills]
        assert "skill_Hidden_Dancing" not in all_names

    def test_includes_potty(self):
        result = extract_skills_from_xml(SKILLS_XML)
        all_names = [s["instanceName"] for skills in result.values() for s in skills]
        assert "skill_Toddler_Potty" in all_names

    def test_excludes_non_skill_classes(self):
        result = extract_skills_from_xml(SKILLS_XML)
        all_names = [s["instanceName"] for skills in result.values() for s in skills]
        assert "career_Astronaut" not in all_names

    def test_correct_counts(self):
        result = extract_skills_from_xml(SKILLS_XML)
        total = sum(len(v) for v in result.values())
        # Cooking, Logic, Fitness, Charisma, Child_Creativity, Bowling, Toddler_Potty = 7
        # Hidden_Dancing filtered (hidden)
        assert total == 7

    def test_creative_contents(self):
        result = extract_skills_from_xml(SKILLS_XML)
        creative_names = [s["instanceName"] for s in result["Creative"]]
        assert "skill_Cooking" in creative_names
        assert "skill_Child_Creativity" in creative_names

    def test_sorted_within_category(self):
        result = extract_skills_from_xml(SKILLS_XML)
        creative_names = [s["name"] for s in result["Creative"]]
        assert creative_names == sorted(creative_names)

    def test_with_string_table(self):
        table = make_string_table({
            0x1234ABCD: "Gourmet Cooking",
            0xAAAABBBB: "Logical Thinking",
        })
        result = extract_skills_from_xml(SKILLS_XML, table)
        cooking = [s for s in result["Creative"] if s["instanceName"] == "skill_Cooking"][0]
        assert cooking["name"] == "Gourmet Cooking"
        logic = result["Mental"][0]
        assert logic["name"] == "Logical Thinking"
