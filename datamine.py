import argparse
import json
import os
import sys

from util.datamining.package_reader import PackageReader
from util.datamining.resource_types import (
    RESOURCE_TYPE_LABELS,
    COMBINED_TUNING_TYPE_ID,
    STRING_TABLE_TYPE_ID,
    DDS_TYPE_ID,
    PNG_TYPE_ID,
    resolve_type_filter,
)
from util.datamining.tuning_parser import TuningParser


def cmd_extract(args):
    """Extract tuning XML from a .package file."""
    reader = PackageReader(args.package)
    reader.read()

    tuning_entries = reader.extract_tuning_entries()
    print("Found {} tuning entries in {}".format(len(tuning_entries), args.package))

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    for entry in tuning_entries:
        xml_str = reader.extract_tuning_xml(entry)
        tuning = TuningParser.parse(xml_str)
        if args.output:
            filename = "{}.xml".format(tuning.name or "{:016X}".format(entry.key.instance))
            with open(os.path.join(args.output, filename), "w", encoding="utf-8") as f:
                f.write(xml_str)
        else:
            print("  {} -- {}: {}".format(entry.key, tuning.tuning_type, tuning.name))


def cmd_info(args):
    """Show information about a .package file."""
    reader = PackageReader(args.package)
    reader.read()

    print("Package: {}".format(args.package))
    print("  Version: {}.{}".format(reader.header.major_version, reader.header.minor_version))
    print("  Entries: {}".format(reader.header.index_entry_count))

    # Count by type
    type_counts = {}
    for entry in reader.entries:
        type_counts[entry.key.type_id] = type_counts.get(entry.key.type_id, 0) + 1

    print("  Resource types:")
    for type_id, count in sorted(type_counts.items()):
        label = RESOURCE_TYPE_LABELS.get(type_id, "")
        suffix = " ({})".format(label) if label else ""
        print("    0x{:08X}: {} entries{}".format(type_id, count, suffix))


def cmd_extract_all(args):
    """Extract resources from all game packages.

    Dispatch modes:
    - No --types:           Extract tuning, strings, and images (useful defaults)
    - --types all:          Extract everything (smart processing for known types,
                            raw .bin for unknown types)
    - --types DDS STBL ...: Extract only the specified types (smart processing
                            where available, raw .bin otherwise)
    """
    from util.datamining.tuning_splitter import split_combined_tuning
    from util.datamining.string_table import StringTableReader
    from util.datamining.image_decoder import decode_image_to_png

    game_folder = args.game_folder
    output_dir = args.output

    # Resolve type filters
    extract_everything = False
    type_filter = None  # None = defaults (tuning + strings + images)

    if args.types:
        # Check for "all" keyword
        normalized = [t.strip().lower() for t in args.types]
        if "all" in normalized:
            extract_everything = True
        else:
            type_filter = set()
            for t in args.types:
                type_filter.add(resolve_type_filter(t))

    # Known types with smart processing
    _SMART_TYPES = {COMBINED_TUNING_TYPE_ID, STRING_TABLE_TYPE_ID, DDS_TYPE_ID, PNG_TYPE_ID}

    def _should_extract(type_id):
        """Check if a given type ID should be extracted."""
        if extract_everything:
            return True
        if type_filter is not None:
            return type_id in type_filter
        # Default: tuning + strings + images
        return type_id in _SMART_TYPES

    os.makedirs(output_dir, exist_ok=True)

    # --- Tuning XML (smart processing) ---
    if _should_extract(COMBINED_TUNING_TYPE_ID):
        _extract_tuning(game_folder, output_dir, split_combined_tuning)

    # --- String Tables (smart processing) ---
    if _should_extract(STRING_TABLE_TYPE_ID):
        _extract_strings(game_folder, output_dir, StringTableReader)

    # --- Images (smart processing) ---
    if _should_extract(DDS_TYPE_ID) or _should_extract(PNG_TYPE_ID):
        img_types = set()
        if _should_extract(DDS_TYPE_ID):
            img_types.add(DDS_TYPE_ID)
        if _should_extract(PNG_TYPE_ID):
            img_types.add(PNG_TYPE_ID)
        _extract_images(game_folder, output_dir, img_types, decode_image_to_png)

    # --- Raw extraction for non-smart types ---
    # Collect type IDs that need raw extraction
    if extract_everything:
        # Extract all types that don't have smart handlers
        _extract_raw(game_folder, output_dir, exclude_types=_SMART_TYPES)
    elif type_filter is not None:
        # Extract requested types that don't have smart handlers
        raw_types = type_filter - _SMART_TYPES
        if raw_types:
            _extract_raw(game_folder, output_dir, include_types=raw_types)


