import json
import os
import sys
import urllib.request
import itertools
import llm_client
import shutil
import multiprocessing
import subprocess
from functools import partial
from execution_trace_formatter import (
    format_enhanced_resolution_report,
    save_enhanced_report,
    analyze_package_usage_frequency
)

# =====================================================================
# ⚙️ Configuration
# =====================================================================
# Global variable to store PyPI import mapping (loaded from JSON file)
# Format: {pypi_package_name: import_name}
# Example: {"pyyaml": "yaml", "pyjwt": "jwt", "python-dotenv": "dotenv"}
PYPI_IMPORT_MAPPING = {}

# =====================================================================
# 🗺️ PyPI Import Mapping Loader
# =====================================================================
def load_pypi_import_mapping(mapping_file="pypi_import_mapping.json"):
    """
    Load PyPI package name to import name mapping from JSON file.
    This is the same mapping used in llm_real_hook.py for package alias resolution.

    Returns:
        dict: {pypi_package_name: import_name}
    """
    if not os.path.exists(mapping_file):
        print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")
        return {}

    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"[🗺️ Mapping Loader] Loaded {len(mapping)} package mappings from {mapping_file}")
        return mapping
    except Exception as e:
        print(f"⚠️ Failed to load mapping file {mapping_file}: {e}")
        return {}

def _resolve_pypi_name_from_import(import_name):
    """
    Resolve an import name to its PyPI package name using the mapping.
    This is the reverse operation of llm_real_hook.py's _resolve_import_name.

    Args:
        import_name: The import name used in code (e.g., 'yaml', 'jwt', 'dotenv')

    Returns:
        The PyPI package name (e.g., 'PyYAML', 'PyJWT', 'python-dotenv'),
        or the original import_name if no mapping found
    """
    if not PYPI_IMPORT_MAPPING:
        return import_name

    # Normalize the import name for lookup
    normalized = import_name.lower().replace('-', '_')

    # Build reverse mapping: import_name -> list of pypi_package_names
    # We need to handle cases where multiple PyPI packages map to the same import name
    reverse_mapping = {}
    for pypi_pkg, import_alias in PYPI_IMPORT_MAPPING.items():
        import_key = import_alias.lower().replace('-', '_')
        if import_key not in reverse_mapping:
            reverse_mapping[import_key] = []
        reverse_mapping[import_key].append(pypi_pkg)

    # Try direct lookup with normalized name
    if normalized in reverse_mapping:
        candidates = reverse_mapping[normalized]
        # If multiple candidates, prefer the one with hyphens (more canonical)
        # and prefer shorter names (base packages over variants)
        candidates_sorted = sorted(candidates, key=lambda x: (
            0 if '-' in x else 1,  # Prefer hyphenated names
            len(x),                # Prefer shorter names
            x                      # Alphabetical as tiebreaker
        ))
        return candidates_sorted[0]

    # Try with hyphen version
    hyphenated = import_name.lower().replace('_', '-')
    if hyphenated in reverse_mapping:
        candidates = reverse_mapping[hyphenated]
        candidates_sorted = sorted(candidates, key=lambda x: (
            0 if '-' in x else 1,
            len(x),
            x
        ))
        return candidates_sorted[0]

    # Try original case-insensitive lookup
    for import_alias, pypi_name in PYPI_IMPORT_MAPPING.items():
        if import_alias.lower() == import_name.lower():
            return pypi_name

    # Check if it's already a PyPI package name (direct match)
    for pypi_name in PYPI_IMPORT_MAPPING.keys():
        if pypi_name.lower() == normalized or pypi_name.lower() == hyphenated:
            return pypi_name

    # No mapping found, return original name
    return import_name

def resolve_import_to_pypi_name(import_name, pypi_import_mapping):
    """
    Resolve an import name to its PyPI package name using the mapping.
    This mirrors the logic in llm_mock_hook.py's _resolve_import_name function.

    Args:
        import_name: The import name used in code (e.g., 'yaml', 'jwt')
        pypi_import_mapping: Dict loaded from pypi_import_mapping.json

    Returns:
        The PyPI package name, or the original import_name if no mapping found
    """
    # Normalize the import name for lookup
    normalized = import_name.lower().replace('-', '_')

    # Create reverse mapping: import_name -> pypi_package_name
    reverse_mapping = {v: k for k, v in pypi_import_mapping.items()}

    # Try direct lookup with normalized name
    if normalized in reverse_mapping:
        resolved = reverse_mapping[normalized]
        return resolved

    # Try with hyphen version
    hyphenated = import_name.lower().replace('_', '-')
    if hyphenated in reverse_mapping:
        resolved = reverse_mapping[hyphenated]
        return resolved

    # Try original case-insensitive lookup
    for import_alias, pypi_name in reverse_mapping.items():
        if import_alias.lower() == import_name.lower():
            return pypi_name

    # Check if it's already a PyPI package name (direct match)
    if normalized in pypi_import_mapping:
        return normalized
    if hyphenated in pypi_import_mapping:
        return hyphenated

    # Check with the loaded mapping using the new resolver
    return _resolve_pypi_name_from_import(import_name)

# =====================================================================
# 📦 PyPI Fetcher & Deductive Logic
# =====================================================================
def get_pypi_versions(package_name, resolve_name=True, return_canonical_name=False, filter_prereleases=False, return_release_dates=False):
    """
    Fetch all available versions for a package in real-time via the PyPI API.

    Args:
        package_name: Package name (import name or PyPI name)
        resolve_name: If True, resolve import name to PyPI name. If False, use package_name as-is.
        return_canonical_name: If True, return tuple (canonical_name, versions). If False, return only versions.
        filter_prereleases: If True, filter out pre-release versions (alpha, beta, rc). Default False.
        return_release_dates: If True, also return release dates for each version.

    Returns:
        If return_canonical_name=False and return_release_dates=False: List of version strings sorted newest to oldest
        If return_canonical_name=True: Tuple of (canonical_package_name, list of versions or dict with dates)
        If return_release_dates=True: Dict {version: release_date}
    """
    pypi_name = _resolve_pypi_name_from_import(package_name) if resolve_name else package_name
    print(f"🔍 Fetching all versions for '{pypi_name}' from PyPI...")

    url = f"https://pypi.org/pypi/{pypi_name}/json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            # Get the official/canonical package name from PyPI
            canonical_name = data["info"]["name"]

            # Get all versions from releases
            all_releases = data["releases"]

            # Optionally filter out pre-release versions
            version_data = {}
            for version, release_files in all_releases.items():
                if filter_prereleases:
                    v_lower = version.lower()
                    # Skip versions with common pre-release identifiers
                    if any(pre in v_lower for pre in ['rc', 'beta', 'alpha', 'dev', 'a0', 'b0', 'c0']):
                        continue

                # Get release date from first file in the release
                release_date = "unknown"
                if release_files and len(release_files) > 0:
                    upload_time = release_files[0].get('upload_time_iso_8601') or release_files[0].get('upload_time')
                    if upload_time:
                        release_date = upload_time.split('T')[0]  # Extract date part

                version_data[version] = release_date

            sorted_versions = sorted(version_data.keys(), reverse=True)

            if return_release_dates:
                if return_canonical_name:
                    return canonical_name, version_data
                return version_data
            else:
                if return_canonical_name:
                    return canonical_name, sorted_versions
                return sorted_versions
    except Exception as e:
        print(f"⚠️ Failed to fetch versions for '{pypi_name}': {e}")
        if return_canonical_name:
            if return_release_dates:
                return package_name, {}
            return package_name, []
        if return_release_dates:
            return {}
        return []


def get_all_pypi_versions_simple(package_name, requirements_versions=None):
    """
    Get all available versions from PyPI, optionally filtered by requirements.txt constraints.

    This function replaces the LLM-based version inference. Instead of using LLM to guess
    which versions are compatible, we simply fetch all available versions from PyPI,
    and the script_based_validator will test them to determine compatibility.

    Args:
        package_name: Name of the package (import name or PyPI name)
        requirements_versions: Optional list of versions from requirements.txt to constrain search

    Returns:
        List of version strings to test
    """
    pypi_name = _resolve_pypi_name_from_import(package_name)
    canonical_name, all_versions = get_pypi_versions(pypi_name, resolve_name=False, return_canonical_name=True)

    if not all_versions:
        print(f"   ⚠️ No versions found on PyPI for '{canonical_name}'")
        return []

    print(f"   📦 Found {len(all_versions)} versions on PyPI for '{canonical_name}'")

    # If requirements.txt specifies versions, use those
    if requirements_versions:
        print(f"   📋 Filtering by requirements.txt: {requirements_versions}")
        # Validate that the required versions exist in PyPI
        validated_versions = []
        for req_ver in requirements_versions:
            # Try exact match first
            if req_ver in all_versions:
                validated_versions.append(req_ver)
            else:
                # Try case-insensitive match
                req_ver_normalized = req_ver.strip().lower()
                for pypi_ver in all_versions:
                    if pypi_ver.strip().lower() == req_ver_normalized:
                        validated_versions.append(pypi_ver)
                        break

        if validated_versions:
            print(f"   ✅ Using {len(validated_versions)} versions from requirements.txt")
            return validated_versions
        else:
            print(f"   ⚠️ No matching versions from requirements.txt, using all {len(all_versions)} versions")
            return all_versions

    # Return all versions if no constraints
    print(f"   ✅ Using all {len(all_versions)} available versions")
    return all_versions


