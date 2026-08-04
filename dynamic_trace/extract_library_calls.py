"""
Library Call Extractor
Extracts all library API calls from a script and organizes them by library.
Saves unique API calls for each library in separate Python scripts under api_log directory.

IMPORTANT NAMING CONVENTIONS:
============================

This module distinguishes between two types of package names:

1. import_name (Python module name):
   - Used in Python import statements: `import OpenSSL`, `from PIL import Image`
   - CASE-SENSITIVE: OpenSSL != openssl, PIL != pil
   - Used for: AST parsing, importlib.import_module, sys.settrace
   - Examples: 'OpenSSL', 'PIL', 'cv2', 'sklearn'
   - PRESERVED AS-IS: Never use .lower() or convert - to _

2. pypi_name (PyPI package name):
   - Used for pip install and PyPI API queries
   - Examples: 'pyOpenSSL', 'Pillow', 'opencv-python', 'scikit-learn'
   - Mapped via pypi_import_mapping.json: {pypi_name: import_name}

The pypi_import_mapping.json bridges these two naming conventions.
Example mapping:
{
  "pyOpenSSL": "OpenSSL",
  "Pillow": "PIL",
  "opencv-python": "cv2",
  "scikit-learn": "sklearn"
}
"""

import ast
import os
import sys
import re
import importlib
import importlib.util
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


