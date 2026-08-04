#!/usr/bin/env python3
"""
Script to extract package version compatibility information

Usage:
    python extract_version_compatibility.py /path/to/api_log/ [output_file.json]

Features:
1. Extract compatible versions from {package_name}_version_compatibility.json in the first-level directory
2. Extract dependency version relationships from {second_package_name}_version_compatibility.json in second-level and deeper directories
3. Build nested version compatibility dictionary
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict


def extract_package_name(filename: str) -> str:
    """
    Extract package name from filename
    Example: keras_compatibility_results.json -> keras
    """
    if filename.endswith('_compatibility_results.json'):
        return filename.replace('_compatibility_results.json', '')
    return None


def process_first_level_version_compatibility(file_path: str) -> tuple:
    """
    Process compatibility.json files in the first-level directory
    Returns: (package_name, compatible_versions_list, is_incompatible)

    If the compatible array is empty, return is_incompatible=True
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        package_name = extract_package_name(os.path.basename(file_path))
        if not package_name:
            return None, [], False

        # Extract all compatible versions
        compatible_versions = []
        is_incompatible = False

        # New format: extract versions directly from 'compatible' array
        if 'compatible' in data and isinstance(data['compatible'], list):
            if len(data['compatible']) == 0:
                # If compatible array is empty, mark as incompatible
                is_incompatible = True
            else:
                for item in data['compatible']:
                    version = item.get('version')
                    if version:
                        compatible_versions.append(version)

        return package_name, compatible_versions, is_incompatible

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, [], False


def process_dependency_version_compatibility(file_path: str, target_package: str) -> tuple:
    """
    Process compatibility.json files in second-level and deeper directories
    Returns: (dependency_package_name, version_mappings, incompatible_parent_versions)

    Note: Naming meaning in the new format:
    - downstream_version: version of the dependency package itself
    - upstream_version: version of the parent package using this dependency
    - incompatible_upstream_versions: incompatible parent package versions

    version_mappings is a dictionary: {parent_version: [dependency_versions]}
    incompatible_parent_versions is a set of incompatible parent package versions
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dependency_package = extract_package_name(os.path.basename(file_path))
        if not dependency_package:
            return None, {}, set()

        # Build version mapping: parent_version -> [dependency_versions]
        # Note: Need to reverse the meaning of downstream/upstream
        version_mappings = defaultdict(list)
        if 'compatible_version_combinations' in data:
            for item in data['compatible_version_combinations']:
                # downstream_version is the dependency package version, upstream_version is the parent package version
                dependency_version = item.get('downstream_version')
                parent_version = item.get('upstream_version')
                if dependency_version and parent_version:
                    version_mappings[parent_version].append(dependency_version)

        # Extract incompatible parent package versions
        incompatible_parent_versions = set()
        if 'incompatible_upstream_versions' in data:
            incompatible_parent_versions = set(data['incompatible_upstream_versions'])

        return dependency_package, dict(version_mappings), incompatible_parent_versions

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, {}, set()


def build_version_compatibility_tree(root_dir: str) -> Dict[str, Any]:
    """
    Build complete compatibility tree
    """
    root_path = Path(root_dir)
    result = {}

    if not root_path.exists():
        print(f"Error: Directory {root_dir} does not exist")
        return result

    # Step 1: Process compatibility.json files in the first-level directory
    print(f"Scanning first-level directory: {root_dir}")
    for file in root_path.glob('*_compatibility_results.json'):
        if file.is_file():
            print(f"  Found first-level file: {file.name}")
            package_name, compatible_versions, is_incompatible = process_first_level_version_compatibility(str(file))

            if package_name:
                if is_incompatible:
                    # If compatible is empty, add incompatible marker
                    result[package_name] = {"incompatible": True}
                    print(f"    Package: {package_name}, marked as incompatible (compatible array is empty)")
                elif compatible_versions:
                    # Initialize package version dictionary
                    result[package_name] = {version: {} for version in compatible_versions}
                    print(f"    Package: {package_name}, compatible versions: {compatible_versions}")

    # Step 2: Recursively process second-level and deeper directories
    for package_name in list(result.keys()):
        # Find corresponding api_log directory
        api_log_dir = root_path / f"{package_name}_api_log"

        if not api_log_dir.exists() or not api_log_dir.is_dir():
            continue

        print(f"\nScanning dependency directory for {package_name}: {api_log_dir}")

        # Recursively find all compatibility.json files
        for file in api_log_dir.rglob('*_compatibility_results.json'):
            if file.is_file():
                print(f"  Found dependency file: {file.relative_to(root_path)}")
                dependency_package, version_mappings, incompatible_parent_versions = process_dependency_version_compatibility(
                    str(file), package_name
                )

                if dependency_package and version_mappings:
                    # Fill dependency information into result dictionary
                    # version_mappings: {parent_version: [dependency_versions]}
                    for parent_version, dependency_versions in version_mappings.items():
                        if parent_version in result[package_name]:
                            if dependency_package not in result[package_name][parent_version]:
                                result[package_name][parent_version][dependency_package] = {}

                            # Add dependency versions
                            for dependency_version in dependency_versions:
                                result[package_name][parent_version][dependency_package][dependency_version] = {}

                            print(f"    {package_name} {parent_version} -> {dependency_package} {dependency_versions}")
                        else:
                            print(f"    Warning: {package_name} version {parent_version} not in compatible version list, skipping")

                    # Add markers for incompatible parent package versions
                    if incompatible_parent_versions:
                        print(f"      Found incompatible {package_name} versions: {incompatible_parent_versions}")
                        for incompatible_version in incompatible_parent_versions:
                            if incompatible_version in result[package_name]:
                                if dependency_package not in result[package_name][incompatible_version]:
                                    result[package_name][incompatible_version][dependency_package] = {}
                                # Add incompatible marker under this parent package version
                                result[package_name][incompatible_version][dependency_package]["incompatible"] = True
                                print(f"        Marked {package_name} {incompatible_version} as incompatible with {dependency_package}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Extract package version compatibility information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_version_compatibility.py /data3/share/jiasheng/LLMMockSystem/pyright/api_log/
    python extract_version_compatibility.py /data3/share/jiasheng/LLMMockSystem/pyright/api_log/ compatibility.json
        """
    )
    parser.add_argument(
        'directory',
        help='Root directory path containing compatibility.json files'
    )
    parser.add_argument(
        'output',
        nargs='?',
        help='Output JSON file path (optional, defaults to standard output)',
        default=None
    )

    args = parser.parse_args()

    # Build compatibility tree
    print(f"Starting to process directory: {args.directory}\n")
    compatibility_tree = build_version_compatibility_tree(args.directory)

    # Output results
    json_output = json.dumps(compatibility_tree, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"\nResults saved to: {args.output}")
    else:
        print("\n" + "=" * 60)
        print("Compatibility tree structure:")
        print("=" * 60)
        print(json_output)

    # Print statistics
    print("\n" + "=" * 60)
    print("Statistics:")
    print("=" * 60)
    for package, versions in compatibility_tree.items():
        # Check if it's an incompatible package
        if isinstance(versions, dict) and "incompatible" in versions and versions["incompatible"] is True:
            print(f"{package}: Marked as incompatible (no compatible versions)")
        else:
            print(f"{package}: {len(versions)} compatible versions")
            for version, deps in versions.items():
                if deps:
                    print(f"  └─ {version}: {len(deps)} dependency packages")
                    for dep_pkg, dep_versions in deps.items():
                        print(f"      └─ {dep_pkg}: {len(dep_versions)} compatible versions")


if __name__ == '__main__':
    main()
