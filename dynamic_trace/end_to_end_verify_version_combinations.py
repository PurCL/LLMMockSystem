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
import re
import multiprocessing
import requests
from packaging.version import parse as parse_version


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

# Convert package name to PyPI name
def get_pypi_name(pkg_name: str) -> str:
    if pkg_name in PYPI_IMPORT_MAPPING:
        return PYPI_IMPORT_MAPPING[pkg_name]
    return pkg_name

# Load PyPI import mapping at module level
SCRIPT_DIR = Path(__file__).parent
PYPI_IMPORT_MAPPING = load_pypi_import_mapping(str(SCRIPT_DIR / "pypi_import_mapping.json"))


def parse_import_error(stderr: str) -> Optional[Dict[str, str]]:
    """
    Parse ImportError from stderr, extract error type, missing library, missing item, and call chain

    Example input:
    ImportError: cannot import name 'ContextOverflowError' from 'langchain_core.exceptions'

    Returns:
    {
        'error_type': 'ImportError',
        'package': 'langchain_core',
        'missing_item': 'ContextOverflowError',
        'call_chain': ['langchain_openai', 'langchain_core']
    }
    """
    if not stderr:
        return None

    # Get the last line (usually the actual error message)
    lines = stderr.strip().split('\n')
    last_line = lines[-1] if lines else ''

    # Regex match: ImportError: cannot import name 'XXX' from 'YYY'
    pattern_import_error = r"ImportError:\s*cannot import name\s+'([^']+)'\s+from\s+'([^']+)'"
    match_import = re.search(pattern_import_error, last_line)

    # Regex match: ModuleNotFoundError: No module named 'XXX'
    pattern_module_not_found = r"ModuleNotFoundError:\s*No module named\s+'([^']+)'"
    match_module = re.search(pattern_module_not_found, last_line)

    error_type = None
    missing_item = None
    full_module = None
    package = None

    # Handle ImportError
    if match_import:
        error_type = 'ImportError'
        missing_item = match_import.group(1)
        full_module = match_import.group(2)
        # Extract package name (part before the first dot)
        package = full_module.split('.')[0]
    # Handle ModuleNotFoundError
    elif match_module:
        error_type = 'ModuleNotFoundError'
        missing_module = match_module.group(1)
        # For ModuleNotFoundError, missing_item is the module name itself
        missing_item = missing_module
        full_module = missing_module
        package = missing_module.split('.')[0]
    else:
        return None

    # Analyze call chain
    call_chain = []

    # Find all "File" lines, extract import paths or package names from file paths
    file_pattern = r'File\s+"([^"]+)"'
    import_pattern = r'(from\s+(\S+)\s+import|import\s+(\S+))'
    site_packages_pattern = r'/site-packages/([^/]+)/'

    # Iterate through each line of the traceback
    i = 0
    while i < len(lines):
        line = lines[i]
        file_match = re.search(file_pattern, line)

        if file_match:
            file_path = file_match.group(1)
            package_from_file = None

            # Try to extract package name from file path (part after site-packages)
            site_match = re.search(site_packages_pattern, file_path)
            if site_match:
                package_from_file = site_match.group(1)
                # Handle special cases like PIL -> pillow
                # Here we directly use the folder name
                if package_from_file and package_from_file not in call_chain:
                    call_chain.append(package_from_file)

            # Check if the next line contains an import statement
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                import_match = re.search(import_pattern, next_line)

                if import_match:
                    # Extract the imported package name
                    if import_match.group(2):  # from X import
                        imported_module = import_match.group(2)
                    elif import_match.group(3):  # import X
                        imported_module = import_match.group(3)
                    else:
                        imported_module = None

                    if imported_module:
                        # Extract top-level package name
                        top_package = imported_module.split('.')[0]

                        # Add to call chain (avoid duplicates)
                        if not call_chain or call_chain[-1] != top_package:
                            call_chain.append(top_package)

        i += 1

    # For ModuleNotFoundError, the missing module should be the last item in the call chain
    if error_type == 'ModuleNotFoundError':
        # Ensure the missing module is at the end of the call chain
        if call_chain and call_chain[-1] != package:
            call_chain.append(package)
        elif not call_chain:
            # If the call chain is empty, find the second-to-last package
            # Find the caller from site-packages paths
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i]
                file_match = re.search(file_pattern, line)
                if file_match:
                    file_path = file_match.group(1)
                    site_match = re.search(site_packages_pattern, file_path)
                    if site_match:
                        caller_package = site_match.group(1)
                        if caller_package != package:
                            call_chain = [caller_package, package]
                            break

            # If still can't find, at least add the target package
            if not call_chain:
                call_chain = [package]
    else:
        # For ImportError, if the call chain is empty, at least add the last package
        if not call_chain:
            call_chain = [package]

    return {
        'error_type': error_type,
        'package': package,
        'missing_item': missing_item,
        'full_module': full_module,
        'call_chain': call_chain
    }