class LibraryCallExtractor:
    """Extracts and organizes library API calls from user scripts"""

    def __init__(self, script_path: str, api_log_dir: str):
        self.script_path = Path(script_path)
        self.api_log_dir = Path(api_log_dir)

        # Create api_log directory
        self.api_log_dir.mkdir(exist_ok=True, parents=True)

        # Store target packages that are third-party and installable
        self.target_packages = set()

        # Store API calls by library
        # Structure: {library_name: {api_call: [(args, kwargs), ...]}}
        self.library_calls = defaultdict(lambda: defaultdict(list))

        # Load PyPI import mapping from JSON file
        self.module_to_package = self._load_pypi_import_mapping()

    def _load_pypi_import_mapping(self) -> Dict[str, str]:
        """
        Load PyPI import mapping from JSON file.
        Returns a dict mapping {import_name: pypi_package_name}.

        The JSON file format is {pypi_package_name: import_name},
        which will be reversed to {import_name: pypi_package_name}.

        Note: import_name is case-sensitive (e.g., 'OpenSSL' != 'openssl'),
        while pypi_package_name is used for pip install and PyPI queries.
        """
        # Look for the mapping file in the same directory as this script
        script_dir = Path(__file__).parent
        mapping_file = script_dir / "pypi_import_mapping.json"

        if not mapping_file.exists():
            print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")
            print("   Using empty mapping. Some packages may not be correctly identified.")
            return {}

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                original_mapping = json.load(f)

            # Reverse the mapping: {import_name: pypi_package_name}
            reversed_mapping = {}
            for pypi_name, import_name in original_mapping.items():
                reversed_mapping[import_name] = pypi_name

            print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file.name}")
            return reversed_mapping
        except Exception as e:
            print(f"⚠️ Failed to load mapping file {mapping_file}: {e}")
            print("   Using empty mapping. Some packages may not be correctly identified.")
            return {}

    def _is_installable_package(self, package_name: str) -> bool:
        """
        Check if a package can be installed via pip install.

        Args:
            package_name: The import name (case-sensitive, e.g., 'OpenSSL')

        Returns:
            True if package is installable via pip
        """
        if not package_name:
            return False

        # Convert import_name to PyPI package name if mapping exists
        # Note: package_name is the import_name, not the PyPI name
        pip_package_name = self.module_to_package.get(package_name, package_name)

        try:
            # Use pip install --dry-run to check if package is installable
            result = subprocess.run(
                ['pip', 'install', '--dry-run', '--no-deps', pip_package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            # If return code is 0, package is installable
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Warning: Could not check if '{pip_package_name}' is installable: {e}")
            return False

    def _is_local_import(self, module_name: str, script_dir: Path) -> bool:
        """Check if an import points to a local directory/file"""
        if not module_name:
            return False

        # Get the top-level module name
        top_level = module_name.split('.')[0]

        # Check if a corresponding .py file or directory exists in the script directory
        py_file = script_dir / f"{top_level}.py"
        py_dir = script_dir / top_level

        if py_file.exists() or (py_dir.exists() and py_dir.is_dir()):
            return True

        return False

    def _extract_script_content(self, script_path: Path) -> List[Tuple[str, str]]:
        """Extract Python code from script (handles both .py and .sh with heredoc)"""
        if script_path.suffix == '.sh':
            with open(script_path, 'r') as f:
                content = f.read()

            python_blocks = []
            heredoc_pattern = r"cat\s+>\s+(\S+\.py)\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\2"
            for match in re.finditer(heredoc_pattern, content, re.DOTALL):
                filename, delimiter, code = match.groups()
                python_blocks.append((filename, code))
            return python_blocks
        else:
            with open(script_path, 'r') as f:
                return [(str(script_path.name), f.read())]

    def _parse_ast(self, code: str, filename: str) -> Optional[ast.AST]:
        """Parse Python code into AST"""
        try:
            return ast.parse(code, filename=filename)
        except SyntaxError as e:
            print(f"Warning: Syntax error in {filename}: {e}")
            return None

    def _extract_imports(self, tree: ast.AST) -> Dict[str, str]:
        """Extract import statements and build import mapping"""
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if alias.name == '*':
                        imports['*'] = module
                    else:
                        name = alias.asname if alias.asname else alias.name
                        imports[name] = f"{module}.{alias.name}" if module else alias.name
        return imports

    def _collect_all_imports(self, python_blocks: List[Tuple[str, str]]) -> Set[str]:
        """Collect all unique package names from imports across all Python blocks"""
        all_packages = set()
        script_dir = self.script_path.parent if self.script_path.is_file() else self.script_path

        for filename, code in python_blocks:
            tree = self._parse_ast(code, filename)
            if not tree:
                continue

            for node in ast.walk(tree):
                package_name = None

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Get the top-level package name
                        package_name = alias.name.split('.')[0]
                        if package_name and not self._is_local_import(package_name, script_dir):
                            all_packages.add(package_name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Get the top-level package name
                        package_name = node.module.split('.')[0]
                        if package_name and not self._is_local_import(package_name, script_dir):
                            all_packages.add(package_name)

        return all_packages

    def _filter_installable_packages(self, packages: Set[str]) -> Set[str]:
        """
        Filter packages to only those that are installable via pip install.

        Args:
            packages: Set of import names (case-sensitive, e.g., {'OpenSSL', 'numpy'})

        Returns:
            Set of installable import names (preserving original case)
        """
        installable = set()
        print(f"\nChecking {len(packages)} packages for installability...")

        for package in sorted(packages):
            # Skip standard library modules
            if self._is_stdlib_module(package):
                print(f"  [SKIP] {package} (standard library)")
                continue

            # Get the actual PyPI package name
            pip_package = self.module_to_package.get(package, package)
            check_msg = f"{package}" if package == pip_package else f"{package} (as {pip_package})"

            # Check if installable
            print(f"  Checking {check_msg}...", end=' ')
            if self._is_installable_package(package):
                # IMPORTANT: Preserve the original case of import_name
                # Do NOT use .lower() as Python imports are case-sensitive
                installable.add(package)
                print("✓ installable")
            else:
                print("✗ not installable")

        return installable

    def _extract_arg_value(self, arg_node: ast.AST) -> Dict[str, any]:
        """Extract argument value with type information"""
        try:
            if isinstance(arg_node, ast.Constant):
                return {'type': 'literal', 'value': arg_node.value}
            elif isinstance(arg_node, ast.Num):
                return {'type': 'literal', 'value': arg_node.n}
            elif isinstance(arg_node, ast.Str):
                return {'type': 'literal', 'value': arg_node.s}
            elif isinstance(arg_node, ast.NameConstant):
                return {'type': 'literal', 'value': arg_node.value}
            elif isinstance(arg_node, ast.Name):
                return {'type': 'variable', 'value': arg_node.id}
            elif isinstance(arg_node, ast.Attribute):
                expr = ast.unparse(arg_node) if hasattr(ast, 'unparse') else self._unparse_attribute(arg_node)
                return {'type': 'expression', 'value': expr}
            elif isinstance(arg_node, ast.List):
                elements = [self._extract_arg_value(e) for e in arg_node.elts]
                return {'type': 'expression', 'value': elements, 'repr': 'list'}
            elif isinstance(arg_node, ast.Tuple):
                elements = [self._extract_arg_value(e) for e in arg_node.elts]
                return {'type': 'expression', 'value': elements, 'repr': 'tuple'}
            elif isinstance(arg_node, ast.Dict):
                items = {}
                for k, v in zip(arg_node.keys, arg_node.values):
                    if k:
                        key = self._extract_arg_value(k)
                        val = self._extract_arg_value(v)
                        if key.get('type') == 'literal':
                            items[key['value']] = val
                        else:
                            items[str(key.get('value', '<expr>'))] = val
                return {'type': 'expression', 'value': items, 'repr': 'dict'}
            elif isinstance(arg_node, ast.Call):
                func_name = self._extract_arg_value(arg_node.func)
                func_str = func_name.get('value', '<func>')
                return {'type': 'expression', 'value': f"{func_str}(...)"}
            else:
                expr = ast.unparse(arg_node) if hasattr(ast, 'unparse') else "<expr>"
                return {'type': 'expression', 'value': expr}
        except Exception:
            return {'type': 'expression', 'value': '<expr>'}

    def _unparse_attribute(self, node: ast.Attribute) -> str:
        """Manually unparse an attribute node"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.insert(0, current.id)
        return '.'.join(parts)

    def _is_target_package(self, module_name: str) -> bool:
        """
        Check if a module belongs to one of the target packages.

        Args:
            module_name: Full module path (e.g., 'OpenSSL.crypto')

        Returns:
            True if the top-level package is in target_packages

        Note: Performs case-insensitive comparison because self.target_packages
        may contain normalized names for lookup, but the original case is
        preserved in the storage.
        """
        if not module_name:
            return False

        # Extract top-level package name (preserve case for now)
        top_level = module_name.split('.')[0]

        # Compare case-insensitively for membership check
        # This allows matching 'OpenSSL' against stored 'OpenSSL'
        for target_pkg in self.target_packages:
            if target_pkg.lower() == top_level.lower():
                return True
        return False

    def _is_builtin(self, name: str) -> bool:
        """Check if a name is a Python builtin"""
        import builtins
        return hasattr(builtins, name)

    import sys

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of Python standard library"""
        # Extract top-level module name (e.g., convert 'os.path' to 'os')
        top_level_name = module_name.split('.')[0]
        return top_level_name in sys.stdlib_module_names

    def _get_package_from_module(self, module_name: str) -> Optional[str]:
        """
        Extract the package name from a module name if it's a target package.

        Args:
            module_name: Full module path (e.g., 'OpenSSL.crypto')

        Returns:
            The top-level import_name (preserving original case) if it's a target,
            otherwise None

        Note: Returns the original case-sensitive import name, not lowercased.
        """
        if not module_name:
            return None

        # Extract top-level package (preserve original case)
        top_level = module_name.split('.')[0]

        if self._is_target_package(module_name):
            # Return the matching package name from target_packages with original case
            for target_pkg in self.target_packages:
                if target_pkg.lower() == top_level.lower():
                    return target_pkg
        return None

    def _extract_function_calls(self, tree: ast.AST, imports: Dict[str, str],
                              source_file: str) -> List[Tuple[str, str, int, List, Dict]]:
        """Extract all function calls from AST with arguments"""
        calls = []

        class CallVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_Call(self, node):
                # Extract positional arguments
                args = []
                for arg in node.args:
                    args.append(self.analyzer._extract_arg_value(arg))

                # Extract keyword arguments
                kwargs = {}
                for keyword in node.keywords:
                    key = keyword.arg if keyword.arg else "**"
                    kwargs[key] = self.analyzer._extract_arg_value(keyword.value)

                # Extract function name
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in imports:
                        full_name = imports[func_name]
                    else:
                        full_name = func_name
                    calls.append((source_file, full_name, node.lineno, args, kwargs))

                elif isinstance(node.func, ast.Attribute):
                    full_name = self._resolve_call_path(node.func, imports)
                    if full_name:
                        calls.append((source_file, full_name, node.lineno, args, kwargs))

                self.generic_visit(node)

            def _resolve_call_path(self, node: ast.Attribute, imports: Dict) -> Optional[str]:
                parts = []
                current = node

                while isinstance(current, ast.Attribute):
                    parts.insert(0, current.attr)
                    current = current.value

                if isinstance(current, ast.Name):
                    base_name = current.id
                    if base_name in imports:
                        parts.insert(0, imports[base_name])
                    else:
                        parts.insert(0, base_name)
                    return '.'.join(parts)
                return None

        visitor = CallVisitor(self)
        visitor.visit(tree)
        return calls

    def _format_arg_for_code(self, arg_data: Dict) -> str:
        """Format an argument for Python code generation"""
        if not isinstance(arg_data, dict):
            return repr(arg_data)

        arg_type = arg_data.get('type', 'expression')
        value = arg_data.get('value')

        if arg_type == 'literal':
            return repr(value)
        elif arg_type == 'variable':
            return str(value)
        elif arg_type == 'expression':
            if isinstance(value, str):
                return value
            else:
                return repr(value)
        else:
            return repr(value)

    def extract_calls(self):
        """Main extraction function"""
        print(f"\n{'='*60}")
        print(f"Extracting Library Calls from: {self.script_path}")
        print(f"{'='*60}\n")

        # Extract and analyze user code
        python_blocks = self._extract_script_content(self.script_path)

        # Step 1: Collect all imports and determine target packages
        print("Step 1: Collecting all imports from code...")
        all_imports = self._collect_all_imports(python_blocks)
        print(f"Found {len(all_imports)} unique imported packages")

        # Step 2: Filter to only installable packages
        print("\nStep 2: Filtering installable packages...")
        self.target_packages = self._filter_installable_packages(all_imports)
        print(f"\nTarget packages ({len(self.target_packages)}): {sorted(self.target_packages)}")

        if not self.target_packages:
            print("\nNo installable third-party packages found!")
            return

        # Step 3: Extract API calls for target packages
        print(f"\nStep 3: Extracting API calls for target packages...")
        for filename, code in python_blocks:
            print(f"Analyzing: {filename}")

            tree = self._parse_ast(code, filename)
            if not tree:
                continue

            imports = self._extract_imports(tree)
            calls = self._extract_function_calls(tree, imports, filename)

            # Categorize calls by library (only target packages)
            for source_file, callee, lineno, args, kwargs in calls:
                package = self._get_package_from_module(callee)
                if package:
                    # Store the call with its arguments
                    call_signature = (
                        callee,
                        tuple((self._format_arg_for_code(arg) for arg in args)),
                        tuple(sorted((k, self._format_arg_for_code(v)) for k, v in kwargs.items()))
                    )
                    self.library_calls[package][callee].append({
                        'args': args,
                        'kwargs': kwargs,
                        'line': lineno,
                        'file': source_file
                    })

        # Print summary
        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\nExtracted {total_calls} library calls from {len(self.library_calls)} libraries")

    def save_api_logs(self):
        """Save API calls for each library to separate Python scripts with deduplication"""
        print(f"\n{'='*60}")
        print("Saving API Logs")
        print(f"{'='*60}\n")

        for library, api_calls in self.library_calls.items():
            # Create a set to track unique API calls
            unique_apis = set()
            api_call_records = []

            for api_name, call_list in sorted(api_calls.items()):
                for call_info in call_list:
                    # Create a unique signature for deduplication
                    args_tuple = tuple(self._format_arg_for_code(arg) for arg in call_info['args'])
                    kwargs_tuple = tuple(sorted((k, self._format_arg_for_code(v))
                                               for k, v in call_info['kwargs'].items()))
                    signature = (api_name, args_tuple, kwargs_tuple)

                    # Only add if not already seen
                    if signature not in unique_apis:
                        unique_apis.add(signature)
                        api_call_records.append({
                            'api': api_name,
                            'args': call_info['args'],
                            'kwargs': call_info['kwargs'],
                            'source_file': call_info['file'],
                            'line': call_info['line']
                        })

            # Generate Python script for this library
            output_file = self.api_log_dir / f"{library}_apis.py"
            self._write_api_log_script(output_file, library, api_call_records)
            print(f"Generated: {output_file} ({len(unique_apis)} unique API calls)")

    def _write_api_log_script(self, output_file: Path, library: str,
                             api_call_records: List[Dict]):
        """Write API calls to a Python script file"""
        with open(output_file, 'w') as f:
            # Write header comments
            f.write(f'# API calls in library: None\n')
            f.write(f'# Discovered from: {self.script_path.name}\n')
            f.write(f'# Target package: None\n')
            f.write(f'# Total unique API calls: {len(api_call_records)}\n')
            f.write(f'\n')

            # Write each API call with its metadata
            for api_id, record in enumerate(api_call_records, 1):
                api_name = record['api']

                # Format arguments
                args_str_list = []
                for arg in record['args']:
                    args_str_list.append(self._format_arg_for_code(arg))

                kwargs_str_list = []
                for k, v in record['kwargs'].items():
                    kwargs_str_list.append(f"{k}={self._format_arg_for_code(v)}")

                all_args = ', '.join(args_str_list + kwargs_str_list)

                # Write API metadata in the required format
                f.write(f'# API ID: {api_id}\n')
                f.write(f'# Found in versions: None\n')
                f.write(f'# Type: call\n')
                f.write(f'# API: {api_name}\n')
                f.write(f'# Call chain: None\n')

                # Write the actual API call
                f.write(f'{api_name}({all_args})\n')
                f.write(f'\n')


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_library_calls.py <script_path> <api_log_dir>")
        print()
        print("Arguments:")
        print("  script_path - Path to the script to analyze (can be .py or .sh)")
        print("  api_log_dir - Directory to save API logs")
        print()
        print("Description:")
        print("  This tool extracts third-party library API calls from your script.")
        print("  It automatically detects third-party packages (those not in Python stdlib")
        print("  and not installed in the current environment).")
        sys.exit(1)

    script_path = sys.argv[1]
    api_log_dir = sys.argv[2]

    extractor = LibraryCallExtractor(script_path, api_log_dir)
    extractor.extract_calls()
    extractor.save_api_logs()

    print(f"\n{'='*60}")
    print("Library Call Extraction Complete!")
    print(f"API logs saved to: {api_log_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()