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
import datetime
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from llm_client import _ask_claude, _run_sync

# Custom temporary directory to avoid disk quota issues on /tmp
CUSTOM_TMP_DIR = "/home/jian1000/data3/tmp/mockvenv_temp"

# Ensure the custom temp directory exists
if not os.path.exists(CUSTOM_TMP_DIR):
    os.makedirs(CUSTOM_TMP_DIR, exist_ok=True)

# Load PyPI to Python module import mapping
PYPI_IMPORT_MAPPING = {}
def load_import_mapping():
    """Load the PyPI to Python module import mapping from JSON file."""
    global PYPI_IMPORT_MAPPING
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mapping_file = os.path.join(script_dir, 'pypi_import_mapping.json')

    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r') as f:
                PYPI_IMPORT_MAPPING = json.load(f)
            print(f"✅ Loaded {len(PYPI_IMPORT_MAPPING)} PyPI import mappings")
        except Exception as e:
            print(f"⚠️ Warning: Could not load pypi_import_mapping.json: {e}")
    else:
        print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")

# Load mapping at module initialization
load_import_mapping()


def pypi_to_import_name(package_name: str) -> str:
    """
    Convert PyPI package name to Python import name.

    Args:
        package_name: PyPI package name (e.g., 'absl-py', 'typing-extensions')

    Returns:
        Python import name (e.g., 'absl', 'typing_extensions')
    """
    # Normalize package name to lowercase for lookup
    normalized_name = package_name.lower().replace('_', '-')

    # Check if there's a mapping
    if normalized_name in PYPI_IMPORT_MAPPING:
        return PYPI_IMPORT_MAPPING[normalized_name]

    # Fallback: replace hyphens with underscores
    # This works for most packages like charset-normalizer -> charset_normalizer
    return package_name.replace('-', '_')


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
    # Convert PyPI package name to Python import name
    import_name = pypi_to_import_name(package_name)

    # Import llm_client
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    prompt = f"""You are an expert Python testing engineer. Generate a test script to verify the existence of APIs in the {package_name} library (Python import name: {import_name}).

API calls observed from runtime execution (sample):
{chr(10).join(api_calls[:100])}
{'... (truncated, showing first 100 of {len(api_calls)} API calls)' if len(api_calls) > 100 else ''}

Total API calls: {len(api_calls)}

CRITICAL RULE: You MUST use the EXACT check_api function provided below. Do NOT modify its logic. Your ONLY job is to:
1. Parse the API calls to extract module paths and attribute names
2. Generate the check_api('module.path', 'attribute_name') calls at the bottom
3. For an API call like "numpy.core.memmap.memmap()", check it as: check_api('numpy.core', 'memmap') - NOT check_api('numpy.core.memmap', 'memmap')
4. Prefer public-facing API paths (e.g., numpy.memmap) over deep internal paths (e.g., numpy.core.memmap) when possible
5. Only check attribute names, ignore parameter values in API calls

Return ONLY the Python script code, no markdown, no explanations.

MANDATORY TEMPLATE - Use this exact code structure:

```python
#!/usr/bin/env python3
import sys
import importlib

total_checks = 0
found_apis = 0

def check_api(module_path, attr_name):
    \"\"\"
    Check if an API exists in the specified module.
    Uses importlib.import_module() for robust module loading.
    \"\"\"
    global total_checks, found_apis
    total_checks += 1
    try:
        # 1. Dynamically import the module first
        module = importlib.import_module(module_path)
        # 2. Check for the attribute
        if hasattr(module, attr_name):
            found_apis += 1
        else:
            print(f"FAILED: {{module_path}}.{{attr_name}} not found in module")
            sys.exit(1)
    except ImportError:
        # Fallback: Sometimes module_path includes a class (e.g., a.b.MyClass)
        # In this case, we need to import the parent module and get the class
        try:
            parts = module_path.rsplit('.', 1)
            if len(parts) == 2:
                parent_module = importlib.import_module(parts[0])
                parent_obj = getattr(parent_module, parts[1])
                if hasattr(parent_obj, attr_name):
                    found_apis += 1
                    return
        except Exception:
            pass
        print(f"FAILED: {{module_path}} could not be imported")
        sys.exit(1)
    except Exception as e:
        print(f"FAILED: {{module_path}}.{{attr_name}} - {{type(e).__name__}}: {{e}}")
        sys.exit(1)

# Main execution
try:
    # Import the base package first to verify it exists
    import {import_name}

    # Generate check_api calls based on the API calls
    # Example: check_api('{import_name}', 'SomeClass')
    # Example: check_api('{import_name}.submodule', 'function_name')

    # YOUR GENERATED CHECK_API CALLS GO HERE:
    # (Generate based on the API calls provided above)

    # Success only if ALL APIs found
    if found_apis == total_checks:
        print(f"SUCCESS: All {{found_apis}}/{{total_checks}} APIs found")
        sys.exit(0)
    else:
        print(f"FAILED: only {{found_apis}}/{{total_checks}} APIs found")
        sys.exit(1)

except ImportError as e:
    print(f"FAILED: Cannot import {import_name} - {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"FAILED: {{type(e).__name__}}: {{e}}")
    sys.exit(1)
```

Generate the complete test script with the check_api() calls filled in:"""

    system_prompt = """You are a Python test script generator specializing in API compatibility testing.

CRITICAL RULES:
1. Always use importlib.import_module() for dynamic module loading - NEVER use module_string.split('.') with getattr loops
2. The check_api() function logic is PROVIDED and must NOT be modified
3. Only generate the check_api() calls based on the API calls in the prompt
4. Distinguish between Modules and Attributes correctly to avoid false failures
5. Generate clean, executable Python code without markdown formatting or explanations"""

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
        Simple Python test script requiring 100% API success (ANY error is INCOMPATIBLE)
    """
    # Convert PyPI package name to Python import name
    import_name = pypi_to_import_name(package_name)

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
            print(f"FAILED: {api_path} not found")
            sys.exit(1)
    except Exception as e:
        # ANY error (including ModuleNotFoundError) is INCOMPATIBLE
        print(f"FAILED: {api_path} - {{type(e).__name__}}: {{e}}")
        sys.exit(1)""")

    script = f"""#!/usr/bin/env python3
import sys

try:
    # Import package
    import {import_name}

    # Track API availability - require 100% success (ANY error is INCOMPATIBLE)
    total_checks = 0
    found_apis = 0

    # Check API availability (sample of {len(api_calls)} total APIs)
{chr(10).join(check_lines)}

    # Success only if ALL APIs found
    if found_apis == total_checks:
        print(f"SUCCESS: All {{found_apis}}/{{total_checks}} APIs found")
        sys.exit(0)
    else:
        print(f"FAILED: only {{found_apis}}/{{total_checks}} APIs found")
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
    python_version: str = "3.11",
    timeout: int = 30,
    requirements_file: str = None
) -> Tuple[bool, Optional[str]]:
    """
    Test a package version by running the test script in a uv virtual environment.

    Args:
        package_name: Name of the package
        version: Version string to test
        test_script: Python test script content
        python_version: Python version for uv venv (e.g., '3.11')
        timeout: Timeout in seconds
        requirements_file: Path to requirements.txt to install additional dependencies

    Returns:
        Tuple of (is_compatible, error_message)
    """
    # Ensure python_version is not empty
    if not python_version or python_version.strip() == "":
        python_version = "3.11"

    with tempfile.TemporaryDirectory(dir=CUSTOM_TMP_DIR) as tmpdir:
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

            # Step 2: Install the package version FIRST
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

            # Step 3: Install other dependencies from requirements.txt (if provided)
            # Install one by one, skip if conflicts occur
            if requirements_file and os.path.exists(requirements_file):
                with open(requirements_file, 'r') as f:
                    requirements_lines = f.readlines()

                # Normalize package name for comparison
                normalized_pkg_name = package_name.lower().replace('_', '-')

                for line in requirements_lines:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse package name from line (handle package==version format)
                    if '==' in line:
                        req_pkg_name, req_version = line.split('==', 1)
                        req_pkg_name = req_pkg_name.strip()
                        req_version = req_version.strip()
                    else:
                        req_pkg_name = line.strip()
                        req_version = None

                    # Skip the package we're currently testing
                    normalized_req_pkg_name = req_pkg_name.lower().replace('_', '-')
                    if normalized_req_pkg_name == normalized_pkg_name:
                        continue

                    # Try to install this dependency
                    if req_version:
                        install_cmd = f"uv pip install --python {python_bin} {req_pkg_name}=={req_version}"
                    else:
                        install_cmd = f"uv pip install --python {python_bin} {req_pkg_name}"

                    try:
                        result = subprocess.run(
                            install_cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            executable='/bin/bash'
                        )

                        # If installation failed (conflict or not found), just skip it
                        if result.returncode != 0:
                            # Silently skip conflicting packages
                            pass
                    except subprocess.TimeoutExpired:
                        # Skip if timeout
                        pass
                    except Exception:
                        # Skip if any error
                        pass

            # Step 4: Run the test script
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


def _mp_worker_test_version(args):
    pkg_name, version, script_content, python_version, timeout, req_file = args
    try:
        is_compatible, error_msg = test_version_with_uv(
            pkg_name, version, script_content, python_version, timeout, req_file
        )
        return (version, is_compatible, error_msg)
    except Exception as e:
        return (version, False, str(e))


def validate_all_packages_with_scripts(
    api_calls_file: str,
    fetched_packages: dict,
    python_version: str = "3.11",
    max_workers: int = 4,
    timeout: int = 30,
    requirements_file: str = None,
    max_retries: int = 5
):
    print("=" * 70)
    print("🧪 SCRIPT-BASED VERSION VALIDATOR (Sequential Packages, Parallel Versions)")
    print("=" * 70)

    # Load API calls
    print(f"\n📂 Loading API calls from: {api_calls_file}")
    api_by_package = parse_api_calls_by_package(api_calls_file)
    print(f"✅ Found API calls for {len(api_by_package)} packages")

    # Use fetched_packages directly (it's already a dict)
    print(f"\n📂 Using fetched packages: {len(fetched_packages)} packages")

    print(f"✅ Found {len(fetched_packages)} packages")

    # Load original requirements.txt to get original versions
    original_versions = {}
    if requirements_file and os.path.exists(requirements_file):
        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '==' in line:
                        pkg_name, version = line.split('==', 1)
                        normalized_name = pkg_name.strip().lower().replace('_', '-')
                        original_versions[normalized_name] = (pkg_name.strip(), version.strip())
            print(f"✅ Loaded {len(original_versions)} package versions from requirements.txt")
        except Exception as e:
            print(f"⚠️ Warning: Could not load requirements.txt: {e}")

    print("\n" + "=" * 70)
    print("🧪 Validating packages sequentially (Versions in parallel)")
    print("=" * 70)

    validated_packages = {}
    validation_report = {
        "total_packages": len(fetched_packages),
        "validated_packages": 0,
        "total_candidate_versions": 0,
        "total_compatible_versions": 0,
        "python_version": python_version,
        "packages": {},
        "total_pypi_versions": 0,
        "total_installable_versions": 0,
        "total_script_passed_versions": 0,
        "requirements_version_failures": [] 
    }

    num_processes = min(max_workers, multiprocessing.cpu_count())
    print(f"🖥️ Using {num_processes} parallel processes for version testing.")

    for idx, (package_name, candidate_versions) in enumerate(fetched_packages.items(), 1):
        print(f"\n[{idx}/{len(fetched_packages)}] Processing Package: {package_name}")
        validation_report["total_candidate_versions"] += len(candidate_versions)

        normalized_name = package_name.lower().replace('_', '-')
        requirements_version = None
        if normalized_name in original_versions:
            _, requirements_version = original_versions[normalized_name]
            print(f"   📋 Requirements version: {requirements_version}")

        api_logs = api_by_package.get(package_name, [])
        compatible_versions = []

        if not api_logs:
            print(f"   ⚠️ No API logs found. Validating installability only.")

            # Convert PyPI package name to Python import name
            import_name = pypi_to_import_name(package_name)
            print(f"   📦 PyPI package: {package_name} → Python import: {import_name}")

            minimal_test_script = f"""#!/usr/bin/env python3
