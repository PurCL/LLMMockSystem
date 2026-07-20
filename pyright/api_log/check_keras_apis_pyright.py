#!/usr/bin/env python3
"""
Pyright-based API Signature Check Script for package: keras
Uses Pyright static type checker to verify API signatures
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import importlib.util


def check_pyright_available() -> bool:
    """Check if pyright is available in the system"""
    try:
        result = subprocess.run(
            ['pyright', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def normalize_value(val: Any) -> Any:
    """
    Normalize parameter values from call_graph.json to proper Python types

    Handles:
    1. String representations of booleans ("True", "False") -> bool
    2. String values with redundant quotes ("'value'" -> "value")
    3. Dict format from call_graph (with 'type' and 'value' keys)
    4. Other type conversions

    Args:
        val: Raw value from call_graph.json

    Returns:
        Normalized value with proper type
    """
    # If it's already a dict with 'type' and 'value' keys (from call_graph),
    # return it as-is for format_value_for_code to handle
    if isinstance(val, dict) and 'type' in val:
        return val

    if isinstance(val, str):
        # Check for string representation of booleans
        if val == "True":
            return True
        elif val == "False":
            return False
        elif val == "None":
            return None

        # Remove redundant quotes from string values
        # e.g., "'malicious_model.keras'" -> "malicious_model.keras"
        if len(val) >= 2:
            # Check if wrapped in single quotes
            if val.startswith("'") and val.endswith("'"):
                return val[1:-1]
            # Check if wrapped in double quotes
            elif val.startswith('"') and val.endswith('"'):
                return val[1:-1]

    return val


def format_value_for_code(val: Any) -> str:
    """
    Format a normalized value as Python code string

    Args:
        val: Normalized value (can be dict with 'type' and 'value' keys)

    Returns:
        String representation suitable for code generation
    """
    # Handle dict format from _extract_arg_value
    if isinstance(val, dict):
        val_type = val.get('type')
        val_value = val.get('value')
        val_repr = val.get('repr')

        if val_type == 'literal':
            # Literal values
            if isinstance(val_value, bool):
                return str(val_value)
            elif isinstance(val_value, (int, float)):
                return str(val_value)
            elif val_value is None:
                return 'None'
            elif isinstance(val_value, str):
                # Use repr() for proper escaping
                return repr(val_value)
            else:
                return repr(val_value)

        elif val_type == 'variable':
            # Variable references - use None as placeholder
            return 'None'

        elif val_type == 'expression':
            # Expression values
            if val_repr == 'list':
                if isinstance(val_value, list):
                    # Recursively format list elements
                    elements = [format_value_for_code(item) for item in val_value]
                    return '[' + ', '.join(elements) + ']'
                else:
                    return '[]'
            elif val_repr == 'dict':
                if isinstance(val_value, dict):
                    # Recursively format dict items
                    items = [f'{repr(k)}: {format_value_for_code(v)}' for k, v in val_value.items()]
                    return '{' + ', '.join(items) + '}'
                else:
                    return '{}'
            elif val_repr == 'tuple':
                if isinstance(val_value, list):
                    elements = [format_value_for_code(item) for item in val_value]
                    return '(' + ', '.join(elements) + ')'
                else:
                    return '()'
            elif isinstance(val_value, str):
                # String expression like "tf.int32" or "tf.constant(...)"
                # Use None as placeholder
                return 'None'
            else:
                return 'None'
        else:
            return 'None'

    # Handle direct values (fallback)
    if isinstance(val, bool):
        return str(val)
    elif isinstance(val, (int, float)):
        return str(val)
    elif val is None:
        return 'None'
    elif isinstance(val, str):
        return repr(val)
    elif isinstance(val, list):
        elements = [format_value_for_code(item) for item in val]
        return '[' + ', '.join(elements) + ']'
    elif isinstance(val, dict):
        items = [f'{repr(k)}: {format_value_for_code(v)}' for k, v in val.items()]
        return '{' + ', '.join(items) + '}'
    else:
        return 'None'


def probe_import_path(api_path: str) -> Optional[str]:
    """
    Probe for the actual import path that works with Pyright.

    For packages with non-standard structures (e.g., Keras 3.3.0), this function
    tries to find a working import path by checking for actual module files.

    Args:
        api_path: Full API path like "keras.layers.Input"

    Returns:
        Modified API path that should work with static analysis, or None if standard path should work
    """
    parts = api_path.split('.')
    if len(parts) < 3:
        return None

    try:
        import importlib.util
        import sys

        package = parts[0]

        # Try to find the package spec
        spec = importlib.util.find_spec(package)
        if not spec or not spec.origin:
            return None

        # Get package location
        from pathlib import Path
        package_path = Path(spec.origin).parent

        # Check if the standard path exists (e.g., keras/layers/)
        standard_submodule_path = package_path / parts[1]

        # Check if .api subpackage path exists (e.g., keras/api/layers/)
        api_submodule_path = package_path / "api" / parts[1]

        # If standard path doesn't exist but .api path does, use .api path
        if not standard_submodule_path.exists() and api_submodule_path.exists():
            # Reconstruct path with .api inserted
            return f"{parts[0]}.api.{'.'.join(parts[1:])}"

    except Exception:
        # If probing fails, return None to use standard path
        pass

    return None


def generate_test_code(api_path: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    """
    Generate Python test code for Pyright to analyze

    This function generates simple import code. The api_path may already be
    adjusted by probe_import_path() called in check_api_with_pyright().

    Args:
        api_path: Full API path like "keras.layers.Input" or "keras.api.layers.Input"
        args: List of positional arguments
        kwargs: Dict of keyword arguments

    Returns:
        Python code string for testing
    """
    parts = api_path.split('.')
    if not parts:
        return ""

    # Generate arguments string (shared across all strategies)
    arg_parts = []

    # Add positional args with normalization
    for arg in args:
        normalized_arg = normalize_value(arg)
        arg_parts.append(format_value_for_code(normalized_arg))

    # Add keyword args with normalization
    for key, val in kwargs.items():
        normalized_val = normalize_value(val)
        formatted_val = format_value_for_code(normalized_val)
        arg_parts.append(f'{key}={formatted_val}')

    args_str = ', '.join(arg_parts)

    # Generate test code based on path structure
    if len(parts) == 1:
        # Simple import: import package
        code = f"""# Test code for {api_path}
