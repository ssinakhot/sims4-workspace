import json
import os
import pytest

from extraction.extract_skills import (
    derive_display_name,
    categorize_skill,
    extract_skill,
    extract_all_skills,
)
from extraction.helpers import resolve_string
from util.datamining.combined_tuning import CombinedTuningParser, TuningElement
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


class TestExtractAllSkills:
    """Integration test using pre-extracted files in a temp directory."""

    def test_extracts_from_packages_dir(self, tmp_path):
        """Write skill XML files to a temp packages dir and extract."""
        # Set up packages dir structure
        skill_dir = tmp_path / "xml" / "Skill"
        skill_dir.mkdir(parents=True)

        # Write individual skill XML files (as extract-all would produce)
        skill_xml = '<I c="Skill" i="statistic" m="statistics.skill" n="skill_Cooking" s="16700">\n  <T n="skill_level_type">MAJOR</T>\n  <T n="hidden">False</T>\n  <L n="tags"><T>Creative</T></L>\n</I>'
        (skill_dir / "skill_Cooking.xml").write_text(skill_xml)

        skill_xml2 = '<I c="Skill" i="statistic" m="statistics.skill" n="skill_Logic" s="16701">\n  <T n="skill_level_type">MAJOR</T>\n  <T n="hidden">False</T>\n  <L n="tags"><T>Mental</T></L>\n</I>'
        (skill_dir / "skill_Logic.xml").write_text(skill_xml2)

        hidden_xml = '<I c="Skill" i="statistic" m="statistics.skill" n="skill_Hidden" s="16710">\n  <T n="skill_level_type">MINOR</T>\n  <T n="hidden">True</T>\n</I>'
        (skill_dir / "skill_Hidden.xml").write_text(hidden_xml)

        output_path = str(tmp_path / "skills.json")
        extract_all_skills(str(tmp_path), output_path, icons_dir=None)

        with open(output_path) as f:
            data = json.load(f)

        skills = data["skills"]
        all_names = [s["instanceName"] for cat in skills.values() for s in cat]
        assert "skill_Cooking" in all_names
        assert "skill_Logic" in all_names
        assert "skill_Hidden" not in all_names
        assert len(all_names) == 2
