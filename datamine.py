import argparse
import os

from datamining.package_reader import PackageReader
from datamining.tuning_parser import TuningParser


def cmd_extract(args):
    """Extract tuning XML from a .package file."""
    reader = PackageReader(args.package)
    reader.read()

    tuning_entries = reader.extract_tuning_entries()
    print(f"Found {len(tuning_entries)} tuning entries in {args.package}")

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    for entry in tuning_entries:
        xml_str = reader.extract_tuning_xml(entry)
        tuning = TuningParser.parse(xml_str)
        if args.output:
            filename = f"{tuning.name or entry.key.instance:016X}.xml"
            with open(os.path.join(args.output, filename), "w", encoding="utf-8") as f:
                f.write(xml_str)
        else:
            print(f"  {entry.key} — {tuning.tuning_type}: {tuning.name}")


def cmd_info(args):
    """Show information about a .package file."""
    reader = PackageReader(args.package)
    reader.read()

    print(f"Package: {args.package}")
    print(f"  Version: {reader.header.major_version}.{reader.header.minor_version}")
    print(f"  Entries: {reader.header.index_entry_count}")

    # Count by type
    type_counts: dict[int, int] = {}
    for entry in reader.entries:
        type_counts[entry.key.type_id] = type_counts.get(entry.key.type_id, 0) + 1

    print(f"  Resource types:")
    for type_id, count in sorted(type_counts.items()):
        label = "Tuning XML" if type_id == 0x03B33DDF else ""
        print(f"    0x{type_id:08X}: {count} entries{' (' + label + ')' if label else ''}")


def main():
    parser = argparse.ArgumentParser(
        description="Sims 4 data mining tools — extract and parse .package files"
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
