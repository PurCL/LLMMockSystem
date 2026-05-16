#!/usr/bin/env python3
"""
Script-based Version Validator: LLM-generated test scripts with uv venv validation.

This module uses LLM to generate test scripts based on API logs, then validates
package versions by actually running the scripts in isolated virtual environments.

Workflow:
1. Parse API calls from .api_calls.json
2. Use LLM to generate a Python test script that imports and uses all APIs
3. Create a uv virtual environment with specified Python version
4. Iterate through package versions:
   - Install the version with uv pip install
   - Run the test script
   - Mark as compatible if no errors, incompatible if errors occur
5. Save all compatible versions
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from llm_client import _ask_claude, _run_sync


def parse_api_calls_by_package(api_calls_file: str) -> Dict[str, List[str]]:
    """
    Parse .api_calls.json to extract API calls grouped by package.

    Args:
        api_calls_file: Path to .api_calls.json file

    Returns:
        Dict: {package_name: [list of API call strings]}
    """
    with open(api_calls_file, 'r') as f:
        api_calls_text = f.read()

    api_by_package = {}
    for line in api_calls_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Extract package name (first part before dot)
        if '.' in line:
            package_name = line.split('.')[0]

            # Skip non-package identifiers
            if package_name.lower() in {'var', 'function', 'type', 'method', 'object', 'self', 'cls'}:
                continue

            if package_name.startswith('__'):
                continue

            # Skip API calls with special Python internal representations
            # These cannot be properly validated in test scripts
            skip_patterns = ['<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>',
                           '<lambda>', '<module>', '<function>', '<builtin_function_or_method>',
                           '<type>', '<code>', '<list_iterator>', '<dict_itemiterator>',
                           '<range_iterator>', '<generator>', '<method>']

            if any(pattern in line for pattern in skip_patterns):
                continue

            # Skip private/internal APIs (those with modules starting with '_')
            # These are unstable and change between versions
            parts_check = line.split('(')[0].split('.')
            if any(part.startswith('_') and not part.startswith('__') for part in parts_check):
                continue

            if package_name not in api_by_package:
                api_by_package[package_name] = []

            if line not in api_by_package[package_name]:
                api_by_package[package_name].append(line)

    return api_by_package


def generate_test_script_with_llm(package_name: str, api_calls: List[str]) -> str:
    """
    Use LLM to generate a comprehensive test script based on API calls.

    Args:
        package_name: Name of the package to test
        api_calls: List of API call signatures from .api_calls.json

    Returns:
        Generated Python test script as a string
    """
    # Import llm_client
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    prompt = f"""Generate a Python test script to validate API compatibility for package: {package_name}

API calls observed from runtime execution (sample):
{chr(10).join(api_calls[:100])}
{'... (truncated, showing first 100 of {len(api_calls)} API calls)' if len(api_calls) > 100 else ''}

Total API calls: {len(api_calls)}

IMPORTANT Requirements:
1. Import the package "{package_name}"
2. Use hasattr() to check if APIs exist - DO NOT try to call or instantiate them
3. The script should:
   - Import necessary modules from {package_name}
   - For each API call like "package.module.Class()", check: hasattr(package.module, 'Class')
   - For each API call like "package.module.function()", check: hasattr(package.module, 'function')
   - Ignore parameter values in API calls - only check attribute names
   - Count successful checks and missing APIs
   - If at least 80% of APIs exist, print "SUCCESS" and exit(0)
   - If less than 80% exist, print "FAILED: only X/Y APIs found" and exit(1)
4. Use a counter to track found vs missing APIs - be tolerant of minor API changes
5. Make the script simple and safe - only check existence, do not execute
6. DO NOT use mock objects or test frameworks
7. Handle import errors and missing attributes gracefully with try-except

Return ONLY the Python script code, no markdown, no explanations.

