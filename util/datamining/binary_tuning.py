"""
Binary DATA format decoder for Sims 4 CombinedTuning resources.

The Sims 4 expansion/game/stuff packs use a compiled binary format (magic "DATA")
instead of XML for CombinedTuning resources (type 0x62E94D38). This module decodes
the binary format back into XML strings that can be parsed by CombinedTuningParser.

Format reference: S4TK (sims4toolkit) MIT-licensed TypeScript implementation.
Binary template: EA's official SimData/CombinedTuning binary template (0x545AC67A).

The binary format encodes XML as 7 tables:
  0: Document metadata (first_element, top_element, element_count, string_table)
  1: XML nodes (text string index, attrs offset, children offset)
  2: Attributes (name string index, value string index)
  3: Node reference array (offsets to child nodes)
  4: Attribute reference array (offsets to attributes)
  5: String reference array (offsets to null-terminated strings)
  6: Character data (raw strings, read via string ref offsets)
"""

import struct
from typing import Dict, List, Optional, Tuple


# Null offset sentinel
RELOFFSET_NULL = -0x80000000


class BinaryDecoder:
    """Simple binary buffer reader with position tracking."""

    def __init__(self, data):
        # type: (bytes) -> None
        self._data = data
        self._pos = 0

    def tell(self):
        # type: () -> int
        return self._pos

    def seek(self, pos):
        # type: (int) -> None
        self._pos = pos

    def skip(self, n):
        # type: (int) -> None
        self._pos += n

    def is_eof(self):
        # type: () -> bool
        return self._pos >= len(self._data)

    def uint8(self):
        # type: () -> int
        val = self._data[self._pos]
        self._pos += 1
        return val

    def int16(self):
        # type: () -> int
        val = struct.unpack_from('<h', self._data, self._pos)[0]
        self._pos += 2
        return val

    def uint16(self):
        # type: () -> int
        val = struct.unpack_from('<H', self._data, self._pos)[0]
        self._pos += 2
        return val

    def int32(self):
        # type: () -> int
        val = struct.unpack_from('<i', self._data, self._pos)[0]
        self._pos += 4
        return val

    def uint32(self):
        # type: () -> int
        val = struct.unpack_from('<I', self._data, self._pos)[0]
        self._pos += 4
        return val

    def uint64(self):
        # type: () -> int
        val = struct.unpack_from('<Q', self._data, self._pos)[0]
        self._pos += 8
        return val

    def float32(self):
        # type: () -> float
        val = struct.unpack_from('<f', self._data, self._pos)[0]
        self._pos += 4
        return val

    def string(self):
        # type: () -> str
        """Read a null-terminated UTF-8 string."""
        end = self._data.index(b'\x00', self._pos)
        s = self._data[self._pos:end].decode('utf-8')
        self._pos = end + 1
        return s

    def chars_utf8(self, n):
        # type: (int) -> str
        s = self._data[self._pos:self._pos + n].decode('utf-8')
        self._pos += n
        return s


# DataType enum values matching the binary template
class DataType:
    Boolean = 0
    Character = 1
    Int8 = 2
    UInt8 = 3
    Int16 = 4
    UInt16 = 5
    Int32 = 6
    UInt32 = 7
    Int64 = 8
    UInt64 = 9
    Float = 10
    String = 11
    HashedString = 12
    Object = 13
    Vector = 14
    Float2 = 15
    Float3 = 16
    Float4 = 17
    TableSetReference = 18
    ResourceKey = 19
    LocalizationKey = 20
    Variant = 21
    Undefined = 22

    @staticmethod
    def alignment(dt):
        # type: (int) -> int
        if dt in (0, 1, 2, 3):  # Bool, Char, Int8, UInt8
            return 1
        if dt in (4, 5):  # Int16, UInt16
            return 2
        if dt in (6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 20, 21):
            return 4
        if dt in (8, 9, 18, 19):  # Int64, UInt64, TableSetRef, ResourceKey
            return 8
        return 1


class TableInfo:
    """Parsed table header."""
    __slots__ = ('name', 'name_hash', 'schema_offset_pos', 'schema_offset',
                 'data_type', 'row_size', 'row_offset_pos', 'row_offset', 'row_count')

    def __init__(self):
        self.name = None          # type: Optional[str]
        self.name_hash = 0        # type: int
        self.schema_offset_pos = 0  # type: int
        self.schema_offset = 0    # type: int
        self.data_type = 0        # type: int
        self.row_size = 0         # type: int
        self.row_offset_pos = 0   # type: int
        self.row_offset = 0       # type: int
        self.row_count = 0        # type: int