import sys
try:
    import {import_name}
    print("SUCCESS")
    sys.exit(0)
except ImportError:
    print("SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {{e}}")
    sys.exit(1)
"""
            process_args = [
                (package_name, v, minimal_test_script, python_version, timeout, requirements_file)
                for v in candidate_versions
            ]

            print(f"   🚀 Testing {len(candidate_versions)} versions in parallel...")
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.map(_mp_worker_test_version, process_args)

            incompatible_count = 0
            installable_count = 0

            for i, (version, is_compatible, error_msg) in enumerate(results, 1):
                if is_compatible:
                    compatible_versions.append(version)
                    installable_count += 1
                else:
                    incompatible_count += 1

            if not compatible_versions and requirements_version:
                print(f"   ⚠️ All install tests failed, keeping requirements version: {requirements_version}")
                compatible_versions = [requirements_version]
            elif not compatible_versions:
                print(f"   ⚠️ All install tests failed, keeping all candidate versions as fallback")
                compatible_versions = candidate_versions
            else:
                print(f"   ✅ Found {len(compatible_versions)} installable versions")

            validated_packages[package_name] = compatible_versions
            validation_report["total_compatible_versions"] += len(compatible_versions)
            validation_report["total_pypi_versions"] += len(candidate_versions)
            validation_report["total_script_passed_versions"] += len(compatible_versions)

            validation_report["packages"][package_name] = {
                "candidate_versions": len(candidate_versions),
                "compatible_versions": len(compatible_versions),
                "filtered_count": incompatible_count,
                "status": "no_api_calls_installability_tested",
                "retry_count": 0,
                "pypi_versions": len(candidate_versions),
                "installable_versions": installable_count,
                "script_passed_versions": len(compatible_versions)
            }

        else:
            print(f"   📝 Found {len(api_logs)} API logs. Generating LLM test scripts...")
            
            retry_count = 0
            error_reason = None
            best_results = []

            for attempt in range(max_retries):
                retry_count = attempt
                print(f"   🔄 Attempt {attempt + 1}/{max_retries}: Generating script & Testing versions...")

                test_script_content = generate_test_script_with_llm(package_name, api_logs)

                process_args = [
                    (package_name, v, test_script_content, python_version, timeout, requirements_file)
                    for v in candidate_versions
                ]

                with multiprocessing.Pool(processes=num_processes) as pool:
                    results = pool.map(_mp_worker_test_version, process_args)

                temp_compatible = []
                temp_req_error = None
                for v, is_compat, err in results:
                    if is_compat:
                        temp_compatible.append(v)
                    else:
                        if v == requirements_version:
                            temp_req_error = err

                best_results = results

                if temp_compatible:
                    compatible_versions = temp_compatible
                    print(f"   ✅ Attempt {attempt + 1} succeeded: Found {len(compatible_versions)} valid versions")
                    break
                else:
                    print(f"   ❌ Attempt {attempt + 1} failed: No valid versions found.")
                    if temp_req_error:
                        error_reason = temp_req_error

            incompatible_count = 0
            installable_count = 0

            for v, is_compat, err in best_results:
                if is_compat:
                    installable_count += 1
                else:
                    incompatible_count += 1
                    # 尝试区分 "安装失败" 和 "安装成功但脚本报错"
                    if err and not ("No matching distribution" in err or "Could not find a version" in err):
                        installable_count += 1

            if compatible_versions:
                validated_packages[package_name] = compatible_versions
                validation_report["validated_packages"] += 1
                validation_report["total_compatible_versions"] += len(compatible_versions)
                validation_report["total_pypi_versions"] += len(candidate_versions)
                validation_report["total_script_passed_versions"] += len(compatible_versions)

                validation_report["packages"][package_name] = {
                    "candidate_versions": len(candidate_versions),
                    "compatible_versions": len(compatible_versions),
                    "filtered_count": incompatible_count,
                    "status": "validated_success",
                    "retry_count": retry_count + 1,
                    "error_reason": None,
                    "pypi_versions": len(candidate_versions),
                    "installable_versions": installable_count,
                    "script_passed_versions": len(compatible_versions)
                }
            else:
                print(f"   ⚠️ Validation failed after {max_retries} attempts.")
                if requirements_version:
                    print(f"   📌 Keeping only requirements version: {requirements_version}")
                    validated_packages[package_name] = [requirements_version]
                    validation_report["total_compatible_versions"] += 1
                    validation_report["total_pypi_versions"] += len(candidate_versions)

                    if error_reason:
                        validation_report["requirements_version_failures"].append(
                            (package_name, requirements_version, error_reason)
                        )

                    validation_report["packages"][package_name] = {
                        "candidate_versions": len(candidate_versions),
                        "compatible_versions": 1,
                        "filtered_count": len(candidate_versions) - 1,
                        "status": "validation_failed_kept_requirements_version_only",
                        "retry_count": max_retries,
                        "error_reason": "all_retries_failed_keeping_requirements_txt_version_only",
                        "pypi_versions": len(candidate_versions),
                        "installable_versions": installable_count,
                        "script_passed_versions": 0
                    }
                else:
                    print(f"   📌 Keeping all {len(candidate_versions)} versions as fallback")
                    validated_packages[package_name] = candidate_versions
                    validation_report["total_compatible_versions"] += len(candidate_versions)
                    validation_report["total_pypi_versions"] += len(candidate_versions)

                    validation_report["packages"][package_name] = {
                        "candidate_versions": len(candidate_versions),
                        "compatible_versions": len(candidate_versions),
                        "filtered_count": 0,
                        "status": "validation_failed_no_requirements_version_kept_all",
                        "retry_count": max_retries,
                        "error_reason": "no_requirements_version_available_keeping_all_pypi_versions",
                        "pypi_versions": len(candidate_versions),
                        "installable_versions": installable_count,
                        "script_passed_versions": 0
                    }

    output_data = {
        "validated_packages": validated_packages,
        "total_packages": len(validated_packages),
        "validated_at": datetime.datetime.now().isoformat(),
        "validation_report": validation_report
    }

    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Python version: {python_version}")
    print(f"Total packages processed: {validation_report['total_packages']}")
    print(f"Successfully validated (API logic): {validation_report['validated_packages']}")
    print(f"Candidate versions (before): {validation_report['total_candidate_versions']}")
    print(f"Compatible versions (after): {validation_report['total_compatible_versions']}")
    filtered = validation_report['total_candidate_versions'] - validation_report['total_compatible_versions']
    if validation_report['total_candidate_versions'] > 0:
        print(f"Filtered out: {filtered} ({100*filtered/validation_report['total_candidate_versions']:.1f}%)")
    print("=" * 70)

    return output_data


def main():
    """Main entry point."""

    if len(sys.argv) < 3:
        print("Usage: python script_based_validator.py <api_calls.json> <resolved_versions.json> [python_version] [max_workers] [timeout] [requirements.txt]")
        print("\nExample:")
        print("  python script_based_validator.py .venv/.api_calls.json resolved_versions.json 3.11 auto 30 requirements.txt")
        print("\nNote: Use 'auto' for max_workers to use min(32, cpu_count())")
        sys.exit(1)

    api_calls_file = sys.argv[1]
    resolved_versions_file = sys.argv[2]
    python_version = sys.argv[3] if len(sys.argv) > 3 else "3.11"

    # Handle max_workers: support 'auto' or specific number
    max_workers_arg = sys.argv[4] if len(sys.argv) > 4 else "auto"
    if max_workers_arg.lower() == "auto":
        cpu_count = multiprocessing.cpu_count()
        max_workers = min(32, cpu_count)
        print(f"🖥️  Auto-detected {max_workers} workers (CPU count: {cpu_count})")
    else:
        max_workers = int(max_workers_arg)

    timeout = int(sys.argv[5]) if len(sys.argv) > 5 else 30
    requirements_file = sys.argv[6] if len(sys.argv) > 6 else None

    if not os.path.exists(api_calls_file):
        print(f"❌ Error: {api_calls_file} not found")
        sys.exit(1)

    if not os.path.exists(resolved_versions_file):
        print(f"❌ Error: {resolved_versions_file} not found")
        sys.exit(1)

    # Call the function and get the result
    result = validate_all_packages_with_scripts(
        api_calls_file,
        resolved_versions_file,
        python_version,
        max_workers,
        timeout,
        requirements_file
    )

    print("\n✅ Validation completed. Result returned in-memory (not saved to file).")


if __name__ == "__main__":
    main()