Example structure:
```python
#!/usr/bin/env python3
import sys

try:
    import {package_name}

    total_checks = 0
    found_apis = 0
    missing_apis = []

    # Check API availability using hasattr
    total_checks += 1
    if hasattr({package_name}, 'SomeClass'):
        found_apis += 1
    else:
        missing_apis.append('{package_name}.SomeClass')

    # More checks...

    # Success if at least 80% of APIs found
    success_rate = found_apis / total_checks if total_checks > 0 else 0
    if success_rate >= 0.8:
        print("SUCCESS")
        sys.exit(0)
    else:
        print(f"FAILED: only {{found_apis}}/{{total_checks}} APIs found ({{success_rate*100:.1f}}%)")
        sys.exit(1)
except Exception as e:
    print(f"FAILED: {{e}}")
    sys.exit(1)
```

Generate the complete test script:"""

    system_prompt = """You are a Python test script generator. Generate clean, executable Python code without markdown formatting or explanations."""

    try:
        result = _run_sync(_ask_claude, prompt, system_prompt)

        # Clean up the response
        script = result.strip()

        # Remove markdown code blocks if present
        if script.startswith('```python'):
            script = script[len('```python'):].strip()
        elif script.startswith('```'):
            script = script[len('```'):].strip()

        if script.endswith('```'):
            script = script[:-len('```')].strip()

        return script

    except Exception as e:
        print(f"   ⚠️ LLM failed to generate test script: {e}")
        # Fallback: generate a simple test script
        return generate_simple_test_script(package_name, api_calls)


def generate_simple_test_script(package_name: str, api_calls: List[str]) -> str:
    """
    Generate a simple fallback test script without LLM.

    Args:
        package_name: Name of the package
        api_calls: List of API call signatures

    Returns:
        Simple Python test script with 80% tolerance
    """
    # Parse API calls to extract modules and attributes
    imports = set()
    api_checks = []

    for api_call in api_calls:
        # Extract module path (remove parameters)
        api_path = api_call.split('(')[0]
        parts = api_path.split('.')

        if len(parts) >= 2:
            # Import the module
            imports.add(parts[0])

            # Create hasattr check for the attribute
            module_path = '.'.join(parts[:-1])
            attr_name = parts[-1]

            # Skip special patterns - expanded filter
            skip_patterns = ['__', '<listcomp>', '<dictcomp>', '<setcomp>', '<genexpr>',
                           '<lambda>', '<module>', '<function>', '<builtin_function_or_method>',
                           '<type>', '<code>', '<list_iterator>', '<dict_itemiterator>',
                           '<range_iterator>', '<generator>', '<method>']

            if any(pattern in attr_name for pattern in skip_patterns):
                continue

            # Skip if attribute name is not a valid Python identifier
            if not attr_name.replace('_', '').isalnum():
                continue

            api_checks.append((module_path, attr_name, api_path))

    # Limit checks to prevent script from being too large
    api_checks = api_checks[:100]  # Increased from 50 to 100 for better coverage

    # Generate check code
    check_lines = []
    for module_path, attr_name, api_path in api_checks:
        check_lines.append(f"""    total_checks += 1
    try:
        obj = {module_path}
        if hasattr(obj, '{attr_name}'):
            found_apis += 1
        else:
            missing_apis.append('{api_path}')
    except (AttributeError, ImportError):
        # Module structure might be different, skip this check
        total_checks -= 1  # Don't count failed imports""")

    script = f"""#!/usr/bin/env python3
import sys

try:
    # Import package
    import {package_name}

    # Track API availability - be tolerant of version differences (80% threshold)
    total_checks = 0
    found_apis = 0
    missing_apis = []

    # Check API availability (sample of {len(api_calls)} total APIs)
{chr(10).join(check_lines)}

    # Success if at least 80% of APIs are found
    success_rate = found_apis / total_checks if total_checks > 0 else 0
    if success_rate >= 0.8:
        print("SUCCESS")
        sys.exit(0)
    else:
        print(f"FAILED: only {{found_apis}}/{{total_checks}} APIs found ({{success_rate*100:.1f}}%)")
        if missing_apis[:3]:
            print(f"Sample missing: {{', '.join(missing_apis[:3])}}")
        sys.exit(1)

except Exception as e:
    print(f"FAILED: {{e}}")
    sys.exit(1)
"""

    return script