class SchemaColumn:
    """Parsed schema column."""
    __slots__ = ('name', 'name_hash', 'data_type', 'flags', 'offset', 'schema_offset')

    def __init__(self):
        self.name = None          # type: Optional[str]
        self.name_hash = 0        # type: int
        self.data_type = 0        # type: int
        self.flags = 0            # type: int
        self.offset = 0           # type: int
        self.schema_offset = 0    # type: int


class Schema:
    """Parsed schema."""
    __slots__ = ('name', 'name_hash', 'schema_hash', 'schema_size',
                 'column_offset_pos', 'column_offset', 'num_columns',
                 'columns', 'name_offset_pos')

    def __init__(self):
        self.name = None             # type: Optional[str]
        self.name_hash = 0           # type: int
        self.schema_hash = 0         # type: int
        self.schema_size = 0         # type: int
        self.column_offset_pos = 0   # type: int
        self.column_offset = 0       # type: int
        self.num_columns = 0         # type: int
        self.columns = []            # type: List[SchemaColumn]
        self.name_offset_pos = 0     # type: int


def _read_string_at(decoder, offset):
    # type: (BinaryDecoder, int) -> Optional[str]
    """Read a null-terminated string at an absolute offset."""
    if offset == RELOFFSET_NULL:
        return None
    saved = decoder.tell()
    decoder.seek(offset)
    s = decoder.string()
    decoder.seek(saved)
    return s


def _seek_to_alignment(decoder, mask):
    # type: (BinaryDecoder, int) -> None
    pos = decoder.tell()
    pad = -pos & mask
    decoder.seek(pos + pad)


def _read_data_type(decoder, type_code):
    # type: (BinaryDecoder, int) -> object
    """Read a single data field based on its type code."""
    if type_code == DataType.Boolean:
        return decoder.uint8()
    elif type_code == DataType.UInt8:
        return decoder.uint8()
    elif type_code == DataType.Character:
        return chr(decoder.uint8())
    elif type_code == DataType.Int8:
        return decoder.uint8()
    elif type_code == DataType.Int16:
        return decoder.int16()
    elif type_code == DataType.UInt16:
        return decoder.uint16()
    elif type_code == DataType.Int32:
        return decoder.int32()
    elif type_code == DataType.UInt32:
        return decoder.uint32()
    elif type_code == DataType.Int64:
        return decoder.uint64()
    elif type_code == DataType.UInt64:
        return decoder.uint64()
    elif type_code == DataType.Float:
        return decoder.float32()
    elif type_code == DataType.String:
        return {'startof_mDataOffset': decoder.tell(), 'mDataOffset': decoder.int32()}
    elif type_code == DataType.HashedString:
        pos = decoder.tell()
        return {'startof_mDataOffset': pos, 'mDataOffset': decoder.int32(), 'mHash': decoder.uint32()}
    elif type_code == DataType.Object:
        return {'startof_mDataOffset': decoder.tell(), 'mDataOffset': decoder.int32()}
    elif type_code == DataType.Vector:
        pos = decoder.tell()
        return {'startof_mDataOffset': pos, 'mDataOffset': decoder.int32(), 'mCount': decoder.uint32()}
    elif type_code == DataType.Float2:
        return (decoder.float32(), decoder.float32())
    elif type_code == DataType.Float3:
        return (decoder.float32(), decoder.float32(), decoder.float32())
    elif type_code == DataType.Float4:
        return (decoder.float32(), decoder.float32(), decoder.float32(), decoder.float32())
    elif type_code == DataType.TableSetReference:
        return decoder.uint64()
    elif type_code == DataType.ResourceKey:
        return {'instance': decoder.uint64(), 'type': decoder.uint32(), 'group': decoder.uint32()}
    elif type_code == DataType.LocalizationKey:
        return decoder.uint32()
    elif type_code == DataType.Variant:
        pos = decoder.tell()
        return {'startof_mDataOffset': pos, 'mDataOffset': decoder.int32(), 'mTypeHash': decoder.uint32()}
    else:
        raise ValueError("Unknown type code: {}".format(type_code))