import {parts[0]}

# Test instantiation/call
result = {parts[0]}({args_str})  # type: ignore
"""
    elif len(parts) == 2:
        # Two-part path: from package import module
        code = f"""# Test code for {api_path}
from {parts[0]} import {parts[1]}

# Test instantiation/call
result = {parts[1]}({args_str})  # type: ignore
"""
    else:
        # Multi-part path like keras.layers.Input or keras.api.layers.Input
        call_name = parts[-1]
        import_path = '.'.join(parts[:-1])

        code = f"""# Test code for {api_path}
from {import_path} import {call_name}

# Test instantiation/call
result = {call_name}({args_str})  # type: ignore
"""

    return code


def check_api_with_pyright(
    api_path: str,
    args: List[Any],
    kwargs: Dict[str, Any],
    temp_dir: Path
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Use Pyright to check if an API signature is valid

    Args:
        api_path: API path like "keras.layers.Input"
        args: Positional arguments
        kwargs: Keyword arguments
        temp_dir: Temporary directory for test files

    Returns:
        Tuple of (is_valid, message, diagnostics)
    """
    # Probe for alternative import path (handles non-standard package structures)
    alternative_path = probe_import_path(api_path)
    actual_api_path = alternative_path if alternative_path else api_path

    # Generate test code with the correct API path
    test_code = generate_test_code(actual_api_path, args, kwargs)

    if not test_code:
        return False, "Failed to generate test code", {}

    # Write test code to temporary file (use original path for filename)
    test_file = temp_dir / f"test_{api_path.replace('.', '_')}.py"
    test_file.write_text(test_code)

    # Create pyright config
    config = {
        "include": [str(test_file)],
        "typeCheckingMode": "basic",
        "reportMissingImports": "error",
        "reportUndefinedVariable": "error",
        "reportGeneralTypeIssues": "error",
        "venvPath": str(Path(__file__).parent),  # venv is in same directory as script
        "venv": ".venv"
    }

    config_file = temp_dir / "pyrightconfig.json"
    config_file.write_text(json.dumps(config, indent=2))

    try:
        # Run pyright
        result = subprocess.run(
            ['pyright', '--outputjson', str(test_file)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(temp_dir)
        )

        # Parse output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False, f"Failed to parse Pyright output: {result.stdout}", {}

        # Check diagnostics
        diagnostics = output.get('generalDiagnostics', [])

        if not diagnostics:
            return True, "API signature is valid", output

        # Filter diagnostics to find relevant errors
        errors = []
        warnings = []

        for diag in diagnostics:
            severity = diag.get('severity', 'error')
            message = diag.get('message', '')

            if severity == 'error':
                # Check if it's an import error (API doesn't exist)
                if 'cannot be resolved' in message.lower() or 'cannot import' in message.lower():
                    return False, f"API not found: {message}", output
                # Check if it's a call signature error
                elif 'argument' in message.lower() or 'parameter' in message.lower():
                    errors.append(message)
                else:
                    errors.append(message)
            elif severity == 'warning':
                warnings.append(message)

        if errors:
            return False, f"Type errors: {'; '.join(errors)}", output

        # Only warnings, consider it valid but with notes
        if warnings:
            return True, f"Valid with warnings: {'; '.join(warnings)}", output

        return True, "API signature is valid", output

    except subprocess.TimeoutExpired:
        return False, "Pyright analysis timed out", {}
    except Exception as e:
        return False, f"Error running Pyright: {str(e)}", {}


def main():
    """Main function to check all APIs for keras"""

    print(f"=" * 80)
    print(f"Pyright-based API Signature Check for Package: keras")
    print(f"=" * 80)
    print()

    # Check if pyright is available
    if not check_pyright_available():
        print("❌ ERROR: Pyright is not installed or not in PATH")
        print("   Please install Pyright:")
        print("   - Using npm: npm install -g pyright")
        print("   - Using pip: pip install pyright")
        sys.exit(1)

    print("✓ Pyright is available")

    # Get pyright version
    result = subprocess.run(['pyright', '--version'], capture_output=True, text=True)
    print(f"✓ {result.stdout.strip()}")
    print()

    # Determine output file path (same directory as this script)
    script_dir = Path(__file__).parent

    # List of APIs to check
    api_checks = [
        {
        "api_id": "1",
        "api": "keras.layers.Input",
        "args": [],
        "kwargs": {'shape': [{'type': 'literal', 'value': 10}], 'name': 'input'},
        "caller": "unknown"
    },
        {
        "api_id": "2",
        "api": "keras.layers.TFSMLayer",
        "args": ['savedmodel_path'],
        "kwargs": {'call_endpoint': 'serving_default'},
        "caller": "unknown"
    },
        {
        "api_id": "3",
        "api": "keras.models.Model",
        "args": [],
        "kwargs": {'inputs': 'input_layer', 'outputs': 'output'},
        "caller": "unknown"
    },
        {
        "api_id": "4",
        "api": "keras.models.load_model",
        "args": ['malicious_model.keras'],
        "kwargs": {'safe_mode': True},
        "caller": "unknown"
    },
    ]

    total_apis = len(api_checks)
    successful_checks = 0
    failed_checks = 0
    results = []
    existing_api_ids = []
    failed_api_ids = []

    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        for idx, check in enumerate(api_checks, 1):
            api_id = check['api_id']
            api = check['api']
            args = check['args']
            kwargs = check['kwargs']
            caller = check['caller']

            print(f"[{idx}/{total_apis}] Checking API: {api} (API ID: {api_id})")
            print(f"  Called by: {caller}")
            print(f"  Expected args: {args}")
            print(f"  Expected kwargs: {kwargs}")

            # Check API signature with Pyright
            is_valid, message, diagnostics = check_api_with_pyright(
                api, args, kwargs, temp_dir
            )

            result_entry = {
                'api_id': api_id,
                'api': api,
                'caller': caller,
                'args': args,
                'kwargs': kwargs,
                'valid': is_valid,
                'message': message
            }
            results.append(result_entry)

            if is_valid:
                print(f"  ✓ {message}")
                successful_checks += 1
                # Add API ID to list of existing APIs
                existing_api_ids.append(api_id)
            else:
                print(f"  ❌ FAILED: {message}")
                failed_checks += 1
                # Add API ID to list of failed APIs
                failed_api_ids.append(api_id)

            # Show detailed diagnostics if available
            if diagnostics and diagnostics.get('generalDiagnostics'):
                print(f"  Diagnostics:")
                for diag in diagnostics['generalDiagnostics'][:3]:  # Show first 3
                    severity = diag.get('severity', 'error')
                    msg = diag.get('message', '')
                    line = diag.get('range', {}).get('start', {}).get('line', '?')
                    print(f"    [{severity.upper()}] Line {line}: {msg}")

            print()

    # Prepare JSON output
    json_output = {
        "package": "keras",
        "total_apis": total_apis,
        "successful_checks": successful_checks,
        "failed_checks": failed_checks,
        "success_rate": f"{successful_checks/total_apis*100:.1f}%" if total_apis > 0 else "N/A",
        "passed_api_ids": existing_api_ids,
        "failed_api_ids": failed_api_ids,
        "details": results
    }

    # Write JSON output to file
    json_output_file = script_dir / "api_check_results_keras.json"
    with open(json_output_file, 'w') as f:
        json.dump(json_output, f, indent=2)

    print(f"JSON results saved to: {json_output_file}")


if __name__ == "__main__":
    main()
