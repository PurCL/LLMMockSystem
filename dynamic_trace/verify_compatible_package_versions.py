#!/usr/bin/env python3
"""
Package Version Compatibility Tester - Refactored Version

Core Design:
1. API Parsing: Extract API calls/attributes and package name from apis.py file
2. Version Fetching: Retrieve all available versions from PyPI
3. Concurrent Environment Creation: Create isolated venv for each version and install package
4. API Detection: Use hasattr and inspect.signature to detect which APIs are supported in each venv
5. Compatibility Analysis: Compare with version_mapping to determine version compatibility

IMPORTANT NAMING CONVENTIONS:
============================

This module distinguishes between two types of package names:

1. import_name (Python module name):
   - Used in Python import statements: `import OpenSSL`, `from PIL import Image`
   - CASE-SENSITIVE: OpenSSL != openssl, PIL != pil
   - Used for: importlib.import_module, hasattr checks, sys.settrace
   - Examples: 'OpenSSL', 'PIL', 'cv2', 'sklearn'
   - PRESERVED AS-IS: Never use .lower() or convert - to _
   - Source: Extracted from *_apis.py filename (e.g., OpenSSL_apis.py -> 'OpenSSL')

2. pypi_name (PyPI package name):
   - Used for pip install and PyPI API queries
   - Examples: 'pyOpenSSL', 'Pillow', 'opencv-python', 'scikit-learn'
   - Obtained via: pypi_import_mapping[import_name] or fallback to import_name

The pypi_import_mapping.json bridges these two naming conventions.
Example mapping:
{
  "pyOpenSSL": "OpenSSL",    # pip install pyOpenSSL -> import OpenSSL
  "Pillow": "PIL",           # pip install Pillow -> from PIL import Image
  "opencv-python": "cv2",    # pip install opencv-python -> import cv2
  "scikit-learn": "sklearn"  # pip install scikit-learn -> import sklearn
}

Key Principles:
- NEVER convert import_name case (no .lower(), no - to _)
- ALWAYS use pypi_name for pip operations
- ALWAYS use import_name for Python import operations

Usage:
    python verify_compatible_package_versions.py <apis_file_path> [options]
"""

import argparse
import json
import subprocess
import sys
import os
import multiprocessing
import re
import ast
from pathlib import Path
from typing import Tuple, Optional, Union, List, Dict, Any, Callable, Set
from collections import defaultdict
import requests
import time
import traceback
import glob
import shutil
from packaging.version import parse as parse_version
import signal


# ============================================================
# Module 1: API Parser - Extract information from apis.py file
# ============================================================

