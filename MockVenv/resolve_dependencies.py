import json
import os
import sys
import urllib.request
import itertools
import llm_client
import shutil
import multiprocessing
from functools import partial

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
def get_pypi_versions(package_name, resolve_name=True, return_canonical_name=False, filter_prereleases=False):
    """
    Fetch all available versions for a package in real-time via the PyPI API.

    Args:
        package_name: Package name (import name or PyPI name)
        resolve_name: If True, resolve import name to PyPI name. If False, use package_name as-is.
        return_canonical_name: If True, return tuple (canonical_name, versions). If False, return only versions.
        filter_prereleases: If True, filter out pre-release versions (alpha, beta, rc). Default False.

    Returns:
        If return_canonical_name=False: List of version strings sorted newest to oldest
        If return_canonical_name=True: Tuple of (canonical_package_name, list of versions)
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
            all_releases = list(data["releases"].keys())

            # Optionally filter out pre-release versions
            if filter_prereleases:
                # More sophisticated pre-release detection
                versions = []
                for v in all_releases:
                    v_lower = v.lower()
                    # Skip versions with common pre-release identifiers
                    if any(pre in v_lower for pre in ['rc', 'beta', 'alpha', 'dev', 'a0', 'b0', 'c0']):
                        continue
                    versions.append(v)
            else:
                versions = all_releases

            sorted_versions = sorted(versions, reverse=True)

            if return_canonical_name:
                return canonical_name, sorted_versions
            return sorted_versions
    except Exception as e:
        print(f"⚠️ Failed to fetch versions for '{pypi_name}': {e}")
        if return_canonical_name:
            return package_name, []
        return []


def analyze_api_signatures_for_hints(package_name, api_signatures, all_versions):
    """
    Use LLM to analyze API signatures and provide intelligent version hints.

    This is a GENERAL-PURPOSE analyzer that works for any package by leveraging
    LLM's knowledge of package version histories and API evolution patterns.

    Args:
        package_name: Name of the package
        api_signatures: List of API call signatures
        all_versions: List of all available versions from PyPI

    Returns:
        dict with LLM-generated analysis results
    """
    if not api_signatures or not all_versions:
        return {
            "detected_patterns": [],
            "version_constraints": None,
            "confidence": "low",
            "reasoning": "Insufficient data for analysis"
        }

    pypi_name = _resolve_pypi_name_from_import(package_name)

    # Prepare prompt for LLM analysis
    prompt = f"""You are a Python package version analyzer with deep knowledge of PyPI packages and their API evolution.

Package: {pypi_name}
Available Versions: {all_versions[:30] if len(all_versions) > 30 else all_versions}
{'(Showing first 30 of ' + str(len(all_versions)) + ' versions)' if len(all_versions) > 30 else ''}

Observed API Signatures (sample):
{chr(10).join(api_signatures[:20])}
{'(Showing first 20 of ' + str(len(api_signatures)) + ' signatures)' if len(api_signatures) > 20 else ''}

TASK: Analyze these API signatures to identify version-specific patterns.

Look for indicators such as:
1. **Deprecated parameters**: Parameters that were removed or renamed in certain versions
   - Example: PyJWT's `verify` parameter (existed in <2.0, changed to `options` in >=2.0)

2. **New parameters**: Parameters that were added in specific versions
   - Example: New optional parameters introduced in major versions

3. **Method/class availability**: APIs that only exist in certain version ranges
   - Example: New methods added in v2.0+, old methods removed in v3.0+

4. **Signature changes**: Parameter order changes, type hint changes, or default value changes

5. **Breaking changes**: Major version bumps that typically introduce incompatibilities

Based on your analysis, return a JSON object with this structure:
{{
  "detected_patterns": ["list of specific patterns you detected"],
  "version_constraints": "suggested version constraint (e.g., '<2.0', '>=2.5', '>=1.0,<2.0') or null if no strong constraint",
  "confidence": "high/medium/low",
  "reasoning": "clear explanation of why you suggested this constraint"
}}