def _extract_tuning(game_folder, output_dir, split_combined_tuning):
    """Extract CombinedTuning into individual XML files."""
    from util.datamining.package_discovery import discover_simulation_packages

    xml_dir = os.path.join(output_dir, "xml")
    modules_dir = os.path.join(xml_dir, "_modules")
    os.makedirs(modules_dir, exist_ok=True)

    sim_packages = discover_simulation_packages(game_folder)
    print("Extracting tuning from {} simulation packages...".format(len(sim_packages)))

    seen_instances = {}  # instance_id -> (cls, name) for dedup tracking
    total_entries = 0
    total_modules = 0

    for pkg_path, rel_path in sim_packages:
        reader = PackageReader(pkg_path)
        reader.read()

        ct_entries = reader.extract_combined_tuning_entries()
        if not ct_entries:
            continue

        for ct_entry in ct_entries:
            try:
                raw_data = reader.extract_resource(ct_entry)
                entries = split_combined_tuning(raw_data)
            except Exception as e:
                print("  Warning: failed to split {}: {}".format(rel_path, e))
                continue

            for entry in entries:
                if entry.element_tag == "I":
                    # Deduplicate by instance ID (delta overrides full)
                    seen_instances[entry.instance_id] = (entry.cls, entry.name)

                    # Write to xml/{ClassName}/{instance_name}.xml
                    cls_dir = os.path.join(xml_dir, entry.cls) if entry.cls else xml_dir
                    os.makedirs(cls_dir, exist_ok=True)
                    filename = "{}.xml".format(entry.name or entry.instance_id)
                    filepath = os.path.join(cls_dir, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(entry.xml)
                    total_entries += 1

                elif entry.element_tag == "M":
                    # Write to xml/_modules/{module_path}.xml
                    filename = "{}.xml".format(entry.name.replace("/", "."))
                    filepath = os.path.join(modules_dir, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(entry.xml)
                    total_modules += 1

    print("  Tuning: {} entries, {} modules ({} unique instances)".format(
        total_entries, total_modules, len(seen_instances)))


def _extract_strings(game_folder, output_dir, StringTableReader):
    """Extract and merge all string tables into a single JSON file."""
    from util.datamining.package_discovery import discover_string_packages

    string_packages = discover_string_packages(game_folder)
    print("Extracting strings from {} string packages...".format(len(string_packages)))

    merged = {}  # hash -> string
    for pkg_path in string_packages:
        reader = PackageReader(pkg_path)
        reader.read()

        stbl_entries = reader.extract_string_table_entries()
        for entry in stbl_entries:
            try:
                data = reader.extract_resource(entry)
                table = StringTableReader.parse(data)
                merged.update(table.strings)
            except Exception as e:
                print("  Warning: failed to parse STBL in {}: {}".format(pkg_path, e))

    # Write merged strings as JSON
    output_path = os.path.join(output_dir, "strings.json")
    # Convert int keys to hex strings for readability
    string_dict = {}
    for key, value in sorted(merged.items()):
        string_dict["0x{:08X}".format(key)] = value

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(string_dict, f, ensure_ascii=False, indent=2)

    print("  Strings: {} entries".format(len(merged)))


def _extract_images(game_folder, output_dir, image_types, decode_image_to_png):
    """Extract all image resources as PNG files.

    Args:
        image_types: set of type IDs to extract (DDS_TYPE_ID, PNG_TYPE_ID, or both)
    """
    from util.datamining.package_discovery import discover_client_packages

    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    client_packages = discover_client_packages(game_folder)
    print("Extracting images from {} client packages...".format(len(client_packages)))

    seen = set()
    total = 0
    errors = 0

    for pkg_path, rel_path in client_packages:
        reader = PackageReader(pkg_path)
        reader.read()

        for entry in reader.entries:
            if entry.key.type_id not in image_types:
                continue

            # Deduplicate by instance ID (delta overrides full)
            instance_id = entry.key.instance
            seen.add(instance_id)

            try:
                data = reader.extract_resource(entry)
                png_data = decode_image_to_png(data)
                filename = "{:016x}.png".format(instance_id)
                filepath = os.path.join(images_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(png_data)
                total += 1
            except Exception:
                errors += 1

    print("  Images: {} extracted ({} unique instances, {} errors)".format(
        total, len(seen), errors))


def _extract_raw(game_folder, output_dir, include_types=None, exclude_types=None):
    """Extract raw resources as .bin files organized by type ID.

    Args:
        include_types: if set, only extract these type IDs
        exclude_types: if set, skip these type IDs (used with --types all)
    """
    from util.datamining.package_discovery import discover_all_packages

    all_packages = discover_all_packages(game_folder)
    print("Extracting raw resources from {} packages...".format(len(all_packages)))

    total = 0
    type_counts = {}
    for pkg_path, rel_path in all_packages:
        reader = PackageReader(pkg_path)
        reader.read()

        for entry in reader.entries:
            tid = entry.key.type_id
            if include_types is not None and tid not in include_types:
                continue
            if exclude_types is not None and tid in exclude_types:
                continue

            type_dir = os.path.join(output_dir, "{:08X}".format(tid))
            os.makedirs(type_dir, exist_ok=True)

            try:
                data = reader.extract_resource(entry)
                filename = "{:08X}_{:016X}.bin".format(entry.key.group, entry.key.instance)
                filepath = os.path.join(type_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(data)
                total += 1
                type_counts[tid] = type_counts.get(tid, 0) + 1
            except Exception as e:
                print("  Warning: failed to extract {}: {}".format(entry.key, e))

    print("  Raw: {} resources extracted across {} types".format(total, len(type_counts)))


def main():
    parser = argparse.ArgumentParser(
        description="Sims 4 data mining tools -- extract and parse .package files"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract tuning XML from a .package file")
    extract_parser.add_argument("package", help="Path to the .package file")
    extract_parser.add_argument("-o", "--output", help="Output directory for extracted XML files")
    extract_parser.set_defaults(func=cmd_extract)

    # info command
    info_parser = subparsers.add_parser("info", help="Show information about a .package file")
    info_parser.add_argument("package", help="Path to the .package file")
    info_parser.set_defaults(func=cmd_info)

    # extract-all command
    extract_all_parser = subparsers.add_parser(
        "extract-all",
        help="Extract resources from all game packages"
    )
    extract_all_parser.add_argument("game_folder", help="Path to the game installation folder")
    extract_all_parser.add_argument("-o", "--output", required=True,
                                     help="Output directory for extracted resources")
    extract_all_parser.add_argument("--types", nargs="+",
                                     help="Resource types to extract. Use 'all' for everything, "
                                          "or specify hex IDs (0x2F7D0004) or labels "
                                          "(DDS, PNG, STBL, Tuning, CombinedTuning). "
                                          "Default: tuning, strings, and images.")
    extract_all_parser.set_defaults(func=cmd_extract_all)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