class APIParser:
    """Responsible for parsing *_apis.py files and extracting package names and API information"""

    @staticmethod
    def parse_api_file(api_file_path: str) -> Dict[str, Any]:
        """
        Parse *_apis.py file

        Args:
            api_file_path: Path to the apis.py file

        Returns:
            {
                'package': str,           # package import_name (case-sensitive)
                'api_calls': List[Dict]   # List of API calls
            }

        Note:
            - package name is extracted from filename as import_name (e.g., 'OpenSSL', 'PIL')
            - Original case is preserved because Python imports are case-sensitive
            - No .lower() or - to _ conversion is performed
        """
        with open(api_file_path, 'r') as f:
            content = f.read()

        # Extract package name (preserve original case)
        # Filename format: {import_name}_apis.py
        filename = Path(api_file_path).stem
        package_name = filename.replace('_apis', '')

        # Parse all API calls
        api_calls = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('# API ID:'):
                api_info = APIParser._parse_single_api(lines, i)
                if api_info['api_call']:
                    api_calls.append(api_info['api_call'])
                i = api_info['next_index']
            else:
                i += 1

        return {
            'package': package_name,
            'api_calls': api_calls
        }

    @staticmethod
    def _parse_single_api(lines: List[str], start_index: int) -> Dict:
        """Parse single API definition, supports dynamic parsing of comment blocks, compatible with import types"""
        i = start_index

        # 1. Parse API ID
        api_id_match = re.match(r'# API ID:\s*(\d+)', lines[i].strip())
        api_id = api_id_match.group(1) if api_id_match else None
        i += 1

        api_type = "call"
        api_name = None
        caller_info = "unknown"

        # 2. Dynamically read comment lines until actual code is encountered
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and continue to next line
            if not line:
                i += 1
                continue

            # Non-empty and non-comment line indicates end of comment section, entering actual code
            if not line.startswith('#'):
                break

            if line.startswith('# Type:'):
                api_type = line.replace('# Type:', '').strip()
            elif line.startswith('# API:') or line.startswith('# Target:'):
                # Compatible with original # API: and new # Target:
                api_name = re.sub(r'^# (API|Target):', '', line).strip()
            elif line.startswith('# Call chain:'):
                caller_info = line.replace('# Call chain:', '').strip()
                if caller_info == 'None':
                    caller_info = 'unknown'
            elif line.startswith('# Attribute access'):
                caller_info = line.replace('# Attribute access', '').strip()
                if caller_info.startswith('('):
                    caller_info = caller_info[1:-1] if caller_info.endswith(')') else caller_info[1:]
                if not caller_info or caller_info == 'None':
                    caller_info = 'attribute access'

            i += 1

        # 3. Parse actual call code
        api_call = None
        if i < len(lines):
            call_line = lines[i].strip()
            is_attribute = (api_type == "attribute")
            is_import = (api_type == "import")
            is_decorator = call_line.startswith('@')

            # For import and attribute, don't parse args/kwargs to prevent AST errors
            if is_attribute or is_import:
                args, kwargs = [], {}
            else:
                args, kwargs = APIParser._parse_call_line(call_line)

            if api_name:
                api_call = {
                    'api_id': api_id,
                    'callee': api_name,
                    'args': args,
                    'kwargs': kwargs,
                    'caller': caller_info,
                    'is_decorator': is_decorator,
                    'is_attribute': is_attribute,
                    'is_import': is_import,       # New flag
                    'type': api_type              # Record original type for later use
                }
            i += 1

        return {
            'api_call': api_call,
            'next_index': i
        }

    @staticmethod
    def _parse_call_line(call_line: str) -> Tuple[List, Dict]:
        """Parse API call code and extract args and kwargs"""
        if call_line.strip().startswith('@'):
            call_line = call_line.strip()[1:]

        match = re.match(r'[\w\.]+\((.*)\)', call_line, re.DOTALL)
        if not match:
            return [], {}

        args_str = match.group(1)

        try:
            parse_str = f"f({args_str})"
            tree = ast.parse(parse_str)
            call_node = tree.body[0].value

            args = [APIParser._ast_node_to_value(arg) for arg in call_node.args]
            kwargs = {kw.arg: APIParser._ast_node_to_value(kw.value) for kw in call_node.keywords}

            return args, kwargs
        except Exception as e:
            print(f"Warning: Failed to parse call line: {call_line[:50]}... Error: {e}")
            return [], {}

    @staticmethod
    def _ast_node_to_value(node):
        """Convert AST node to Python value"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [APIParser._ast_node_to_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Tuple):
            return [APIParser._ast_node_to_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            result = {}
            for key, value in zip(node.keys, node.values):
                if key is None:
                    continue
                key_val = APIParser._ast_node_to_value(key)
                val_val = APIParser._ast_node_to_value(value)
                result[key_val] = val_val
            return result
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        elif isinstance(node, ast.Call):
            return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        else:
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                return str(node)


# ============================================================
# Module 2: Version Fetcher - Retrieve package version list from PyPI
# ============================================================

class PackageVersionFetcher:
    """Responsible for fetching all available versions of a package from PyPI"""

    def __init__(self, pypi_import_mapping: Dict[str, str] = None):
        """
        Initialize version fetcher

        Args:
            pypi_import_mapping: {import_name: pypi_package_name} mapping dictionary
                                Example: {'PIL': 'Pillow', 'cv2': 'opencv-python'}

        Note:
            - import_name: Module name used in Python code (case-sensitive), e.g., 'OpenSSL', 'PIL'
            - pypi_package_name: Package name on PyPI (used for pip install), e.g., 'pyOpenSSL', 'Pillow'
        """
        self.pypi_import_mapping = pypi_import_mapping or {}

    def get_pypi_package_name(self, import_name: str) -> str:
        """
        Get package name on PyPI (may differ from import name)

        Args:
            import_name: Name used when importing in Python (case-sensitive)
                        Example: 'PIL', 'OpenSSL', 'cv2'

        Returns:
            Package name on PyPI (used for pip install and PyPI API queries)
            Example: 'Pillow', 'pyOpenSSL', 'opencv-python'

        Note:
            If not found in mapping, returns original import_name
            No case conversion or - to _ replacement is performed
        """
        if import_name in self.pypi_import_mapping:
            pypi_name = self.pypi_import_mapping[import_name]
            print(f"[Mapping] Using PyPI package name '{pypi_name}' for import name '{import_name}'")
            return pypi_name
        # Return original name without any conversion
        return import_name

    def fetch_all_versions(self, package_name: str) -> List[str]:
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
            pypi_package_name = self.get_pypi_package_name(package_name)
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
            return set()


# ============================================================
# Module 3: Environment Manager - Create venv and install packages
# ============================================================

class VenvManager:
    """
    Responsible for creating and managing virtual environments

    Note:
        - Uses pypi_import_mapping to convert import_name to pypi_name for installation
        - Example: import_name='PIL' -> pypi_name='Pillow' -> pip install Pillow
    """

    def __init__(self, pypi_import_mapping: Dict[str, str] = None):
        """
        Args:
            pypi_import_mapping: {import_name: pypi_package_name} mapping
        """
        self.pypi_import_mapping = pypi_import_mapping or {}

    def setup_venv(self, work_dir: str, venv_name: str = '.venv') -> Tuple[bool, str]:
        """
        Create isolated virtual environment

        Args:
            work_dir: Working directory
            venv_name: Name of venv directory

        Returns:
            (Success flag, Error message)
        """
        try:
            venv_path = os.path.join(work_dir, venv_name)
            # Create isolated environment variables
            venv_creation_env = {
                'PATH': os.environ.get('PATH', ''),
                'HOME': os.environ.get('HOME', ''),
                'USER': os.environ.get('USER', ''),
                'LOGNAME': os.environ.get('LOGNAME', ''),
                'PYTHONHOME': '',
                'PYTHONPATH': '',
                'PYTHONUSERBASE': '',
                'PYTHONSTARTUP': '',
                'PYTHONOPTIMIZE': '',
                'PYTHONDONTWRITEBYTECODE': '1',
                'PYTHONNOUSERSITE': '1',
                'LANG': os.environ.get('LANG', 'C.UTF-8'),
                'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
            }

            # Create new venv
            result = subprocess.run(
                ['python3', '-m', 'venv', '--clear', venv_path],
                capture_output=True,
                text=True,
                timeout=120,
                env=venv_creation_env
            )

            if result.returncode != 0:
                return False, f"Failed to create venv: {result.stderr}"

            # Verify venv was created successfully
            pip_path = os.path.join(venv_path, 'bin', 'pip')
            if not os.path.exists(pip_path):
                return False, f"Venv created but pip not found at {pip_path}"

            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Timeout while creating venv"
        except Exception as e:
            return False, f"Error creating venv: {str(e)}"

    def install_package(self,
                        package_name: Union[str, List[str], Dict[str, Optional[str]]],
                        venv_path: str,
                        version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Install one or more packages in venv.
        Installing multiple packages together significantly improves speed and allows pip to resolve dependencies uniformly.

        Args:
            package_name: Can be one of three formats:
                - str: Single import_name, e.g., "numpy", "PIL", "OpenSSL"
                - List[str]: List of import_names, e.g., ["numpy", "PIL"]
                - Dict[str, Optional[str]]: Mapping from import_name to version, e.g., {"numpy": "1.24.0", "PIL": None}
            venv_path: Path to venv
            version: Version number for single package installation. Ignored if package_name is a list or dict.

        Returns:
            (Success flag, Error message)

        Note:
            - Input package_name is import_name (case-sensitive)
            - Will be converted to PyPI package name via pypi_import_mapping for installation
            - Example: import_name='PIL' -> pypi_name='Pillow' -> pip install Pillow==xxx
        """
        # 1. Normalize input, convert to {import_name: version} dictionary format
        packages_to_install = {}
        if isinstance(package_name, str):
            packages_to_install[package_name] = version
        elif isinstance(package_name, list):
            for pkg in package_name:
                packages_to_install[pkg] = None
        elif isinstance(package_name, dict):
            packages_to_install = package_name
        else:
            return False, f"Unsupported package_name type: {type(package_name)}"

        if not packages_to_install:
            return True, ""  # No packages to install

        # 2. Handle import_name to PyPI name mapping and generate final installation specs
        package_specs = []
        for import_name, pkg_ver in packages_to_install.items():
            # Find mapping: import_name -> pypi_name
            if hasattr(self, 'pypi_import_mapping') and import_name in self.pypi_import_mapping:
                pypi_pkg_name = self.pypi_import_mapping[import_name]
                print(f"  [Mapping] Using PyPI package name '{pypi_pkg_name}' for import name '{import_name}'")
            else:
                # If no mapping exists, use import_name as PyPI package name directly
                # Note: No case conversion or - to _ replacement
                pypi_pkg_name = import_name

            if pkg_ver:
                package_specs.append(f"{pypi_pkg_name}=={pkg_ver}")
            else:
                package_specs.append(pypi_pkg_name)

        specs_str = " ".join(package_specs)
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        tmp_dir = os.path.join(venv_path, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)

        # 3. Create isolated environment variables
        pip_install_env = {
            'PATH': f"{os.path.join(venv_path, 'bin')}:{os.environ.get('PATH', '')}",
            'HOME': os.environ.get('HOME', ''),
            'VIRTUAL_ENV': venv_path,
            'PYTHONHOME': '',
            'PYTHONPATH': '',
            'PYTHONUSERBASE': '',
            'PYTHONDONTWRITEBYTECODE': '1', # Save disk I/O
            'PYTHONNOUSERSITE': '1',        # Strict environment isolation
            'PIP_CONFIG_FILE': '/dev/null',
            'PIP_REQUIRE_VIRTUALENV': '1',
            'PIP_NO_INPUT': '1',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1', # Skip network check, improve efficiency
            'PIP_QUIET': '1',                     # Keep multi-process output clean
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
        }

        # 4. Execute installation
        cmd = [pip_path, 'install'] + package_specs
    
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=pip_install_env,
                )

                if result.returncode != 0:
                    stderr_lower = result.stderr.lower()

                    # Identify permanent errors like pip dependency conflicts or package not found, stop retrying
                    permanent_errors = [
                        "resolutionimpossible",
                        "conflict",
                        "no matching distribution",
                        "could not find a version"
                    ]

                    if any(error in stderr_lower for error in permanent_errors):
                        return False, f"Package conflict or not found for {specs_str}:\n{result.stderr}"

                    # If maximum retries reached, return final error
                    if attempt == max_retries:
                        return False, f"Failed to install {specs_str} after {max_retries} attempts:\n{result.stderr}"

                    # For network issues or other failures, wait and retry
                    time.sleep(3)
                    continue

                # Installation successful
                return True, ""
                
            except subprocess.TimeoutExpired:
                if attempt == max_retries:
                    return False, f"Timeout while installing {specs_str} after {max_retries} attempts"
                time.sleep(3)
                continue
                
            except Exception as e:
                if attempt == max_retries:
                    return False, f"Error installing packages after {max_retries} attempts: {str(e)}"
                time.sleep(3)
                continue

    def get_package_version(self, package_name, venv_path):
        """
        Get the version of a package in the specified virtual environment.

        Args:
            package_name: import_name (case-sensitive)
            venv_path: Virtual environment path

        Returns:
            Version string, or None if package is not installed

        Note:
            - Will try to convert import_name to pypi_name via mapping for query
            - Example: import_name='PIL' -> query version of 'Pillow'
        """
        # Convert import_name to pypi_name (if mapping exists)
        if hasattr(self, 'pypi_import_mapping') and package_name in self.pypi_import_mapping:
            pypi_package_name = self.pypi_import_mapping[package_name]
        else:
            pypi_package_name = package_name

        # Determine python/pip executable path in virtual environment (compatible with Linux/Mac and Windows)
        if os.name == 'nt':
            pip_executable = os.path.join(venv_path, 'Scripts', 'pip.exe')
        else:
            pip_executable = os.path.join(venv_path, 'bin', 'pip')

        try:
            # Execute pip show <pypi_package_name>
            result = subprocess.run(
                [pip_executable, "show", pypi_package_name],
                capture_output=True,
                text=True,
                check=False
            )

            # If package doesn't exist, pip show returns non-zero status code with no normal output
            if result.returncode != 0:
                return None

            # Parse Version line from output
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    # Return version number after colon, remove extra whitespace (e.g., "Version: 1.2.3" -> "1.2.3")
                    return line.split(":", 1)[1].strip()

        except Exception as e:
            print(f"Exception occurred while detecting package version: {e}")
            return None

        return None