IMPORTANT:
- Only suggest version constraints if you detect CLEAR breaking change indicators
- If APIs appear stable across versions, return confidence: "low" and version_constraints: null
- Be conservative: prefer no constraint over incorrect constraint
- Focus on ACTUAL API compatibility, not just guessing

Your response (JSON only):"""

    try:
        # Use LLM to analyze the patterns
        print(f"   🧠 [Pattern Analyzer] Asking LLM to analyze API patterns for {pypi_name}...")
        result = llm_client.analyze_api_patterns(prompt)

        if result and isinstance(result, dict):
            print(f"   💡 [Pattern Analyzer] Confidence: {result.get('confidence', 'unknown')}")
            return result
        else:
            print(f"   ⚠️ [Pattern Analyzer] Failed to get valid response")
            return {
                "detected_patterns": [],
                "version_constraints": None,
                "confidence": "low",
                "reasoning": "LLM analysis failed"
            }
    except Exception as e:
        print(f"   ⚠️ [Pattern Analyzer] Error during analysis: {e}")
        return {
            "detected_patterns": [],
            "version_constraints": None,
            "confidence": "low",
            "reasoning": f"Analysis error: {e}"
        }


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


def infer_versions_from_llm(package_name, api_signatures, requirements_versions=None):
    """
    Call the abstracted LLM Client to deduce an array of compatible versions
    based on the observed API signatures.

    Args:
        package_name: Name of the package
        api_signatures: List of API call signatures (e.g., ["semver.VersionInfo()", ...])
        requirements_versions: Optional list of versions from requirements.txt to constrain search
    """
    pypi_name = _resolve_pypi_name_from_import(package_name)
    # Get all versions including pre-releases initially for better debugging
    # Also get the canonical name from PyPI to ensure case-correct matching
    # Use resolve_name=False since we already resolved the name above
    canonical_name, all_versions_raw = get_pypi_versions(pypi_name, resolve_name=False, return_canonical_name=True)

    if not all_versions_raw:
        return []

    # If we have requirements.txt constraints, use those versions directly
    # if requirements_versions:
    #     # For pinned versions (from requirements.txt), we should use them as-is
    #     # and not filter them further with LLM analysis
    #     print(f"   📋 Using pinned versions from requirements.txt: {requirements_versions}")

    #     # Validate that the required versions exist in PyPI (case-insensitive check)
    #     validated_versions = []
    #     for req_ver in requirements_versions:
    #         # Try exact match first
    #         if req_ver in all_versions_raw:
    #             validated_versions.append(req_ver)
    #         else:
    #             # Try case-insensitive and whitespace-tolerant match
    #             req_ver_normalized = req_ver.strip().lower()
    #             found = False
    #             for pypi_ver in all_versions_raw:
    #                 if pypi_ver.strip().lower() == req_ver_normalized:
    #                     validated_versions.append(pypi_ver)
    #                     found = True
    #                     break

    #             if not found:
    #                 print(f"   ⚠️ Warning: Version '{req_ver}' from requirements.txt not found in PyPI")
    #                 print(f"   💡 Attempting to use it anyway (PyPI may accept it)")
    #                 # Still include the version even if not found in the filtered list
    #                 # because PyPI's pre-release filter might have excluded it
    #                 validated_versions.append(req_ver)

    #     if not validated_versions:
    #         print(f"   ⚠️ No versions from requirements.txt found in PyPI for '{canonical_name}'")
    #         print(f"   📋 Requirements.txt versions: {requirements_versions}")
    #         print(f"   📦 Available PyPI versions (first 20): {all_versions_raw[:20]}")
    #         return []

    #     # For requirements.txt pinned versions, skip LLM analysis and return directly
    #     return validated_versions

    # If no requirements.txt constraints, proceed with all versions
    all_versions = all_versions_raw

    if not api_signatures:
        return all_versions

    print(f"🧠 [LLM Engine] Analyzing API signatures for '{package_name}'...")
    print(f"   📊 Analyzing {len(api_signatures)} API calls against {len(all_versions)} versions")

    # Analyze signatures for version hints using LLM
    hints = analyze_api_signatures_for_hints(package_name, api_signatures, all_versions)
    if hints["confidence"] in ["high", "medium"]:
        print(f"   🔍 Detected patterns: {', '.join(hints['detected_patterns'])}")
        if hints.get('version_constraints'):
            print(f"   💡 Version hint: {hints['version_constraints']}")
        print(f"   📝 Reasoning: {hints.get('reasoning', 'N/A')}")

    # Enhanced prompt with better guidance on version range inference
    # Build hints section dynamically based on LLM pattern analysis
    hints_section = ""
    if hints['confidence'] in ['high', 'medium']:
        hints_section = f"""