def parse_api_calls_from_text(api_calls_text):
    """
    Parse .api_calls.json content (plain text format) to extract API signatures.

    Format example:
    semver.VersionInfo()
    semver.VersionInfo.parse(version="0.5.0")
    bitmath.Byte()

    Returns a dict: {package_name: [list of API signatures]}
    """
    # List of exact non-package identifiers to filter out
    NON_PACKAGE_NAMES = {
        'var',           # Variable names
        'function',      # Function references
        'type',          # Type references
        'method',        # Method references
        'object',        # Object references
        'self',          # Instance references
        'cls',           # Class references
    }

    api_by_package = {}
    total_api_calls = 0

    for line in api_calls_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        total_api_calls += 1

        # Extract package name (first part before first dot)
        if '.' in line:
            package_name = line.split('.')[0]

            # Filter out non-package identifiers (exact match)
            if package_name.lower() in NON_PACKAGE_NAMES:
                continue

            # Filter out private/magic methods
            if package_name.startswith('__'):
                continue

            # Only keep top-level package names
            if package_name not in api_by_package:
                api_by_package[package_name] = []

            # Only add unique signatures
            if line not in api_by_package[package_name]:
                api_by_package[package_name].append(line)

    print(f"📊 Total API calls found: {total_api_calls}")
    print(f"📦 After filtering, {len(api_by_package)} unique packages identified")

    return api_by_package


def get_versions_for_validation(package_name, api_signatures, requirements_versions=None, return_enhanced_info=False):
    """
    Get package versions that need to be validated.

    This function replaces the old LLM-based inference. Instead of using LLM to guess compatible
    versions, we simply fetch all available versions from PyPI. The actual compatibility testing
    will be done by script_based_validator.

    Args:
        package_name: Name of the package
        api_signatures: List of API call signatures (for enhanced info only)
        requirements_versions: Optional list of versions from requirements.txt (checked against PyPI)
        return_enhanced_info: If True, return dict with versions and metadata

    Returns:
        If return_enhanced_info=False: List of version strings to test
        If return_enhanced_info=True: Dict with keys: versions, reasoning, api_usage, release_dates
    """
    pypi_name = _resolve_pypi_name_from_import(package_name)
    canonical_name, all_versions = get_pypi_versions(pypi_name, resolve_name=False, return_canonical_name=True)

    # Also fetch release dates if enhanced info is requested
    release_dates = {}
    if return_enhanced_info:
        _, release_dates = get_pypi_versions(pypi_name, resolve_name=False, return_canonical_name=True, return_release_dates=True)

    if not all_versions:
        if return_enhanced_info:
            return {
                "versions": [],
                "reasoning": {"confidence": "none", "reasoning": "Package not found on PyPI"},
                "api_usage": api_signatures if api_signatures else [],
                "release_dates": {}
            }
        return []

    print(f"📦 Fetching versions for '{package_name}'...")
    print(f"   📊 Found {len(all_versions)} versions on PyPI")

    # NEW: Check if requirements.txt version exists in PyPI
    if requirements_versions:
        print(f"   📋 Requirements.txt specifies: {requirements_versions}")

        # Validate that requirements.txt versions exist in PyPI
        missing_versions = []
        for req_ver in requirements_versions:
            if req_ver not in all_versions:
                missing_versions.append(req_ver)

        if missing_versions:
            # Version not found in PyPI - return only requirements.txt version
            print(f"   ⚠️ WARNING: Version(s) {missing_versions} not found on PyPI!")
            print(f"   ⚠️ This indicates a problem with the requirements.txt version")
            print(f"   📌 Returning only requirements.txt version: {requirements_versions}")

            if return_enhanced_info:
                return {
                    "versions": requirements_versions,  # Return requirements.txt version even if not on PyPI
                    "reasoning": {
                        "confidence": "error",
                        "reasoning": f"Requirements.txt version(s) {missing_versions} not found on PyPI. Possible issues: version typo, package renamed, or version yanked from PyPI."
                    },
                    "api_usage": api_signatures if api_signatures else [],
                    "release_dates": {},
                    "error": "version_not_on_pypi"
                }
            return requirements_versions
        else:
            print(f"   ✅ Requirements.txt version(s) found on PyPI")
            print(f"   🔄 Will test all {len(all_versions)} available versions")
    else:
        print(f"   ✅ Testing all {len(all_versions)} available versions")

    versions_to_test = all_versions

    if return_enhanced_info:
        return {
            "versions": versions_to_test,
            "reasoning": {
                "confidence": "pending_validation",
                "reasoning": "All versions fetched from PyPI, will be validated by script-based testing"
            },
            "api_usage": api_signatures if api_signatures else [],
            "release_dates": {v: release_dates.get(v, "unknown") for v in versions_to_test}
        }

    return versions_to_test


def _resolve_requirements_package_name(package_name):
    """
    Resolve a package name from requirements.txt to its canonical PyPI name by querying PyPI API.
    This handles cases where requirements.txt uses lowercase names (e.g., 'pyjwt')
    but PyPI requires the canonical form (e.g., 'PyJWT').

    Args:
        package_name: Package name as written in requirements.txt

    Returns:
        The canonical PyPI package name (with correct casing)
    """
    # Query PyPI API to get the canonical name
    canonical_name, _ = get_pypi_versions(package_name, resolve_name=False, return_canonical_name=True)
    return canonical_name


def load_requirements_txt(requirements_path):
    """
    Load requirements.txt and parse package names and their version constraints.
    Package names are normalized to their canonical PyPI names by querying PyPI API.

    Returns: dict {canonical_package_name: [list of allowed versions]} or {canonical_package_name: None} if all versions allowed
    """
    if not os.path.exists(requirements_path):
        print(f"⚠️ requirements.txt not found at: {requirements_path}")
        return {}

    # First pass: collect all package names
    raw_requirements = []
    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Simple parsing - handle package==version or package>=version, etc.
            if '==' in line:
                parts = line.split('==')
                package_name = parts[0].strip()
                version = parts[1].strip()
                raw_requirements.append((package_name, [version]))
            else:
                # If no specific version, we'll fetch all versions later
                # Remove version specifiers
                package_name = line.split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0].strip()
                raw_requirements.append((package_name, None))

    # Second pass: normalize all package names to canonical form (with progress indicator)
    print(f"🔍 Normalizing {len(raw_requirements)} package name(s) from requirements.txt...")
    requirements = {}
    name_mappings = []

    for idx, (package_name, versions) in enumerate(raw_requirements, 1):
        # Show progress for large requirements files
        if len(raw_requirements) > 10:
            print(f"   [{idx}/{len(raw_requirements)}] Resolving '{package_name}'...")

        # Normalize package name to canonical PyPI name by querying PyPI
        canonical_name = _resolve_requirements_package_name(package_name)
        if canonical_name != package_name:
            name_mappings.append((package_name, canonical_name))
        requirements[canonical_name] = versions

    # Report any package name normalizations
    if name_mappings:
        print(f"\n🗺️ Normalized {len(name_mappings)} package name(s):")
        for original, canonical in name_mappings:
            print(f"   • '{original}' → '{canonical}'")

    return requirements


def _process_package_with_api(args):
    """
    Worker function to process a single package with API signatures.
    Used for parallel processing.

    Args:
        args: tuple of (idx, total, import_name, api_signatures, pypi_import_mapping, requirements_packages, requirements, testscript_dir)

    Returns:
        tuple: (matched_req_pkg, versions, error_msg) or None if package not in requirements
    """
    idx, total, import_name, api_signatures, pypi_import_mapping, requirements_packages, requirements, testscript_dir = args

    try:
        # Resolve import name to PyPI package name using the mapping
        pypi_name = resolve_import_to_pypi_name(import_name, pypi_import_mapping)

        print(f"\n[{idx}/{total}] Processing import: {import_name}")
        if pypi_name != import_name:
            print(f"   🗺️ Resolved to PyPI package: {pypi_name}")
        print(f"   📝 Total API calls: {len(api_signatures)}")

        # Check if this PyPI package is in requirements.txt
        matched_req_pkg = None
        for req_pkg in requirements_packages:
            if (req_pkg.lower().replace('-', '_') == pypi_name.lower().replace('-', '_') or
                req_pkg.lower().replace('_', '-') == pypi_name.lower().replace('_', '-')):
                matched_req_pkg = req_pkg
                break

        if not matched_req_pkg:
            print(f"   ⚠️ Package '{pypi_name}' not found in requirements.txt, skipping")
            return None

        print(f"   ✅ Matched to requirements.txt package: {matched_req_pkg}")

        # Get version constraints from requirements.txt if available
        req_versions = requirements.get(matched_req_pkg)
        if req_versions:
            print(f"   📋 Constrained by requirements.txt: {req_versions}")
        else:
            print(f"   📋 In requirements.txt (all versions allowed)")

        # Get versions to validate (with enhanced info)
        enhanced_result = get_versions_for_validation(import_name, api_signatures, req_versions,
                                                       return_enhanced_info=True)

        versions = enhanced_result.get('versions', [])
        if versions:
            print(f"   ✅ Result: {len(versions)} compatible versions found")
            print(f"   📌 Top versions: {versions[:5]}")
            return (matched_req_pkg, enhanced_result, None)
        else:
            print(f"   ⚠️ Result: No compatible versions found")
            return (matched_req_pkg, enhanced_result, None)

    except Exception as e:
        error_msg = f"Error processing {import_name}: {str(e)}"
        print(f"   ❌ {error_msg}")
        return (import_name, [], error_msg)