# ============================================================
# Module 5: Compatibility Analysis Module - Analyze Version Compatibility
# ============================================================

class CompatibilityAnalyzer:
    """Responsible for analyzing version compatibility (based on version_mapping)"""

    @staticmethod
    def load_version_mapping(package_name: str, apis_dir: str) -> Dict:
        """
        Load version_mapping file

        Args:
            package_name: Package name
            apis_dir: API directory

        Returns:
            version_mapping dictionary, returns empty dict if not exists
        """
        mapping_file = os.path.join(apis_dir, f"{package_name}_version_mapping.json")

        if not os.path.exists(mapping_file):
            return {}

        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading version mapping file: {e}")
            return {}

    @staticmethod
    def analyze_compatibility(
        supported_api_ids: List[str],
        unsupported_api_ids: Dict[str, str],
        version_mapping: Dict,
        version: str
    ) -> Dict:
        """
        Analyze version compatibility

        Args:
            supported_api_ids: List of supported API IDs
            unsupported_api_ids: List of unsupported API IDs
            version_mapping: version mapping dictionary
            version: Current version number

        Returns:
            Compatibility analysis result
        """
        result = {
            'status': 'incompatible',
            'compatible_upstream_versions': [],
            'error_message': '',
            'incompatible_upstream_versions': []
        }

        if not version_mapping:
            # User code scenario: check if there are unsupported APIs
            if unsupported_api_ids:
                result['status'] = 'incompatible'
                result['error_message'] = f"Version {version} does not support required API IDs: {unsupported_api_ids}"
            else:
                result['status'] = 'compatible'
        else:
            # Dependency package scenario: check which target versions are compatible
            compatible_upstream_versions = []
            incompatible_upstream_versions = []

            # Convert supported_api_ids to set (handle complex types)
            supported_set = set()
            for api_id in supported_api_ids:
                if isinstance(api_id, (dict, list)):
                    supported_set.add(json.dumps(api_id, sort_keys=True))
                else:
                    supported_set.add(str(api_id))

            # Check each target version
            for upstream_version, required_api_ids in version_mapping.items():
                # Convert required_api_ids to set
                required_set = set()
                for api_id in required_api_ids:
                    if isinstance(api_id, (dict, list)):
                        required_set.add(json.dumps(api_id, sort_keys=True))
                    else:
                        required_set.add(str(api_id))

                # Check if all required APIs are in supported
                if required_set.issubset(supported_set):
                    compatible_upstream_versions.append(upstream_version)
                else:
                    # If not a subset, missing dependent APIs, record as incompatible
                    incompatible_upstream_versions.append(upstream_version)

            # Write results to result dictionary
            result['compatible_upstream_versions'] = compatible_upstream_versions
            result['incompatible_upstream_versions'] = incompatible_upstream_versions

            if compatible_upstream_versions:
                result['status'] = 'compatible'
            else:
                result['status'] = 'incompatible'
                result['error_message'] = f"Version {version} is not compatible with any dependent package versions"

        return result


# ============================================================
# Module 6: Version Processing Worker - Concurrent Processing of Single Version
# ============================================================