PATTERN ANALYSIS RESULTS (Confidence: {hints['confidence'].upper()}):
{chr(10).join([f"- Detected Pattern: {p}" for p in hints['detected_patterns']]) if hints['detected_patterns'] else "- No specific patterns detected"}
{f"- Suggested Version Constraint: {hints['version_constraints']}" if hints.get('version_constraints') else "- No version constraint suggested"}
- Analysis Reasoning: {hints.get('reasoning', 'N/A')}
"""

    prompt = f"""You are an expert Python Dependency Resolution Engine with deep knowledge of PyPI packages and their version histories.

TARGET PACKAGE: {canonical_name}

AVAILABLE VERSIONS (sorted newest to oldest):
{all_versions[:30] if len(all_versions) > 30 else all_versions}
{'>>> Showing first 30 of ' + str(len(all_versions)) + ' total versions' if len(all_versions) > 30 else ''}

OBSERVED API SIGNATURES (from actual runtime execution):
Total API calls: {len(api_signatures)}
{chr(10).join(api_signatures[:30])}
{'>>> Showing first 30 signatures' if len(api_signatures) > 30 else ''}
{hints_section}

═══════════════════════════════════════════════════════════════
TASK: VERSION COMPATIBILITY ANALYSIS
═══════════════════════════════════════════════════════════════

Your mission: Identify ALL versions of {canonical_name} that are compatible with the observed API signatures above.

ANALYSIS METHODOLOGY:

1. **API Signature Examination**:
   - Examine each API call for version-specific indicators
   - Look for deprecated/renamed parameters across version history
   - Identify methods/classes that were added or removed in certain versions
   - Pay attention to parameter types, default values, and calling conventions

2. **Breaking Change Detection**:
   - Major version bumps (e.g., 1.x → 2.x) often introduce breaking changes
   - API deprecations typically happen across major versions
   - Parameter renames, signature changes, or removed methods indicate incompatibility
   - Only exclude versions with CONFIRMED incompatibilities

3. **Version Range Strategy**:
   - **DEFAULT APPROACH: Return BROAD ranges when APIs are stable**
   - If an API pattern is stable across v1.0-v1.9, include ALL those versions
   - Don't artificially narrow the range without evidence of breaking changes
   - Multiple compatible versions are MORE valuable than a single version

4. **Confidence Calibration**:
   - High confidence: Clear breaking changes detected (e.g., parameter renames)
   - Medium confidence: Partial evidence (e.g., major version pattern)
   - Low confidence: Stable APIs across versions → return wider range

5. **Evidence-Based Reasoning**:
   - Base decisions on actual API compatibility, not speculation
   - If pattern analysis suggests a constraint, validate it against the API signatures
   - When in doubt, include the version (false positives better than false negatives)

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Return ONLY a JSON array of compatible version strings (newest to oldest).
Include ALL versions that could reasonably support these API patterns.

Example: ["2.1.0", "2.0.9", "2.0.8", "2.0.7", "2.0.6", "2.0.5", "2.0.4"]

