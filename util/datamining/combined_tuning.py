"""
CombinedTuning XML parser for The Sims 4.

CombinedTuning (resource type 0x62E94D38) is a single large XML resource
containing all tuning entries for a package.

The format uses a shared reference table: a <g> element at the root holds
shared values indexed by the "x" attribute. Throughout the rest of the tree,
<r x="..."> elements reference those shared values.

Each tuning entry is an <I> element with attributes:
  c (class), i (tuning type), m (module), n (name), s (instance ID).

This module provides iteration over those elements and helpers to read
common child node patterns, automatically resolving shared references.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Iterator, List, Optional


class _RefTable:
    """Shared value reference table built from the <g> element."""

    def __init__(self):
        # type: () -> None
        self._table = {}  # type: Dict[str, ET.Element]

    @classmethod
    def from_element(cls, g_element):
        # type: (ET.Element) -> _RefTable
        """Build the reference table from a <g> element."""
        table = cls()
        for child in g_element:
            x = child.get("x")
            if x is not None:
                table._table[x] = child
        return table

    def resolve(self, ref_element):
        # type: (ET.Element) -> Optional[ET.Element]
        """Resolve an <r x="..."> reference to the shared element."""
        x = ref_element.get("x")
        if x is not None:
            return self._table.get(x)
        return None

    def __len__(self):
        # type: () -> int
        return len(self._table)


# Sentinel for when no ref table is available
_NO_REFS = _RefTable()


class TuningElement:
    """Wrapper around an <I> element providing field accessor helpers.

    Automatically resolves <r x="..."> references through the shared ref table.
    """

    def __init__(self, element, ref_table=None):
        # type: (ET.Element, Optional[_RefTable]) -> None
        self._el = element
        self._refs = ref_table or _NO_REFS

    # -- Top-level attributes --

    @property
    def cls(self):
        # type: () -> str
        """Class name (c attribute), e.g. 'Skill', 'Career'."""
        return self._el.get("c", "")

    @property
    def tuning_type(self):
        # type: () -> str
        """Tuning type (i attribute), e.g. 'statistic', 'career'."""
        return self._el.get("i", "")

    @property
    def module(self):
        # type: () -> str
        """Module path (m attribute), e.g. 'statistics.skill'."""
        return self._el.get("m", "")

    @property
    def name(self):
        # type: () -> str
        """Instance name (n attribute), e.g. 'skill_Cooking'."""
        return self._el.get("n", "")

    @property
    def instance_id(self):
        # type: () -> int
        """Tuning instance ID (s attribute)."""
        return int(self._el.get("s", "0"))

    # -- Reference resolution --

    def _resolve_element(self, el):
        # type: (ET.Element) -> ET.Element
        """If el is an <r> reference, resolve it; otherwise return as-is."""
        if el.tag == "r":
            resolved = self._refs.resolve(el)
            if resolved is not None:
                return resolved
        return el

    def _get_text(self, el):
        # type: (ET.Element) -> Optional[str]
        """Get text from an element, resolving references if needed."""
        resolved = self._resolve_element(el)
        if resolved.text:
            return resolved.text.strip()
        return None

    # -- Child node accessors --

    def get_value(self, field_name):
        # type: (str) -> Optional[str]
        """Get text content of a child field, resolving references.

        Looks for <T n="field_name">, <E n="field_name">, or <r n="field_name">
        and returns the text content (resolving <r> through the ref table).
        """
        for child in self._el:
            if child.get("n") == field_name:
                return self._get_text(child)
        return None

    def get_enum(self, field_name):
        # type: (str) -> Optional[str]
        """Get an enum value (same as get_value, but named for clarity)."""
        return self.get_value(field_name)

    def get_bool(self, field_name, default=False):
        # type: (str, bool) -> bool
        """Get a boolean field. Returns default if field is absent."""
        val = self.get_value(field_name)
        if val is None:
            return default
        return val.lower() == "true"

    def get_list(self, field_name):
        # type: (str) -> List[str]
        """Get values from an <L n="field_name"> list, resolving references.

        Returns text values from children inside the <L>, resolving any <r>
        references through the shared table.
        """
        for child in self._el:
            if child.tag == "L" and child.get("n") == field_name:
                result = []
                for item in child:
                    text = self._get_text(item)
                    if text:
                        result.append(text)
                return result
            # The list itself might be a reference
            if child.tag == "r" and child.get("n") == field_name:
                resolved = self._refs.resolve(child)
                if resolved is not None and resolved.tag == "L":
                    result = []
                    for item in resolved:
                        text = self._get_text(item)
                        if text:
                            result.append(text)
                    return result
        return []

    def get_child_element(self, field_name):
        # type: (str) -> Optional[ET.Element]
        """Get a direct child element by its n attribute, resolving references."""
        for child in self._el:
            if child.get("n") == field_name:
                return self._resolve_element(child)
        return None

    @property
    def raw(self):
        # type: () -> ET.Element
        """Access the underlying ElementTree element for complex parsing."""
        return self._el

    def to_dict(self):
        # type: () -> Dict[str, str]
        """Return the top-level attributes as a dict."""
        return {
            "cls": self.cls,
            "tuning_type": self.tuning_type,
            "module": self.module,
            "name": self.name,
            "instance_id": self.instance_id,
        }

    def __repr__(self):
        # type: () -> str
        return "TuningElement(c={!r}, n={!r}, s={})".format(
            self.cls, self.name, self.instance_id
        )


class CombinedTuningParser:
    """Parses a CombinedTuning XML resource into iterable TuningElements.

    Supports two formats:
    - Simple: <M> root with <I> children directly
    - Full game: <combined> root with <g> shared refs + <R> groups containing <I>
    """

    def __init__(self, xml_data):
        # type: (str) -> None
        """Parse CombinedTuning XML.

        Args:
            xml_data: The raw XML string from a CombinedTuning resource.
        """
        self._root = ET.fromstring(xml_data)

        # Build reference table from <g> element if present
        g_element = self._root.find("g")
        if g_element is not None:
            self._refs = _RefTable.from_element(g_element)
        else:
            self._refs = _NO_REFS

        # Find all <I> elements with a c= attribute anywhere in the tree.
        self._elements = [
            TuningElement(el, self._refs)
            for el in self._root.iter("I")
            if el.get("c") is not None
        ]

    @property
    def ref_count(self):
        # type: () -> int
        """Number of entries in the shared reference table."""
        return len(self._refs)

    def __len__(self):
        # type: () -> int
        return len(self._elements)

    def __iter__(self):
        # type: () -> Iterator[TuningElement]
        return iter(self._elements)

    def by_class(self, cls_name):
        # type: (str) -> List[TuningElement]
        """Filter elements by class name (c attribute).

        Args:
            cls_name: e.g. 'Skill', 'Career', 'Trait'
        """
        return [el for el in self._elements if el.cls == cls_name]

    def by_module(self, module_path):
        # type: (str) -> List[TuningElement]
        """Filter elements by module path (m attribute)."""
        return [el for el in self._elements if el.module == module_path]

    def by_tuning_type(self, tuning_type):
        # type: (str) -> List[TuningElement]
        """Filter elements by tuning type (i attribute)."""
        return [el for el in self._elements if el.tuning_type == tuning_type]

    def find_by_name(self, name):
        # type: (str) -> Optional[TuningElement]
        """Find a single element by instance name (n attribute)."""
        for el in self._elements:
            if el.name == name:
                return el
        return None

    def find_by_instance_id(self, instance_id):
        # type: (str) -> Optional[TuningElement]
        """Find a single element by tuning instance ID (s attribute)."""
        for el in self._elements:
            if el.instance_id == instance_id:
                return el
        return None
