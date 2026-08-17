#!/usr/bin/env python3
"""
Script to extract package version compatibility information

Usage:
    python extract_version_compatibility.py /path/to/api_log/ [output_file.json]

Features:
1. Extract compatible versions from {package_name}_version_compatibility.json in the first-level directory
2. Extract dependency version relationships recursively for second-level and deeper directories
3. Build nested version compatibility dictionary of arbitrary depth
4. Mark versions as {"incompatible": True} if no compatible combinations are found
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

        compatible_versions = []
        is_incompatible = False

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
    Process compatibility.json files in dependency directories
    Returns: (dependency_package, version_mappings, incompatible_parent_versions, is_totally_incompatible)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dependency_package = extract_package_name(os.path.basename(file_path))
        if not dependency_package:
            return None, {}, set(), False

        version_mappings = defaultdict(list)
        is_totally_incompatible = False

        if 'compatible_version_combinations' in data:
            combinations = data['compatible_version_combinations']
            # If the combinations array is explicitly empty, the dependency is totally incompatible
            if isinstance(combinations, list) and len(combinations) == 0:
                is_totally_incompatible = True
            
            for item in combinations:
                dependency_version = item.get('downstream_version')
                parent_version = item.get('upstream_version')
                if dependency_version and parent_version:
                    version_mappings[parent_version].append(dependency_version)

        incompatible_parent_versions = set()
        if 'incompatible_upstream_versions' in data:
            incompatible_parent_versions = set(data['incompatible_upstream_versions'])

        return dependency_package, dict(version_mappings), incompatible_parent_versions, is_totally_incompatible

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, {}, set(), False


def _build_dependency_tree_recursive(current_dir: Path, current_pkg_name: str, target_parent_version: str) -> Dict[str, Any]:
    """
    Recursive core logic: Find all dependencies for current_pkg_name at target_parent_version in current_dir.
    Returns a dictionary representing the subtree mounted under this node.
    """
    sub_tree = {}
    
    # Only scan the direct children of the current directory, NOT rglob
    if not current_dir.exists() or not current_dir.is_dir():
        return sub_tree

    for file in current_dir.glob('*_compatibility_results.json'):
        if not file.is_file():
            continue
            
        dependency_package, version_mappings, incompatible_parent_versions, is_totally_incompatible = process_dependency_version_compatibility(
            str(file), current_pkg_name
        )
        
        if not dependency_package:
            continue

        # 1. Check for complete incompatibility or specific parent version incompatibility
        if is_totally_incompatible or (target_parent_version in incompatible_parent_versions):
            sub_tree[dependency_package] = {"incompatible": True}
            print(f"        Marked {current_pkg_name} {target_parent_version} as incompatible with {dependency_package}")
            continue

        # 2. Check if there are compatible combinations for this specific parent version
        if target_parent_version in version_mappings:
            dependency_versions = version_mappings[target_parent_version]
            sub_tree[dependency_package] = {}
            
            # Identify the next level log directory (e.g. for package B, look for B_api_log)
            next_log_dir = current_dir / f"{dependency_package}_api_log"
            
            for dep_version in dependency_versions:
                # Recursively dig deeper!
                sub_tree[dependency_package][dep_version] = _build_dependency_tree_recursive(
                    next_log_dir, dependency_package, dep_version
                )
                
    return sub_tree


def build_version_compatibility_tree(root_dir: str) -> Dict[str, Any]:
    """
    Build complete compatibility tree (True Recursive Implementation)
    """
    root_path = Path(root_dir)
    result = {}

    if not root_path.exists():
        print(f"Error: Directory {root_dir} does not exist")
        return result

    # Step 1: Process compatibility.json files in the root directory using glob
    print(f"Scanning root directory: {root_dir}")
    for file in root_path.glob('*_compatibility_results.json'):
        if not file.is_file():
            continue
            
        print(f"  Found root file: {file.name}")
        package_name, compatible_versions, is_incompatible = process_first_level_version_compatibility(str(file))

        if not package_name:
            continue

        if is_incompatible:
            # If compatible is empty, add incompatible marker
            result[package_name] = {"incompatible": True}
            print(f"    Package: {package_name}, marked as incompatible (compatible array is empty)")
        elif compatible_versions:
            # Initialize package version dictionary
            result[package_name] = {}
            print(f"    Package: {package_name}, compatible versions: {compatible_versions}")
            
            # Step 2: Trigger recursive dependency processing for each valid version
            log_dir = root_path / f"{package_name}_api_log"
            for version in compatible_versions:
                result[package_name][version] = _build_dependency_tree_recursive(log_dir, package_name, version)

    return result


def print_tree_stats(tree: Dict[str, Any], indent: int = 0):
    """
    Recursively print statistics for the compatibility tree.
    """
    prefix = "  " * indent
    for package, versions in tree.items():
        if isinstance(versions, dict) and versions.get("incompatible") is True:
            print(f"{prefix}└─ {package}: Marked as incompatible (no compatible versions)")
        else:
            print(f"{prefix}└─ {package}: {len(versions)} compatible versions")
            for version, deps in versions.items():
                if deps:
                    print(f"{prefix}    └─ {version}: {len(deps)} dependency packages")
                    print_tree_stats(deps, indent + 3)


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
    print_tree_stats(compatibility_tree)


if __name__ == '__main__':
    main()