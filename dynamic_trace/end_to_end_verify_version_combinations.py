#!/usr/bin/env python3
"""
Version Combination Exploit Tester (Venv Version)

This script tests different version combinations of packages
from a compatibility file against a CVE exploit script.

Features:
1. Creates virtual environment with venv
2. Installs packages one by one with pip
3. Verifies installed versions and retries if needed
4. Runs exploit script via bash
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from datetime import datetime
import tempfile
import shutil
import random
import time


def load_pypi_import_mapping(mapping_file="pypi_import_mapping.json"):
    """Load PyPI package name to import name mapping from JSON file and reverse it."""
    if not os.path.exists(mapping_file):
        print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")
        return {}

    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            original_mapping = json.load(f)

        # Reverse the mapping: {import_name: pypi_package_name}
        reversed_mapping = {}
        for pypi_name, import_name in original_mapping.items():
            reversed_mapping[import_name] = pypi_name

        print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file}")
        return reversed_mapping
    except Exception as e:
        print(f"⚠️ Failed to load mapping file {mapping_file}: {e}")
        return {}


# Load PyPI import mapping at module level
SCRIPT_DIR = Path(__file__).parent
PYPI_IMPORT_MAPPING = load_pypi_import_mapping(str(SCRIPT_DIR / "pypi_import_mapping.json"))


def load_compatibility_file(filepath: str) -> Dict:
    """Load and parse the version compatibility JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        print(f"[*] Loaded compatibility file with {len(data)} root packages")

        # Replace all import names with PyPI package names
        print(f"[*] Replacing import names with PyPI package names...")
        data = replace_import_names_with_pypi_names(data)

        return data

    except Exception as e:
        print(f"[!] Error loading compatibility file: {e}", file=sys.stderr)
        sys.exit(1)


def check_for_incompatible_packages(compatibility_data: Dict) -> List[str]:
    """
    Check if any packages are marked as incompatible.
    Returns a list of incompatible package names.
    """
    incompatible_packages = []

    for package_name, versions_data in compatibility_data.items():
        # Check if the package is marked as incompatible at the root level
        if isinstance(versions_data, dict) and versions_data.get('incompatible', False):
            incompatible_packages.append(package_name)

    return incompatible_packages


def replace_import_names_with_pypi_names(data: Dict) -> Dict:
    """Recursively replace all import names with PyPI package names"""
    if not isinstance(data, dict):
        return data

    result = {}

    for key, value in data.items():
        # Replace the key (package name) if it's in the mapping
        new_key = key
        if key in PYPI_IMPORT_MAPPING:
            new_key = PYPI_IMPORT_MAPPING[key]
            print(f"[Mapping] Replacing '{key}' with PyPI name '{new_key}'")

        # Recursively process the value
        if isinstance(value, dict):
            result[new_key] = replace_import_names_with_pypi_names(value)
        else:
            result[new_key] = value

    return result