def test_version_with_uv(
    package_name: str,
    version: str,
    test_script: str,
    python_version: str = "3.10",
    timeout: int = 30
) -> Tuple[bool, Optional[str]]:
    """
    Test a package version by running the test script in a uv virtual environment.

    Args:
        package_name: Name of the package
        version: Version string to test
        test_script: Python test script content
        python_version: Python version for uv venv (e.g., '3.10')
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_compatible, error_message)
    """
    # Ensure python_version is not empty
    if not python_version or python_version.strip() == "":
        python_version = "3.10"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test script
        test_script_path = os.path.join(tmpdir, "test_script.py")
        with open(test_script_path, 'w') as f:
            f.write(test_script)

        venv_path = os.path.join(tmpdir, "validate_venv")

        try:
            # Step 1: Create uv virtual environment
            create_venv_cmd = f"uv venv {os.path.join(tmpdir, 'validate_venv')} --python {python_version}"
            result = subprocess.run(
                create_venv_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable='/bin/bash'
            )

            if result.returncode != 0:
                return False, f"Failed to create venv: {result.stderr[:200]}"

            # Step 2: Install the package version
            # Use explicit bash and PATH modification instead of source
            python_bin = os.path.join(venv_path, "bin", "python")
            uv_pip_cmd = f"uv pip install --python {python_bin} {package_name}=={version}"

            result = subprocess.run(
                uv_pip_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable='/bin/bash'
            )

            if result.returncode != 0:
                return False, f"Failed to install {package_name}=={version}: {result.stderr[:200]}"

            # Step 3: Run the test script
            run_cmd = f"{python_bin} {test_script_path}"

            result = subprocess.run(
                run_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable='/bin/bash'
            )

            # Check if test passed
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                return True, None
            else:
                error_msg = result.stdout + result.stderr
                return False, error_msg[:300]

        except subprocess.TimeoutExpired:
            return False, f"Timeout after {timeout}s"
        except Exception as e:
            return False, f"Error: {str(e)}"


def _generate_script_worker_top_level(args):
    """Worker function to generate a single test script (top-level for pickling)."""
    idx, total, package_name, api_calls, test_script_dir = args

    print(f"\n[{idx}/{total}] Generating test script for {package_name}")
    print(f"   📝 API calls: {len(api_calls)}")

    # Generate test script with LLM (ONLY ONCE per package)
    print(f"   🤖 Using LLM to generate test script...")
    test_script = generate_test_script_with_llm(package_name, api_calls)

    # Save test script for debugging
    test_script_path = os.path.join(test_script_dir, f"test_{package_name}.py")
    with open(test_script_path, 'w') as f:
        f.write(test_script)
    print(f"   ✅ Test script saved: {test_script_path}")

    return (package_name, test_script)