class VersionWorker:
    """Responsible for processing the complete workflow of a single version"""

    def __init__(
        self,
        pypi_import_mapping: Dict[str, str]
    ):
        self.venv_manager = VenvManager(pypi_import_mapping)

    def process_single_version(self, args: Tuple) -> Dict:
        """
        Process complete workflow for a single version

        Args:
            args: (package_name, version, api_calls, work_dir, version_index)
            Note: version parameter is already normalized (special characters replaced)

        Returns:
            Processing result dictionary
        """

        package_name, version, api_calls, work_dir, version_index = args

        venv_name = '.venv'
        # version is already normalized, use directly
        version_dir = os.path.join(work_dir, f'{package_name}_version_{version}')

        result = {
            'version': version,
            'status': 'incompatible',
            'api_check': False,
            'error_message': '',
            'stdout': '',
            'stderr': '',
            'supported_api_ids': list(),
            'unsupported_api_ids': dict(),
            'compatible_upstream_versions': [],
            'incompatible_upstream_versions': [],
        }

        print(f"\n[Worker {version_index}] {'='*60}")
        print(f"[Worker {version_index}] Processing {package_name} version {version}")
        print(f"[Worker {version_index}] Version directory: {version_dir}")
        print(f"[Worker {version_index}] {'='*60}")

        try:
            # Step 1: Create version directory
            print(f"[Worker {version_index}] Step 1: Creating version directory...")

            # If directory already exists, clear it (delete) first
            if os.path.exists(version_dir):
                print(f"[Worker {version_index}] Directory already exists, clearing old files...")
                shutil.rmtree(version_dir)

            # Recreate clean directory
            os.makedirs(version_dir, exist_ok=True)
            print(f"[Worker {version_index}] ✓ Version directory created and is empty")

            # Step 2: Create venv
            print(f"[Worker {version_index}] Step 2: Setting up isolated virtual environment...")
            success, error = self.venv_manager.setup_venv(version_dir, venv_name)
            if not success:
                result['error_message'] = f"Venv setup failed: {error}"
                print(f"[Worker {version_index}] ✗ {result['error_message']}")
                return result
            print(f"[Worker {version_index}] ✓ Isolated virtual environment created")

            # Step 3: Install package
            venv_path = os.path.join(version_dir, venv_name)
            print(f"[Worker {version_index}] Step 3: Installing {package_name}=={version}...")
            success, error = self.venv_manager.install_package(
                package_name=package_name,
                venv_path=venv_path,
                version=version
            )
            if not success:
                result['error_message'] = f"Installation failed: {error}"
                print(f"[Worker {version_index}] ✗ {result['error_message']}")
                return result
            print(f"[Worker {version_index}] ✓ Package installed successfully")

            # Step 4 & 5: Generate and run API checks (individual API detection + auto dependency resolution)
            print(f"[Worker {version_index}] Step 4 & 5: Running API checks one by one with auto-healing...")
            python_path = os.path.join(venv_path, 'bin', 'python')
            pip_path = os.path.join(venv_path, 'bin', 'pip')

            max_retries = 10
            # Keep accumulated dictionary as previously installed dependencies are still valid for later APIs
            accumulated_packages = {package_name: version}
            
            supported_ids = set()
            failed_api_ids = dict()

            # Test each API independently
            for api_index, api_call in enumerate(api_calls, 1):
                api_id = api_call.get('api_id')
                api_path = api_call.get('callee', 'Unknown API')

                print(f"[Worker {version_index}] Testing API {api_index}/{len(api_calls)}: {api_path} (ID: {api_id})")

                attempt = 0
                while attempt <= max_retries:
                    # 1. Generate check script for this single API only
                    script_content = self._generate_hasattr_check_script(
                        package_name, api_call  # Note: passing single api_call here
                    )

                    # 2. Run script
                    # Expected: compatible returns 0 (success=True), incompatible or crash returns non-0
                    success, stdout, stderr = self._run_check_script(
                        script_content=script_content,
                        python_path=python_path,
                        version_dir=version_dir
                    )

                    # 3. Analyze result
                    if success:
                        supported_ids.add(api_id)
                        print(f"  [Worker {version_index}] ✓ API {api_id} is compatible.")
                        break  # Current API test passed, exit retry loop, process next API

                    # Failure case, try to capture missing package name with regex
                    missing_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr)

                    if missing_match:
                        missing_pkg = missing_match.group(1)
                        print(f"  [Worker {version_index}] Warning: Missing runtime dependency: '{missing_pkg}'")

                        print(f"  [Worker {version_index}] Auto-installing: {missing_pkg} (Attempt {attempt+1}/{max_retries})...")

                        install_success, error_msg = self.venv_manager.install_package(
                            package_name=missing_pkg,
                            venv_path=venv_path,
                        )

                        if install_success:
                            current_package_name_version = self.venv_manager.get_package_version(
                                package_name=package_name,
                                venv_path=venv_path
                            )
                            if not current_package_name_version == version:
                                install_success, error_msg = self.venv_manager.install_package(
                                    package_name=package_name,
                                    venv_path=venv_path,
                                    version=version
                                )
                                if not install_success:
                                    err_brief = error_msg.strip().split('\n')[-1][:150]
                                    failed_api_ids[api_id] = f"✗ Failed to re-install {package_name}=={version} after installing {missing_pkg}: {err_brief}"
                                    print(f"  [Worker {version_index}] {failed_api_ids[api_id]}")
                                    break  # Give up current API, exit retry loop
                            print(f"  [Worker {version_index}] ✓ Installed successfully, retrying API {api_id}...")
                            attempt += 1
                            continue  # Environment fixed, go back to while loop start, test current API again
                        else:
                            # Complete installation failure
                            err_brief = error_msg.strip().split('\n')[-1][:150]
                            failed_api_ids[api_id] = f"✗ Failed to auto-install {missing_pkg}: {err_brief}"
                            print(f"  [Worker {version_index}] {failed_api_ids[api_id]}")
                            break  # Give up current API, exit retry loop
                    else:
                        # Non-package-missing failure (real API incompatibility, type error, or Segfault crash)
                        # Prioritize capturing '✗ incompatible' info from stdout, fall back to stderr
                        err_brief = ""
                        incompatible_match = re.search(r"✗ incompatible:\s*(.*)", stdout)
                        if incompatible_match:
                            err_brief = f"Incompatible: {incompatible_match.group(1).strip()}"
                        else:
                            # If complete crash
                            err_brief = f"Crash/Error: {stderr.strip().split(chr(10))[-1][:150] if stderr else stdout.strip()[-150:]}"

                        failed_api_ids[api_id] = err_brief
                        print(f"  [Worker {version_index}] ✗ API {api_id} failed: {err_brief}")
                        break  # Record error, exit retry loop, process next API

                else:
                    # while loop finished normally (reached max_retries without successful break)
                    failed_api_ids[api_id] = f"✗ Maximum retries reached ({max_retries}). Giving up."
                    print(f"  [Worker {version_index}] {failed_api_ids[api_id]}")

            # Step 6: Parse results
            print(f"[Worker {version_index}] Step 6: Consolidating results...")

            # Convert to downstream required data structure
            result['supported_api_ids'] = sorted(list(supported_ids))
            result['unsupported_api_ids'] = failed_api_ids

            print(f"[Worker {version_index}] ✓ Supported APIs Count: {len(supported_ids)}")
            print(f"[Worker {version_index}] ✗ Unsupported APIs Count: {len(failed_api_ids)}")

            # Step 7: Analyze compatibility
            print(f"[Worker {version_index}] Step 7: Analyzing compatibility...")
            version_mapping = CompatibilityAnalyzer.load_version_mapping(package_name, work_dir)

            compatibility_result = CompatibilityAnalyzer.analyze_compatibility(
                result['supported_api_ids'], result['unsupported_api_ids'].keys(), version_mapping, version
            )

            result['status'] = compatibility_result['status']
            result['compatible_upstream_versions'] = compatibility_result['compatible_upstream_versions']
            result['incompatible_upstream_versions'] = compatibility_result['incompatible_upstream_versions']
            result['error_message'] = compatibility_result.get('error_message', '')
            result['api_check'] = (compatibility_result['status'] == 'compatible')

            if result['status'] == 'compatible':
                if version_mapping:
                    print(f"[Worker {version_index}] ✓ Version {version} is compatible with versions: {result['compatible_upstream_versions']}")
                else:
                    print(f"[Worker {version_index}] ✓ Version {version} is compatible with user code")
            else:
                print(f"[Worker {version_index}] ✗ {result['error_message']}")

            # Initialize a dictionary to save trace results
            result['api_traces'] = {}

            if compatibility_result['status'] == 'compatible':
                # Trace each API independently
                for api_index, api_call in enumerate(api_calls, 1):
                    api_id = api_call.get('api_id')
                    api_path = api_call.get('callee', 'Unknown API')

                    # [New]: Check if current entry is import type, skip analysis directly
                    if api_call.get('type') == 'import' or api_call.get('is_import'):
                        continue

                    if api_id not in result['supported_api_ids']: # Only analyze APIs in supported_api_ids
                        continue

                    print(f"[Worker {version_index}] Tracing API {api_index}/{len(api_calls)}: {api_path} (ID: {api_id})")

                    # 1. Generate check script
                    script_content = self._generate_trace_script(package_name, api_call)

                    # 2. Run script
                    success, stdout, stderr = self._run_trace_script(
                        script_content=script_content,
                        python_path=python_path,
                        version_dir=version_dir
                    )

                    # 3. Analyze and save result
                    if success:
                        print(f"  [Worker {version_index}] ✓ API {api_id} traced successfully.")
                        # Convert stdout (call chain separated by newlines) to list and save
                        trace_list = [line.strip() for line in stdout.splitlines() if line.strip()]

                        # Add judgment for stderr
                        status_msg = f"success (with {stderr.strip()})" if stderr.strip() else "success"

                        result['api_traces'][api_id] = {
                            "callee": api_path,
                            "trace": trace_list,
                            "status": status_msg
                        }
                    else:
                        # Extract last line of error message
                        err_text = stderr if stderr else stdout
                        if not err_text:
                            err_text = "Unknown error occurred during tracing."
                        err_brief = f"Crash/Error: {err_text.strip().splitlines()[-1][:150]}"
                        print(f"  [Worker {version_index}] ✗ API {api_id} failed: {err_brief}")

                        result['api_traces'][api_id] = {
                            "callee": api_path,
                            "trace": [],
                            "status": err_brief
                        }

            return result

        except Exception as e:
            print(f"[Worker {version_index}] ✗ Unexpected error: {e}")
            traceback.print_exc()
            result['error_message'] = f"Unexpected error: {str(e)}"
            return result

        finally:
            # Step 8: Clean up
            print(f"[Worker {version_index}] Step 8: Cleaning up version directory...")
            try:
                # ignore_errors=True is equivalent to rm -rf error tolerance, silently ignores even if directory doesn't exist or files are locked
                shutil.rmtree(version_dir, ignore_errors=True)
                print(f"[Worker {version_index}] ✓ Directory cleaned up")
            except Exception as e:
                print(f"[Worker {version_index}] Warning: Failed to clean up directory: {e}")

    def _generate_hasattr_check_script(
        self,
        package: str,
        api_call: dict
    ) -> str:
        """
        Generate Python script for checking single API / Import detection.
        Returns code 0 on success, non-0 on failure. Missing package errors are written to stderr for outer Worker to capture.

        Args:
            package: import_name (case-sensitive), e.g., 'OpenSSL', 'PIL'
            api_call: API call information dictionary

        Note:
            - package parameter is import_name, used for importlib.import_module
            - No .lower() or - to _ conversion on package
        """
        callee = api_call.get('callee', '')
        is_attribute = api_call.get('is_attribute', False)
        is_import = api_call.get('is_import', False)  # New: extract import flag
        args_py = repr(api_call.get('args', []))
        kwargs_py = repr(api_call.get('kwargs', {}))

        # Build script with f-string, directly hardcode parameters in script, no need for command-line args
        script_content = f'''#!/usr/bin/env python3
import sys
import inspect
import importlib

def check_api(api_path: str, is_attribute: bool, is_import: bool, args: list, kwargs: dict) -> tuple:
    parts = api_path.split('.')
    if len(parts) < 1:
        return False, f"Invalid API path: {{api_path}}"

    obj = None

    # Try import from longest path to shortest path, solves deep import like keras.models.load_model
    # Also perfectly supports scenarios like from a.b import c where import target is an object
    for i in range(len(parts), 0, -1):
        mod_name = '.'.join(parts[:i])
        try:
            obj = importlib.import_module(mod_name)
            for attr in parts[i:]:
                if not hasattr(obj, attr):
                    return False, f"Attribute '{{attr}}' not found in {{mod_name}}"
                obj = getattr(obj, attr)
            break

        except ModuleNotFoundError as e:
            if e.name == mod_name:
                continue
            # Missing underlying dependency, raise upward
            raise e

    if obj is None:
        return False, f"Could not import any base module for {{api_path}}"

    # === New: If cross-library import check, success if target object can be resolved ===
    if is_import:
        return True, "Import successful"

    if is_attribute:
        return True, "Attribute exists"

    if not callable(obj):
        return False, f"{{api_path}} is not callable"

    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError) as e:
        return True, f"Cannot inspect signature (assumed compatible): {{e}}"

    try:
        sig.bind_partial(*args, **kwargs)
        return True, "API signature matches perfectly"
    except TypeError as e:
        return False, f"Signature mismatch: {{str(e)}}"

def main():
    api_path = {repr(callee)}
    is_attribute = {repr(is_attribute)}
    is_import = {repr(is_import)}
    args = {args_py}
    kwargs = {kwargs_py}
    
    try:
        compatible, message = check_api(api_path, is_attribute, is_import, args, kwargs)
        if compatible:
            print(f"✓ compatible: {{message}}")
            sys.exit(0)  # Success, return code 0
        else:
            print(f"✗ incompatible: {{message}}")
            sys.exit(1)  # API incompatible/module not found, return code 1

    except ModuleNotFoundError as e:
        # Format error output to stderr for outer layer regex to capture precisely
        sys.stderr.write(f"ModuleNotFoundError: No module named '{{e.name}}'\\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Runtime error: {{str(e)}}\\n")
        sys.exit(3)

if __name__ == "__main__":
    main()
'''
        return script_content

    def _run_check_script(
        self,
        script_content: str,
        python_path: str,
        version_dir: str
    ) -> Tuple[bool, str, str]:
        """
        Run single API check script

        Returns:
            (success status, stdout, stderr)
        """
        try:
            check_script_path = os.path.join(version_dir, 'api_check_script.py')
            with open(check_script_path, 'w') as f:
                f.write(script_content)
            os.chmod(check_script_path, 0o755)

            result = subprocess.run(
                [python_path, check_script_path],
                capture_output=True,
                text=True,
                timeout=60,  # Since only checking one API, significantly reduce timeout (was 300 seconds)
                cwd=version_dir
            )

            # returncode 0 means sys.exit(0) was triggered in script, i.e., fully compatible
            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            partial_out = e.stdout if isinstance(e.stdout, str) else ""
            partial_err = e.stderr if isinstance(e.stderr, str) else ""
            return False, partial_out, f"Timeout (60s) for single API.\nPartial stderr: {partial_err[:200]}"

        except Exception as e:
            return False, "", f"Error running API check script: {str(e)}"

    def _generate_trace_script(
        self,
        package: str,
        api_call: dict
    ) -> str:
        """
        Generate cross-library call analysis script (Boundary Tracer)
        Clean version: records all cross-library calls and imports, automatically uses Mock fallback retry when original parameters error.
        (New: capture underlying cross-library import behavior via sys.addaudithook)

        Args:
            package: import_name (case-sensitive), e.g., 'OpenSSL', 'keras'
            api_call: API call information dictionary

        Note:
            - package parameter is import_name, used for boundary detection
            - No case conversion on package
        """
        callee = api_call.get('callee', '')
        args_py = repr(api_call.get('args', []))
        kwargs_py = repr(api_call.get('kwargs', {}))
        
        script_content = f'''#!/usr/bin/env python3
import sys
import importlib
import inspect
import json
from unittest.mock import MagicMock

def get_api_object(api_path: str):
    parts = api_path.split('.')
    obj = None
    for i in range(len(parts), 0, -1):
        mod_name = '.'.join(parts[:i])
        try:
            obj = importlib.import_module(mod_name)
            for attr in parts[i:]:
                obj = getattr(obj, attr)
            break
        except ModuleNotFoundError as e:
            if e.name == mod_name:
                continue
            raise e
    return obj

def safe_repr(val):
    """Safely convert parameter to string, prevent crash from Tensor or large objects"""
    try:
        val_type = type(val).__name__
        if "Tensor" in val_type or "Variable" in val_type:
            shape = getattr(val, 'shape', '?')
            dtype = getattr(val, 'dtype', '?')
            return f"<{{val_type}}: shape={{{{shape}}}}, dtype={{{{dtype}}}}>"
        s = repr(val)
        return s[:200] + "..." if len(s) > 200 else s
    except Exception:
        return "<Unrepresentable Object>"

def generate_mock_kwargs(func_obj):
    """Generate MagicMock fake parameters based on function signature"""
    kwargs = {{}}
    try:
        sig = inspect.signature(func_obj)
        for name, param in sig.parameters.items():
            if param.default == inspect.Parameter.empty and name not in ('self', 'args', 'kwargs'):
                kwargs[name] = MagicMock()
    except Exception:
        pass
    return kwargs

def main():
    api_path = {repr(callee)}
    source_pkg = {repr(package)}
    args = {args_py}
    kwargs = {kwargs_py}
    
    recorded_apis = set()
    recorded_imports = set()

    # === New: Import Audit Hook ===
    def import_audit_hook(event, args):
        if event == "import":
            module_name = args[0]

            # Trace call stack back to find which actual module initiated this import
            frame = sys._getframe()
            caller_mod = ""
            caller_func = ""
            while frame:
                mod = frame.f_globals.get("__name__", "")
                # Filter out Python underlying importlib mechanism and our own generated main wrapper layer
                if mod and not mod.startswith("importlib.") and mod not in ("builtins", "__main__"):
                    caller_mod = mod
                    caller_func = frame.f_code.co_name
                    break
                frame = frame.f_back

            # Boundary discovered! Caller is source_pkg, and target module to import is not source_pkg
            if caller_mod.startswith(source_pkg) and not module_name.startswith(source_pkg):
                downstream_pkg = module_name.split('.')[0]
                import_signature = f"{{caller_mod}} -> {{module_name}}"

                if import_signature not in recorded_imports:
                    recorded_imports.add(import_signature)

                    import_record = {{
                        "type": "import",
                        "downstream_package": downstream_pkg,
                        "downstream_module": module_name,
                        "called_by": f"{{caller_mod}}.{{caller_func}}"
                    }}
                    # Output dedicated [BOUNDARY_IMPORT] prefix to distinguish from function calls
                    print(f"[BOUNDARY_IMPORT]{{json.dumps(import_record)}}")

    # Register system-level audit hook
    sys.addaudithook(import_audit_hook)
    # ============================================

    def tracer(frame, event, arg):
        if event == 'call':
            caller_frame = frame.f_back
            if not caller_frame:
                return tracer

            caller_mod = caller_frame.f_globals.get("__name__", "")
            callee_mod = frame.f_globals.get("__name__", "")

            # Boundary discovered! Caller is source_pkg, Callee is not source_pkg
            if caller_mod.startswith(source_pkg) and not callee_mod.startswith(source_pkg):
                func_name = frame.f_code.co_name
                api_signature = f"{{callee_mod}}.{{func_name}}"
                downstream_pkg = callee_mod.split('.')[0] if callee_mod else "builtins"

                # As long as not recorded, record print and pass
                if api_signature not in recorded_apis:
                    recorded_apis.add(api_signature)

                    try:
                        arg_info = inspect.getargvalues(frame)
                        args_dict = {{}}
                        for arg_name in arg_info.args:
                            args_dict[arg_name] = safe_repr(arg_info.locals.get(arg_name))

                        if arg_info.varargs:
                            args_dict[arg_info.varargs] = safe_repr(arg_info.locals.get(arg_info.varargs))
                        if arg_info.keywords:
                            args_dict[arg_info.keywords] = safe_repr(arg_info.locals.get(arg_info.keywords))
                    except Exception as e:
                        args_dict = {{"error": f"Failed to extract args: {{str(e)}}"}}

                    call_record = {{
                        "type": "call",
                        "downstream_package": downstream_pkg,
                        "downstream_api": api_signature,
                        "called_by": f"{{caller_mod}}.{{caller_frame.f_code.co_name}}",
                        "args": args_dict
                    }}
                    print(f"[BOUNDARY_CALL]{{json.dumps(call_record)}}")

        return tracer

    # --- Execution Controller ---
    def execute_with_trace(*run_args, **run_kwargs):
        nonlocal recorded_apis
        recorded_apis.clear()  # Clear deduplication set before each retry to ensure new trace can be printed completely

        original_trace = sys.gettrace()
        try:
            sys.settrace(tracer)
            func_obj(*run_args, **run_kwargs)
            return True, "Execution completed normally"
        except Exception as e:
            # Capture regular parameter or runtime errors
            return False, f"{{type(e).__name__}}: {{str(e)}}"
        finally:
            sys.settrace(original_trace)

    try:
        func_obj = get_api_object(api_path)
    except Exception as e:
        sys.stderr.write(f"Import error: {{str(e)}}\\n")
        sys.exit(3)

    is_import_test = {api_call.get('is_import', False)}
    
    if is_import_test:
        if func_obj is not None:
            print("Import successful!")
            sys.exit(0)
        else:
            sys.exit(1)

    if func_obj is None or not callable(func_obj):
        sys.stderr.write(f"{{api_path}} is not callable or not found\\n")
        sys.exit(1)

    # 1. Try original parameters
    success, msg = execute_with_trace(*args, **kwargs)

    # 2. If original parameters trigger exception, automatically enter Mock fallback strategy
    if not success:
        sys.stderr.write(f"Original args failed with: {{msg}}. Retrying with MagicMock...\\n")
        mock_kwargs = generate_mock_kwargs(func_obj)
        success_mock, msg_mock = execute_with_trace(**mock_kwargs)

        if not success_mock:
            sys.stderr.write(f"Mock args also failed with: {{msg_mock}}\\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
'''
        return script_content

    def _run_trace_script(self,
        script_content: str,
        python_path: str,
        version_dir: str):

        try:
            trace_script_path = os.path.join(version_dir, 'api_trace_script.py')
            with open(trace_script_path, 'w') as f:
                f.write(script_content)
            os.chmod(trace_script_path, 0o755)

            result = subprocess.run(
                [python_path, trace_script_path],
                capture_output=True,
                text=True,
                timeout=60,  # Since only checking one API, significantly reduce timeout (was 300 seconds)
                cwd=version_dir
            )

            # returncode 0 means sys.exit(0) was triggered in script, i.e., fully compatible
            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            partial_out = e.stdout if isinstance(e.stdout, str) else ""
            partial_err = e.stderr if isinstance(e.stderr, str) else ""
            return False, partial_out, f"Timeout (60s) for tracing single API.\nPartial stderr: {partial_err[:200]}"

        except Exception as e:
            return False, "", f"Error running API trace script: {str(e)}"