def parse_binary_data(data):
    # type: (bytes) -> Tuple[List[TableInfo], List[Schema], List[list], int]
    """Parse the binary DATA format header, tables, schemas, and row data.

    Returns (tables, schemas, table_data, version).
    table_data[i] is a list of row dicts (if schema) or raw values (if no schema).
    """
    decoder = BinaryDecoder(data)

    # Header
    magic = decoder.chars_utf8(4)
    if magic != "DATA":
        raise ValueError("Not a DATA file (got {!r})".format(magic))

    version = decoder.uint32()
    if version < 0x100 or version > 0x101:
        raise ValueError("Unknown DATA version: 0x{:X}".format(version))

    # Table header offset (relative) and count
    table_header_pos = decoder.tell()
    table_header_offset = decoder.int32()
    num_tables = decoder.int32()

    # Schema offset (relative) and count
    schema_pos = decoder.tell()
    schema_offset = decoder.int32()
    num_schemas = decoder.int32()

    # Unused field (version 0x101+)
    if version >= 0x101:
        _unused = decoder.uint32()

    # Read table headers
    decoder.seek(table_header_pos + table_header_offset)
    tables = []  # type: List[TableInfo]
    for _ in range(num_tables):
        t = TableInfo()
        name_offset_pos = decoder.tell()
        name_offset = decoder.int32()
        t.name_hash = decoder.uint32()
        t.name = _read_string_at(decoder, name_offset_pos + name_offset) if name_offset != RELOFFSET_NULL else None
        t.schema_offset_pos = decoder.tell()
        t.schema_offset = decoder.int32()
        t.data_type = decoder.uint32()
        t.row_size = decoder.uint32()
        t.row_offset_pos = decoder.tell()
        t.row_offset = decoder.int32()
        t.row_count = decoder.uint32()
        tables.append(t)

    row_data_start = decoder.tell()

    # Read schemas
    decoder.seek(schema_pos + schema_offset)
    schemas = []  # type: List[Schema]
    last_column_end = 0
    for _ in range(num_schemas):
        s = Schema()
        s.name_offset_pos = decoder.tell()
        name_offset = decoder.int32()
        s.name_hash = decoder.uint32()
        s.name = _read_string_at(decoder, s.name_offset_pos + name_offset) if name_offset != RELOFFSET_NULL else None
        s.schema_hash = decoder.uint32()
        s.schema_size = decoder.uint32()
        s.column_offset_pos = decoder.tell()
        s.column_offset = decoder.int32()
        s.num_columns = decoder.uint32()
        schema_end = decoder.tell()

        # Read columns
        decoder.seek(s.column_offset_pos + s.column_offset)
        s.columns = []
        for _ in range(s.num_columns):
            col = SchemaColumn()
            col_name_pos = decoder.tell()
            col_name_offset = decoder.int32()
            col.name_hash = decoder.uint32()
            col.name = _read_string_at(decoder, col_name_pos + col_name_offset) if col_name_offset != RELOFFSET_NULL else None
            col.data_type = decoder.uint16()
            col.flags = decoder.uint16()
            col.offset = decoder.uint32()
            col.schema_offset = decoder.int32()
            s.columns.append(col)
        s.columns.sort(key=lambda c: c.offset)
        last_column_end = decoder.tell()
        decoder.seek(schema_end)
        schemas.append(s)

    # Read row data for each table
    decoder.seek(row_data_start)

    def get_schema_index(offset, row_size=0):
        # type: (int, int) -> int
        # Primary: match by absolute offset to schema header position
        for idx, sch in enumerate(schemas):
            if offset == sch.name_offset_pos:
                return idx
        # Fallback: some packages store schema offsets that don't match header
        # positions directly. Match by schema_size == row_size instead.
        if row_size > 0:
            for idx, sch in enumerate(schemas):
                if sch.schema_size == row_size:
                    return idx
        raise ValueError("Unknown schema at offset {}".format(offset))

    table_data = []  # type: List[list]
    for i in range(num_tables):
        _seek_to_alignment(decoder, 15)
        # Combined tuning doesn't need row-size alignment
        tbl = tables[i]
        rows = []

        for _ in range(tbl.row_count):
            if tbl.schema_offset == RELOFFSET_NULL:
                # No schema — just read raw values
                rows.append(_read_data_type(decoder, tbl.data_type))
                alignment = DataType.alignment(tbl.data_type)
                _seek_to_alignment(decoder, alignment - 1)
            else:
                # Has schema — read structured row
                si = get_schema_index(tbl.schema_offset_pos + tbl.schema_offset, tbl.row_size)
                schema = schemas[si]
                row_start = decoder.tell()
                row = {}
                for col in schema.columns:
                    decoder.seek(row_start + col.offset)
                    row[col.name] = _read_data_type(decoder, col.data_type)
                decoder.seek(row_start + schema.schema_size)
                rows.append(row)
                _seek_to_alignment(decoder, 0)  # alignment 1 minimum

        table_data.append(rows)
        _seek_to_alignment(decoder, 15)

    return tables, schemas, table_data, version


