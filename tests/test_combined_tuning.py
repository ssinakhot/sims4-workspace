import pytest

from util.datamining.combined_tuning import CombinedTuningParser, TuningElement


SAMPLE_COMBINED_XML = """\
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
  <I c="Skill" i="statistic" m="statistics.skill" n="skill_HiddenDancing" s="16702">
    <T n="hidden">True</T>
    <T n="skill_level_type">MINOR</T>
  </I>
  <I c="Career" i="career" m="careers.career_tuning" n="career_Astronaut" s="25000">
    <T n="career_name">0xCCCCDDDD</T>
    <T n="career_description">0xEEEEFFFF</T>
  </I>
  <I c="Trait" i="trait" m="traits.traits" n="trait_OccultVampire" s="99000">
    <T n="display_name">0x11112222</T>
  </I>
</M>
"""


class TestCombinedTuningParser:
    def test_parse_and_count(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        assert len(parser) == 5

    def test_iteration(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        names = [el.name for el in parser]
        assert "skill_Cooking" in names
        assert "career_Astronaut" in names

    def test_by_class(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        skills = parser.by_class("Skill")
        assert len(skills) == 3
        assert all(el.cls == "Skill" for el in skills)

    def test_by_class_no_match(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        assert len(parser.by_class("Nonexistent")) == 0

    def test_by_module(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        career_els = parser.by_module("careers.career_tuning")
        assert len(career_els) == 1
        assert career_els[0].name == "career_Astronaut"

    def test_by_tuning_type(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        stats = parser.by_tuning_type("statistic")
        assert len(stats) == 3

    def test_find_by_name(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        el = parser.find_by_name("skill_Cooking")
        assert el is not None
        assert el.instance_id == 16700

    def test_find_by_name_missing(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        assert parser.find_by_name("nonexistent") is None

    def test_find_by_instance_id(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        el = parser.find_by_instance_id(25000)
        assert el is not None
        assert el.name == "career_Astronaut"


class TestTuningElement:
    @pytest.fixture
    def cooking_skill(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        return parser.find_by_name("skill_Cooking")

    def test_attributes(self, cooking_skill):
        assert cooking_skill.cls == "Skill"
        assert cooking_skill.tuning_type == "statistic"
        assert cooking_skill.module == "statistics.skill"
        assert cooking_skill.name == "skill_Cooking"
        assert cooking_skill.instance_id == 16700

    def test_get_value(self, cooking_skill):
        assert cooking_skill.get_value("stat_name") == "0x1234ABCD"
        assert cooking_skill.get_value("skill_level_type") == "MAJOR"

    def test_get_value_missing(self, cooking_skill):
        assert cooking_skill.get_value("nonexistent") is None

    def test_get_enum(self, cooking_skill):
        assert cooking_skill.get_enum("skill_level_type") == "MAJOR"

    def test_get_bool_false(self, cooking_skill):
        assert cooking_skill.get_bool("hidden") is False

    def test_get_bool_true(self):
        parser = CombinedTuningParser(SAMPLE_COMBINED_XML)
        hidden_skill = parser.find_by_name("skill_HiddenDancing")
        assert hidden_skill.get_bool("hidden") is True

    def test_get_bool_default(self, cooking_skill):
        assert cooking_skill.get_bool("nonexistent") is False
        assert cooking_skill.get_bool("nonexistent", default=True) is True

    def test_get_list(self, cooking_skill):
        tags = cooking_skill.get_list("tags")
        assert tags == ["Creative", "Cooking"]

    def test_get_list_missing(self, cooking_skill):
        assert cooking_skill.get_list("nonexistent") == []

    def test_get_child_element(self, cooking_skill):
        el = cooking_skill.get_child_element("tags")
        assert el is not None
        assert el.tag == "L"

    def test_get_child_element_missing(self, cooking_skill):
        assert cooking_skill.get_child_element("nonexistent") is None

    def test_to_dict(self, cooking_skill):
        d = cooking_skill.to_dict()
        assert d["cls"] == "Skill"
        assert d["name"] == "skill_Cooking"
        assert d["instance_id"] == 16700

    def test_repr(self, cooking_skill):
        r = repr(cooking_skill)
        assert "Skill" in r
        assert "skill_Cooking" in r
        assert "16700" in r

    def test_raw_access(self, cooking_skill):
        raw = cooking_skill.raw
        assert raw.tag == "I"
        assert raw.get("c") == "Skill"