def fetch_all_versions(package_name: str) -> List[str]:
    """
    Fetch all available versions of a package from PyPI (sorted in descending order)

    Args:
        package_name: package import_name (case-sensitive)
                     Example: 'OpenSSL', 'PIL', 'numpy'

    Returns:
        Standardized version list (descending order, newest first)
        Special characters like / and : in version numbers are replaced with _

    Note:
        - Input package_name is import_name, will be converted to pypi_name via mapping
        - Versions are sorted according to semantic versioning rules (using packaging.version.parse)
    """

    try:
        # Get PyPI package name via mapping (if exists)
        pypi_package_name = get_pypi_name(package_name)
        url = f"https://pypi.org/pypi/{pypi_package_name}/json"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Get all versions
        raw_versions = list(data.get('releases', {}).keys())

        # Sort in descending order using packaging.version.parse
        # reverse=True means from newest to oldest (e.g., 2.10.0 -> 2.9.0 -> 1.0.0)
        sorted_versions = sorted(raw_versions, key=parse_version, reverse=True)

        # Standardize version numbers: replace special characters with underscores
        safe_versions = [version.replace('/', '_').replace(':', '_') for version in sorted_versions]

        print(f"Found {len(raw_versions)} total versions for {pypi_package_name}. Standardized and returning the top {len(safe_versions)} latest versions.")

        return safe_versions

    except Exception as e:
        print(f"Error fetching versions for {package_name}: {e}", file=sys.stderr)
        return []


def fetch_package_versions_by_call_chain(package_name: str, call_chain: List[str], compatibility_data: Dict, combo: Dict[str, str] = None) -> Tuple[List[str], bool]:
    """
    Fetch package versions from compatibility.json following the call_chain path

    Args:
        package_name: PyPI package name (target package)
        call_chain: Call chain list, e.g., ['langchain_openai', 'langchain_core']
        compatibility_data: Loaded compatibility data
        combo: Version combination dict to specify version for each package in call_chain

    Returns:
        (Version list in descending order, whether this is a new package)
    """
    versions_set = set()

    target_pypi_name = get_pypi_name(package_name)

    # Convert all package names in call_chain to PyPI names
    pypi_call_chain = [get_pypi_name(pkg) for pkg in call_chain]

    print(f"[*] Following call chain to find versions: {' -> '.join(pypi_call_chain)}")

    # Navigate to the target package following the call_chain path
    current_data = compatibility_data

    for i, chain_package in enumerate(pypi_call_chain[:-1]):  # Iterate through all packages except the last one
        if not isinstance(current_data, dict):
            print(f"[!] Data is not a dict at chain level {i} (package: {chain_package})")
            return [], False

        # Find the package in the current chain
        if chain_package in current_data:
            # Get all version data for this package
            package_versions = current_data[chain_package]

            if not isinstance(package_versions, dict):
                print(f"[!] No version data found for {chain_package} in call chain")
                return [], False

            target_version = combo[chain_package]
            current_data = package_versions[target_version]
            print(f"[*] Using combo version: {chain_package}=={target_version}")
        else:
            print(f"[!] Package {chain_package} not found in call chain at level {i}")
            return [], False

    # Now current_data should point to the dependency dict of the second-to-last package in call_chain
    # We need to extract versions of the last package (target package) from here
    last_package = pypi_call_chain[-1]

    # Access the dictionary directly, no need for loops and recursion
    if isinstance(current_data, dict) and last_package in current_data:
        target_package_data = current_data[last_package]

        if isinstance(target_package_data, dict):
            for version in target_package_data:  # Iterate through dict keys
                if version != 'incompatible':
                    versions_set.add(version)

    is_new_package = False
    if not versions_set:
        # If no versions found, try fetching from PyPI API
        print(f"[*] No versions found in compatibility data, fetching from PyPI...")
        all_versions = fetch_all_versions(package_name)
        if all_versions:
            versions_set = set(all_versions)
            is_new_package = True
            print(f"[*] This is a new package not in compatibility data")

    # Convert to list and sort in descending order by version number
    sorted_versions = sorted(list(versions_set), key=parse_version, reverse=True)
    print(f"[*] Found {len(sorted_versions)} versions for {package_name} following call chain")
    return sorted_versions, is_new_package