# ============================================================
# Module 7: Result Saving Module - Save Test Results
# ============================================================

class ResultSaver:
    """Responsible for saving test results to JSON file"""

    @staticmethod
    def save_results(
        package_name: str,
        results: List[Dict],
        apis_dir: str,
        version_mapping_file: str
    ):
        """
        Save test results

        Args:
            package_name: Package name
            results: Result list
            apis_dir: API file directory
            version_mapping_file: version_mapping file path
        """
        if not results:
            print("No results to save")
            return

        compatiblity_file = os.path.join(apis_dir, f"{package_name}_compatibility_results.json")
        if os.path.exists(version_mapping_file):
            # Dependency package scenario: output version combinations
            compatible_version_combinations = []
            incompatible_upstream_versions_sets = []

            for r in results:
                if r and r.get('status') == 'compatible' and r.get('compatible_upstream_versions'):
                    for upstream_version in r['compatible_upstream_versions']:
                        compatible_version_combinations.append({
                            'downstream_version': r['version'],
                            'upstream_version': upstream_version,
                            'supported_api_ids': r.get('supported_api_ids', [])
                        })
                incompatible_upstream_versions_set = set(r['incompatible_upstream_versions'])
                incompatible_upstream_versions_sets.append(incompatible_upstream_versions_set)

            common_incompatible_upstream_versions = list(set.intersection(*incompatible_upstream_versions_sets))

            output_data = {
                'type': 'dependency_compatibility',
                'package_name': package_name,
                'compatible_version_combinations': compatible_version_combinations,
                'total_combinations': len(compatible_version_combinations),
                'incompatible_upstream_versions': sorted(common_incompatible_upstream_versions)
            }

            with open(compatiblity_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"\n{'='*60}")
            print(f"Results saved to: {compatiblity_file}")
            print(f"{'='*60}")
            print(f"Summary:")
            print(f"  Total compatible version combinations: {len(compatible_version_combinations)}")
        else:
            # User code scenario: output compatible/incompatible versions
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
                            'unsupported_api_ids': r.get('unsupported_api_ids', dict()),
                            'error_message': r.get('error_message', '')
                        })

            output_data = {
                'type': 'user_code_compatibility',
                'package_name': package_name,
                'compatible': compatible_versions,
                'incompatible': incompatible_versions
            }

            with open(compatiblity_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            # Calculate statistics
            total = len(results)
            compatible_count = len(compatible_versions)
            incompatible_count = len(incompatible_versions)
            compatibility_rate = f"{(compatible_count/total*100):.2f}%" if total > 0 else "0%"

            print(f"\n{'='*60}")
            print(f"Results saved to: {compatiblity_file}")
            print(f"{'='*60}")
            print(f"Summary:")
            print(f"  Total versions tested: {total}")
            print(f"  Compatible: {compatible_count}")
            print(f"  Incompatible: {incompatible_count}")
            print(f"  Compatibility rate: {compatibility_rate}")

        ResultSaver.generate_api_logs_and_mapping(results, package_name, apis_dir)

    @staticmethod
    def generate_api_logs_and_mapping(results, package_name, apis_dir):
        """
        Process all version traces, deduplicate and generate downstream library api_log and version_mapping

        :param results: List containing trace results for each version
        :param package_name: Target library name (e.g., 'keras')
        :param apis_dir: Parent directory for API logs output
        """
        # 1. Create output directory
        api_log_dir = os.path.join(apis_dir, f"{package_name}_api_log")
        os.makedirs(api_log_dir, exist_ok=True)

        # Used to store mapping from downstream package to specific API info
        # Structure: package_to_apis[downstream_pkg][unique_key] = api_info_dict
        package_to_apis = defaultdict(dict)

        # Used to store which newly assigned downstream API IDs each version contains
        # Structure: version_mapping[version] = set(api_ids)
        version_mapping = defaultdict(set)

        global_api_id = 1

        def normalize_args(args_dict):
            """Clean dynamic memory addresses and Mock IDs in args for precise deduplication"""
            args_str = json.dumps(args_dict, sort_keys=True)
            # Replace Python object memory addresses: 0x7fa6c2da8e50 -> 0xXXX
            args_str = re.sub(r'0x[0-9a-fA-F]+', '0xXXX', args_str)
            # Replace MagicMock id: id='140299277876144' -> id='XXX'
            args_str = re.sub(r"id='\d+'", "id='XXX'", args_str)
            return args_str

        print(f"[*] Aggregating and analyzing cross-library boundary calls...")

        # 2. Iterate through all results, extract and deduplicate downstream API calls
        for result in results:
            # Assume your result has version identifier, if not, adjust to your version field
            version = result.get('version', 'unknown_version')
            api_traces = result.get('api_traces', {})

            for original_api_id, trace_data in api_traces.items():
                trace_list = trace_data.get('trace', [])

                for line in trace_list:
                    # Intercept both CALL and IMPORT
                    if line.startswith('[BOUNDARY_CALL]') or line.startswith('[BOUNDARY_IMPORT]'):
                        prefix = '[BOUNDARY_CALL]' if line.startswith('[BOUNDARY_CALL]') else '[BOUNDARY_IMPORT]'
                        json_str = line.replace(prefix, '').strip()

                        try:
                            call_record = json.loads(json_str)
                        except json.JSONDecodeError:
                            continue

                        downstream_pkg = call_record.get('downstream_package', 'unknown')

                        if downstream_pkg in sys.stdlib_module_names:
                            # Ignore standard library calls or imports
                            continue

                        record_type = call_record.get('type', 'call')
                        called_by = call_record.get('called_by', 'unknown')

                        if record_type == 'call':
                            downstream_api = call_record.get('downstream_api', 'unknown')
                            args_dict = call_record.get('args', {})
                            # Generate deduplication unique key: API name + cleaned parameter structure
                            norm_args_str = normalize_args(args_dict)
                            unique_key = f"call::{downstream_api}::{norm_args_str}"
                        else:
                            # For import type, target is specific module
                            downstream_api = call_record.get('downstream_module', 'unknown')
                            args_dict = {}  # import behavior has no parameters
                            # Generate deduplication unique key: only need to mark as import and add module name
                            unique_key = f"import::{downstream_api}"

                        # Discover brand new downstream API call or cross-library import
                        if unique_key not in package_to_apis[downstream_pkg]:
                            package_to_apis[downstream_pkg][unique_key] = {
                                "api_id": global_api_id,
                                "type": record_type,          # Mark type for convenient downstream generation of corresponding test script format
                                "api_name": downstream_api,   # Function signature for call, module name for import
                                "called_by": called_by,
                                "args_dict": args_dict,       # Empty dict for import
                                "versions": set()
                            }
                            global_api_id += 1

                        # Bind this API/Import with current Version
                        api_info = package_to_apis[downstream_pkg][unique_key]
                        api_info["versions"].add(version)
                        version_mapping[version].add(api_info["api_id"])

        # 3. Generate {downstream_package}_apis.py and corresponding version_mapping.json by downstream package
        print(f"[*] Generating API Log scripts (found {global_api_id - 1} unique calls in total)...")
        for pkg, apis in package_to_apis.items():

            # ==================== 3a. Generate {pkg}_apis.py ====================
            file_path = os.path.join(api_log_dir, f"{pkg}_apis.py")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# API Calls for {pkg}\n")
                f.write(f"# Auto-extracted boundary calls originating from {package_name}\n")
                f.write(f"import importlib\n\n")  # New: ensure downstream script can run dynamic imports smoothly

                # Sort by API ID in ascending order to ensure file looks neat
                sorted_apis = sorted(apis.values(), key=lambda x: x["api_id"])
                for api in sorted_apis:
                    api_id = api["api_id"]
                    versions_str = ", ".join(sorted(api["versions"]))
                    api_name = api["api_name"]
                    called_by = api["called_by"]
                    api_type = api.get("type", "call")  # Get type, defaults to call

                    # Generate different test code based on different types
                    if api_type == "call":
                        # Reassemble dict into kwargs style string
                        args_parts = []
                        for k, v in api["args_dict"].items():
                            args_parts.append(f"{k}={v}")
                        args_str = ", ".join(args_parts)
                        # Generate code form similar to keras.layers.Input(...)
                        executable_code = f"{api_name}({args_str})"
                    elif api_type == "import":
                        # For import behavior, use dynamic import to verify compatibility (success if no ModuleNotFoundError)
                        executable_code = f"importlib.import_module('{api_name}')"
                    else:
                        executable_code = f"# Unknown API type: {api_type}"

                    f.write(f"# API ID: {api_id}\n")
                    f.write(f"# Found in versions: {versions_str}\n")
                    f.write(f"# Type: {api_type}\n")
                    f.write(f"# Target: {api_name}\n")
                    f.write(f"# Call chain: {called_by}\n")
                    f.write(f"{executable_code}\n\n")

            # ==================== 4. Generate {pkg}_version_mapping.json ====================
            # Dynamically count api_id set corresponding to each version in current downstream package
            pkg_version_mapping = {}
            for api in apis.values():
                api_id = api["api_id"]
                for ver in api["versions"]:
                    if ver not in pkg_version_mapping:
                        pkg_version_mapping[ver] = set()
                    pkg_version_mapping[ver].add(api_id)

            # Convert set to sorted list for json serialization
            final_mapping = {
                ver: sorted(list(ids))
                for ver, ids in pkg_version_mapping.items()
            }

            # Modify filename to be named after current downstream package pkg
            mapping_file = os.path.join(api_log_dir, f"{pkg}_version_mapping.json")
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(final_mapping, f, indent=4)

        print(f"[+] Successfully generated API Log directory: {api_log_dir}")


# ============================================================
# Module 8: Main Controller - Coordinate Overall Workflow
# ============================================================

class CompatibilityTester:
    """Main controller: coordinate overall test workflow"""

    def __init__(self, num_workers: int = None):
        # Load PyPI import mapping
        script_dir = Path(__file__).parent
        self.pypi_import_mapping = self._load_pypi_import_mapping(
            str(script_dir / "pypi_import_mapping.json")
        )

        # Initialize each module
        self.api_parser = APIParser()
        self.version_fetcher = PackageVersionFetcher(self.pypi_import_mapping)

        # Determine worker count
        self.num_workers = num_workers

    def run(
        self,
        apis_file_path: str,
        output_file: str = None,
        limit: int = None
    ):
        """
        Run compatibility test

        Args:
            apis_file_path: apis.py file path
            output_file: Output file path (optional)
            limit: Limit number of versions to test (optional)
        """
        print(f"{'='*60}")
        print(f"Package Version Compatibility Tester")
        print(f"{'='*60}\n")

        # Step 1: Parse API file
        print(f"Step 1: Parsing APIs file: {apis_file_path}")
        parsed_data = self.api_parser.parse_api_file(apis_file_path)
        package_name = parsed_data['package']
        api_calls = parsed_data['api_calls']

        print(f"  ✓ Found package: {package_name}")
        print(f"  ✓ Found {len(api_calls)} API calls ({len(set(c['callee'] for c in api_calls))} unique APIs)\n")

        # Step 2: Get all versions
        print(f"Step 2: Fetching available versions from PyPI...")
        # versions = self.version_fetcher.fetch_all_versions(package_name)
        versions = ['2.53.0']  # For debugging, use above line in production

        if not versions:
            print(f"  ✗ No versions found for package '{package_name}'")
            sys.exit(1)


        print(f"  ✓ Will test {limit} versions\n")

        # Step 3: Test all versions in parallel
        print(f"Step 3: Testing all versions in parallel ({self.num_workers} workers)")
        apis_dir = os.path.dirname(os.path.abspath(apis_file_path))

        results = []
        try:
            worker = VersionWorker(self.pypi_import_mapping)
            next_idx = 0  # Track global next version index to feed to multiprocessing

            with multiprocessing.Pool(processes=self.num_workers) as pool:

                # [New] Outer round loop: test round by round as long as not all versions tested
                while next_idx < len(versions):
                    active_tasks = []
                    batch_results = []
                    batch_success_count = 0

                    # 1. Initialize current batch: first put at most limit versions into process pool
                    initial_batch_size = min(limit, len(versions) - next_idx)
                    for _ in range(initial_batch_size):
                        arg_tuple = (package_name, versions[next_idx], api_calls, apis_dir, next_idx)
                        task = pool.apply_async(worker.process_single_version, args=(arg_tuple,))
                        active_tasks.append(task)
                        next_idx += 1

                    # 2. Poll current batch: continue monitoring as long as tasks running in pool
                    while active_tasks:
                        still_active = []

                        for task in active_tasks:
                            if task.ready():
                                try:
                                    result = task.get()

                                    # -- Check if installation failed --
                                    is_failed = False
                                    if isinstance(result, dict):
                                        error_msg = result.get('error_message', '')
                                        if error_msg and "Installation failed:" in error_msg:
                                            print(f"Warning: Skipping: captured {error_msg.splitlines()[0]}, trying next version...")
                                            is_failed = True

                                    if is_failed:
                                        # Failed: if backup versions available, get next version to fill, ensure batch can gather enough valid results
                                        if next_idx < len(versions):
                                            arg_tuple = (package_name, versions[next_idx], api_calls, apis_dir, next_idx)
                                            new_task = pool.apply_async(worker.process_single_version, args=(arg_tuple,))
                                            still_active.append(new_task)
                                            next_idx += 1
                                        continue

                                    # -- Success case (whether compatible or incompatible) --
                                    batch_results.append(result)
                                    batch_success_count += 1

                                except Exception as worker_exception:
                                    # -- Check if uncaught installation exception was thrown --
                                    if "Installation failed:" in str(worker_exception):
                                        print(f"Warning: worker threw Installation failed exception, skipping, trying next...")
                                        if next_idx < len(versions):
                                            arg_tuple = (package_name, versions[next_idx], api_calls, apis_dir, next_idx)
                                            new_task = pool.apply_async(worker.process_single_version, args=(arg_tuple,))
                                            still_active.append(new_task)
                                            next_idx += 1
                                    else:
                                        # Encountered unexpected other serious error, throw up
                                        raise worker_exception
                            else:
                                # Task not finished, keep in queue
                                still_active.append(task)

                        # Update running task list, release CPU briefly
                        active_tasks = still_active
                        if active_tasks:
                            time.sleep(0.1)

                    # ====== Current batch execution completed ======
                    # Append batch results to total result list
                    results.extend(batch_results)
                    print(f"\nCurrent batch execution completed. Successfully produced {batch_success_count} results.")

                    # [New] Check batch results: whether at least one 'compatible' included
                    has_compatible = False
                    for r in batch_results:
                        if isinstance(r, dict) and r.get('status') == 'compatible':
                            has_compatible = True
                            break

                    if has_compatible:
                        print(f"Found compatible version in this batch, stopping further detection.")
                        break  # Exit outermost while loop, end testing
                    else:
                        if next_idx < len(versions):
                            print(f"Warning: No compatible version found in this batch (all incompatible etc.).")
                            print(f"Continuing to extract at most {limit} from remaining versions for next batch test...\n")
                        else:
                            print(f"All backup versions exhausted, no compatible version found in the end.")
                            break

        except KeyboardInterrupt:
            print("\n\nProcessing interrupted by user")
            # Only execute force kill cleanup when user manually stops with Ctrl+C
            try:
                pool.terminate()
                pool.join()
            except:
                pass
            sys.exit(1)
        except Exception as e:
            print(f"Fatal error during processing: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

        print(f"  ✓ Processed a total of {len(results)} valid results.\n")

        # Step 4: Save results
        print(f"Step 4: Saving results...")

        version_mapping_file = os.path.join(apis_dir, f"{package_name}_version_mapping.json")

        ResultSaver.save_results(package_name, results, apis_dir, version_mapping_file)

    @staticmethod
    def _load_pypi_import_mapping(mapping_file: str) -> Dict[str, str]:
        """Load PyPI import mapping"""
        if not os.path.exists(mapping_file):
            print(f"Warning: pypi_import_mapping.json not found at {mapping_file}")
            return {}

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                original_mapping = json.load(f)

            # Reverse mapping: {import_name: pypi_package_name}
            reversed_mapping = {}
            for pypi_name, import_name in original_mapping.items():
                reversed_mapping[import_name] = pypi_name

            print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file}")
            return reversed_mapping
        except Exception as e:
            print(f"Warning: Failed to load mapping file {mapping_file}: {e}")
            return {}


# ============================================================
# Main Entry Point
# ============================================================

def main():
    # Force use spawn method for better isolation
    multiprocessing.set_start_method('spawn', force=True)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Test package versions for API compatibility using pyright'
    )
    parser.add_argument(
        'apis_file',
        type=str,
        help='Path to the *_apis.py file (e.g., /path/to/keras_apis.py)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path (default: saved in same directory as apis file)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit the number of versions to test (for testing purposes)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of worker processes (default: 10)'
    )

    args = parser.parse_args()

    # Verify file path
    apis_file_path = os.path.abspath(args.apis_file)
    if not os.path.exists(apis_file_path):
        print(f"Error: APIs file not found: {apis_file_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(apis_file_path):
        print(f"Error: Path is not a file: {apis_file_path}", file=sys.stderr)
        sys.exit(1)

    # Create tester and run
    try:
        tester = CompatibilityTester(num_workers=args.workers)
        tester.run(
            apis_file_path=apis_file_path,
            output_file=args.output,
            limit=args.limit
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
