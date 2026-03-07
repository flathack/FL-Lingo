"""CLI entry point for validating Freelancer resource access."""

from __future__ import annotations

import argparse
from pathlib import Path

from .catalog import CatalogLoader, pair_catalogs
from .exporters import export_catalog_json
from .models import ResourceKind
from .stats import summarize_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flatlas-translator",
        description="Inspect Freelancer resource DLLs for FLAtlas Translator.",
    )
    parser.add_argument(
        "install_dir",
        type=Path,
        help="Path to the Freelancer installation root.",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Print discovered DLLs and string counts.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=3,
        help="How many sample strings to print per DLL when --dump is used.",
    )
    parser.add_argument(
        "--include-infocards",
        action="store_true",
        help="Also inspect RT_HTML resources used for infocards.",
    )
    parser.add_argument(
        "--compare-dir",
        type=Path,
        help="Optional second Freelancer installation to compare by DLL name and entry counts.",
    )
    parser.add_argument(
        "--paired-only",
        action="store_true",
        help="When comparing, only print units that have a matching target entry.",
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        help="Write the loaded catalog or paired comparison catalog to a JSON file.",
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="When exporting a paired catalog, include only entries whose target text differs.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    loader = CatalogLoader()
    catalog = loader.load_catalog(args.install_dir, include_infocards=args.include_infocards)
    dll_names = sorted({unit.source.dll_name for unit in catalog.units})
    print(f"Freelancer.ini: {catalog.freelancer_ini}")
    print(f"Discovered resource DLLs: {len(dll_names)}")

    if not args.dump:
        if args.compare_dir:
            paired_catalog = _print_compare_summary(
                catalog,
                args.compare_dir,
                include_infocards=args.include_infocards,
                paired_only=args.paired_only,
            )
            if args.export_json:
                output = export_catalog_json(
                    paired_catalog,
                    args.export_json,
                    changed_only=args.changed_only,
                )
                print(f"Exported JSON: {output}")
        elif args.export_json:
            output = export_catalog_json(catalog, args.export_json)
            print(f"Exported JSON: {output}")
        return 0

    if not loader._string_reader.available:
        print("pefile is not installed, cannot inspect DLL resources.")
        return 1

    sample_limit = max(0, int(args.sample_limit))
    for dll_name in dll_names:
        dll_units = catalog.by_dll(dll_name)
        string_units = [unit for unit in dll_units if unit.kind == ResourceKind.STRING]
        infocard_units = [unit for unit in dll_units if unit.kind == ResourceKind.INFOCARD]
        dll_path = dll_units[0].source.dll_path if dll_units else Path(dll_name)
        details = f"{len(string_units)} strings"
        if args.include_infocards:
            details += f", {len(infocard_units)} infocards"
        print(f"- {dll_name} -> {dll_path} ({details})")
        if sample_limit <= 0:
            continue
        for unit in string_units[:sample_limit]:
            preview = unit.source_text.replace("\n", " ").strip()
            print(f"  [{unit.source.local_id}] {preview[:80]}")
        if args.include_infocards:
            for unit in infocard_units[:sample_limit]:
                preview = " ".join(unit.source_text.split())
                print(f"  <html:{unit.source.local_id}> {preview[:80]}")

    if args.compare_dir:
        paired_catalog = _print_compare_summary(
            catalog,
            args.compare_dir,
            include_infocards=args.include_infocards,
            paired_only=args.paired_only,
        )
        if args.export_json:
            output = export_catalog_json(
                paired_catalog,
                args.export_json,
                changed_only=args.changed_only,
            )
            print()
            print(f"Exported JSON: {output}")
    elif args.export_json:
        output = export_catalog_json(catalog, args.export_json)
        print()
        print(f"Exported JSON: {output}")

    return 0


def _print_compare_summary(
    source_catalog,
    compare_dir: Path,
    *,
    include_infocards: bool,
    paired_only: bool,
) :
    print()
    print(f"Comparison against: {compare_dir}")
    loader = CatalogLoader()
    target_catalog = loader.load_catalog(compare_dir, include_infocards=include_infocards)
    paired_catalog = pair_catalogs(source_catalog, target_catalog)

    for dll_name in sorted({unit.source.dll_name for unit in paired_catalog.units}):
        dll_units = paired_catalog.by_dll(dll_name)
        string_units = [unit for unit in dll_units if unit.kind == ResourceKind.STRING]
        infocard_units = [unit for unit in dll_units if unit.kind == ResourceKind.INFOCARD]
        matched_strings = sum(1 for unit in string_units if unit.target is not None)
        matched_infocards = sum(1 for unit in infocard_units if unit.target is not None)
        changed_strings = sum(1 for unit in string_units if unit.is_changed)
        changed_infocards = sum(1 for unit in infocard_units if unit.is_changed)
        if paired_only and matched_strings == 0 and matched_infocards == 0:
            continue
        message = (
            f"- {dll_name}: strings matched {matched_strings}/{len(string_units)}, "
            f"changed {changed_strings}"
        )
        if include_infocards:
            message += (
                f", infocards matched {matched_infocards}/{len(infocard_units)}, "
                f"changed {changed_infocards}"
            )
        print(message)
    print()
    string_stats = summarize_catalog(paired_catalog, ResourceKind.STRING)
    print(
        f"Totals strings: matched {string_stats.matched}/{string_stats.total}, "
        f"changed {string_stats.changed}"
    )
    if include_infocards:
        infocard_stats = summarize_catalog(paired_catalog, ResourceKind.INFOCARD)
        print(
            f"Totals infocards: matched {infocard_stats.matched}/{infocard_stats.total}, "
            f"changed {infocard_stats.changed}"
        )
    return paired_catalog



if __name__ == "__main__":
    raise SystemExit(main())