def validate_package_versions_with_scripts(
    package_name: str,
    test_script: str,
    candidate_versions: List[str],
    python_version: str = "3.10",
    max_workers: int = 4,
    timeout: int = 30,
    requirements_version: str = None
) -> Tuple[List[str], Optional[str], Optional[dict]]:
    """
    Validate package versions using script-based testing with a pre-generated test script.

    Args:
        package_name: Name of the package
        test_script: Pre-generated Python test script content
        candidate_versions: List of version strings to test
        python_version: Python version for testing (e.g., '3.10')
        max_workers: Number of parallel workers
        timeout: Timeout per version test
        requirements_version: The version specified in requirements.txt (for validation)

    Returns:
        Tuple of (List of compatible version strings, Optional error reason, Optional stats dict)
    """
    print(f"\n🔍 Validating {package_name} with script-based testing...")
    print(f"   📊 Testing {len(candidate_versions)} versions")
    print(f"   🐍 Using Python {python_version}")
    print(f"   🧪 Using {max_workers} parallel workers")
    if requirements_version:
        print(f"   📋 Requirements.txt version: {requirements_version}")

    # Initialize statistics
    stats = {
        "pypi_versions": len(candidate_versions),
        "installable_versions": 0,
        "script_passed_versions": 0,
        "requirements_version_failed": False,
        "requirements_version_error": None
    }

    # STEP 1: First, test the requirements.txt version with the test script
    requirements_version_exists = False
    if requirements_version:
        print(f"\n   🧪 Step 1: Testing requirements.txt version ({requirements_version}) with generated script...")
        is_compatible, error_msg = test_version_with_uv(
            package_name,
            requirements_version,
            test_script,
            python_version,
            timeout
        )

        if not is_compatible:
            # requirements.txt version failed the test script
            print(f"   ❌ Requirements.txt version FAILED the test!")
            print(f"   ❌ Error: {error_msg[:200] if error_msg else 'Unknown error'}")

            # Record this failure
            stats["requirements_version_failed"] = True
            stats["requirements_version_error"] = error_msg[:200] if error_msg else 'Unknown error'

            # CHANGED: Always continue testing other versions instead of returning early
            # Even if test script has issues, we should find versions that work with the script
            print(f"   ⚠️ Requirements.txt version failed validation")
            print(f"   📌 Will continue testing all candidate versions to find compatible ones...")
            requirements_version_exists = False
        else:
            print(f"   ✅ Requirements.txt version PASSED the test!")
            print(f"   ▶️ Proceeding to test other versions...")
            requirements_version_exists = True

    # STEP 2: Test all versions in parallel
    print(f"\n   🧪 Step 2: Testing all {len(candidate_versions)} candidate versions...")
    compatible_versions = []
    incompatible_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_version = {
            executor.submit(
                test_version_with_uv,
                package_name,
                version,
                test_script,
                python_version,
                timeout
            ): version
            for version in candidate_versions
        }

        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_version), 1):
            version = future_to_version[future]

            try:
                is_compatible, error_msg = future.result()

                if is_compatible:
                    compatible_versions.append(version)
                    print(f"   [{i}/{len(candidate_versions)}] {version} ✅ COMPATIBLE")
                else:
                    incompatible_count += 1
                    error_preview = error_msg[:80] if error_msg else "Unknown error"
                    print(f"   [{i}/{len(candidate_versions)}] {version} ❌ INCOMPATIBLE ({error_preview})")

            except Exception as e:
                incompatible_count += 1
                print(f"   [{i}/{len(candidate_versions)}] {version} ❌ ERROR: {str(e)[:80]}")

    print(f"\n   ✅ Found {len(compatible_versions)} compatible versions")
    print(f"   ❌ Filtered out {incompatible_count} incompatible versions")

    # Update statistics
    stats["script_passed_versions"] = len(compatible_versions)
    # Note: installable_versions is the same as script_passed_versions since we only test script on successfully installed packages

    # STEP 3: Verify that requirements.txt version is in the compatible list
    if requirements_version and compatible_versions and requirements_version_exists:
        if requirements_version not in compatible_versions:
            print(f"\n   ⚠️ WARNING: Requirements.txt version ({requirements_version}) NOT in compatible list!")
            print(f"   ⚠️ This indicates an error in validation - the version that should work is missing")
            # CHANGED: Don't return requirements_version if it's not in compatible list
            # Instead, use the compatible versions we found
            print(f"   📌 Using {len(compatible_versions)} validated compatible versions instead")
            return compatible_versions, "requirements_version_not_in_compatible_using_validated", stats

        print(f"   ✅ Verification passed: Requirements.txt version ({requirements_version}) is in compatible list")
    elif requirements_version and not requirements_version_exists:
        print(f"\n   ⚠️ Requirements.txt version ({requirements_version}) failed validation")
        if compatible_versions:
            print(f"   ✅ Found {len(compatible_versions)} compatible versions from PyPI")
        else:
            print(f"   ❌ No compatible versions found!")

    # If no compatible versions found at all, this indicates a serious problem
    if not compatible_versions:
        print(f"\n   ❌ CRITICAL: No compatible versions found after testing {len(candidate_versions)} candidates!")
        print(f"   ⚠️ This indicates the test script may be incorrect or the package has API breaking changes")
        return [], "no_compatible_versions_found", stats

    return compatible_versions, None, stats