def select_package_versions(compatibility_data: Dict,
                           mode: str = 'random', max_total_attempts: int = 100) -> Optional[Dict[str, str]]:
    """Select a valid combination of package versions from compatibility data"""

    def select_combination_attempt():
        """Attempt to select one valid combination"""
        selected_versions: Dict[str, str] = {}

        def select_version_recursive(pkg_name: str, available_versions: Dict,
                                     depth: int = 0) -> bool:
            """Recursively select versions for a package and its dependencies"""
            # Check if package already selected
            if pkg_name in selected_versions:
                current_version = selected_versions[pkg_name]
                if current_version not in available_versions:
                    # Version conflict
                    return False
                else:
                    # Use the existing version and continue with its deps
                    deps = available_versions[current_version]
                    if isinstance(deps, dict):
                        for dep_pkg, dep_versions in deps.items():
                            if not select_version_recursive(dep_pkg, dep_versions, depth + 1):
                                return False
                    return True

            # Get available versions list
            versions = list(available_versions.keys())

            if not versions:
                # No versions available
                return False

            # Select version based on mode
            if mode == 'random':
                versions = versions.copy()
                random.shuffle(versions)
            elif mode == 'latest':
                versions = sorted(versions, reverse=True)
            # 'first' mode keeps original order

            # Try each version
            for version in versions:
                # Check if this version is marked as incompatible
                version_data = available_versions[version]
                if isinstance(version_data, dict) and version_data.get('incompatible', False):
                    # Skip this version as it's marked incompatible
                    continue

                # Save current state for backtracking
                saved_versions = selected_versions.copy()

                # Select this version
                selected_versions[pkg_name] = version

                # Process dependencies
                deps = version_data
                all_deps_ok = True

                # Check if deps is a dictionary before iterating
                if isinstance(deps, dict):
                    for dep_pkg, dep_versions in deps.items():
                        if not select_version_recursive(dep_pkg, dep_versions, depth + 1):
                            all_deps_ok = False
                            break

                if all_deps_ok:
                    return True  # Success!

                # Backtrack: restore saved state
                selected_versions.clear()
                selected_versions.update(saved_versions)

            return False  # No valid version found

        # Process each root package
        for root_pkg, versions_data in compatibility_data.items():
            if not select_version_recursive(root_pkg, versions_data):
                return None

        return selected_versions if selected_versions else None

    # Try to find a valid combination
    for attempt in range(max_total_attempts):
        result = select_combination_attempt()

        if result:
            print(f"[+] Found valid version combination after {attempt + 1} attempt(s)")
            return result

        # If mode is not random, no point trying again
        if mode != 'random':
            break

    print(f"[!] Could not find valid version combination after {max_total_attempts} attempts")
    return None


def generate_version_combinations(compatibility_data: Dict,
                                  mode: str = 'random',
                                  count: int = 1) -> List[Dict[str, str]]:
    """Generate multiple valid version combinations"""
    combinations = []
    seen_combinations = set()

    attempts = 0
    max_total_attempts = count * 100

    while len(combinations) < count and attempts < max_total_attempts:
        attempts += 1

        version_combo = select_package_versions(compatibility_data, mode, max_total_attempts)

        if version_combo:
            # Create a hashable representation
            combo_key = tuple(sorted(version_combo.items()))

            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                combinations.append(version_combo)
                print(f"[*] Generated combination {len(combinations)}/{count}")

    if len(combinations) == 0:
        print(f"\n[!] Could not generate any valid combinations after {attempts} attempts")
        print(f"[!] The compatibility constraints may be too restrictive or conflicting")
    elif len(combinations) < count:
        print(f"\n[!] Warning: Only generated {len(combinations)} combinations out of {count} requested")

    return combinations


def create_virtual_environment(venv_path: str) -> bool:
    """Create a Python virtual environment"""
    try:
        print(f"[*] Creating virtual environment at {venv_path}...")
        subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"[+] Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to create virtual environment: {e}")
        print(f"[!] stderr: {e.stderr}")
        return False


def get_venv_python(venv_path: str) -> str:
    """Get the path to the Python interpreter in the virtual environment"""
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")


def get_venv_pip(venv_path: str) -> str:
    """Get the path to pip in the virtual environment"""
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        return os.path.join(venv_path, "bin", "pip")


def install_package(venv_path: str, package_name: str, version: str, max_retries: int = 3) -> bool:
    """Install a specific version of a package in the virtual environment"""
    pip_path = get_venv_pip(venv_path)
    package_spec = f"{package_name}=={version}"

    for attempt in range(max_retries):
        try:
            print(f"[*] Installing {package_spec} (attempt {attempt + 1}/{max_retries})...")
            result = subprocess.run(
                [pip_path, "install", package_spec],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per package
            )
            print(f"[+] Successfully installed {package_spec}")
            return True
        except subprocess.TimeoutExpired:
            print(f"[!] Installation of {package_spec} timed out (attempt {attempt + 1}/{max_retries})")
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to install {package_spec} (attempt {attempt + 1}/{max_retries})")
            print(f"[!] stderr: {e.stderr}")

        if attempt < max_retries - 1:
            time.sleep(2)  # Wait before retry

    return False