def _get_position(ref):
    # type: (dict) -> int
    """Resolve a DataOffsetObject to absolute position."""
    offset = ref['mDataOffset']
    if offset == RELOFFSET_NULL:
        return RELOFFSET_NULL
    return ref['startof_mDataOffset'] + offset


def _is_null(ref):
    # type: (dict) -> bool
    return ref['mDataOffset'] == RELOFFSET_NULL


def decode_combined_tuning(data):
    # type: (bytes) -> str
    """Decode binary DATA combined tuning to XML string.

    Args:
        data: Raw decompressed CombinedTuning resource bytes (starts with "DATA").

    Returns:
        XML string equivalent to what the XML-format CombinedTuning would contain.
    """
    tables, schemas, table_data, version = parse_binary_data(data)
    decoder = BinaryDecoder(data)

    if len(tables) < 7:
        raise ValueError("CombinedTuning DATA needs >= 7 tables, got {}".format(len(tables)))

    # Table assignments (per S4TK)
    meta_rows = table_data[0]       # PackedXmlDocument
    node_rows = table_data[1]       # PackedXmlNode
    attr_rows = table_data[2]       # PackedXmlAttributes
    node_refs = table_data[3]       # DataOffsetObject[]
    attr_refs = table_data[4]       # DataOffsetObject[]
    string_refs = table_data[5]     # DataOffsetObject[]
    # table_data[6] = character data (strings read via decoder)

    if not meta_rows:
        raise ValueError("Empty metadata table in CombinedTuning DATA")

    meta = meta_rows[0]

    # Compute table data start offsets (aligned to 16 bytes)
    table_offsets = []  # type: List[int]
    for tbl in tables:
        pos = tbl.row_offset_pos + tbl.row_offset
        pad = -pos & 15
        table_offsets.append(pos + pad)

    first_element_pos = _get_position(meta['first_element'])

    def row_index_at(position, table_index):
        # type: (int, int) -> int
        table_start = table_offsets[table_index]
        return (position - table_start) // tables[table_index].row_size

    def get_text(text_row):
        # type: (int) -> str
        text_ref = string_refs[text_row]
        pos = _get_position(text_ref)
        saved = decoder.tell()
        decoder.seek(pos)
        s = decoder.string()
        decoder.seek(saved)
        return s

    def _escape_xml(s):
        # type: (str) -> str
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def read_attributes(first_attr_pos):
        # type: (int) -> List[Tuple[str, str]]
        attrs = []  # type: List[Tuple[str, str]]
        idx = row_index_at(first_attr_pos, 4)
        while idx < len(attr_refs):
            ref = attr_refs[idx]
            if _is_null(ref):
                break
            attr_pos = _get_position(ref)
            attr_row_idx = row_index_at(attr_pos, 2)
            attr_row = attr_rows[attr_row_idx]
            name = get_text(attr_row['name'])
            value = get_text(attr_row['value'])
            attrs.append((name, value))
            idx += 1
        return attrs

    def read_children(first_child_pos):
        # type: (int) -> List[str]
        children = []  # type: List[str]
        idx = row_index_at(first_child_pos, 3)
        while idx < len(node_refs):
            ref = node_refs[idx]
            if _is_null(ref):
                break
            child_pos = _get_position(ref)
            children.append(read_node(child_pos))
            idx += 1
        return children

    def read_node(position):
        # type: (int) -> str
        node_idx = row_index_at(position, 1)
        node = node_rows[node_idx]
        text = get_text(node['text'])

        has_attrs = not _is_null(node['attrs'])
        has_children = not _is_null(node['children'])

        if not has_attrs and not has_children:
            if position >= first_element_pos:
                # Empty element
                return "<{} />".format(_escape_xml(text))
            else:
                # Text node
                return _escape_xml(text)

        parts = []  # type: List[str]
        parts.append("<{}".format(text))

        if has_attrs:
            attrs = read_attributes(_get_position(node['attrs']))
            for name, value in attrs:
                parts.append(' {}="{}"'.format(name, _escape_xml(value)))

        if has_children:
            parts.append(">")
            children = read_children(_get_position(node['children']))
            parts.extend(children)
            parts.append("</{}>".format(text))
        else:
            parts.append(" />")

        return "".join(parts)

    top_pos = _get_position(meta['top_element'])
    xml_content = read_node(top_pos)
    return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_content


def is_binary_combined_tuning(data):
    # type: (bytes) -> bool
    """Check if data is binary DATA format CombinedTuning."""
    return len(data) >= 4 and data[:4] == b'DATA'