def _process_package_without_api(args):
    """
    Worker function to process a single package without API signatures.
    Used for parallel processing.

    Args:
        args: tuple of (idx, total, package_name, requirements)

    Returns:
        tuple: (package_name, enhanced_result, error_msg)
    """
    idx, total, package_name, requirements = args

    try:
        print(f"\n[{idx}/{total}] Processing package: {package_name}")

        # Get version constraints from requirements.txt
        req_versions = requirements.get(package_name)

        # Fetch all versions from PyPI with release dates
        canonical_name, release_dates = get_pypi_versions(
            package_name, resolve_name=False, return_canonical_name=True, return_release_dates=True
        )
        all_versions = list(release_dates.keys())

        if all_versions:
            print(f"   📦 Found {len(all_versions)} versions on PyPI for '{canonical_name}'")
            print(f"   🔍 Testing installability with 'uv pip install'...")

            # Test each version with uv pip install
            installable_versions = []
            tested_count = 0

            for version in all_versions:
                tested_count += 1
                # Test if version can be installed with uv
                import subprocess
                import tempfile
                import shutil

                # Create a temporary venv for testing
                temp_venv = tempfile.mkdtemp(prefix=f"test_venv_{canonical_name}_{version}_")
                try:
                    # Create venv
                    result_create = subprocess.run(
                        ["uv", "venv", temp_venv],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result_create.returncode == 0:
                        # Try to install the package
                        result_install = subprocess.run(
                            ["uv", "pip", "install", f"{canonical_name}=={version}"],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            env={**os.environ, "VIRTUAL_ENV": temp_venv}
                        )

                        if result_install.returncode == 0:
                            installable_versions.append(version)
                            if tested_count <= 5 or tested_count % 10 == 0:
                                print(f"      ✅ [{tested_count}/{min(len(all_versions), max_test_limit)}] {canonical_name}=={version} is installable")
                        else:
                            if tested_count <= 5:
                                print(f"      ❌ [{tested_count}/{min(len(all_versions), max_test_limit)}] {canonical_name}=={version} failed: {result_install.stderr.strip()[:100]}")

                except subprocess.TimeoutExpired:
                    if tested_count <= 5:
                        print(f"      ⏱️ [{tested_count}/{min(len(all_versions), max_test_limit)}] {canonical_name}=={version} timed out")
                except Exception as e:
                    if tested_count <= 5:
                        print(f"      ⚠️ [{tested_count}/{min(len(all_versions), max_test_limit)}] {canonical_name}=={version} error: {str(e)[:100]}")
                finally:
                    # Cleanup temp venv
                    try:
                        shutil.rmtree(temp_venv, ignore_errors=True)
                    except:
                        pass

            # Use installable versions instead of all versions
            final_versions = installable_versions

            if req_versions:
                print(f"   📋 Requirements.txt specifies: {req_versions}")

            if final_versions:
                print(f"   ✅ Found {len(final_versions)} installable versions (out of {len(all_versions)} total)")
                print(f"   📌 Top installable versions: {final_versions[:5]}")

                # Build enhanced result
                enhanced_result = {
                    "versions": final_versions,
                    "reasoning": {
                        "confidence": "medium",
                        "reasoning": f"Tested with uv pip install, {len(final_versions)}/{len(all_versions)} versions are installable"
                    },
                    "api_usage": [],
                    "release_dates": {v: release_dates.get(v, "unknown") for v in final_versions}
                }
                return (package_name, enhanced_result, None)
            else:
                print(f"   ⚠️ No installable versions found for package: {package_name}")
                enhanced_result = {
                    "versions": [],
                    "reasoning": {"confidence": "none", "reasoning": f"No installable versions found (tested {tested_count} versions)"},
                    "api_usage": [],
                    "release_dates": {}
                }
                return (package_name, enhanced_result, None)
        else:
            print(f"   ⚠️ No versions found on PyPI for package: {package_name}")
            enhanced_result = {
                "versions": [],
                "reasoning": {"confidence": "none", "reasoning": "Package not found on PyPI"},
                "api_usage": [],
                "release_dates": {}
            }
            return (package_name, enhanced_result, None)

    except Exception as e:
        error_msg = f"Error processing {package_name}: {str(e)}"
        print(f"   ❌ {error_msg}")
        enhanced_result = {
            "versions": [],
            "reasoning": {"confidence": "error", "reasoning": str(e)},
            "api_usage": [],
            "release_dates": {}
        }
        return (package_name, enhanced_result, error_msg)


def generate_package_combinations(resolved_packages):
    """
    Generate all possible combinations of package versions.

    Args:
        resolved_packages: dict {package_name: [list of compatible versions]}

    Returns:
        list of dicts, each representing one combination: {package_name: version}
    """
    if not resolved_packages:
        return []

    # Get package names and their version lists
    packages = list(resolved_packages.keys())
    version_lists = [resolved_packages[pkg] for pkg in packages]

    # Generate all combinations using itertools.product
    all_combinations = []
    for combo in itertools.product(*version_lists):
        combination_dict = {packages[i]: combo[i] for i in range(len(packages))}
        all_combinations.append(combination_dict)

    return all_combinations


def build_docker_image(dockerfile_path, image_tag, timeout=300):
    """
    Build a Docker image from a Dockerfile.

    Args:
        dockerfile_path: Path to the Dockerfile
        image_tag: Tag for the Docker image (e.g., 'myapp:v1')
        timeout: Build timeout in seconds (default: 300s = 5 minutes)

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    import subprocess
    import time

    dockerfile_dir = os.path.dirname(dockerfile_path)
    dockerfile_name = os.path.basename(dockerfile_path)

    print(f"   🐳 Building Docker image '{image_tag}' from {dockerfile_name}...")

    try:
        # Run docker build command
        result = subprocess.run(
            ['docker', 'build', '-f', dockerfile_name, '-t', image_tag, '.'],
            cwd=dockerfile_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            print(f"      ✅ Docker build succeeded!")
            return (True, None)
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            print(f"      ❌ Docker build failed!")
            print(f"      Error: {error_msg[:500]}...")  # Print first 500 chars
            return (False, error_msg)

    except subprocess.TimeoutExpired:
        error_msg = f"Docker build timed out after {timeout} seconds"
        print(f"      ⏱️  {error_msg}")
        return (False, error_msg)
    except Exception as e:
        error_msg = str(e)
        print(f"      ❌ Docker build failed with exception: {error_msg}")
        return (False, error_msg)


def generate_dockerfile(combination, base_image="python:3.11-slim", project_path=None, use_llm=True, python_version=None):
    """
    Generate a Dockerfile for a specific package combination.

    Args:
        combination: dict {package_name: version}
        base_image: Docker base image to use (will be overridden by python_version if provided)
        project_path: Optional path to project directory for volume mounting
        use_llm: If True, use LLM to generate content (default). If False, use template.
        python_version: Optional Python version string (e.g., '3.10', '3.11', 'python3.10')
                       If provided, will override base_image with appropriate python:<version>-slim

    Returns:
        dict with keys:
            - 'dockerfile': str (Dockerfile content)
            - 'readme_section': str (README section for this configuration)
    """
    # Override base_image if python_version is provided
    if python_version:
        # Normalize python_version to just the version number (e.g., '3.10')
        version_str = python_version.replace('python', '').strip()
        base_image = f"python:{version_str}-slim"
    if use_llm:
        # 💡 Use LLM to generate Dockerfile and README content (without writing files)
        print(f"   🤖 Using LLM to generate Dockerfile content...")
        result = llm_client.generate_dockerfile_content(
            combination=combination,
            base_image=base_image,
            project_path=project_path
        )
        return result
    else:
        # Fallback: Use original template-based generation
        dockerfile_content = f"""FROM {base_image}

WORKDIR /app

# This ensures only the specified packages are installed, not their transitive dependencies
RUN pip install --no-cache-dir \\
"""

        # Add each package with its version
        for i, (package, version) in enumerate(combination.items()):
            if i < len(combination) - 1:
                dockerfile_content += f"    {package}=={version} \\\n"
            else:
                dockerfile_content += f"    {package}=={version}\n"

        if project_path:
            # If project_path is provided, use volume mounting
            dockerfile_content += f"""
# Project files will be mounted from host at runtime
# Volume mount: {project_path} -> /app/project

# Keep container running for interactive access
CMD ["tail", "-f", "/dev/null"]
"""
        else:
            # Default behavior: keep container running
            dockerfile_content += """
# Keep container running for interactive access
CMD ["tail", "-f", "/dev/null"]
"""

        # Generate simple README section
        packages_str = ', '.join([f'{k}=={v}' for k, v in combination.items()])
        readme_section = f"""### Configuration
Packages: {packages_str}

Build: `docker build -f Dockerfile -t myapp .`
Run: `docker run -d myapp` (run in background)
Interactive: `docker run -it myapp /bin/bash` (enter container directly)
"""

        return {
            "dockerfile": dockerfile_content,
            "readme_section": readme_section
        }


def generate_version_combinations(resolved_packages, requirements, resolved_packages_enhanced, num_combinations):
    """
    Generate version combinations prioritizing requirements.txt versions.
    Strategy:
    1. First combination: all versions from requirements.txt
    2. Subsequent combinations: modify 1-3 packages at a time

    Args:
        resolved_packages: dict {package_name: [list of compatible versions]}
        requirements: dict {package_name: version_from_requirements}
        resolved_packages_enhanced: dict with enhanced info including release_dates
        num_combinations: Number of combinations to generate ('all' or number)

    Returns:
        list of dicts, each dict is {package_name: version}
    """
    packages = list(resolved_packages.keys())

    # Build base combination from requirements.txt
    base_combination = {}
    version_lists_sorted = {}

    for pkg in packages:
        versions = resolved_packages[pkg]

        # Sort versions by release date (newest first)
        if resolved_packages_enhanced and pkg in resolved_packages_enhanced:
            release_dates = resolved_packages_enhanced[pkg].get('release_dates', {})
            if release_dates:
                versions_with_dates = [(v, release_dates.get(v, "unknown")) for v in versions]
                versions_with_dates.sort(key=lambda x: (x[1] in ("unknown", None), x[1] or ""), reverse=True)
                sorted_versions = [v for v, _ in versions_with_dates]
            else:
                sorted_versions = versions
        else:
            sorted_versions = versions

        version_lists_sorted[pkg] = sorted_versions

        # Try to use version from requirements.txt
        if pkg in requirements and requirements[pkg]:
            req_version = requirements[pkg][0] if isinstance(requirements[pkg], list) else requirements[pkg]
            if req_version in sorted_versions:
                base_combination[pkg] = req_version
            else:
                # If requirements version not in compatible list, use newest
                base_combination[pkg] = sorted_versions[0]
        else:
            # Use newest version
            base_combination[pkg] = sorted_versions[0]

    combinations = [base_combination.copy()]

    # If num_combinations is 'all', generate all possible combinations
    if num_combinations == 'all':
        # Generate all combinations (can be very large!)
        import itertools
        all_version_lists = [version_lists_sorted[pkg] for pkg in packages]
        for combo_tuple in itertools.product(*all_version_lists):
            combo = {packages[i]: combo_tuple[i] for i in range(len(packages))}
            if combo not in combinations:
                combinations.append(combo)
    else:
        # Generate combinations by modifying 1-3 packages at a time
        target_count = int(num_combinations)

        # Strategy: modify packages one by one, then combinations of 2, then 3
        for num_changes in [1, 2, 3]:
            if len(combinations) >= target_count * 3:  # Generate 3x more to account for build failures
                break

            import itertools
            for pkg_subset in itertools.combinations(packages, num_changes):
                if len(combinations) >= target_count * 3:
                    break

                # For each package in subset, try different versions
                pkg_version_choices = [version_lists_sorted[pkg] for pkg in pkg_subset]

                for version_tuple in itertools.product(*pkg_version_choices):
                    if len(combinations) >= target_count * 3:
                        break

                    new_combo = base_combination.copy()
                    for i, pkg in enumerate(pkg_subset):
                        new_combo[pkg] = version_tuple[i]

                    # Skip if this combination already exists or is the base
                    if new_combo not in combinations:
                        combinations.append(new_combo)

    return combinations


def llm_guided_dockerfile_generation(resolved_packages, project_path=None, use_llm=True, python_version=None, resolved_packages_enhanced=None, num_dockerfiles=10, max_attempts=50, build_timeout=300, requirements=None):
    """
    Generate Dockerfiles by testing different version combinations.

    This function iteratively:
    1. Starts with versions from requirements.txt
    2. Generates a Dockerfile and attempts to build it
    3. If build fails, tries next pre-generated combination
    4. If build succeeds, records it and continues
    5. Repeats until we have the desired number of successful Dockerfiles

    Args:
        resolved_packages: dict {package_name: [list of compatible versions]}
        project_path: Optional path to project directory for volume mounting
        use_llm: If True, use LLM to generate Dockerfile content (default). If False, use template.
        python_version: Optional Python version string (e.g., '3.10', '3.11') to use in Dockerfile base image
        resolved_packages_enhanced: Optional dict with enhanced info including release_dates
        num_dockerfiles: Number of successful Dockerfiles to generate (default: 10), or 'all'
        max_attempts: Maximum number of build attempts before giving up (default: 50)
        build_timeout: Timeout for each Docker build in seconds (default: 300)
        requirements: dict {package_name: version_from_requirements} for prioritizing combinations
    """
    if not resolved_packages:
        print("❌ No packages to generate Dockerfiles from.")
        return

    # Generate version combinations prioritizing requirements.txt
    print("\n📅 Generating version combinations (prioritizing requirements.txt versions)...")

    # Determine target number
    if num_dockerfiles == 'all':
        target_dockerfiles = 'all'
        print("   🎯 Target: Generate ALL possible combinations")
    else:
        try:
            target_dockerfiles = int(num_dockerfiles)
            print(f"   🎯 Target: {target_dockerfiles} successful Dockerfiles")
        except ValueError:
            print(f"   ⚠️ Invalid num_dockerfiles value: {num_dockerfiles}, defaulting to 1")
            target_dockerfiles = 1
            num_dockerfiles = 1

    # Generate combinations
    if not requirements:
        requirements = {}

    all_combinations = generate_version_combinations(
        resolved_packages,
        requirements,
        resolved_packages_enhanced,
        num_dockerfiles
    )

    print(f"   ✅ Generated {len(all_combinations)} version combinations to try")
    print(f"   📦 First combination (from requirements.txt):")
    for pkg, ver in list(all_combinations[0].items())[:5]:
        print(f"      • {pkg}=={ver}")
    if len(all_combinations[0]) > 5:
        print(f"      ... and {len(all_combinations[0]) - 5} more packages")

    # Setup output directory
    output_dir = "generated_dockerfiles"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    print(f"\n🔨 Starting Docker build process...")
    if target_dockerfiles == 'all':
        print(f"   Target: ALL successful Dockerfiles (testing {len(all_combinations)} combinations)")
    else:
        print(f"   Target: {target_dockerfiles} successful Dockerfiles")
    print(f"   Available combinations: {len(all_combinations)}")
    print(f"   Build timeout: {build_timeout}s per Dockerfile")

    # Track successful and failed combinations
    successful_combinations = []
    failed_combinations = []
    attempt_count = 0
    combination_index = 0

    # Create summary file
    summary_file = os.path.join(output_dir, "README.md")
    with open(summary_file, 'w') as f:
        f.write(f"# Dockerfile Generation Summary\n\n")
        f.write(f"Generated at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        if target_dockerfiles == 'all':
            f.write(f"Target: ALL successful Dockerfiles\n\n")
        else:
            f.write(f"Target: {target_dockerfiles} successful Dockerfiles\n\n")

        # Add Docker usage instructions
        f.write(f"## 🐳 How to Run These Dockerfiles\n\n")
        if project_path:
            abs_project_path = os.path.abspath(project_path)
            f.write(f"### Build and Run Example\n\n")
            f.write(f"```bash\n")
            f.write(f"# Build a Docker image\n")
            f.write(f"cd {output_dir}\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n\n")
            f.write(f"# Run with project mounted\n")
            f.write(f"docker run -it --rm -v {abs_project_path}:/app/project myapp:v1 /bin/bash\n")
            f.write(f"```\n\n")
        else:
            f.write(f"```bash\n")
            f.write(f"cd {output_dir}\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n")
            f.write(f"docker run -it --rm myapp:v1 /bin/bash\n")
            f.write(f"```\n\n")

        f.write(f"## Generated Configurations\n\n")

    # Main loop: try each combination
    while combination_index < len(all_combinations):
        # Check if we've reached target (unless target is 'all')
        if target_dockerfiles != 'all' and len(successful_combinations) >= target_dockerfiles:
            break

        current_combination = all_combinations[combination_index]
        combination_index += 1
        attempt_count += 1

        print(f"\n{'='*80}")
        if target_dockerfiles == 'all':
            print(f"🔄 Attempt {attempt_count}/{len(all_combinations)} (Success: {len(successful_combinations)})")
        else:
            print(f"🔄 Attempt {attempt_count}/{len(all_combinations)} (Success: {len(successful_combinations)}/{target_dockerfiles})")
        print(f"{'='*80}")

        # Print current combination (show first 5 packages)
        print(f"\n📦 Testing combination:")
        pkg_items = list(current_combination.items())
        for pkg, ver in pkg_items[:5]:
            print(f"   • {pkg}=={ver}")
        if len(pkg_items) > 5:
            print(f"   ... and {len(pkg_items) - 5} more packages")

        # Generate Dockerfile
        generated_content = generate_dockerfile(
            current_combination,
            project_path=project_path,
            use_llm=use_llm,
            python_version=python_version
        )

        dockerfile_content = generated_content.get('dockerfile', '')
        readme_section = generated_content.get('readme_section', '')

        # Write Dockerfile to temp location
        temp_dockerfile = os.path.join(output_dir, f"Dockerfile_temp")
        with open(temp_dockerfile, 'w') as f:
            f.write(dockerfile_content)

        # Try to build the Docker image
        image_tag = f"test_build_{attempt_count}"
        success, error_message = build_docker_image(temp_dockerfile, image_tag, timeout=build_timeout)

        if success:
            # Build succeeded! Save this Dockerfile
            success_idx = len(successful_combinations) + 1
            final_filename = f"Dockerfile_{success_idx}"
            final_filepath = os.path.join(output_dir, final_filename)

            # Rename temp file to final name
            os.rename(temp_dockerfile, final_filepath)

            successful_combinations.append(current_combination.copy())

            if target_dockerfiles == 'all':
                print(f"\n   ✅ SUCCESS! Saved as {final_filename}")
                print(f"      Progress: {len(successful_combinations)} successful so far")
            else:
                print(f"\n   ✅ SUCCESS! Saved as {final_filename}")
                print(f"      Progress: {len(successful_combinations)}/{target_dockerfiles} successful")

            # Add to README
            with open(summary_file, 'a') as f:
                f.write(f"### {final_filename} ✅\n")
                if readme_section:
                    f.write(readme_section)
                else:
                    f.write(f"```\n")
                    # Show first 10 packages, then summarize rest
                    pkg_items = list(current_combination.items())
                    for pkg, ver in pkg_items[:10]:
                        f.write(f"{pkg}=={ver}\n")
                    if len(pkg_items) > 10:
                        f.write(f"# ... and {len(pkg_items) - 10} more packages\n")
                    f.write(f"```\n")
                f.write("\n\n")

        else:
            # Build failed, record this combination and continue to next
            failed_combinations.append(current_combination.copy())

            print(f"\n   ❌ Build failed. Moving to next combination...")
            if error_message:
                # Show first 200 chars of error
                error_preview = error_message[:200] + "..." if len(error_message) > 200 else error_message
                print(f"      Error preview: {error_preview}")

            # Remove temp file
            if os.path.exists(temp_dockerfile):
                os.remove(temp_dockerfile)

    # Final summary
    print(f"\n{'='*80}")
    print(f"🎉 Dockerfile Generation Complete!")
    print(f"{'='*80}")
    if target_dockerfiles == 'all':
        print(f"✅ Successfully built: {len(successful_combinations)} Dockerfiles")
    else:
        print(f"✅ Successfully built: {len(successful_combinations)}/{target_dockerfiles} Dockerfiles")
    print(f"❌ Failed attempts: {len(failed_combinations)}")
    print(f"📊 Total combinations tested: {attempt_count}/{len(all_combinations)}")
    if attempt_count > 0:
        print(f"📈 Success rate: {len(successful_combinations)/attempt_count*100:.1f}%")
    print(f"📁 Output directory: {output_dir}/")
    print(f"📄 Summary: {summary_file}")

    # Update summary file with final statistics
    with open(summary_file, 'a') as f:
        f.write(f"\n## Final Statistics\n\n")
        f.write(f"- Successful builds: {len(successful_combinations)}\n")
        f.write(f"- Failed attempts: {len(failed_combinations)}\n")
        f.write(f"- Total combinations tested: {attempt_count}\n")
        if attempt_count > 0:
            f.write(f"- Success rate: {len(successful_combinations)/attempt_count*100:.1f}%\n")

    if target_dockerfiles != 'all' and len(successful_combinations) < target_dockerfiles:
        print(f"\n⚠️  Warning: Only generated {len(successful_combinations)} successful Dockerfiles")
        print(f"   Tested all {len(all_combinations)} available combinations")


def interactive_dockerfile_generation_optimized(resolved_packages, project_path=None, use_llm=True, python_version=None, resolved_packages_enhanced=None):
    """
    Allow user to interactively select how many Dockerfiles to generate.
    Generates combinations on-demand to avoid memory issues.

    IMPORTANT: Dockerfiles are now sorted by release date (newest first) to prioritize
    testing with the most recent package versions.

    Args:
        resolved_packages: dict {package_name: [list of compatible versions]}
        project_path: Optional path to project directory for volume mounting
        use_llm: If True, use LLM to generate Dockerfile content (default). If False, use template.
        python_version: Optional Python version string (e.g., '3.10', '3.11') to use in Dockerfile base image
        resolved_packages_enhanced: Optional dict with enhanced info including release_dates
    """
    if not resolved_packages:
        print("❌ No packages to generate Dockerfiles from.")
        return

    # Sort each package's versions by release date (newest first)
    print("\n📅 Sorting package versions by release date (newest first)...")
    packages = list(resolved_packages.keys())
    version_lists_sorted = []

    for pkg in packages:
        versions = resolved_packages[pkg]

        # Try to get release dates from enhanced info
        if resolved_packages_enhanced and pkg in resolved_packages_enhanced:
            release_dates = resolved_packages_enhanced[pkg].get('release_dates', {})
            if release_dates:
                # Sort versions by release date (newest first)
                # Format: YYYY-MM-DD or "unknown"
                versions_with_dates = []
                for v in versions:
                    date_str = release_dates.get(v, "unknown")
                    versions_with_dates.append((v, date_str))

                # Sort by date descending (newest first), treat "unknown" and None as oldest
                versions_with_dates.sort(key=lambda x: (x[1] in ("unknown", None), x[1] or ""), reverse=True)
                sorted_versions = [v for v, _ in versions_with_dates]

                print(f"   ✅ {pkg}: Sorted {len(sorted_versions)} versions by release date")
                print(f"      Newest: {sorted_versions[0]} ({release_dates.get(sorted_versions[0], 'unknown')})")
                if len(sorted_versions) > 1:
                    print(f"      Oldest: {sorted_versions[-1]} ({release_dates.get(sorted_versions[-1], 'unknown')})")

                version_lists_sorted.append(sorted_versions)
            else:
                # No release dates available, use as-is
                print(f"   ⚠️  {pkg}: No release dates available, using original order")
                version_lists_sorted.append(versions)
        else:
            # No enhanced info, use as-is
            print(f"   ⚠️  {pkg}: No enhanced info available, using original order")
            version_lists_sorted.append(versions)

    version_lists = version_lists_sorted

    # Calculate total possible combinations
    total_combinations = 1
    for versions in version_lists:
        total_combinations *= len(versions)

    print(f"\n📊 Total possible package combinations: {total_combinations:,}")

    if total_combinations > 1000:
        print(f"⚠️  Note: Large number of combinations!")
        print(f"   We'll generate combinations on-demand to save memory.")

    # Ask user how many Dockerfiles to generate
    while True:
        prompt = f"\n🐳 How many Dockerfiles would you like to generate?\n"
        prompt += f"   Options: 1-{min(total_combinations, 100)}"
        if total_combinations > 100:
            prompt += f" (max 100 recommended)"
        prompt += f"\n   Enter 'all' to generate all {total_combinations:,} combinations"
        prompt += f"\n   Default: 1\n"
        prompt += f"   Enter your choice: "

        user_input = input(prompt).strip()

        if not user_input:
            num_dockerfiles = 1
            break

        if user_input.lower() == 'all':
            num_dockerfiles = total_combinations
            confirm = input(f"\n⚠️  This will generate {total_combinations:,} Dockerfiles. Continue? (y/N): ").strip().lower()
            if confirm == 'y':
                break
            else:
                continue

        try:
            num_dockerfiles = int(user_input)
            if 1 <= num_dockerfiles <= total_combinations:
                break
            else:
                print(f"❌ Please enter a number between 1 and {total_combinations:,}")
        except ValueError:
            print("❌ Please enter a valid number or 'all'")

    # Generate Dockerfiles
    output_dir = "generated_dockerfiles"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    print(f"\n🔨 Generating {num_dockerfiles} Dockerfile(s) in '{output_dir}/'...")

    # Create a summary file with detailed instructions
    summary_file = os.path.join(output_dir, "README.md")
    with open(summary_file, 'w') as f:
        f.write(f"# Generated Dockerfiles Summary\n\n")
        f.write(f"Generated at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total combinations available: {total_combinations:,}\n")
        f.write(f"Dockerfiles generated: {num_dockerfiles}\n\n")

        # Add Docker usage instructions at the beginning
        f.write(f"## 🐳 How to Run These Dockerfiles\n\n")

        if project_path:
            abs_project_path = os.path.abspath(project_path)
            f.write(f"### Method 1: Run Container in Background and Exec Into It\n\n")
            f.write(f"This method runs the container in the background, allowing you to exec into it for manual operations.\n\n")
            f.write(f"```bash\n")
            f.write(f"# 1. Navigate to the generated dockerfiles directory\n")
            f.write(f"cd {output_dir}\n\n")
            f.write(f"# 2. Build a Docker image (example with Dockerfile_1)\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n\n")
            f.write(f"# 3. Run the container in background with your project mounted\n")
            f.write(f"docker run -d --name myapp_container -v {abs_project_path}:/app/project myapp:v1\n\n")
            f.write(f"# 4. Enter the container for manual operations\n")
            f.write(f"docker exec -it myapp_container /bin/bash\n\n")
            f.write(f"# 5. When done, stop and remove the container\n")
            f.write(f"docker stop myapp_container\n")
            f.write(f"docker rm myapp_container\n")
            f.write(f"```\n\n")
            f.write(f"### Method 2: Run Container Directly in Interactive Mode\n\n")
            f.write(f"```bash\n")
            f.write(f"# Build and run directly in interactive mode\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n")
            f.write(f"docker run -it --rm -v {abs_project_path}:/app/project myapp:v1 /bin/bash\n\n")
            f.write(f"# Test different package combinations\n")
            f.write(f"docker build -f Dockerfile_2 -t myapp:v2 .\n")
            f.write(f"docker run -it --rm -v {abs_project_path}:/app/project myapp:v2 /bin/bash\n")
            f.write(f"```\n\n")
            f.write(f"### 📝 Important Notes\n\n")
            f.write(f"- **Container Purpose**: Containers are designed to stay running for manual interaction, not automatic execution\n")
            f.write(f"- **Project Mount Path**: Your project at `{abs_project_path}` will be mounted to `/app/project` inside the container\n")
            f.write(f"- **Live Updates**: Any changes to your project files on the host will be immediately reflected in the container\n")
            f.write(f"- **Manual Operations**: You can run your application manually inside the container as needed\n")
            f.write(f"- **Cleanup**: Remove unused images with `docker rmi myapp:v1 myapp:v2 ...`\n\n")
        else:
            f.write(f"### Method 1: Run Container in Background and Exec Into It\n\n")
            f.write(f"```bash\n")
            f.write(f"# 1. Navigate to the generated dockerfiles directory\n")
            f.write(f"cd {output_dir}\n\n")
            f.write(f"# 2. Build a Docker image\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n\n")
            f.write(f"# 3. Run the container in background\n")
            f.write(f"docker run -d --name myapp_container myapp:v1\n\n")
            f.write(f"# 4. Enter the container for manual operations\n")
            f.write(f"docker exec -it myapp_container /bin/bash\n\n")
            f.write(f"# 5. Optionally mount your project files:\n")
            f.write(f"docker run -d --name myapp_container -v /path/to/your/project:/app/project myapp:v1\n\n")
            f.write(f"# 6. When done, stop and remove the container\n")
            f.write(f"docker stop myapp_container\n")
            f.write(f"docker rm myapp_container\n")
            f.write(f"```\n\n")
            f.write(f"### Method 2: Run Container Directly in Interactive Mode\n\n")
            f.write(f"```bash\n")
            f.write(f"# Build and run directly in interactive mode\n")
            f.write(f"docker build -f Dockerfile_1 -t myapp:v1 .\n")
            f.write(f"docker run -it --rm myapp:v1 /bin/bash\n\n")
            f.write(f"# With volume mounting\n")
            f.write(f"docker run -it --rm -v /path/to/your/project:/app/project myapp:v1 /bin/bash\n")
            f.write(f"```\n\n")
            f.write(f"### 📝 Important Notes\n\n")
            f.write(f"- **Container Purpose**: Containers are designed to stay running for manual interaction, not automatic execution\n")
            f.write(f"- **Manual Operations**: You can run your application manually inside the container as needed\n")
            f.write(f"- **Volume Mounting**: You can mount your project directory using `-v` flag when running the container\n")
            f.write(f"- **Cleanup**: Remove unused images with `docker rmi myapp:v1 myapp:v2 ...`\n\n")

        f.write(f"## Generated Configurations\n\n")

    # Generate combinations on-demand using itertools
    combo_generator = itertools.product(*version_lists)

    for i in range(num_dockerfiles):
        combo = next(combo_generator)
        combination = {packages[j]: combo[j] for j in range(len(packages))}

        # 💡 Call LLM to generate Dockerfile and README content (LLM won't write files)
        generated_content = generate_dockerfile(combination, project_path=project_path, use_llm=use_llm, python_version=python_version)

        # 📝 Extract content from LLM response
        dockerfile_content = generated_content.get('dockerfile', '')
        readme_section = generated_content.get('readme_section', '')

        # Create filename with package versions
        filename = f"Dockerfile_{i+1}"
        filepath = os.path.join(output_dir, filename)

        # ✍️ Write the Dockerfile (resolve_dependencies.py is responsible for writing)
        with open(filepath, 'w') as f:
            f.write(dockerfile_content)

        print(f"\n   [{i+1}/{num_dockerfiles}] Generated: {filepath}")
        packages_str = ', '.join([f'{k}=={v}' for k, v in combination.items()])
        print(f"      📦 Packages: {packages_str}")

        # ✍️ Add to README summary (resolve_dependencies.py is responsible for writing)
        with open(summary_file, 'a') as f:
            f.write(f"### {filename}\n")
            # Use LLM-generated README section if available
            if readme_section:
                f.write(readme_section)
                f.write("\n\n")
            else:
                # Fallback to simple format
                f.write(f"```\n")
                for pkg, ver in combination.items():
                    f.write(f"{pkg}=={ver}\n")
                f.write(f"```\n\n")

    print(f"\n✨ All Dockerfiles generated successfully!")
    print(f"   📁 Location: {output_dir}/")
    print(f"   📄 Summary: {summary_file}")

    if project_path:
        # Convert project_path to absolute path
        abs_project_path = os.path.abspath(project_path)
        print(f"\n{'='*60}")
        print(f"🐳 Docker Usage Instructions (with volume mounting)")
        print(f"{'='*60}")
        print(f"\n1️⃣  Build the Docker image:")
        print(f"   cd {output_dir}")
        print(f"   docker build -f Dockerfile_1 -t myapp:v1 .")
        print(f"\n2️⃣  Run the container in background with project mounted:")
        print(f"   docker run -d --name myapp_container -v {abs_project_path}:/app/project myapp:v1")
        print(f"\n3️⃣  Enter the container for manual operations:")
        print(f"   docker exec -it myapp_container /bin/bash")
        print(f"\n4️⃣  Or run directly in interactive mode:")
        print(f"   docker run -it --rm -v {abs_project_path}:/app/project myapp:v1 /bin/bash")
        print(f"\n5️⃣  Test different package combinations:")
        print(f"   docker build -f Dockerfile_2 -t myapp:v2 .")
        print(f"   docker run -it --rm -v {abs_project_path}:/app/project myapp:v2 /bin/bash")
        print(f"\n💡 Important Notes:")
        print(f"   • Containers are designed for manual interaction, not automatic execution")
        print(f"   • The project at '{abs_project_path}' will be mounted to '/app/project' in the container")
        print(f"   • You can run your application manually inside the container")
        print(f"   • See {summary_file} for detailed usage instructions")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"🐳 Docker Usage Instructions")
        print(f"{'='*60}")
        print(f"\n1️⃣  Build the Docker image:")
        print(f"   cd {output_dir}")
        print(f"   docker build -f Dockerfile_1 -t myapp:v1 .")
        print(f"\n2️⃣  Run the container in background:")
        print(f"   docker run -d --name myapp_container myapp:v1")
        print(f"\n3️⃣  Enter the container for manual operations:")
        print(f"   docker exec -it myapp_container /bin/bash")
        print(f"\n4️⃣  Or run directly in interactive mode:")
        print(f"   docker run -it --rm myapp:v1 /bin/bash")
        print(f"\n💡 Important Notes:")
        print(f"   • Containers are designed for manual interaction, not automatic execution")
        print(f"   • You can mount your project using -v flag when running the container")
        print(f"   • See {summary_file} for detailed usage instructions")
        print(f"{'='*60}")


# =====================================================================
# 🚀 Main Execution Flow
# =====================================================================
def main():
    global PYPI_IMPORT_MAPPING

    print("="*50)
    print("🧠 LLM-Driven Dependency Resolver")
    print("="*50)

    # Load PyPI import mapping at startup
    print("\n" + "="*50)
    print("🗺️ Loading PyPI Import Mapping")
    print("="*50)

    # Try to find pypi_import_mapping.json in current directory or MockVenv directory
    mapping_file_candidates = [
        "pypi_import_mapping.json",
        os.path.join(os.path.dirname(__file__), "pypi_import_mapping.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "pypi_import_mapping.json")
    ]

    mapping_file_path = None
    for candidate in mapping_file_candidates:
        if os.path.exists(candidate):
            mapping_file_path = candidate
            break

    if mapping_file_path:
        PYPI_IMPORT_MAPPING = load_pypi_import_mapping(mapping_file_path)
        if PYPI_IMPORT_MAPPING:
            print(f"✅ Successfully loaded {len(PYPI_IMPORT_MAPPING)} package mappings from {mapping_file_path}")
        else:
            print(f"⚠️ Warning: No mappings loaded from {mapping_file_path}")
    else:
        print(f"⚠️ Warning: pypi_import_mapping.json not found in expected locations:")
        for candidate in mapping_file_candidates:
            print(f"   - {candidate}")
        print("   Continuing without package name mappings...")

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("❌ Error: State file path is required")
        print("Usage: python resolve_dependencies.py <state_file_path> [mode] [requirements_file] [project_path] [use_llm] [python_version] [num_dockerfiles]")
        print("  use_llm: 'true' (default) to use LLM for Dockerfile generation, 'false' to use template")
        print("  num_dockerfiles: Number of Dockerfiles to generate: 'all' for all combinations, or a number (default: '1')")
        sys.exit(1)

    state_file = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'mock'
    requirements_path = sys.argv[3] if len(sys.argv) > 3 else "requirements.txt"
    project_path = sys.argv[4] if len(sys.argv) > 4 else None
    use_llm_arg = sys.argv[5] if len(sys.argv) > 5 else 'true'
    use_llm = use_llm_arg.lower() != 'false'  # Default to True unless explicitly set to 'false'
    python_version = sys.argv[6] if len(sys.argv) > 6 else "3.10"
    num_dockerfiles_arg = sys.argv[7] if len(sys.argv) > 7 else "1"

    if not os.path.exists(state_file):
        print(f"\n❌ File not found: {state_file}")
        sys.exit(1)

    print(f"📂 Using state file: {state_file}")
    print(f"🎯 Mode: {mode}")
    if project_path:
        print(f"📁 Project path: {project_path}")
    print(f"🤖 LLM Dockerfile Generation: {'Enabled' if use_llm else 'Disabled (using template)'}")
    print(f"🐍 Python version for validation: {python_version}")

    # Load requirements.txt for package constraints
    requirements = load_requirements_txt(requirements_path)
    if requirements:
        print(f"📋 Loaded {len(requirements)} packages from requirements.txt: {requirements_path}")
    else:
        print(f"⚠️ No requirements.txt found or empty, will use all available versions from PyPI")

    # Dictionary to store the resolved configuration
    resolved_packages = {}
    resolved_packages_enhanced = {}  # Enhanced info with reasoning, api_usage, etc.
    validation_report = None  # Will be set if validation is performed

    # Define testscript_dir for cleanup purposes
    testscript_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_test_scripts")

    if mode == 'real':
        # Read requirements.txt and store all package names
        print("\n" + "="*50)
        print("📋 STEP 1: Reading requirements.txt and storing all package names")
        print("="*50)
        requirements_packages = set()
        if requirements:
            requirements_packages = set(requirements.keys())
            print(f"✅ Found {len(requirements_packages)} packages in requirements.txt:")
            for pkg in sorted(requirements_packages):
                version_info = requirements[pkg]
                if version_info:
                    print(f"   • {pkg} (version: {version_info})")
                else:
                    print(f"   • {pkg} (all versions)")
        else:
            print("⚠️ No packages found in requirements.txt")

        # Read .api_calls.json (plain text format)
        print("\n" + "="*50)
        print("📦 STEP 2: Reading API calls from .api_calls.json")
        print("="*50)
        with open(state_file, 'r') as f:
            api_calls_text = f.read()

        # Parse API calls by package
        api_by_package = parse_api_calls_from_text(api_calls_text)
        print(f"✅ Found API calls for {len(api_by_package)} packages: {', '.join(api_by_package.keys())}")

        # Track which requirements packages have been matched
        matched_requirements_packages = set()

        # Process each package from API logs with parallel processing
        print("\n" + "="*50)
        print("📦 STEP 3: Analyzing API signatures to infer compatible versions")
        print("="*50)

        # Calculate number of processes to use: min(32, cpu_count())
        num_processes = min(32, multiprocessing.cpu_count())
        print(f"🚀 Using {num_processes} parallel processes for package inference")

        # Prepare arguments for parallel processing
        api_package_items = list(api_by_package.items())
        total_packages = len(api_package_items)

        process_args = [
            (idx, total_packages, import_name, api_signatures, PYPI_IMPORT_MAPPING, requirements_packages, requirements, testscript_dir)
            for idx, (import_name, api_signatures) in enumerate(api_package_items, 1)
        ]

        # Process packages in parallel
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.map(_process_package_with_api, process_args)

        # Collect results
        for result in results:
            if result is not None:
                matched_req_pkg, enhanced_result, error_msg = result
                if error_msg:
                    print(f"   ⚠️ Warning: {error_msg}")
                else:
                    versions = enhanced_result.get('versions', [])
                    if versions:
                        resolved_packages[matched_req_pkg] = versions
                        resolved_packages_enhanced[matched_req_pkg] = enhanced_result
                        matched_requirements_packages.add(matched_req_pkg)

        # For packages in requirements.txt without API logs, add all versions
        print("\n" + "="*50)
        print("📦 STEP 4: Processing remaining packages without API logs")
        print("="*50)
        packages_without_api = requirements_packages - matched_requirements_packages

        if packages_without_api:
            print(f"Found {len(packages_without_api)} packages in requirements.txt without API logs:")
            for pkg in sorted(packages_without_api):
                print(f"   • {pkg}")

            # Prepare arguments for parallel processing
            packages_list = sorted(packages_without_api)
            total_without_api = len(packages_list)

            process_args = [
                (idx, total_without_api, package_name, requirements)
                for idx, package_name in enumerate(packages_list, 1)
            ]

            # Process packages in parallel
            print(f"🚀 Using {num_processes} parallel processes for package fetching")
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.map(_process_package_without_api, process_args)

            # Collect results
            for result in results:
                package_name, enhanced_result, error_msg = result
                if error_msg:
                    print(f"   ⚠️ Warning: {error_msg}")
                else:
                    versions = enhanced_result.get('versions', [])
                    if versions:
                        resolved_packages[package_name] = versions
                        resolved_packages_enhanced[package_name] = enhanced_result
        else:
            print("✅ All packages in requirements.txt have API logs")

    else:  # mock mode
        # Original mock mode logic
        with open(state_file, "r") as f:
            state = json.load(f)

        core_imports = state.get("core_imports", {})
        mocked_imports = state.get("mocked_imports", {})

        print("\n📦 Scanning dependencies and consulting LLM...")

        # Ignore specific internal/framework modules that shouldn't be mocked
        ignored_mocks = ["sitecustomize", "org", "org.python", "a2wsgi", "cython"]

        for pkg, info in mocked_imports.items():
            if pkg in ignored_mocks:
                continue

            features = info.get("api_features", {})

            # Get version constraints from requirements.txt if available
            pypi_name = _resolve_pypi_name_from_import(pkg)
            req_versions = None
            if pypi_name in requirements:
                req_versions = requirements[pypi_name]

            # Convert features dict to list of API signatures for consistency
            api_signatures = []
            if features:
                for api_name, api_info in features.items():
                    api_signatures.append(f"{pkg}.{api_name}()")

            enhanced_result = get_versions_for_validation(pkg, api_signatures, req_versions,
                                                          return_enhanced_info=True)
            versions = enhanced_result.get('versions', [])

            if versions:
                resolved_packages[pypi_name] = versions
                resolved_packages_enhanced[pypi_name] = enhanced_result
                print(f"   ✅ '{pypi_name}': Locked in {len(versions)} compatible versions")

    # =================================================================
    # 💾 Output the Resolved Versions JSON
    # =================================================================
    print("\n" + "="*50)
    print("💾 STEP 4: Saving results")
    print("="*50)

    # Create result directory if it doesn't exist
    result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result")
    os.makedirs(result_dir, exist_ok=True)

    config_output_path = os.path.join(result_dir, "resolved_versions.json")
    resolved_config = {
        "mode": mode,
        "resolved_packages": resolved_packages,
        "resolved_packages_enhanced": resolved_packages_enhanced,
        "total_packages": len(resolved_packages),
        "generated_at": __import__('datetime').datetime.now().isoformat()
    }

    with open(config_output_path, "w") as f:
        json.dump(resolved_config, f, indent=4)

    print(f"✅ Saved resolved versions to: {config_output_path}")
    print(f"   📦 Total packages resolved: {len(resolved_packages)}")

    # =================================================================
    # 🧪 STEP 4.5: Script-based Version Validation (Real Mode Only)
    # =================================================================
    if mode == 'real' and resolved_packages:
        print("\n" + "="*50)
        print("🧪 STEP 4.5: Script-based Version Validation & Filtering")
        print("="*50)
        print("This step validates package versions by:")
        print("  1. Using LLM to generate test scripts based on API logs")
        print("  2. Creating uv virtual environments for each version")
        print("  3. Running actual tests to verify API compatibility")
        print("Versions that fail tests will be filtered out.")

        try:
            # Import script-based validator
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, script_dir)
            from script_based_validator import validate_all_packages_with_scripts

            # Calculate optimal parallel workers: min(32, cpu_count())
            cpu_count = multiprocessing.cpu_count()
            optimal_workers = min(32, cpu_count)
            print(f"🖥️  Using {optimal_workers} parallel workers (CPU count: {cpu_count})")

            # Run script-based validation with retry logic
            validated_output = os.path.join(result_dir, "validated_versions.json")
            validate_all_packages_with_scripts(
                api_calls_file=state_file,
                resolved_versions_file=config_output_path,
                output_file=validated_output,
                python_version=python_version,
                max_workers=optimal_workers,
                timeout=30,  # Timeout per version test
                requirements_file=requirements_path if requirements_path else None,
                max_retries=5  # Retry up to 5 times for inference failures
            )

            # -----------------------------------------------------------------
            # 💡 NEW LOGIC: Extract inferred versions, update memory, delete validated.json
            # -----------------------------------------------------------------
            with open(validated_output, 'r') as f:
                validated_data = json.load(f)

            validated_packages = validated_data.get('resolved_packages', {})
            validation_report = validated_data.get('validation_report', {})
            packages_info = validation_report.get('packages', {})

            if validated_packages:
                print("\n✅ Validation complete. Updating packages and sorting by release date...")
                # Update resolved_packages with validated versions
                resolved_packages = validated_packages

                for pkg_name, enhanced_info in resolved_packages_enhanced.items():
                    pkg_info = packages_info.get(pkg_name, {})
                    status = pkg_info.get('status', 'unknown')
                    
                    final_versions = validated_packages.get(pkg_name, enhanced_info.get('versions', []))
                    
                    release_dates = enhanced_info.get('release_dates', {})
                    final_versions.sort(key=lambda v: (
                        release_dates.get(v) not in ("unknown", None, ""),
                        release_dates.get(v) or ""
                    ), reverse=True)

                    enhanced_info['versions'] = final_versions
                    enhanced_info['validation_status'] = status
                    
                    if status in ['validated_success', 'no_api_calls_kept_all']:
                        enhanced_info['category'] = 'success'
                    else:
                        enhanced_info['category'] = 'failed'

                # Immediately delete intermediate files including validated_versions.json
                intermediate_files = [
                    os.path.join(result_dir, "resolved_versions.json"),
                    validated_output  # This is validated_versions.json
                ]
                print("\n🗑️  Cleaning up intermediate validation files...")
                for tmp_file in intermediate_files:
                    if os.path.exists(tmp_file):
                        try:
                            os.remove(tmp_file)
                            print(f"   🗑️  Removed: {os.path.basename(tmp_file)}")
                        except Exception as e:
                            print(f"   ⚠️ Warning: Could not remove {os.path.basename(tmp_file)}: {e}")

            else:
                print("\n⚠️ Validation produced no results. Using original resolved versions.")

        except ImportError as e:
            print(f"\n⚠️ Warning: Could not import script_based_validator: {e}")
            print("   Continuing with resolved versions only.")
        except Exception as e:
            print(f"\n⚠️ Warning: Version validation failed: {e}")
            print("   Continuing with resolved versions only.")
            import traceback
            traceback.print_exc()

    # =================================================================
    # 📊 Generate Enhanced User-Friendly Report
    # =================================================================
    if mode == 'real':
        print("\n" + "="*50)
        print("📊 Generating enhanced resolution report (Based on Inferred Packages)")
        print("="*50)

        # Get paths for trace files
        venv_dir = os.path.dirname(state_file)
        execution_trace_file = os.path.join(venv_dir, ".execution_trace.json")

        # Prepare validation statistics for the report (if available)
        validation_stats = None
        if validation_report:
            # Extract and format validation statistics
            validation_stats = {
                "total_pypi_versions": validation_report.get("total_pypi_versions", 0),
                "total_installable_versions": validation_report.get("total_pypi_versions", 0),  # Assume all PyPI versions are installable initially
                "total_script_passed_versions": validation_report.get("total_script_passed_versions", 0),
                "requirements_version_failures": validation_report.get("requirements_version_failures", []),
                "packages": validation_report.get("packages", {})
            }

        # Generate and save the enhanced report
        enhanced_report_path = "resolution_report.txt"
        try:
            # resolved_packages_enhanced is already filtered above!
            save_enhanced_report(
                resolved_packages_enhanced,
                state_file,  # .api_calls.json
                enhanced_report_path,
                execution_trace_file if os.path.exists(execution_trace_file) else None,
                project_path,
                requirements_path if requirements_path else None,
                validation_stats
            )
            print(f"✅ Enhanced resolution report saved to: {enhanced_report_path}")
            print(f"   This report includes:")
            print(f"      • Program execution trace")
            print(f"      • Package usage frequency ranking")
            print(f"      • Validation statistics (PyPI fetch, installation, script testing)")
            print(f"      • Requirements.txt version validation results")
            print(f"      • Detailed version reasoning for each package")
            print(f"      • Release dates for compatible versions")
        except Exception as e:
            print(f"⚠️ Warning: Failed to generate enhanced report: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n📊 Summary of inferred packages for Docker builds:")
    total_versions_product = 1
    for pkg, versions in resolved_packages.items():
        num_versions = len(versions)
        print(f"   • {pkg}: {num_versions} compatible versions")
        total_versions_product *= num_versions

    print(f"\n💡 Total possible combinations: {total_versions_product:,}")
    if total_versions_product > 1000:
        print(f"⚠️  Note: Generating all combinations would create {total_versions_product:,} configurations!")
        print(f"   We'll let you choose how many Dockerfiles to generate instead.")

    # =================================================================
    # 🐳 LLM-Guided Dockerfile Generation with Build Testing
    # =================================================================
    print("\n" + "="*50)
    print("🐳 STEP 5: LLM-Guided Dockerfile Generation (Based on Inferred Packages)")
    print("="*50)

    # Parse num_dockerfiles parameter
    if num_dockerfiles_arg.lower() == 'all':
        num_dockerfiles_to_generate = 'all'
    else:
        try:
            num_dockerfiles_to_generate = int(num_dockerfiles_arg)
        except ValueError:
            print(f"⚠️ Invalid num_dockerfiles value: {num_dockerfiles_arg}, defaulting to 1")
            num_dockerfiles_to_generate = 1

    # Generate Dockerfiles by testing different version combinations
    # resolved_packages is already filtered!
    llm_guided_dockerfile_generation(
        resolved_packages,
        project_path=project_path,
        use_llm=use_llm,
        python_version=python_version,
        resolved_packages_enhanced=resolved_packages_enhanced,
        num_dockerfiles=num_dockerfiles_to_generate,
        max_attempts=50,     # Not used anymore, kept for compatibility
        build_timeout=300,   # 5 minutes per build
        requirements=requirements
    )

    # =================================================================
    # 🧹 STEP 6: Cleanup and Generate Final Output Files
    # =================================================================
    print("\n" + "="*50)
    print("🧹 STEP 6: Cleanup and Generate Final Output Files")
    print("="*50)

    # 6.1: Remove intermediate directories and old result files (not needed in final output)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Remove testscript directory
    if os.path.exists(testscript_dir):
        try:
            shutil.rmtree(testscript_dir)
            print(f"   ✅ Removed intermediate directory: {testscript_dir}")
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to remove testscript directory: {e}")

    # 6.2: Generate final output files 
    print("\n" + "="*50)
    print("📤 Generating Final Output Files")
    print("="*50)

    # Get the .venv directory path
    venv_dir = os.path.dirname(state_file) if state_file else os.path.join(os.getcwd(), ".venv")

    # Output File 1: Execution Trace (copy from .venv/.execution_trace.json)
    execution_trace_source = os.path.join(venv_dir, ".execution_trace.json")
    execution_trace_output = os.path.join(result_dir, "execution_trace.json")

    if os.path.exists(execution_trace_source):
        shutil.copy2(execution_trace_source, execution_trace_output)
        print(f"   ✅ File 1: Execution trace → {execution_trace_output}")

        # Show file size
        file_size = os.path.getsize(execution_trace_output)
        print(f"      Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    else:
        print(f"   ⚠️ Warning: Execution trace not found at {execution_trace_source}")

    # Note: Inferred package versions were already generated and saved in Step 4.5.
    
    print("\n" + "="*50)
    print("✅ Final Output Summary")
    print("="*50)
    if mode == 'real':
        inferred_versions_output = os.path.join(result_dir, "inferred_package_versions.json")
        print(f"   📄 Primary Output File: {inferred_versions_output} (successfully inferred packages)")
        print(f"   📄 Trace Output File: {execution_trace_output} (program execution trace)")
        print(f"   📄 Report Output File: resolution_report.txt (human-readable report)")
        print(f"   🐳 Dockerfiles Output: ./generated_dockerfiles/ (Based strictly on inferred packages)")
    else:
        print(f"   📄 Output File: {config_output_path} (resolved package versions)")
    print("="*50)


if __name__ == "__main__":
    main()