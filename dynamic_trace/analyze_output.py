#!/usr/bin/env python3
"""
Script for analyzing output.json file
Statistics on version count and installable version count for each package

Usage:
    python analyze_output.py <compatibility_file_path>
"""

import argparse
import json
import subprocess
import sys
from typing import Dict, List, Tuple
import requests


def get_package_versions(package_name: str) -> List[str]:
    """
    Fetch all available versions of a package from PyPI

    Args:
        package_name: Package name (e.g. 'numpy')

    Returns:
        List of version strings
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        versions = list(data.get('releases', {}).keys())
        return versions
    except Exception as e:
        print(f"Error fetching versions for {package_name}: {e}", file=sys.stderr)
        return []


def install_package(package_name: str, version: str) -> Tuple[bool, str]:
    """
    Try to install a specific version of a package (test only, not actually installed to current environment)

    Args:
        package_name: Package name
        version: Version string

    Returns:
        Tuple of (whether installable, error message)
    """
    try:
        package_spec = f"{package_name}=={version}"
        # Use --dry-run to test if can be installed, without actually installing
        # Use pip download to check if package exists
        result = subprocess.run(
            ['pip', 'download', '--no-deps', '--dry-run', package_spec],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, f"Cannot download {package_spec}: {result.stderr}"

        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"Timeout installing {package_name}=={version}"
    except Exception as e:
        return False, f"Error installing package: {str(e)}"


def collect_all_packages_recursive(data: Dict, depth: int = 0) -> Tuple[set, set]:
    """
    Recursively collect package names at all levels

    Args:
        data: JSON data structure
        depth: Current recursion depth (0 for top-level package name, 1 for version, 2 for next-level package name)

    Returns:
        Tuple[Set of all package names, Set of package names with version=ALL (contains all packages, deduplicated)]
    """
    packages = set()
    all_version_packages = set()

    if not isinstance(data, dict):
        return packages, all_version_packages

    for key, value in data.items():
        # Even-numbered levels (0, 2, 4...) are package names
        if depth % 2 == 0:
            if "ALL" in value.keys():
                # If contains ALL version, add to all_version_packages
                all_version_packages.add(key)
            else:
                # Regular package
                packages.add(key)

            # Add all packages (with or without ALL version) to all_version_packages for deduplicated statistics
            all_version_packages.add(key)

        # Recursively process next level
        if isinstance(value, dict):
            sub_packages, sub_all_packages = collect_all_packages_recursive(value, depth + 1)
            packages.update(sub_packages)
            all_version_packages.update(sub_all_packages)

    return packages, all_version_packages


def analyze_output_file(file_path: str) -> Dict:
    """
    Analyze output.json file, recursively analyze packages at all levels

    Args:
        file_path: Path to output.json file

    Returns:
        Dictionary containing analysis results
    """
    print(f"Reading file: {file_path}")

    with open(file_path, 'r') as f:
        data = json.load(f)

    # Recursively collect all package names
    print(f"\nRecursively collecting all package names...")
    all_packages, all_version_packages = collect_all_packages_recursive(data, depth=0)
    all_packages = sorted(all_packages)  # Sort for easier viewing
    all_version_packages = sorted(all_version_packages)  # Sort for easier viewing

    print(f"Found {len(all_packages)} different packages (only packages without ALL version)")
    print(f"Found {len(all_version_packages)} packages (contains all packages, deduplicated)")
    print(f"Package list: {', '.join(list(all_packages)[:10])}..." if len(all_packages) > 10 else f"Package list: {', '.join(all_packages)}")
    print(f"All package list (deduplicated): {', '.join(list(all_version_packages)[:10])}..." if len(all_version_packages) > 10 else f"All package list (deduplicated): {', '.join(all_version_packages)}")

    results = {
        'total_packages': len(all_packages),
        'total_all_version_packages': len(all_version_packages),
        'packages': {},
        'all_version_packages': {},
        'all_package_names': list(all_packages),
        'all_version_package_names': list(all_version_packages)
    }

    print(f"\nStarting analysis of each package...\n")

    for package_name in all_packages:
        print(f"{'='*80}")
        print(f"Analyzing package: {package_name}")
        print(f"{'='*80}")

        # Fetch all available versions from PyPI
        print(f"  Fetching available versions from PyPI...")
        pypi_versions = get_package_versions(package_name)

        if pypi_versions:
            print(f"  PyPI has {len(pypi_versions)} versions")
            installable_count = len(pypi_versions)

            results['packages'][package_name] = {
                'pypi_versions_count': installable_count,
                'pypi_versions': pypi_versions[:10],  # Only save first 10 versions to save space
                'exists_on_pypi': True
            }

            print(f"  ✓ Package exists on PyPI")
        else:
            print(f"  ✗ Package does not exist on PyPI")
            results['packages'][package_name] = {
                'pypi_versions_count': 0,
                'pypi_versions': [],
                'exists_on_pypi': False
            }

        print()

    # Analyze all packages (includes ALL version and non-ALL version, deduplicated)
    print(f"\nStarting analysis of all packages (includes ALL version and non-ALL version, deduplicated)...\n")

    for package_name in all_version_packages:
        print(f"{'='*80}")
        print(f"Analyzing package: {package_name}")
        print(f"{'='*80}")

        # Fetch all available versions from PyPI
        print(f"  Fetching available versions from PyPI...")
        pypi_versions = get_package_versions(package_name)

        if pypi_versions:
            print(f"  PyPI has {len(pypi_versions)} versions")
            installable_count = len(pypi_versions)

            results['all_version_packages'][package_name] = {
                'pypi_versions_count': installable_count,
                'pypi_versions': pypi_versions[:10],  # Only save first 10 versions to save space
                'exists_on_pypi': True
            }

            print(f"  ✓ Package exists on PyPI")
        else:
            print(f"  ✗ Package does not exist on PyPI")
            results['all_version_packages'][package_name] = {
                'pypi_versions_count': 0,
                'pypi_versions': [],
                'exists_on_pypi': False
            }

        print()

    return results


def print_summary(results: Dict):
    """
    Print summary statistics

    Args:
        results: Analysis results dictionary
    """
    print(f"\n{'='*80}")
    print(f"Summary Statistics")
    print(f"{'='*80}\n")

    print(f"Regular package count (only packages without ALL version): {results['total_packages']}")
    print(f"All package count (contains all packages, deduplicated): {results['total_all_version_packages']}\n")

    # Statistics for regular packages
    packages_on_pypi = 0
    packages_not_on_pypi = 0
    total_pypi_versions = 0

    print(f"=== Regular Package Statistics ===\n")
    print(f"{'Package Name':<35} {'PyPI Status':<15} {'PyPI Version Count':<15}")
    print(f"{'-'*80}")

    for package_name, stats in sorted(results['packages'].items()):
        status = "✓ Exists" if stats['exists_on_pypi'] else "✗ Not exists"
        version_count = stats['pypi_versions_count']

        if stats['exists_on_pypi']:
            packages_on_pypi += 1
            total_pypi_versions += version_count
        else:
            packages_not_on_pypi += 1

        print(f"{package_name:<35} {status:<15} {version_count:<15}")

    print(f"{'-'*80}")
    total_packages_count = results['total_packages']
    pypi_rate = f"{(packages_on_pypi/total_packages_count*100):.2f}%" if total_packages_count > 0 else "0%"
    package_ratio = f"{packages_on_pypi}/{total_packages_count}"
    print(f"{'Total':<35} {package_ratio:<15} {total_pypi_versions:<15}")
    print(f"\nPackages existing on PyPI: {packages_on_pypi}")
    print(f"Packages not existing on PyPI: {packages_not_on_pypi}")
    print(f"PyPI existence rate: {pypi_rate}")

    # Statistics for packages with ALL version
    all_packages_on_pypi = 0
    all_packages_not_on_pypi = 0
    all_total_pypi_versions = 0

    print(f"\n{'='*80}")
    print(f"=== All Package Statistics (includes ALL version and non-ALL version, deduplicated) ===\n")
    print(f"{'Package Name':<35} {'PyPI Status':<15} {'PyPI Version Count':<15}")
    print(f"{'-'*80}")

    for package_name, stats in sorted(results['all_version_packages'].items()):
        status = "✓ Exists" if stats['exists_on_pypi'] else "✗ Not exists"
        version_count = stats['pypi_versions_count']

        if stats['exists_on_pypi']:
            all_packages_on_pypi += 1
            all_total_pypi_versions += version_count
        else:
            all_packages_not_on_pypi += 1

        print(f"{package_name:<35} {status:<15} {version_count:<15}")

    print(f"{'-'*80}")
    total_all_packages_count = results['total_all_version_packages']
    all_pypi_rate = f"{(all_packages_on_pypi/total_all_packages_count*100):.2f}%" if total_all_packages_count > 0 else "0%"
    all_package_ratio = f"{all_packages_on_pypi}/{total_all_packages_count}"
    print(f"{'Total':<35} {all_package_ratio:<15} {all_total_pypi_versions:<15}")
    print(f"\nPackages existing on PyPI: {all_packages_on_pypi}")
    print(f"Packages not existing on PyPI: {all_packages_not_on_pypi}")
    print(f"PyPI existence rate: {all_pypi_rate}")
    print(f"\n{'='*80}\n")


def save_results(results: Dict, output_file: str = "analysis_results.json"):
    """
    Save analysis results to JSON file

    Args:
        results: Analysis results dictionary
        output_file: Output file path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Analysis results saved to: {output_file}")


def main():
    # Create command line argument parser
    parser = argparse.ArgumentParser(
        description='Analyze compatibility.json file, count versions and installable versions for each package'
    )
    parser.add_argument(
        'compatibility_file',
        help='Path to compatibility.json file'
    )
    parser.add_argument(
        '-o', '--output',
        default='analysis_results.json',
        help='Output file path (default: analysis_results.json)'
    )

    # Parse command line arguments
    args = parser.parse_args()

    input_file = args.compatibility_file
    output_file = args.output

    try:
        # Analyze file
        results = analyze_output_file(input_file)

        # Print summary
        print_summary(results)

        # Save results
        save_results(results, output_file)

    except FileNotFoundError:
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: JSON parsing failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