def verify_single_version(args: Tuple) -> Tuple[str, bool, str]:
    """
    Verify whether a single version contains the specified item in an isolated environment

    Args:
        args: (package_name, version, missing_item, full_module, work_dir)

    Returns:
        (version, success, error_message)
    """
    package_name, version, missing_item, full_module, work_dir = args

    # Create version-specific directory
    version_dir = os.path.join(work_dir, f"verify_{package_name}_{version.replace('/', '_').replace(':', '_')}")

    try:
        os.makedirs(version_dir, exist_ok=True)

        # Create virtual environment
        venv_path = os.path.join(version_dir, 'venv')
        result = subprocess.run(
            [sys.executable, '-m', 'venv', venv_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return (version, False, f"Failed to create venv: {result.stderr}")

        # Install package
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        pypi_package_name = get_pypi_name(package_name)
        result = subprocess.run(
            [pip_path, 'install', f'{pypi_package_name}=={version}'],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            return (version, False, f"Failed to install: {result.stderr[:200]}")

        # Create test script - use full module path
        test_script = os.path.join(version_dir, 'test_import.py')
        script_content = f"""
import sys
try:
    from {full_module} import {missing_item}
    print("SUCCESS: Found {missing_item}")
    sys.exit(0)
except ImportError as e:
    print(f"FAILED: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(2)
"""

        with open(test_script, 'w') as f:
            f.write(script_content)

        # Run test script
        python_path = os.path.join(venv_path, 'bin', 'python')
        result = subprocess.run(
            [python_path, test_script],
            capture_output=True,
            text=True,
            timeout=60
        )

        success = (result.returncode == 0)
        message = result.stdout.strip() if result.stdout else result.stderr.strip()

        return (version, success, message)

    except subprocess.TimeoutExpired:
        return (version, False, "Timeout")
    except Exception as e:
        return (version, False, str(e))
    finally:
        # Cleanup
        if os.path.exists(version_dir):
            try:
                shutil.rmtree(version_dir)
            except:
                pass


def remove_failed_versions_from_call_chain(
    compatibility_data: Dict,
    call_chain: List[str],
    failed_versions: List[str],
    target_package: str,
    combo: Dict[str, str] = None
) -> None:
    """
    Remove all failed_versions of target_package along the call chain path from compatibility_data

    Args:
        compatibility_data: Compatibility data (will be modified directly)
        call_chain: Call chain list, e.g., ['langchain_openai', 'langchain_core']
        failed_versions: List of versions to remove
        target_package: Target package name (import name)
        combo: Version combination dict to specify version for each package in call_chain
    """
    # Convert package name to PyPI name
    def get_pypi_name(pkg_name: str) -> str:
        if pkg_name in PYPI_IMPORT_MAPPING:
            return PYPI_IMPORT_MAPPING[pkg_name]
        return pkg_name

    target_pypi_name = get_pypi_name(target_package)
    pypi_call_chain = [get_pypi_name(pkg) for pkg in call_chain]

    print(f"[*] Removing versions {failed_versions} for {target_pypi_name} along call chain: {' -> '.join(pypi_call_chain)}")

    # Navigate to the location in the call chain and delete failed versions
    current_data = compatibility_data

    for i, chain_package in enumerate(pypi_call_chain[:-1]):
        if not isinstance(current_data, dict):
            print(f"[!] Cannot navigate: data is not a dict at chain level {i}")
            return

        if chain_package not in current_data:
            print(f"[!] Package {chain_package} not found in call chain at level {i}")
            return

        package_versions = current_data[chain_package]

        if not isinstance(package_versions, dict):
            print(f"[!] No version data for {chain_package}")
            return

        target_version = combo[chain_package]
        current_data = package_versions[target_version]
        print(f"[*] Navigating to {chain_package}=={target_version} (from combo)")

    # Now delete failed versions of the last package
    last_package = pypi_call_chain[-1]

    if isinstance(current_data, dict) and last_package in current_data:
        target_versions_dict = current_data[last_package]

        if isinstance(target_versions_dict, dict):
            for ver in failed_versions:
                if ver in target_versions_dict:
                    del target_versions_dict[ver]
                    print(f"[*] Removed version {ver} from {last_package}")


def add_successful_versions_from_call_chain(
    compatibility_data: Dict,
    call_chain: List[str],
    successful_versions: List[str],
    target_package: str,
    combo: Dict[str, str] = None
) -> None:
    """
    Add all successful_versions of target_package along the call chain path to compatibility_data

    Args:
        compatibility_data: Compatibility data (will be modified directly)
        call_chain: Call chain list, e.g., ['langchain_openai', 'langchain_core']
        successful_versions: List of versions to add
        target_package: Target package name (import name)
        combo: Version combination dict to specify version for each package in call_chain
    """
    # Convert package name to PyPI name
    def get_pypi_name(pkg_name: str) -> str:
        if pkg_name in PYPI_IMPORT_MAPPING:
            return PYPI_IMPORT_MAPPING[pkg_name]
        return pkg_name

    target_pypi_name = get_pypi_name(target_package)
    pypi_call_chain = [get_pypi_name(pkg) for pkg in call_chain]

    print(f"[*] Adding versions {successful_versions} for {target_pypi_name} along call chain: {' -> '.join(pypi_call_chain)}")

    # Navigate to the location in the call chain and add successful versions
    current_data = compatibility_data

    for i, chain_package in enumerate(pypi_call_chain[:-1]):
        if not isinstance(current_data, dict):
            print(f"[!] Cannot navigate: data is not a dict at chain level {i}")
            return

        if chain_package not in current_data:
            print(f"[!] Package {chain_package} not found in call chain at level {i}")
            return

        package_versions = current_data[chain_package]

        if not isinstance(package_versions, dict):
            print(f"[!] No version data for {chain_package}")
            return

        target_version = combo[chain_package]
        if target_version not in package_versions:
            print(f"[!] Version {target_version} not found for {chain_package}")
            return

        current_data = package_versions[target_version]
        print(f"[*] Navigating to {chain_package}=={target_version} (from combo)")

    # Now add successful versions of the last package
    last_package = pypi_call_chain[-1]

    # If the target package doesn't exist, create it
    if last_package not in current_data:
        current_data[last_package] = {}
        print(f"[*] Created new entry for {last_package}")

    target_versions_dict = current_data[last_package]

    if not isinstance(target_versions_dict, dict):
        print(f"[!] Target versions dict is not a dict for {last_package}")
        return

    # Add all successful versions (with empty dict as value)
    for ver in successful_versions:
        if ver not in target_versions_dict:
            target_versions_dict[ver] = {}
            print(f"[*] Added version {ver} to {last_package}")
        else:
            print(f"[*] Version {ver} already exists in {last_package}")


def verify_single_version_installability(args: Tuple) -> Tuple[str, bool, str]:
    """
    Verify whether a single version can be installed (for newly added packages)

    Args:
        args: (package_name, version, work_dir)

    Returns:
        (version, success, error_message)
    """
    package_name, version, work_dir = args

    # Create version-specific directory
    version_dir = os.path.join(work_dir, f"install_check_{package_name}_{version.replace('/', '_').replace(':', '_')}")

    try:
        os.makedirs(version_dir, exist_ok=True)

        # Create virtual environment
        venv_path = os.path.join(version_dir, 'venv')
        result = subprocess.run(
            [sys.executable, '-m', 'venv', venv_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return (version, False, f"Failed to create venv: {result.stderr}")

        # Try to install package
        success = install_package(venv_path, package_name, version, max_retries=1)

        if success:
            return (version, True, f"Successfully installed {package_name}=={version}")
        else:
            return (version, False, f"Failed to install {package_name}=={version}")

    except subprocess.TimeoutExpired:
        return (version, False, "Timeout")
    except Exception as e:
        return (version, False, str(e))
    finally:
        # Cleanup
        if os.path.exists(version_dir):
            try:
                shutil.rmtree(version_dir)
            except:
                pass


def verify_package_versions_for_missing_item(
    package_name: str,
    missing_item: str,
    test_dir: str,
    full_module: str = None,
    max_workers: int = 10,
    compatibility_data: Dict = None,
    call_chain: List[str] = None,
    combo: Dict[str, str] = None
) -> Tuple[List[str], bool]:
    """
    Verify all versions of a package in parallel to find versions that don't contain the specified item

    Args:
        package_name: Package name
        missing_item: Missing class/function name
        test_dir: Test directory
        full_module: Full module path (e.g., langchain_core.exceptions)
        max_workers: Maximum number of parallel workers
        compatibility_data: compatibility.json data (if provided, fetch versions from it)
        call_chain: Call chain list (if provided, fetch versions following the call chain)
        combo: Version combination dict to specify version for each package in call_chain

    Returns:
        (List of failed versions or list of successfully installed versions, whether this is a new package)
    """
    # If full module path not provided, use package name
    if full_module is None:
        full_module = package_name.replace('-', '_')

    print(f"\n[*] Fetching versions for {package_name}...")

    versions, is_new_package = fetch_package_versions_by_call_chain(package_name, call_chain, compatibility_data, combo)

    if not versions:
        print(f"[!] No versions found for {package_name}")
        return [], False

    # Create verification working directory
    verify_work_dir = os.path.join(test_dir, f"verify_{package_name}")
    os.makedirs(verify_work_dir, exist_ok=True)

    result_versions = []

    if not is_new_package:
        # Existing package: test which versions don't contain missing_item
        print(f"[*] Testing {len(versions)} versions for presence of '{missing_item}' in '{full_module}'...")

        # Prepare arguments
        args_list = [
            (package_name, version, missing_item, full_module, verify_work_dir)
            for version in versions
        ]

        # Execute verification in parallel
        try:
            with multiprocessing.Pool(processes=max_workers) as pool:
                results = pool.map(verify_single_version, args_list)

            # Collect failed versions
            for version, success, message in results:
                if not success:
                    result_versions.append(version)
                    print(f"  [✗] {package_name}=={version}: {message[:100]}")
                else:
                    print(f"  [✓] {package_name}=={version}: {message}")

        except KeyboardInterrupt:
            print("\n[!] Verification interrupted by user")
            pool.terminate()
            pool.join()
        except Exception as e:
            print(f"[!] Error during verification: {e}")
    else:
        # New package: test which versions can be successfully installed
        print(f"[*] Testing {len(versions)} versions for installability (new package)...")

        # Prepare arguments
        args_list = [
            (package_name, version, verify_work_dir)
            for version in versions
        ]

        # Execute installation verification in parallel
        try:
            with multiprocessing.Pool(processes=max_workers) as pool:
                results = pool.map(verify_single_version_installability, args_list)

            # Collect successfully installed versions
            for version, success, message in results:
                if success:
                    result_versions.append(version)
                    print(f"  [✓] {package_name}=={version}: {message}")
                else:
                    print(f"  [✗] {package_name}=={version}: {message[:100]}")

        except KeyboardInterrupt:
            print("\n[!] Verification interrupted by user")
            pool.terminate()
            pool.join()
        except Exception as e:
            print(f"[!] Error during verification: {e}")

    # Cleanup working directory
    if os.path.exists(verify_work_dir):
        try:
            shutil.rmtree(verify_work_dir)
        except:
            pass

    return result_versions, is_new_package


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


import random
from typing import Dict, Optional

def select_package_versions(compatibility_data: Dict, mode: str = 'random') -> Optional[Dict[str, str]]:
    """
    Select a valid combination of package versions from compatibility data.
    Uses exhaustive Depth-First Search (DFS) with backtracking.
    """
    selected_versions: Dict[str, str] = {}

    def select_version_recursive(pkg_name: str, available_versions: Dict, depth: int = 0) -> bool:
        if not isinstance(available_versions, dict):
            return False

        # 1. 获取所有可用版本 (自动过滤掉 'incompatible' 标记)
        versions = [v for v in available_versions.keys() if v != 'incompatible']
        
        # 如果过滤后没有任何有效版本，说明这个包彻底走不通
        if not versions:
            return False

        # 2. 菱形依赖/交叉依赖校验
        if pkg_name in selected_versions:
            current_version = selected_versions[pkg_name]
            if current_version not in versions:
                return False
            else:
                deps = available_versions[current_version]
                if isinstance(deps, dict):
                    # 如果已选版本的当前上下文是 incompatible 的，校验失败
                    if deps.get('incompatible') is True:
                        return False
                    
                    for dep_pkg, dep_versions in deps.items():
                        if dep_pkg == 'incompatible': 
                            continue
                        if not select_version_recursive(dep_pkg, dep_versions, depth + 1):
                            return False
                return True

        # 3. 决定模式尝试顺序
        if mode == 'random':
            versions = versions.copy()
            random.shuffle(versions)
        elif mode == 'latest':
            versions = sorted(versions, reverse=True)

        # 4. 回溯核心：逐个尝试所有版本
        for version in versions:
            deps = available_versions[version]

            # ====================================================
            # [核心修复 1]：单版本精准隔离
            # 如果当前 version 自己被标记为 incompatible，仅跳过这一个版本！
            # ====================================================
            if isinstance(deps, dict) and deps.get('incompatible') is True:
                continue

            # ====================================================
            # [核心修复 2]：子依赖深度熔断
            # 只有当某个子依赖【彻底没有任何可用版本】时，才熔断当前 version
            # ====================================================
            has_dead_dep = False
            if isinstance(deps, dict):
                for dep_pkg, dep_versions in deps.items():
                    if dep_pkg == 'incompatible':
                        continue
                    
                    if isinstance(dep_versions, dict):
                        valid_dep_vars = [v for v in dep_versions.keys() if v != 'incompatible']
                        if dep_versions.get('incompatible') is True and not valid_dep_vars:
                            has_dead_dep = True
                            break
            
            if has_dead_dep:
                continue 

            # 保存当前状态，进入沙箱尝试
            saved_versions = selected_versions.copy()
            selected_versions[pkg_name] = version
            
            # 递归处理所有子依赖
            all_deps_ok = True
            if isinstance(deps, dict):
                for dep_pkg, dep_versions in deps.items():
                    # 过滤掉非包名的内部标记键
                    if dep_pkg == 'incompatible':
                        continue
                        
                    if not select_version_recursive(dep_pkg, dep_versions, depth + 1):
                        all_deps_ok = False
                        break
            
            # 如果整棵子树成功，一路向上放行
            if all_deps_ok:
                return True 
            
            # 撤销尝试，循环将无缝进入 next version
            selected_versions.clear()
            selected_versions.update(saved_versions)

        # 5. 所有有效 version 都试完了依然不行，触发上层回溯
        return False

    # 启动解析
    for root_pkg, versions_data in compatibility_data.items():
        if not select_version_recursive(root_pkg, versions_data):
            print(f"[!] Could not find valid version combination. Failed at root package: {root_pkg}")
            return None

    print(f"[+] Successfully found a valid version combination!")
    return selected_versions




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

        if result.returncode == 0:
            print(f"[+] Exploit script completed successfully (exit code 0)")
            return True, result.stdout, result.stderr, result.returncode
        else:
            print(f"[-] Exploit script failed with exit code {result.returncode}")
            return False, result.stdout, result.stderr, result.returncode

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
                            work_dir: str,
                            compatibility_data: Dict = None) -> Dict:
    """Test a single version combination by creating venv and running exploit"""
    result = {
        'version_combination': version_combo.copy(),
        'actual_versions': {},
        'install_commands': [],
        'success': False,
        'error': None,
        'exploit_output': None,
        'stdout': None,
        'stderr': None,
        'returncode': None,
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
        exploit_success, stdout, stderr, returncode = run_exploit_script(venv_path, exploit_script, work_dir)
        exploit_output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n\nReturn code: {returncode}"
        result['exploit_output'] = exploit_output
        result['success'] = exploit_success
        result['stdout'] = stdout
        result['stderr'] = stderr
        result['returncode'] = returncode

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

    print(f"\n[*] Starting tests for {args.count} version combination(s) using '{args.mode}' mode")
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
    seen_combinations = set()

    max_attempts_per_combo = 100  # Maximum attempts to generate a unique combo

    while len(results) < args.count:
        i = len(results) + 1
        print(f"\n[*] Testing combination {i}/{args.count}")

        # Generate a unique version combination
        combo = None
        attempts = 0
        while attempts < max_attempts_per_combo:
            attempts += 1
            temp_combo = select_package_versions(compatibility_data, args.mode)

            # ==========================================
            # 修复 1：如果 DFS 直接返回 None，说明整棵树彻底无解！
            # 没必要再试 100 次了，直接 break 熔断。
            # ==========================================
            if temp_combo is None:
                print(f"[!] DFS exhaustively proved that NO valid combination exists in the compatibility data.")
                break

            # Create a hashable representation to check for duplicates
            combo_key = tuple(sorted(temp_combo.items()))

            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                combo = temp_combo
                print(f"[+] Generated unique combination after {attempts} attempt(s)")
                break
            else:
                print(f"[*] Duplicate combination found, regenerating... (attempt {attempts}/{max_attempts_per_combo})")

        # ==========================================
        # 修复 2：如果 combo 是 None，说明根本凑不出兼容版本。
        # 此时应该直接结束整个测试任务（break），而不是 continue 死循环！
        # ==========================================
        if combo is None:
            print(f"[!] Aborting test sequence due to failure in generating a valid combination.")
            break

        # Create a subdirectory for this test
        test_dir = os.path.join(base_work_dir, f"test_{i}")
        os.makedirs(test_dir, exist_ok=True)

        try:
            result = test_version_combination(
                args.exploit,
                combo,
                test_dir,
                compatibility_data
            )

            if result['error'] == "Exploit failed to trigger":
                # Parse stderr to get ImportError information
                stderr_content = result.get('stderr', '')
                import_error_info = parse_import_error(stderr_content)

                if import_error_info:
                    print(f"\n[*] Detected ImportError: {import_error_info['error_type']}")
                    print(f"    Missing: {import_error_info['missing_item']} from {import_error_info['full_module']}")
                    print(f"    Call chain: {' -> '.join(import_error_info['call_chain'])}")

                    # Verify all versions of this package in parallel
                    result_versions, is_new_package = verify_package_versions_for_missing_item(
                        package_name=import_error_info['package'],
                        missing_item=import_error_info['missing_item'],
                        full_module=import_error_info['full_module'],
                        test_dir=test_dir,
                        compatibility_data=compatibility_data,
                        call_chain=import_error_info['call_chain'],
                        combo=combo
                    )

                    if result_versions:
                        if not is_new_package:
                            # Existing package: remove versions that don't contain missing_item
                            print(f"\n[!] Failed versions for {import_error_info['package']}:")
                            for ver in result_versions:
                                print(f"    - {ver}")

                            # Modify compatibility_data to remove failed versions in the call chain
                            print(f"\n[*] Removing failed versions from compatibility_data along call chain...")
                            remove_failed_versions_from_call_chain(
                                compatibility_data,
                                import_error_info['call_chain'],
                                result_versions,
                                import_error_info['package'],
                                combo
                            )

                            print(f"[*] Will retry testing this combination after removing failed versions.")
                        else:
                            # New package: add versions that can be successfully installed
                            print(f"\n[+] Successfully installed versions for {import_error_info['package']} (new package):")
                            for ver in result_versions:
                                print(f"    - {ver}")

                            # Modify compatibility_data to add successful versions in the call chain
                            print(f"\n[*] Adding successful versions to compatibility_data along call chain...")
                            add_successful_versions_from_call_chain(
                                compatibility_data,
                                import_error_info['call_chain'],
                                result_versions,
                                import_error_info['package'],
                                combo
                            )

                            print(f"[*] Will retry testing this combination after adding successful versions.")

                        continue

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
            'total_combinations': len(results),
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
    print(f"\n[*] Total combinations tested: {len(results)}")
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

    # Save filtered compatibility_data
    compatibility_prefix = os.path.splitext(args.compatibility)[0]
    filtered_output_file = f"{compatibility_prefix}_filtered.json"
    with open(filtered_output_file, 'w') as f:
        json.dump(compatibility_data, f, indent=2)
    print(f"[*] Filtered compatibility data saved to: {filtered_output_file}")

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