def get_installed_version(venv_path: str, package_name: str) -> Optional[str]:
    """Get the installed version of a package"""
    pip_path = get_venv_pip(venv_path)

    try:
        result = subprocess.run(
            [pip_path, "show", package_name],
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Parse the output to find the version
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
                return version

        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def verify_and_fix_versions(venv_path: str, desired_versions: Dict[str, str],
                            max_iterations: int = 10) -> Tuple[bool, Dict[str, str]]:
    """
    Verify installed package versions and retry installation if needed.
    Returns (success, actual_versions)
    """
    print(f"\n[*] Verifying and fixing package versions (max {max_iterations} iterations)...")

    for iteration in range(max_iterations):
        print(f"\n[*] Verification iteration {iteration + 1}/{max_iterations}")

        mismatched_packages = []
        actual_versions = {}

        # Check all packages
        for package_name, desired_version in sorted(desired_versions.items()):
            installed_version = get_installed_version(venv_path, package_name)
            actual_versions[package_name] = installed_version

            if installed_version is None:
                print(f"[!] Package {package_name} is not installed")
                mismatched_packages.append((package_name, desired_version))
            elif installed_version != desired_version:
                print(f"[!] Version mismatch for {package_name}: expected {desired_version}, got {installed_version}")
                mismatched_packages.append((package_name, desired_version))
            else:
                print(f"[+] {package_name}=={installed_version} ✓")

        # If all versions match, we're done
        if not mismatched_packages:
            print(f"\n[+] All package versions verified successfully!")
            return True, actual_versions

        # Retry installing mismatched packages
        print(f"\n[*] Found {len(mismatched_packages)} mismatched packages, retrying installation...")
        for package_name, desired_version in mismatched_packages:
            install_package(venv_path, package_name, desired_version)

        # Small delay before next verification
        time.sleep(1)

    # Max iterations reached
    print(f"\n[!] Failed to fix all version mismatches after {max_iterations} iterations")
    return False, actual_versions


def install_packages_in_venv(venv_path: str, version_combo: Dict[str, str]) -> Tuple[bool, Dict[str, str]]:
    """
    Install packages in the virtual environment and verify versions.
    Returns (success, actual_versions)
    """
    print(f"\n[*] Installing {len(version_combo)} packages...")

    # First, install all packages
    failed_packages = []
    for package_name, version in sorted(version_combo.items()):
        if not install_package(venv_path, package_name, version):
            failed_packages.append(f"{package_name}=={version}")

    if failed_packages:
        print(f"\n[!] Failed to install some packages: {', '.join(failed_packages)}")

    # Now verify and fix versions
    success, actual_versions = verify_and_fix_versions(venv_path, version_combo)

    return success, actual_versions


def run_exploit_script(venv_path: str, exploit_script: str, work_dir: str) -> Tuple[bool, str]:
    """
    Run the exploit script using bash.
    Returns (success, output)
    """
    print(f"\n[*] Running exploit script: {exploit_script}")

    # Check if exploit script exists
    if not os.path.exists(exploit_script):
        error_msg = f"Exploit script not found: {exploit_script}"
        print(f"[!] {error_msg}")
        return False, error_msg

    try:
        # Get the absolute path to the exploit script
        exploit_script_abs = os.path.abspath(exploit_script)

        # Set up environment with the venv's Python
        env = os.environ.copy()
        python_path = get_venv_python(venv_path)
        venv_bin = os.path.dirname(python_path)
        env['PATH'] = venv_bin + os.pathsep + env.get('PATH', '')
        env['VIRTUAL_ENV'] = venv_path

        # Run the exploit script
        result = subprocess.run(
            ["bash", exploit_script_abs],
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nReturn code: {result.returncode}"

        if result.returncode == 0:
            print(f"[+] Exploit script completed successfully (exit code 0)")
            return True, output
        else:
            print(f"[-] Exploit script failed with exit code {result.returncode}")
            return False, output

    except subprocess.TimeoutExpired:
        error_msg = "Exploit script timed out after 5 minutes"
        print(f"[!] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error running exploit script: {str(e)}"
        print(f"[!] {error_msg}")
        return False, error_msg


def test_version_combination(exploit_script: str,
                            version_combo: Dict[str, str],
                            work_dir: str) -> Dict:
    """Test a single version combination by creating venv and running exploit"""
    result = {
        'version_combination': version_combo.copy(),
        'actual_versions': {},
        'install_commands': [],
        'success': False,
        'error': None,
        'exploit_output': None,
        'timestamp': datetime.now().isoformat()
    }

    print(f"\n{'='*70}")
    print(f"Testing version combination:")
    print(f"Total packages: {len(version_combo)}")
    # Show first 10 packages
    shown = 0
    for pkg, ver in sorted(version_combo.items()):
        if shown < 10:
            print(f"  {pkg}=={ver}")
            shown += 1
    if len(version_combo) > 10:
        print(f"  ... and {len(version_combo) - 10} more packages")
    print(f"{'='*70}")

    packages_to_install = version_combo

    try:
        # Create virtual environment
        venv_path = os.path.join(work_dir, "venv")
        if not create_virtual_environment(venv_path):
            result['error'] = "Failed to create virtual environment"
            return result

        # Record install commands
        for pkg, ver in sorted(packages_to_install.items()):
            result['install_commands'].append(f"pip install {pkg}=={ver}")

        # Install packages and verify versions
        install_success, actual_versions = install_packages_in_venv(venv_path, packages_to_install)
        result['actual_versions'] = actual_versions

        if not install_success:
            result['error'] = "Failed to install packages with correct versions"
            print(f"[-] Package installation/verification failed")
            return result

        # Run exploit script
        exploit_success, exploit_output = run_exploit_script(venv_path, exploit_script, work_dir)
        result['exploit_output'] = exploit_output
        result['success'] = exploit_success

        if exploit_success:
            print(f"[+] Successfully triggered the exploit!")
        else:
            print(f"[-] Failed to trigger the exploit")
            result['error'] = "Exploit failed to trigger"

    except Exception as e:
        error_msg = f"Unexpected error during testing: {str(e)}"
        print(f"[!] {error_msg}")
        result['error'] = error_msg
        result['exploit_output'] = error_msg

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Test version combinations against CVE exploit (Venv Version)'
    )
    parser.add_argument(
        'exploit',
        help='Path to exploit script (bash)'
    )
    parser.add_argument(
        'compatibility',
        help='Path to version compatibility JSON file'
    )
    parser.add_argument(
        '--mode', '-m',
        default='random',
        choices=['random', 'first', 'latest'],
        help='Version selection mode'
    )
    parser.add_argument(
        '--count', '-n',
        type=int,
        default=1,
        help='Number of version combinations to test'
    )
    parser.add_argument(
        '--output', '-o',
        default='exploit_test_results.json',
        help='Output file for test results (default: exploit_test_results.json)'
    )

    args = parser.parse_args()

    # Validate input files
    if not os.path.exists(args.exploit):
        print(f"[!] Exploit script not found: {args.exploit}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.compatibility):
        print(f"[!] Compatibility file not found: {args.compatibility}", file=sys.stderr)
        sys.exit(1)

    # Load compatibility data
    compatibility_data = load_compatibility_file(args.compatibility)

    if not compatibility_data:
        print("[!] No compatibility data found in file", file=sys.stderr)
        sys.exit(1)

    # Check for incompatible packages
    incompatible_packages = check_for_incompatible_packages(compatibility_data)
    if incompatible_packages:
        print("\n" + "="*70, file=sys.stderr)
        print("INCOMPATIBLE PACKAGES FOUND", file=sys.stderr)
        print("="*70, file=sys.stderr)
        print(f"\n[!] Cannot find suitable versions for the following package(s):", file=sys.stderr)
        for pkg in incompatible_packages:
            print(f"    - {pkg} (marked as incompatible)", file=sys.stderr)
        print(f"\n[!] The compatibility file indicates these packages have no compatible versions.", file=sys.stderr)
        print(f"[!] Compatibility file: {args.compatibility}", file=sys.stderr)
        print(f"\n[*] Exiting without running tests.", file=sys.stderr)
        sys.exit(1)

    # Generate version combinations
    print(f"\n[*] Generating {args.count} version combination(s) using '{args.mode}' mode...")
    combinations = generate_version_combinations(compatibility_data, args.mode, args.count)

    if not combinations:
        print("\n" + "="*70, file=sys.stderr)
        print("NO VALID COMBINATIONS FOUND", file=sys.stderr)
        print("="*70, file=sys.stderr)
        print("\n[!] No valid version combinations could be generated.", file=sys.stderr)
        print("[!] This may be because:", file=sys.stderr)
        print("    - The compatibility file has conflicting version constraints", file=sys.stderr)
        print("    - All available versions are marked as incompatible", file=sys.stderr)
        print("    - The dependency tree cannot be satisfied", file=sys.stderr)
        print(f"\n[*] Compatibility file: {args.compatibility}", file=sys.stderr)
        print(f"[*] Number of root packages: {len(compatibility_data)}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[*] Starting tests for {len(combinations)} version combination(s)")
    print(f"[*] Exploit: {args.exploit}")
    print(f"[*] Compatibility: {args.compatibility}")
    print(f"[*] Mode: {args.mode}")

    # Prepare working directory (always use temp directory and always cleanup)
    base_work_dir = tempfile.mkdtemp(prefix='exploit_test_')

    print(f"[*] Working directory: {base_work_dir}")

    # Test each combination
    results = []
    successful_combinations = []
    successful_results = []
    failed_combinations = []

    for i, combo in enumerate(combinations, 1):
        print(f"\n[*] Testing combination {i}/{len(combinations)}")

        # Create a subdirectory for this test
        test_dir = os.path.join(base_work_dir, f"test_{i}")
        os.makedirs(test_dir, exist_ok=True)

        try:
            result = test_version_combination(
                args.exploit,
                combo,
                test_dir,
            )

            results.append(result)

            if result['success']:
                combo_str = ', '.join([f"{pkg}=={ver}" for pkg, ver in sorted(combo.items())[:10]])
                if len(combo) > 10:
                    combo_str += f" ... and {len(combo) - 10} more"
                successful_combinations.append(combo_str)
                successful_results.append(result)
            else:
                combo_str = ', '.join([f"{pkg}=={ver}" for pkg, ver in sorted(combo.items())[:5]])
                failed_combinations.append(
                    f"{combo_str}: {result.get('error', 'Exploit failed')}"
                )

        except Exception as e:
            print(f"[!] Unexpected error testing combination: {e}")
            results.append({
                'version_combination': combo.copy(),
                'actual_versions': {},
                'success': False,
                'error': str(e),
                'exploit_output': None,
                'timestamp': datetime.now().isoformat()
            })

        finally:
            # Cleanup test directory
            if os.path.exists(test_dir):
                try:
                    shutil.rmtree(test_dir)
                except Exception as e:
                    print(f"[!] Warning: Could not clean up {test_dir}: {e}")

    # Save results to specified output file
    output_file = args.output
    output_data = {
        'metadata': {
            'exploit_script': os.path.abspath(args.exploit),
            'compatibility_file': os.path.abspath(args.compatibility),
            'test_timestamp': datetime.now().isoformat(),
            'total_combinations': len(combinations),
            'successful_combinations': len(successful_combinations),
            'failed_combinations': len(failed_combinations),
        },
        'results': results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'='*70}")
    print(f"TESTING COMPLETE")
    print(f"{'='*70}")
    print(f"\n[*] Total combinations tested: {len(combinations)}")
    print(f"[+] Successful exploits: {len(successful_combinations)}")
    print(f"[-] Failed exploits: {len(failed_combinations)}")

    if successful_combinations:
        print(f"\n[+] Successful combinations:")
        for i, combo in enumerate(successful_combinations):
            print(f"    {i+1}. {combo}")

    if failed_combinations:
        print(f"\n[-] Failed combinations:")
        for combo in failed_combinations:
            print(f"    - {combo}")

    print(f"\n[*] Results saved to: {output_file}")

    # Cleanup working directory
    if os.path.exists(base_work_dir):
        try:
            shutil.rmtree(base_work_dir)
            print(f"[*] Cleaned up working directory: {base_work_dir}")
        except Exception as e:
            print(f"[!] Warning: Could not clean up {base_work_dir}: {e}")

    return 0 if successful_combinations else 1


if __name__ == '__main__':
    sys.exit(main())