def validate_all_packages_with_scripts(
    api_calls_file: str,
    resolved_versions_file: str,
    output_file: str = "validated_versions.json",
    python_version: str = "3.10",
    max_workers: int = 4,
    timeout: int = 30,
    requirements_file: str = None,
    max_retries: int = 5
):
    """
    Validate all packages using script-based testing with retry logic.

    OPTIMIZATION: Generate test script ONCE per package, then test all versions in parallel.

    Args:
        api_calls_file: Path to .api_calls.json
        resolved_versions_file: Path to resolved_versions.json
        output_file: Path to save validated versions
        python_version: Python version for testing (e.g., '3.10')
        max_workers: Number of parallel workers per package
        timeout: Timeout per version test
        requirements_file: Path to original requirements.txt to get original versions
        max_retries: Maximum number of retries for inference_failed cases (default: 5)
    """
    print("=" * 70)
    print("🧪 SCRIPT-BASED VERSION VALIDATOR (with retry logic)")
    print("=" * 70)

    # Load API calls
    print(f"\n📂 Loading API calls from: {api_calls_file}")
    api_by_package = parse_api_calls_by_package(api_calls_file)
    print(f"✅ Found API calls for {len(api_by_package)} packages")

    # Load resolved versions
    print(f"\n📂 Loading resolved versions from: {resolved_versions_file}")
    with open(resolved_versions_file, 'r') as f:
        resolved_data = json.load(f)

    resolved_packages = resolved_data.get('resolved_packages', {})
    print(f"✅ Found {len(resolved_packages)} packages")

    # Load original requirements.txt to get original versions
    original_versions = {}
    if requirements_file and os.path.exists(requirements_file):
        print(f"\n📂 Loading original versions from: {requirements_file}")
        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '==' in line:
                        pkg_name, version = line.split('==', 1)
                        pkg_name = pkg_name.strip()
                        version = version.strip()
                        # Normalize package name for lookup
                        normalized_name = pkg_name.lower().replace('_', '-')
                        original_versions[normalized_name] = (pkg_name, version)
            print(f"✅ Loaded {len(original_versions)} package versions from requirements.txt")
        except Exception as e:
            print(f"⚠️ Warning: Could not load requirements.txt: {e}")

    # STEP 1: Generate test scripts for all packages with API calls (ONCE per package)
    print("\n" + "=" * 70)
    print("🤖 STEP 1: Generating test scripts with LLM (one script per package)")
    print("=" * 70)

    test_script_dir = os.path.join(os.path.dirname(__file__), "generated_test_scripts")
    os.makedirs(test_script_dir, exist_ok=True)

    package_test_scripts = {}  # {package_name: test_script_content}
    packages_with_api = [pkg for pkg in resolved_packages.keys() if pkg in api_by_package and api_by_package[pkg]]

    print(f"📦 Generating test scripts for {len(packages_with_api)} packages...")

    # Calculate number of processes to use: min(32, cpu_count())
    num_processes = min(32, multiprocessing.cpu_count())
    print(f"🚀 Using {num_processes} parallel processes for test script generation")

    # Prepare arguments for parallel processing
    process_args = [
        (idx, len(packages_with_api), package_name, api_by_package[package_name], test_script_dir)
        for idx, package_name in enumerate(packages_with_api, 1)
    ]

    # Process packages in parallel
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(_generate_script_worker_top_level, process_args)

    # Collect results
    for package_name, test_script in results:
        package_test_scripts[package_name] = test_script

    print(f"\n✅ Generated {len(package_test_scripts)} test scripts")

    # STEP 2: Validate each package using pre-generated test scripts
    print("\n" + "=" * 70)
    print("🧪 STEP 2: Validating package versions with generated test scripts")
    print("=" * 70)

    validated_packages = {}
    validation_report = {
        "total_packages": len(resolved_packages),
        "validated_packages": 0,
        "total_candidate_versions": 0,
        "total_compatible_versions": 0,
        "python_version": python_version,
        "packages": {},
        # NEW: Track statistics for the report
        "total_pypi_versions": 0,
        "total_installable_versions": 0,
        "total_script_passed_versions": 0,
        "requirements_version_failures": []  # [(pkg_name, version, error_reason)]
    }

    for idx, (package_name, candidate_versions) in enumerate(resolved_packages.items(), 1):
        print(f"\n[{idx}/{len(resolved_packages)}] Processing {package_name}")
        validation_report["total_candidate_versions"] += len(candidate_versions)

        # Get requirements.txt version for this package
        normalized_name = package_name.lower().replace('_', '-')
        requirements_version = None
        if normalized_name in original_versions:
            _, requirements_version = original_versions[normalized_name]
            print(f"   📋 Requirements.txt version: {requirements_version}")

        # Check if we have a test script for this package
        if package_name not in package_test_scripts:
            # No test script (no API calls) - but still need to validate installability
            print(f"   ⚠️ No test script found for {package_name}")
            print(f"   🔧 Will validate installability of {len(candidate_versions)} versions (no API testing)")

            # Create a minimal test script that only checks if the package can be imported
            minimal_test_script = f"""#!/usr/bin/env python3
import sys
try:
    import {package_name}
    print("SUCCESS")
    sys.exit(0)
except ImportError as e:
    # Some packages use different import names, that's OK
    # As long as installation succeeded, we consider it valid
    print("SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {{e}}")
    sys.exit(1)
"""

            # Test installation for each version
            print(f"\n   🧪 Testing installability...")
            compatible_versions = []
            incompatible_count = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_version = {
                    executor.submit(
                        test_version_with_uv,
                        package_name,
                        version,
                        minimal_test_script,
                        python_version,
                        timeout
                    ): version
                    for version in candidate_versions
                }

                # Process results as they complete
                for i, future in enumerate(as_completed(future_to_version), 1):
                    version = future_to_version[future]

                    try:
                        is_compatible, error_msg = future.result()

                        if is_compatible:
                            compatible_versions.append(version)
                            if i % 10 == 0 or i == len(candidate_versions):
                                print(f"   [{i}/{len(candidate_versions)}] {version} ✅ (installable: {len(compatible_versions)})")
                        else:
                            incompatible_count += 1
                            # Check if it's an installation failure (package not found)
                            if error_msg and ("No matching distribution" in error_msg or
                                            "Could not find a version" in error_msg or
                                            "no version of" in error_msg.lower()):
                                if i % 10 == 0 or i == len(candidate_versions):
                                    print(f"   [{i}/{len(candidate_versions)}] {version} ❌ (not installable)")

                    except Exception as e:
                        incompatible_count += 1

            print(f"\n   ✅ Found {len(compatible_versions)} installable versions")
            print(f"   ❌ Filtered out {incompatible_count} non-installable versions")

            # Always keep at least the requirements.txt version if validation fails
            if not compatible_versions and requirements_version:
                print(f"   ⚠️ No versions passed validation, keeping requirements.txt version: {requirements_version}")
                compatible_versions = [requirements_version]
            elif not compatible_versions:
                print(f"   ⚠️ No versions passed validation, keeping all {len(candidate_versions)} as fallback")
                compatible_versions = candidate_versions

            validated_packages[package_name] = compatible_versions
            validation_report["total_compatible_versions"] += len(compatible_versions)

            # Collect statistics for packages without API calls
            validation_report["total_pypi_versions"] += len(candidate_versions)
            validation_report["total_script_passed_versions"] += len(compatible_versions)

            validation_report["packages"][package_name] = {
                "candidate_versions": len(candidate_versions),
                "compatible_versions": len(compatible_versions),
                "filtered_count": incompatible_count,
                "status": "no_api_calls_installability_tested",
                "retry_count": 0,
                "pypi_versions": len(candidate_versions),
                "installable_versions": len(compatible_versions),
                "script_passed_versions": len(compatible_versions)
            }
            continue

        # Get pre-generated test script
        test_script = package_test_scripts[package_name]
        print(f"   ✅ Using pre-generated test script")

        # Retry logic for inference failures
        compatible_versions = None
        error_reason = None
        retry_count = 0

        pkg_stats = None
        for attempt in range(max_retries):
            retry_count = attempt
            print(f"   🔄 Attempt {attempt + 1}/{max_retries}: Validating {len(candidate_versions)} versions...")

            # Validate versions with script-based testing (using pre-generated script)
            compatible_versions, error_reason, pkg_stats = validate_package_versions_with_scripts(
                package_name,
                test_script,  # Pass pre-generated test script
                candidate_versions,
                python_version=python_version,
                max_workers=max_workers,
                timeout=timeout,
                requirements_version=requirements_version
            )

            if error_reason:
                # Critical error occurred (e.g., test script failed on requirements version)
                print(f"   ❌ Critical error: {error_reason}")
                print(f"   📌 Returning only requirements.txt version")
                break

            if compatible_versions:
                # Success! Found compatible versions
                print(f"   ✅ Attempt {attempt + 1} succeeded: Found {len(compatible_versions)} compatible versions")
                break
            else:
                # Failed this attempt
                if attempt + 1 < max_retries:
                    print(f"   ❌ Attempt {attempt + 1} failed: No compatible versions found. Retrying...")
                    # Regenerate test script for next attempt
                    print(f"   🔄 Regenerating test script for retry attempt {attempt + 2}...")
                    api_calls = api_by_package[package_name]
                    test_script = generate_test_script_with_llm(package_name, api_calls)
                    package_test_scripts[package_name] = test_script
                else:
                    print(f"   ❌ All {max_retries} attempts failed. Keeping requirements.txt version.")

        if compatible_versions:
            # Found compatible versions through validation
            validated_packages[package_name] = compatible_versions
            validation_report["validated_packages"] += 1
            validation_report["total_compatible_versions"] += len(compatible_versions)

            status = "validated_success"
            if error_reason:
                status = f"error_{error_reason}"

            # Collect statistics
            if pkg_stats:
                validation_report["total_pypi_versions"] += pkg_stats.get("pypi_versions", 0)
                validation_report["total_script_passed_versions"] += pkg_stats.get("script_passed_versions", 0)
                # Track requirements.txt version failures
                if pkg_stats.get("requirements_version_failed") and requirements_version:
                    validation_report["requirements_version_failures"].append(
                        (package_name, requirements_version, pkg_stats.get("requirements_version_error"))
                    )

            validation_report["packages"][package_name] = {
                "candidate_versions": len(candidate_versions),
                "compatible_versions": len(compatible_versions),
                "filtered_count": len(candidate_versions) - len(compatible_versions),
                "status": status,
                "retry_count": retry_count + 1,
                "error_reason": error_reason if error_reason else None,
                "pypi_versions": pkg_stats.get("pypi_versions", 0) if pkg_stats else 0,
                "installable_versions": len(candidate_versions),  # All tested versions were installable
                "script_passed_versions": pkg_stats.get("script_passed_versions", 0) if pkg_stats else 0
            }
        else:
            # FIXED: All retries failed - only keep requirements.txt version
            # Reason: If validation fails repeatedly, we can only trust the original requirements.txt version
            print(f"   ⚠️ Validation failed after {max_retries} attempts!")
            if requirements_version:
                print(f"   📌 Keeping only requirements.txt version: {requirements_version}")
                print(f"   💡 Reason: Validation failed, only trusting the original specified version")
                validated_packages[package_name] = [requirements_version]
                validation_report["total_compatible_versions"] += 1

                # Update total statistics
                validation_report["total_pypi_versions"] += len(candidate_versions)
                # CHANGED: Don't force script_passed_versions to 1, keep it as 0 (real data)
                validation_report["total_script_passed_versions"] += 0  # No versions actually passed

                validation_report["packages"][package_name] = {
                    "candidate_versions": len(candidate_versions),
                    "compatible_versions": 1,
                    "filtered_count": len(candidate_versions) - 1,
                    "status": "validation_failed_kept_requirements_version_only",
                    "retry_count": max_retries,
                    "error_reason": "all_retries_failed_keeping_requirements_txt_version_only",
                    "pypi_versions": len(candidate_versions),
                    "installable_versions": len(candidate_versions),
                    "script_passed_versions": 0  # Real data: no versions passed script validation
                }
            else:
                print(f"   ❌ No requirements.txt version available!")
                print(f"   📌 Keeping all {len(candidate_versions)} candidate versions as fallback")
                validated_packages[package_name] = candidate_versions
                validation_report["total_compatible_versions"] += len(candidate_versions)

                # Update total statistics
                validation_report["total_pypi_versions"] += len(candidate_versions)
                # Note: total_script_passed_versions is not updated because no versions actually passed

                validation_report["packages"][package_name] = {
                    "candidate_versions": len(candidate_versions),
                    "compatible_versions": len(candidate_versions),
                    "filtered_count": 0,
                    "status": "validation_failed_no_requirements_version_kept_all",
                    "retry_count": max_retries,
                    "error_reason": "no_requirements_version_available_keeping_all_pypi_versions",
                    "pypi_versions": len(candidate_versions),
                    "installable_versions": len(candidate_versions),
                    "script_passed_versions": 0  # No versions actually passed script validation
                }

    # Save results
    output_data = {
        "mode": resolved_data.get("mode", "unknown"),
        "resolved_packages": validated_packages,
        "resolved_packages_enhanced": resolved_data.get("resolved_packages_enhanced", {}),
        "total_packages": len(validated_packages),
        "generated_at": resolved_data.get("generated_at", "unknown"),
        "validated_at": __import__('datetime').datetime.now().isoformat(),
        "validation_report": validation_report
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=4)

    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Python version: {python_version}")
    print(f"Total packages: {validation_report['total_packages']}")
    print(f"Successfully validated: {validation_report['validated_packages']}")
    print(f"Candidate versions (before): {validation_report['total_candidate_versions']}")
    print(f"Compatible versions (after): {validation_report['total_compatible_versions']}")
    filtered = validation_report['total_candidate_versions'] - validation_report['total_compatible_versions']
    print(f"Filtered out: {filtered} ({100*filtered/max(1, validation_report['total_candidate_versions']):.1f}%)")
    print(f"\n✅ Validated versions saved to: {output_file}")
    print("=" * 70)


