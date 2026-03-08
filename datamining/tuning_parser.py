"""
Tuning XML parser for The Sims 4.

Parses tuning XML extracted from .package files into structured data.
Tuning files define game objects, interactions, buffs, traits, and other game data.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class TuningFile:
    """Represents a parsed Sims 4 tuning XML file."""
    instance_id: int
    tuning_type: str  # e.g. "interaction", "buff", "trait", "object"
    name: str         # e.g. "buff_Angry"
    cls: str = ""     # e.g. "sims4.tuning.instances.buff"
    references: list[int] = field(default_factory=list)  # instance IDs this tuning references


class TuningParser:
    """Parses Sims 4 tuning XML into TuningFile objects."""

    @staticmethod
    def parse(xml_string: str) -> TuningFile:
        """Parse a tuning XML string into a TuningFile.

        Typical tuning XML root element looks like:
            <I c="ClassName" i="tuning_type" m="module.path" n="TuningName" s="12345">
        """
        root = ET.fromstring(xml_string)

        instance_id = int(root.get("s", "0"))
        tuning_type = root.get("i", "")
        name = root.get("n", "")
        cls = root.get("c", "")

        # Collect all referenced tuning instance IDs
        references = TuningParser._collect_references(root)

        return TuningFile(
            instance_id=instance_id,
            tuning_type=tuning_type,
            name=name,
            cls=cls,
            references=references,
        )

    @staticmethod
    def _collect_references(element: ET.Element) -> list[int]:
        """Recursively collect all tuning instance ID references (s= attributes on T tags)."""
        refs = []
        for child in element.iter():
            # Tuning references appear as <T n="...">instance_id</T>
            # or elements with s= attributes
            if child.tag == "T" and child.text:
                try:
                    ref_id = int(child.text.strip())
                    if ref_id > 0:
                        refs.append(ref_id)
                except ValueError:
                    pass
        return refs

    @staticmethod
    def parse_multiple(xml_strings: list[str]) -> list[TuningFile]:
        """Parse multiple tuning XML strings."""
        results = []
        for xml_str in xml_strings:
            try:
                results.append(TuningParser.parse(xml_str))
            except ET.ParseError:
                continue
        return results