Your response (JSON array only):"""

    # 💡 Elegant one-line call to our LLM service hub
    valid_versions = llm_client.infer_versions(prompt)

    if valid_versions:
        print(f"   ✅ [LLM Insight] Constrained from {len(all_versions)} down to {len(valid_versions)} compatible versions.")
        return valid_versions

    # Fallback strategy: if inference fails or returns empty, assume all stable versions
    return all_versions


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
        args: tuple of (idx, total, import_name, api_signatures, pypi_import_mapping, requirements_packages, requirements)

    Returns:
        tuple: (matched_req_pkg, versions, error_msg) or None if package not in requirements
    """
    idx, total, import_name, api_signatures, pypi_import_mapping, requirements_packages, requirements = args

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

        # Infer compatible versions based on API signatures
        versions = infer_versions_from_llm(import_name, api_signatures, req_versions)

        if versions:
            print(f"   ✅ Result: {len(versions)} compatible versions found")
            print(f"   📌 Top versions: {versions[:5]}")
            return (matched_req_pkg, versions, None)
        else:
            print(f"   ⚠️ Result: No compatible versions found")
            return (matched_req_pkg, [], None)

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
        tuple: (package_name, versions, error_msg)
    """
    idx, total, package_name, requirements = args

    try:
        print(f"\n[{idx}/{total}] Processing package: {package_name}")

        # Get version constraints from requirements.txt
        req_versions = requirements.get(package_name)

        # Fetch all versions from PyPI
        all_versions = get_pypi_versions(package_name, resolve_name=False)

        if all_versions:
            # If requirements.txt specifies versions, use those; otherwise use all
            if req_versions:
                filtered_versions = [v for v in all_versions if v in req_versions]
                if filtered_versions:
                    print(f"   ✅ {len(filtered_versions)} versions from requirements.txt")
                    print(f"   📌 Versions: {filtered_versions}")
                    return (package_name, filtered_versions, None)
                else:
                    # Fall back to all versions if constraints don't match
                    print(f"   ⚠️ No matching versions, using all {len(all_versions)} versions")
                    print(f"   📌 Top versions: {all_versions[:5]}")
                    return (package_name, all_versions, None)
            else:
                print(f"   ✅ All {len(all_versions)} versions allowed (no API constraints)")
                print(f"   📌 Top versions: {all_versions[:5]}")
                return (package_name, all_versions, None)
        else:
            print(f"   ⚠️ No versions found on PyPI for package: {package_name}")
            return (package_name, [], None)

    except Exception as e:
        error_msg = f"Error processing {package_name}: {str(e)}"
        print(f"   ❌ {error_msg}")
        return (package_name, [], error_msg)


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


def generate_dockerfile(combination, base_image="python:3.11-slim", project_path=None, use_llm=True):
    """
    Generate a Dockerfile for a specific package combination.

    Args:
        combination: dict {package_name: version}
        base_image: Docker base image to use
        project_path: Optional path to project directory for volume mounting
        use_llm: If True, use LLM to generate content (default). If False, use template.

    Returns:
        dict with keys:
            - 'dockerfile': str (Dockerfile content)
            - 'readme_section': str (README section for this configuration)
    """
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

# Install packages WITHOUT their dependencies (--no-deps flag)
# This ensures only the specified packages are installed, not their transitive dependencies
RUN pip install --no-cache-dir --no-deps \\
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


def interactive_dockerfile_generation_optimized(resolved_packages, project_path=None, use_llm=True):
    """
    Allow user to interactively select how many Dockerfiles to generate.
    Generates combinations on-demand to avoid memory issues.

    Args:
        resolved_packages: dict {package_name: [list of compatible versions]}
        project_path: Optional path to project directory for volume mounting
        use_llm: If True, use LLM to generate Dockerfile content (default). If False, use template.
    """
    if not resolved_packages:
        print("❌ No packages to generate Dockerfiles from.")
        return

    # Calculate total possible combinations
    packages = list(resolved_packages.keys())
    version_lists = [resolved_packages[pkg] for pkg in packages]
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
            f.write(f"- **No Dependencies Flag**: All packages are installed with `--no-deps` flag, meaning only the specified packages are installed WITHOUT their transitive dependencies\n")
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
            f.write(f"- **No Dependencies Flag**: All packages are installed with `--no-deps` flag, meaning only the specified packages are installed WITHOUT their transitive dependencies\n")
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
        generated_content = generate_dockerfile(combination, project_path=project_path, use_llm=use_llm)

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
        print(f"   • Packages are installed with --no-deps flag (NO transitive dependencies)")
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
        print(f"   • Packages are installed with --no-deps flag (NO transitive dependencies)")
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
        print("Usage: python resolve_dependencies.py <state_file_path> [mode] [requirements_file] [project_path] [use_llm]")
        print("  use_llm: 'true' (default) to use LLM for Dockerfile generation, 'false' to use template")
        sys.exit(1)

    state_file = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'mock'
    requirements_path = sys.argv[3] if len(sys.argv) > 3 else "requirements.txt"
    project_path = sys.argv[4] if len(sys.argv) > 4 else None
    use_llm_arg = sys.argv[5] if len(sys.argv) > 5 else 'true'
    use_llm = use_llm_arg.lower() != 'false'  # Default to True unless explicitly set to 'false'

    if not os.path.exists(state_file):
        print(f"\n❌ File not found: {state_file}")
        sys.exit(1)

    print(f"📂 Using state file: {state_file}")
    print(f"🎯 Mode: {mode}")
    if project_path:
        print(f"📁 Project path: {project_path}")
    print(f"🤖 LLM Dockerfile Generation: {'Enabled' if use_llm else 'Disabled (using template)'}")

    # Load requirements.txt for package constraints
    requirements = load_requirements_txt(requirements_path)
    if requirements:
        print(f"📋 Loaded {len(requirements)} packages from requirements.txt: {requirements_path}")
    else:
        print(f"⚠️ No requirements.txt found or empty, will use all available versions from PyPI")

    # Dictionary to store the resolved configuration
    resolved_packages = {}

    if mode == 'real':
        # Load pypi_import_mapping.json first
        print("\n" + "="*50)
        print("🗺️ STEP 0: Loading PyPI import mapping")
        print("="*50)
        # Try to find pypi_import_mapping.json in current directory or MockVenv directory
        mapping_file_path = "pypi_import_mapping.json"
        pypi_import_mapping = {}
        if os.path.exists(mapping_file_path):
            pypi_import_mapping = load_pypi_import_mapping(mapping_file_path)
        else:
            raise FileNotFoundError(f"⚠️ pypi_import_mapping.json not found in expected paths: {mapping_file_path}")

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
            (idx, total_packages, import_name, api_signatures, pypi_import_mapping, requirements_packages, requirements)
            for idx, (import_name, api_signatures) in enumerate(api_package_items, 1)
        ]

        # Process packages in parallel
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = pool.map(_process_package_with_api, process_args)

        # Collect results
        for result in results:
            if result is not None:
                matched_req_pkg, versions, error_msg = result
                if error_msg:
                    print(f"   ⚠️ Warning: {error_msg}")
                elif versions:
                    resolved_packages[matched_req_pkg] = versions
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
                package_name, versions, error_msg = result
                if error_msg:
                    print(f"   ⚠️ Warning: {error_msg}")
                elif versions:
                    resolved_packages[package_name] = versions
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

            versions = infer_versions_from_llm(pkg, api_signatures, req_versions)

            if versions:
                resolved_packages[pypi_name] = versions
                print(f"   ✅ '{pypi_name}': Locked in {len(versions)} compatible versions")

    # =================================================================
    # 💾 Output the Resolved Versions JSON
    # =================================================================
    print("\n" + "="*50)
    print("💾 STEP 4: Saving results")
    print("="*50)

    config_output_path = "resolved_versions.json"
    resolved_config = {
        "mode": mode,
        "resolved_packages": resolved_packages,
        "total_packages": len(resolved_packages),
        "generated_at": __import__('datetime').datetime.now().isoformat()
    }

    with open(config_output_path, "w") as f:
        json.dump(resolved_config, f, indent=4)

    print(f"✅ Saved resolved versions to: {config_output_path}")
    print(f"   📦 Total packages resolved: {len(resolved_packages)}")

    # Print summary
    print("\n📊 Summary of resolved packages:")
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
    # 🐳 Interactive Dockerfile Generation (without generating all combinations)
    # =================================================================
    print("\n" + "="*50)
    print("🐳 STEP 5: Dockerfile Generation")
    print("="*50)

    # Generate combinations on-demand during dockerfile generation
    # This avoids memory issues with large combination sets
    interactive_dockerfile_generation_optimized(resolved_packages, project_path=project_path, use_llm=use_llm)


if __name__ == "__main__":
    main()