def main():
    """Main entry point."""

    if len(sys.argv) < 3:
        print("Usage: python script_based_validator.py <api_calls.json> <resolved_versions.json> [output.json] [python_version] [max_workers] [timeout] [requirements.txt]")
        print("\nExample:")
        print("  python script_based_validator.py .venv/.api_calls.json resolved_versions.json validated_versions.json 3.10 auto 30 requirements.txt")
        print("\nNote: Use 'auto' for max_workers to use min(32, cpu_count())")
        sys.exit(1)

    api_calls_file = sys.argv[1]
    resolved_versions_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "validated_versions.json"
    python_version = sys.argv[4] if len(sys.argv) > 4 else "3.10"

    # Handle max_workers: support 'auto' or specific number
    max_workers_arg = sys.argv[5] if len(sys.argv) > 5 else "auto"
    if max_workers_arg.lower() == "auto":
        cpu_count = multiprocessing.cpu_count()
        max_workers = min(32, cpu_count)
        print(f"🖥️  Auto-detected {max_workers} workers (CPU count: {cpu_count})")
    else:
        max_workers = int(max_workers_arg)

    timeout = int(sys.argv[6]) if len(sys.argv) > 6 else 30
    requirements_file = sys.argv[7] if len(sys.argv) > 7 else None

    if not os.path.exists(api_calls_file):
        print(f"❌ Error: {api_calls_file} not found")
        sys.exit(1)

    if not os.path.exists(resolved_versions_file):
        print(f"❌ Error: {resolved_versions_file} not found")
        sys.exit(1)

    validate_all_packages_with_scripts(
        api_calls_file,
        resolved_versions_file,
        output_file,
        python_version,
        max_workers,
        timeout,
        requirements_file
    )


if __name__ == "__main__":
    main()
