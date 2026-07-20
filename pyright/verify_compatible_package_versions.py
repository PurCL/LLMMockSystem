#!/usr/bin/env python3
"""
Package Version Compatibility Tester
Tests different versions of a package against pyright API checks
"""

import argparse
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import requests


def get_package_versions(package_name: str) -> List[str]:
    """
    Fetch all available versions of a package from PyPI

    Args:
        package_name: Name of the package (e.g., 'keras')

    Returns:
        List of version strings, sorted from oldest to newest
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        versions = list(data.get('releases', {}).keys())
        print(f"Found {len(versions)} versions for {package_name}")
        return versions
    except Exception as e:
        print(f"Error fetching versions for {package_name}: {e}", file=sys.stderr)
        return []


def setup_venv(work_dir: str) -> Tuple[bool, str]:
    """
    Create a fresh virtual environment

    Args:
        work_dir: Directory where to create the venv

    Returns:
        Tuple of (success, error_message)
    """
    try:
        venv_path = os.path.join(work_dir, '.venv')

        # Remove existing .venv
        subprocess.run(
            ['rm', '-rf', venv_path],
            check=True,
            timeout=30
        )

        # Create new venv
        result = subprocess.run(
            ['uv', 'venv', venv_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return False, f"Failed to create venv: {result.stderr}"

        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Timeout while creating venv"
    except Exception as e:
        return False, f"Error creating venv: {str(e)}"


def install_package(package_name: str, version: str, venv_path: str) -> Tuple[bool, str]:
    """
    Install a specific version of a package in the current venv

    Args:
        package_name: Name of the package
        version: Version string
        venv_path: Path to the virtual environment

    Returns:
        Tuple of (success, error_message)
    """
    try:
        package_spec = f"{package_name}=={version}"
        result = subprocess.run(
            ['uv', 'pip', 'install', '--python', venv_path, '--no-deps', package_spec],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            return False, f"Failed to install {package_spec}: {result.stderr}"

        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"Timeout while installing {package_name}=={version}"
    except Exception as e:
        return False, f"Error installing package: {str(e)}"


def run_api_check(script_path: str, python_path: str) -> Tuple[bool, str, str]:
    """
    Run the pyright API check script

    Args:
        script_path: Path to the API check script
        python_path: Path to the Python interpreter in venv

    Returns:
        Tuple of (success, stdout, stderr)
    """
    # Check if script exists
    if not Path(script_path).exists():
        return False, "", f"API check script not found: {script_path}"

    try:
        result = subprocess.run(
            [python_path, script_path],
            capture_output=True,
            text=True,
            timeout=600
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout while running API check"
    except Exception as e:
        return False, "", f"Error running API check: {str(e)}"


def get_supported_api_ids(package_name: str, script_dir: str) -> Tuple[bool, List[int], List[int]]:
    """
    Read the api_check_results_{package_name}.json file to get supported and unsupported API IDs

    Args:
        package_name: Name of the package
        script_dir: Directory where the check script is located

    Returns:
        Tuple of (success, supported_api_ids, unsupported_api_ids)
    """
    result_file = os.path.join(script_dir, f"api_check_results_{package_name}.json")

    if not os.path.exists(result_file):
        return False, [], []

    try:
        with open(result_file, 'r') as f:
            data = json.load(f)

        # Extract passed and failed API IDs from the result file
        passed_api_ids = [int(api_id) for api_id in data.get('passed_api_ids', [])]
        failed_api_ids = [int(api_id) for api_id in data.get('failed_api_ids', [])]

        return True, passed_api_ids, failed_api_ids
    except Exception as e:
        print(f"Error reading API check results: {e}")
        return False, [], []


def load_version_mapping(package_name: str, script_dir: str) -> Dict:
    """
    Load the version mapping file if it exists

    Args:
        package_name: Name of the package
        script_dir: Directory where the check script is located

    Returns:
        Dictionary containing version mapping or empty dict if not found
    """
    mapping_file = os.path.join(script_dir, f"{package_name}_version_mapping.json")

    if not os.path.exists(mapping_file):
        return {}

    try:
        with open(mapping_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading version mapping file: {e}")
        return {}


def test_package_version(package_name: str, version: str, script_path: str, work_dir: str) -> Dict:
    """
    Test a specific version of a package

    Args:
        package_name: Name of the package
        version: Version string
        script_path: Path to the API check script
        work_dir: Working directory for venv

    Returns:
        Dictionary with test results
    """

    result = {
        'version': version,
        'status': 'unknown',
        'venv_setup': False,
        'installation': False,
        'api_check': False,
        'error_message': '',
        'stdout': '',
        'stderr': '',
        'supported_api_ids': [],
        'unsupported_api_ids': [],
        'compatible_with_versions': []  # For dependency packages
    }

    print(f"\n{'='*60}")
    print(f"Testing {package_name} version {version}")
    print(f"{'='*60}")

    # Step 1: Setup venv
    print("Step 1: Setting up virtual environment...")
    success, error = setup_venv(work_dir)
    if not success:
        result['status'] = 'incompatible'
        result['error_message'] = f"Venv setup failed: {error}"
        print(f"✗ {result['error_message']}")
        return result

    result['venv_setup'] = True
    print("✓ Virtual environment created")

    # Step 2: Install package
    venv_path = os.path.join(work_dir, '.venv')
    print(f"Step 2: Installing {package_name}=={version}...")
    success, error = install_package(package_name, version, venv_path)
    if not success:
        result['status'] = 'incompatible'
        result['error_message'] = f"Installation failed: {error}"
        print(f"✗ {result['error_message']}")
        return result

    result['installation'] = True
    print(f"✓ Package installed successfully")

    # Step 3: Run API check
    print("Step 3: Running API check...")
    python_path = os.path.join(venv_path, 'bin', 'python')
    success, stdout, stderr = run_api_check(script_path, python_path)
    result['stdout'] = stdout
    result['stderr'] = stderr

    # Step 4: Get supported API IDs from the result file
    print("Step 4: Analyzing API check results...")
    script_dir = os.path.dirname(script_path)
    success_reading, supported_ids, unsupported_ids = get_supported_api_ids(package_name, script_dir)

    if not success_reading:
        result['status'] = 'incompatible'
        result['error_message'] = f"Failed to read API check results"
        print(f"✗ {result['error_message']}")
        return result

    result['supported_api_ids'] = supported_ids
    result['unsupported_api_ids'] = unsupported_ids
    print(f"✓ Supported API IDs: {supported_ids}")
    print(f"✗ Unsupported API IDs: {unsupported_ids}")

    # Step 5: Check version mapping if exists
    version_mapping = load_version_mapping(package_name, script_dir)

    if not version_mapping:
        # This is from user code, check if there are any unsupported APIs
        print("Step 5: Checking user code compatibility...")
        if unsupported_ids:
            result['status'] = 'incompatible'
            result['error_message'] = f"Version {version} does not support required API IDs: {unsupported_ids}"
            print(f"✗ {result['error_message']}")
        else:
            result['status'] = 'compatible'
            result['api_check'] = True
            print(f"✓ Version {version} is compatible with user code")
    else:
        # This is a dependency package, check compatibility with mapped versions
        print("Step 5: Checking compatibility with dependent package versions...")
        compatible_versions = []
        supported_set = set(supported_ids)

        for target_version, required_api_ids in version_mapping.items():
            required_set = set(required_api_ids)
            # Check if all required APIs are supported
            if required_set.issubset(supported_set):
                compatible_versions.append(target_version)
                print(f"✓ Compatible with version {target_version}")
            else:
                missing_apis = required_set - supported_set
                print(f"✗ Not compatible with version {target_version} (missing API IDs: {missing_apis})")

        result['compatible_with_versions'] = compatible_versions

        if compatible_versions:
            result['status'] = 'compatible'
            result['api_check'] = True
            print(f"✓ Version {version} is compatible with versions: {compatible_versions}")
        else:
            result['status'] = 'incompatible'
            result['error_message'] = f"Version {version} is not compatible with any dependent package versions"
            print(f"✗ {result['error_message']}")

    return result


def save_results(package_name: str, results: List[Dict], output_file: str = None, has_version_mapping: bool = False):
    """
    Save test results to a JSON file

    Args:
        package_name: Name of the package
        results: List of test result dictionaries
        output_file: Optional output file path
        has_version_mapping: Whether the package has a version mapping file
    """
    if not results:
        print("No results to save")
        return

    if output_file is None:
        output_file = f"{package_name}_version_compatibility.json"

    if has_version_mapping:
        # For dependency packages with version mapping, output version combinations
        version_combinations = []

        for r in results:
            if r and r.get('status') == 'compatible' and r.get('compatible_with_versions'):
                for target_version in r['compatible_with_versions']:
                    version_combinations.append({
                        'dependency_version': r['version'],
                        'target_version': target_version,
                        'supported_api_ids': r.get('supported_api_ids', [])
                    })

        output_data = {
            'type': 'dependency_compatibility',
            'package_name': package_name,
            'version_combinations': version_combinations,
            'total_combinations': len(version_combinations)
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Results saved to: {output_file}")
        print(f"{'='*60}")
        print(f"Summary:")
        print(f"  Total compatible version combinations: {len(version_combinations)}")

    else:
        # For user code packages without version mapping
        compatible_versions = []
        incompatible_versions = []

        for r in results:
            if r and 'status' in r and 'version' in r:
                if r['status'] == 'compatible':
                    compatible_versions.append({
                        'version': r['version'],
                        'supported_api_ids': r.get('supported_api_ids', [])
                    })
                elif r['status'] == 'incompatible':
                    incompatible_versions.append({
                        'version': r['version'],
                        'unsupported_api_ids': r.get('unsupported_api_ids', []),
                        'error_message': r.get('error_message', '')
                    })

        output_data = {
            'type': 'user_code_compatibility',
            'package_name': package_name,
            'compatible': compatible_versions,
            'incompatible': incompatible_versions
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        # Calculate statistics for display
        total = len(results)
        compatible_count = len(compatible_versions)
        incompatible_count = len(incompatible_versions)
        compatibility_rate = f"{(compatible_count/total*100):.2f}%" if total > 0 else "0%"

        print(f"\n{'='*60}")
        print(f"Results saved to: {output_file}")
        print(f"{'='*60}")
        print(f"Summary:")
        print(f"  Total versions tested: {total}")
        print(f"  Compatible: {compatible_count}")
        print(f"  Incompatible: {incompatible_count}")
        print(f"  Compatibility rate: {compatibility_rate}")


def main():
    parser = argparse.ArgumentParser(
        description='Test package versions for API compatibility using pyright'
    )
    parser.add_argument(
        'script_path',
        type=str,
        help='Path to the API check script (e.g., /path/to/check_keras_apis_pyright.py)'
    )
    parser.add_argument(
        'package_name',
        type=str,
        help='Name of the package to test (e.g., keras, numpy)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (default: saved in same directory as script)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit the number of versions to test (for testing purposes)'
    )
    parser.add_argument(
        '--skip-errors',
        action='store_true',
        help='Continue testing even if some versions fail'
    )

    args = parser.parse_args()

    script_path = os.path.abspath(args.script_path)
    package_name = args.package_name

    # Validate script path
    if not os.path.exists(script_path):
        print(f"Error: Script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(script_path):
        print(f"Error: Path is not a file: {script_path}", file=sys.stderr)
        sys.exit(1)

    # Get script directory (for output and venv)
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)

    print(f"Starting compatibility test for package: {package_name}")
    print(f"Using script: {script_name}")
    print(f"Script directory: {script_dir}")
    print(f"{'='*60}\n")

    # Fetch all versions
    print("Fetching available versions from PyPI...")
    versions = get_package_versions(package_name)

    if not versions:
        print(f"Error: No versions found for package '{package_name}'", file=sys.stderr)
        sys.exit(1)

    # Apply limit if specified
    if args.limit:
        print(f"Limiting to {args.limit} versions for testing")
        versions = versions[:args.limit]

    print(f"Will test {len(versions)} versions\n")

    # Test each version
    results = []
    try:
        for i, version in enumerate(versions, 1):

            print(f"\nProgress: {i}/{len(versions)}")

            try:
                result = test_package_version(package_name, version, script_path, script_dir)
                results.append(result)
            except KeyboardInterrupt:
                print("\n\nTest interrupted by user")
                break
            except Exception as e:
                error_result = {
                    'version': version,
                    'status': 'incompatible',
                    'venv_setup': False,
                    'installation': False,
                    'api_check': False,
                    'error_message': f"Unexpected error: {str(e)}",
                    'stdout': '',
                    'stderr': ''
                }
                results.append(error_result)
                print(f"✗ Unexpected error: {e}")

                if not args.skip_errors:
                    print("Stopping due to error. Use --skip-errors to continue.")
                    break
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output file path
    if args.output:
        output_file = args.output
    else:
        # Save in the same directory as the script
        output_file = os.path.join(script_dir, f"{package_name}_version_compatibility.json")

    # Check if version mapping exists
    version_mapping_file = os.path.join(script_dir, f"{package_name}_version_mapping.json")
    has_version_mapping = os.path.exists(version_mapping_file)

    # Save results
    if results:
        save_results(package_name, results, output_file, has_version_mapping)
    else:
        print("No results to save")
        sys.exit(1)


if __name__ == '__main__':
    main()
