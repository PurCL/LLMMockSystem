#!/usr/bin/env python3
"""
Library Dependency Tracer - Improved Version
Traces which third-party library APIs are called by a specific Python script
through a target package's API calls.

Usage:
    python trace_library_dependencies.py <target_script> <package_name> <compatibility_json> [--output_dir <dir>] [--depth_limit <limit>]

Note:
    Each version is processed independently in a loop:
    - For version in versions:
        1. Create fresh virtual environment
        2. Install package==version (without dependencies)
        3. Analyze dependencies
        4. Clean up virtual environment
    - Aggregate results from all versions
"""

import ast
import os
import sys
import re
import subprocess
import importlib.util
import importlib.metadata
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


class LibraryDependencyTracer:
    """Traces library-to-library API calls"""

    def __init__(
        self,
        target_script: str,
        package_name: str,
        version: str,
        output_dir: str = None,
        depth_limit: int = 10
    ):
        self.target_script = Path(target_script)
        self.package_name = package_name.lower().replace('-', '_')
        self.version = version
        self.output_dir = Path(output_dir) if output_dir else self.target_script.parent / f"{package_name}_api_log"
        self.depth_limit = depth_limit

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Get package installation path
        self.package_path = self._find_package_path()

        # Store target packages that are third-party and installable
        self.target_packages = set()

        # Store discovered API calls by library
        # Structure: {library_name: {api_call: [call_info, ...]}}
        self.library_calls = defaultdict(lambda: defaultdict(list))

        # Track what we've analyzed to avoid duplicates
        self.analyzed_apis = set()

        # Track call chains for better reporting
        self.call_chains = defaultdict(list)

        # Store compatibility results for final reporting
        self.all_compatibility_results = {}

    def load_compatible_versions(self, compatibility_json: Path) -> List[str]:
        """Load compatible versions from JSON file (supports both user_code_compatibility and dependency_compatibility)"""
        try:
            with open(compatibility_json, 'r') as f:
                data = json.load(f)

            compatibility_type = data.get('type', '')

            if compatibility_type == 'user_code_compatibility':
                # Extract version strings from the compatible array
                compatible_data = data.get('compatible', [])
                compatible_versions = [item['version'] for item in compatible_data]

                print(f"\nType: user_code_compatibility")
                print(f"Found {len(compatible_versions)} compatible versions")
                if compatible_versions:
                    print(f"Compatible versions: {compatible_versions}")

            elif compatibility_type == 'dependency_compatibility':
                # Extract unique dependency_version values from version_combinations
                version_combinations = data.get('version_combinations', [])
                dependency_versions = [item['dependency_version'] for item in version_combinations]
                # Remove duplicates while preserving order
                compatible_versions = list(dict.fromkeys(dependency_versions))

                print(f"\nType: dependency_compatibility")
                print(f"Found {len(compatible_versions)} unique dependency versions")
                if compatible_versions:
                    print(f"Dependency versions: {compatible_versions}")
            else:
                print(f"⚠️ Unknown compatibility type: {compatibility_type}")
                compatible_versions = []

            # Store for final reporting
            package_name = compatibility_json.stem.replace('_version_compatibility', '')
            self.all_compatibility_results[package_name] = data

            return compatible_versions

        except Exception as e:
            print(f"❌ Error loading compatibility JSON: {e}")
            return []

    def _is_installable_package(self, package_name: str) -> bool:
        """Check if a package can be installed via uv pip install"""
        if not package_name:
            return False

        try:
            # Use uv pip install --dry-run to check if package is installable
            result = subprocess.run(
                ['uv', 'pip', 'install', '--dry-run', package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            # If return code is 0, package is installable
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"  Warning: Could not check if '{package_name}' is installable: {e}")
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

        # Also check if it's the package itself
        if top_level.lower() == self.package_name:
            return True

        # If we have package_path, check if it's in the package directory
        if self.package_path:
            package_dir = self.package_path.parent
            potential_module = package_dir / top_level
            if potential_module.exists() and potential_module.is_dir():
                return True

        return False

    def _find_package_path(self) -> Optional[Path]:
        """Find installation path for the target package"""
        try:
            spec = importlib.util.find_spec(self.package_name)
            if spec and spec.origin:
                pkg_path = Path(spec.origin).parent
                print(f"Found target package '{self.package_name}': {pkg_path}")
                return pkg_path
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            print(f"Error: Could not find package '{self.package_name}': {e}")
        return None

    def _is_builtin(self, name: str) -> bool:
        """Check if a name is a Python builtin"""
        import builtins
        return hasattr(builtins, name)

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of Python standard library"""
        # Check if it's a builtin
        if self._is_builtin(module_name):
            return True

        stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()

        # For Python < 3.10, manually check common stdlib modules
        if not stdlib_modules:
            common_stdlib = {
                'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
                'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
                'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
                'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
                'contextlib', 'contextvars', 'copy', 'copyreg', 'crypt', 'csv', 'ctypes',
                'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
                'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
                'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
                'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip',
                'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp',
                'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
                'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
                'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt',
                'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse',
                'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools',
                'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath',
                'pprint', 'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc',
                'queue', 'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
                'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
                'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
                'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
                'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig',
                'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test',
                'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize',
                'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types',
                'typing', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings',
                'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
                'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib'
            }
            stdlib_modules = common_stdlib

        return module_name.lower() in stdlib_modules

    def _is_third_party_package(self, module_name: str) -> bool:
        """Check if a module is a third-party package by checking if it's in target_packages"""
        if not module_name:
            return False

        top_level = module_name.split('.')[0].lower()

        # Check if it's in our target packages (already validated as installable)
        return top_level in self.target_packages

    def _get_package_from_module(self, module_name: str) -> Optional[str]:
        """Extract the package name from a module name if it's a target package"""
        if not module_name:
            return None
        top_level = module_name.split('.')[0].lower()
        if self._is_third_party_package(module_name):
            return top_level
        return None

    def _parse_ast(self, code: str, filename: str) -> Optional[ast.AST]:
        """Parse Python code into AST"""
        try:
            return ast.parse(code, filename=filename)
        except SyntaxError:
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

    def _collect_all_imports_from_package(self, package_path: Path) -> Set[str]:
        """Collect all unique package names from imports in the target package's source code"""
        all_packages = set()

        if not package_path or not package_path.exists():
            print(f"Warning: Package path does not exist: {package_path}")
            return all_packages

        # If package_path is a file, use its parent directory
        if package_path.is_file():
            package_dir = package_path.parent
        else:
            package_dir = package_path

        # Find all Python files in the package
        python_files = list(package_dir.rglob('*.py'))
        print(f"Scanning {len(python_files)} Python files in package '{self.package_name}'...")

        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
            except Exception as e:
                # print(f"  Warning: Could not read {py_file}: {e}")
                continue

            tree = self._parse_ast(code, str(py_file))
            if not tree:
                continue

            for node in ast.walk(tree):
                package_name = None

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Get the top-level package name
                        package_name = alias.name.split('.')[0]
                        if package_name and not self._is_local_import(package_name, package_dir):
                            all_packages.add(package_name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Get the top-level package name
                        package_name = node.module.split('.')[0]
                        if package_name and not self._is_local_import(package_name, package_dir):
                            all_packages.add(package_name)

        return all_packages

    def _filter_installable_packages(self, packages: Set[str]) -> Set[str]:
        """Filter packages to only those that are installable via uv pip install"""
        installable = set()
        print(f"\nChecking {len(packages)} packages for installability...")

        for package in sorted(packages):
            # Skip standard library modules
            if self._is_stdlib_module(package):
                print(f"  [SKIP] {package} (standard library)")
                continue

            # Skip the target package itself
            if package.lower() == self.package_name:
                print(f"  [SKIP] {package} (target package)")
                continue

            # Check if installable
            print(f"  Checking {package}...", end=' ')
            if self._is_installable_package(package):
                installable.add(package.lower())
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

    def _search_function_in_package(self, package_name: str, function_name: str) -> List[Path]:
        """Search for function definition in package using grep"""
        # For the target package, use the stored path
        if package_name == self.package_name:
            if not self.package_path:
                return []
            base_path = self.package_path
        else:
            # For other packages, try to find them
            try:
                spec = importlib.util.find_spec(package_name)
                if spec and spec.origin:
                    base_path = Path(spec.origin).parent
                else:
                    return []
            except (ImportError, ModuleNotFoundError, AttributeError):
                return []

        if not base_path.is_dir():
            base_path = base_path.parent

        results = []
        try:
            patterns = [
                f"def {function_name}(",
                f"async def {function_name}("
            ]

            for pattern in patterns:
                result = subprocess.run(
                    ['grep', '-r', '-l', pattern, str(base_path), '--include=*.py'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout:
                    for file in result.stdout.strip().split('\n'):
                        if file:
                            results.append(Path(file))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return results

    def _extract_function_body_calls(self, tree: ast.AST, target_function: str,
                                    imports: Dict[str, str]) -> List[Tuple[str, List, Dict]]:
        """Extract all API calls made within a specific function"""
        calls = []

        class FunctionCallExtractor(ast.NodeVisitor):
            def __init__(self, analyzer, target_func, imports):
                self.analyzer = analyzer
                self.target_func = target_func
                self.imports = imports
                self.in_target = False
                self.calls = []

            def visit_FunctionDef(self, node):
                if node.name == self.target_func:
                    self.in_target = True
                    self.generic_visit(node)
                    self.in_target = False
                else:
                    self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

            def visit_Call(self, node):
                if self.in_target:
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in self.imports:
                            func_name = self.imports[func_name]
                    elif isinstance(node.func, ast.Attribute):
                        func_name = self._resolve_call_path(node.func, self.imports)

                    if func_name:
                        args = [self.analyzer._extract_arg_value(arg) for arg in node.args]
                        kwargs = {
                            keyword.arg if keyword.arg else "**":
                            self.analyzer._extract_arg_value(keyword.value)
                            for keyword in node.keywords
                        }
                        self.calls.append((func_name, args, kwargs))

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

        extractor = FunctionCallExtractor(self, target_function, imports)
        extractor.visit(tree)
        return extractor.calls

    def _analyze_api_function(self, api_path: str, depth: int = 0, chain: List[str] = None) -> List[Tuple[str, List, Dict, List[str]]]:
        """
        Analyze a single API function to find what library APIs it calls
        Returns: List of (api_call, args, kwargs, call_chain)
        """
        if chain is None:
            chain = []

        if depth >= self.depth_limit:
            return []

        if api_path in self.analyzed_apis:
            return []
        self.analyzed_apis.add(api_path)

        print(f"  {'  ' * depth}Analyzing: {api_path}")

        current_chain = chain + [api_path]

        # Parse the API path
        parts = api_path.rsplit('.', 1)
        if len(parts) == 2:
            module_name, function_name = parts
        else:
            return []

        # Determine the source package
        # First check if it's from the target package itself
        top_level_module = module_name.split('.')[0].lower()

        if top_level_module == self.package_name:
            # This is from our target package - we should trace into it
            source_package = self.package_name
        else:
            # Check if it's a third-party package
            source_package = self._get_package_from_module(module_name)
            if not source_package:
                # Not a known third-party package, skip it
                return []

        # Search for function definition
        function_files = self._search_function_in_package(source_package, function_name)
        if not function_files:
            print(f"  {'  ' * depth}  Function not found in source")
            return []

        all_calls = []

        # Analyze each file where the function is defined
        for file_path in function_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()

                tree = self._parse_ast(code, str(file_path))
                if not tree:
                    continue

                # Extract imports from the file
                imports = self._extract_imports(tree)

                calls = self._extract_function_body_calls(tree, function_name, imports)

                # Process each call found in the function body
                for callee, args, kwargs in calls:
                    callee_top_level = callee.split('.')[0].lower()

                    # Check if this call is to a third-party package
                    if self._is_third_party_package(callee):
                        callee_package = self._get_package_from_module(callee)
                        if callee_package:
                            # This is a library API call we're interested in - record it
                            all_calls.append((callee, args, kwargs, current_chain))
                            print(f"  {'  ' * depth}  ✓ Found call to third-party package: {callee}")

                    # If it's a call to the target package itself, recursively trace it
                    elif callee_top_level == self.package_name:
                        print(f"  {'  ' * depth}  → Recursing into target package call: {callee}")
                        nested_calls = self._analyze_api_function(callee, depth + 1, current_chain)
                        all_calls.extend(nested_calls)

            except Exception as e:
                print(f"  {'  ' * depth}  Error analyzing {file_path}: {e}")
                continue

        return all_calls

    def trace_dependencies(self):
        """Main tracing function - analyzes the target script"""
        print(f"\n{'='*60}")
        print("Tracing Library Dependencies")
        print(f"{'='*60}\n")

        if not self.target_script.exists():
            print(f"Error: Target script not found: {self.target_script}")
            return

        if not self.package_path:
            print(f"Error: Target package '{self.package_name}' not found in environment")
            return

        print(f"Analyzing script: {self.target_script}")
        print(f"Target package: {self.package_name}")
        print(f"Package path: {self.package_path}\n")

        # Step 1: Collect all imports from the target package's source code
        print("Step 1: Collecting all imports from target package's source code...")
        all_imports = self._collect_all_imports_from_package(self.package_path)
        print(f"Found {len(all_imports)} unique imported packages\n")

        # Step 2: Filter to only installable packages
        print("Step 2: Filtering installable packages...")
        self.target_packages = self._filter_installable_packages(all_imports)
        print(f"\nTarget packages ({len(self.target_packages)}): {sorted(self.target_packages)}\n")

        if not self.target_packages:
            print("No installable third-party packages found!")
            return

        # Read and parse the target script
        try:
            with open(self.target_script, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading script: {e}")
            return

        tree = self._parse_ast(code, str(self.target_script))
        if not tree:
            print("Error: Could not parse the target script")
            return

        # Extract all API calls from the script
        print(f"Step 3: Analyzing API calls from script...")

        # Extract all function calls from the script
        api_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = self._resolve_attribute_path(node.func, {})

                if func_name:
                    api_calls.append(func_name)

        print(f"Found {len(api_calls)} API calls in script\n")

        # Trace each API call
        for api_call in set(api_calls):  # Use set to avoid duplicates
            print(f"\nTracing: {api_call}")
            discovered_calls = self._analyze_api_function(api_call, depth=0, chain=[])

            # Store discovered calls
            for callee, args, kwargs, call_chain in discovered_calls:
                callee_package = self._get_package_from_module(callee)
                if callee_package:
                    self.library_calls[callee_package][callee].append({
                        'args': args,
                        'kwargs': kwargs,
                        'source_api': api_call,
                        'call_chain': call_chain
                    })

        # Print summary
        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\n{'='*60}")
        print(f"Discovered {total_calls} API calls across {len(self.library_calls)} libraries")
        for lib in sorted(self.library_calls.keys()):
            call_count = sum(len(calls) for calls in self.library_calls[lib].values())
            print(f"  - {lib}: {call_count} calls")
        print(f"{'='*60}")

    def _resolve_attribute_path(self, node: ast.Attribute, imports: Dict[str, str]) -> Optional[str]:
        """Resolve an attribute access path to a full module path"""
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

    def save_api_logs(self):
        """Save API logs with newly discovered calls - returns dict of library->api calls for aggregation"""
        print(f"\n{'='*60}")
        print(f"Processing API Logs for version {self.version}")
        print(f"{'='*60}\n")

        if not self.library_calls:
            print("No API calls discovered")
            return {}

        # Return the library calls for aggregation
        result = {}
        for library, api_calls in self.library_calls.items():
            result[library] = []
            for api_name, call_list in api_calls.items():
                for call_info in call_list:
                    # Format the API call
                    args_str_list = [self._format_arg_for_code(arg) for arg in call_info['args']]
                    kwargs_str_list = [f"{k}={self._format_arg_for_code(v)}"
                                     for k, v in call_info['kwargs'].items()]
                    all_args = ', '.join(args_str_list + kwargs_str_list)

                    api_call_str = f"{api_name}({all_args})"

                    result[library].append({
                        'api_call': api_call_str,
                        'api_name': api_name,
                        'source_api': call_info['source_api'],
                        'call_chain': call_info.get('call_chain', []),
                        'args': call_info['args'],
                        'kwargs': call_info['kwargs']
                    })

        return result


def setup_environment_and_trace(target_script: str, package_name: str, version: str,
                                 output_dir: str, depth_limit: int) -> Dict[str, List[Dict]]:
    """Setup environment for a specific version and trace dependencies"""
    print(f"\n{'='*80}")
    print(f"Processing version: {version}")
    print(f"{'='*80}\n")

    # Step 0: Create virtual environment and install package
    print(f"Setting up virtual environment for {package_name}=={version}...")

    # Remove existing venv if it exists
    print("Removing existing .venv directory...")
    subprocess.run(['rm', '-rf', '.venv'], check=False)

    # Create new venv
    print("Creating new virtual environment...")
    result = subprocess.run(['uv', 'venv', '.venv'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error creating virtual environment: {result.stderr}")
        return {}
    print("✓ Virtual environment created")

    # Install package without dependencies
    print(f"Installing {package_name}=={version} (without dependencies)...")
    result = subprocess.run(
        ['uv', 'pip', 'install', '--no-deps', f'{package_name}=={version}'],
        capture_output=True,
        text=True,
        env={**os.environ, 'VIRTUAL_ENV': os.path.join(os.getcwd(), '.venv')}
    )
    if result.returncode != 0:
        print(f"Error installing package: {result.stderr}")
        return {}
    print(f"✓ Package {package_name}=={version} installed")

    # Update Python path to use the venv
    # Clear previous venv paths from sys.path
    sys.path = [p for p in sys.path if '.venv' not in p]
    venv_site_packages = Path('.venv/lib').glob('python*/site-packages')
    for site_packages_path in venv_site_packages:
        sys.path.insert(0, str(site_packages_path))

    print(f"Environment setup complete\n")

    # Trace dependencies
    tracer = LibraryDependencyTracer(target_script, package_name, version, output_dir, depth_limit)
    tracer.trace_dependencies()
    api_logs = tracer.save_api_logs()

    return api_logs


def aggregate_and_save_results(all_version_results: Dict[str, Dict[str, List[Dict]]],
                               output_dir: Path, package_name: str, target_script: str):
    """Aggregate results from all versions and save to files"""
    print(f"\n{'='*80}")
    print("Aggregating results from all versions")
    print(f"{'='*80}\n")

    # Structure to hold aggregated data
    # {library_name: {api_call_str: {'id': int, 'data': dict, 'versions': set}}}
    aggregated_data = defaultdict(dict)

    # Structure to track which API IDs are in each version
    # {library_name: {version: [api_ids]}}
    version_mapping = defaultdict(lambda: defaultdict(list))

    # Process each version's results
    for version, libraries in all_version_results.items():
        print(f"Processing version {version}...")
        for library_name, api_calls in libraries.items():
            if library_name not in aggregated_data:
                aggregated_data[library_name] = {}

            for api_call_data in api_calls:
                api_call_str = api_call_data['api_call']

                # If this API call is new, assign it an ID
                if api_call_str not in aggregated_data[library_name]:
                    api_id = len(aggregated_data[library_name]) + 1
                    aggregated_data[library_name][api_call_str] = {
                        'id': api_id,
                        'data': api_call_data,
                        'versions': set()
                    }

                # Add this version to the API call's version set
                aggregated_data[library_name][api_call_str]['versions'].add(version)

                # Track API ID for this version
                api_id = aggregated_data[library_name][api_call_str]['id']
                if api_id not in version_mapping[library_name][version]:
                    version_mapping[library_name][version].append(api_id)

    # Save aggregated results to files
    print(f"\nSaving aggregated results to {output_dir}...\n")

    for library_name, api_calls_dict in sorted(aggregated_data.items()):
        # Create the apis.py file
        output_file = output_dir / f"{library_name}_apis.py"

        lines = []
        lines.append(f"# API calls in library: {library_name}")
        lines.append(f"# Discovered from: {Path(target_script).name}")
        lines.append(f"# Target package: {package_name}")
        lines.append(f"# Total unique API calls: {len(api_calls_dict)}")
        lines.append("")

        # Sort by API ID
        sorted_apis = sorted(api_calls_dict.items(), key=lambda x: x[1]['id'])

        for api_call_str, api_info in sorted_apis:
            api_id = api_info['id']
            api_data = api_info['data']
            versions = sorted(api_info['versions'])

            lines.append(f"# API ID: {api_id}")
            lines.append(f"# Found in versions: {', '.join(versions)}")
            lines.append(f"# API: {api_data['api_name']}")

            if api_data.get('call_chain'):
                chain_str = " -> ".join(api_data['call_chain'])
                lines.append(f"# Call chain: {api_data['source_api']} -> {chain_str} -> {api_data['api_name']}")
            else:
                lines.append(f"# Called by: {api_data['source_api']}")

            lines.append(f"{api_call_str}")
            lines.append("")

        # Write the apis.py file
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Created: {output_file} ({len(api_calls_dict)} unique API calls)")

        # Create the corresponding JSON file for version mapping
        json_file = output_dir / f"{library_name}_version_mapping.json"

        # Convert version_mapping to serializable format
        version_data = {}
        for version in version_mapping[library_name]:
            version_data[version] = sorted(version_mapping[library_name][version])

        with open(json_file, 'w') as f:
            json.dump(version_data, f, indent=2)

        print(f"Created: {json_file}")

    print(f"\n{'='*80}")
    print("Aggregation complete!")
    print(f"{'='*80}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python trace_library_dependencies.py <target_script> <package_name> <compatibility_json> [--output_dir <dir>] [--depth_limit <limit>]")
        print()
        print("Arguments:")
        print("  target_script         - Path to the Python script to analyze")
        print("  package_name          - Name of the package to trace (e.g., 'requests', 'numpy')")
        print("  compatibility_json    - Path to JSON file containing compatible versions")
        print("                         (e.g., 'keras_version_compatibility.json')")
        print("  --output_dir <dir>    - Optional: Directory to save API logs (default: ./<package_name>_api_log)")
        print("  --depth_limit <limit> - Optional: Maximum tracing depth (default: 10)")
        print()
        print("Description:")
        print("  This tool traces third-party library API calls made by a target package across multiple versions.")
        print("  Versions are loaded from a compatibility JSON file that supports both:")
        print("    - user_code_compatibility: extracts 'version' from 'compatible' array")
        print("    - dependency_compatibility: extracts 'dependency_version' from 'version_combinations'")
        print("  For each version, the script:")
        print("    1. Creates a fresh virtual environment")
        print("    2. Installs package==version (without dependencies)")
        print("    3. Analyzes the dependencies")
        print("    4. Cleans up the virtual environment")
        print("  Finally, it aggregates results from all versions into unified API logs.")
        print()
        print("Example:")
        print("  python3 trace_library_dependencies.py api_log/keras_apis.py keras api_log/keras_version_compatibility.json")
        print("  python3 trace_library_dependencies.py api_log/keras_apis.py keras api_log/keras_version_compatibility.json --output_dir ./output --depth_limit 5")
        sys.exit(1)

    # Parse arguments
    target_script = sys.argv[1]
    package_name = sys.argv[2]
    compatibility_json_path = sys.argv[3]

    # Optional arguments
    output_dir = None
    depth_limit = 10

    i = 4
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--output_dir':
            if i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --output_dir requires a value")
                sys.exit(1)
        elif arg == '--depth_limit':
            if i + 1 < len(sys.argv):
                try:
                    depth_limit = int(sys.argv[i + 1])
                    i += 2
                except ValueError:
                    print("Error: --depth_limit must be an integer")
                    sys.exit(1)
            else:
                print("Error: --depth_limit requires a value")
                sys.exit(1)
        else:
            print(f"Error: Unknown argument '{arg}'")
            sys.exit(1)

    # Load versions from compatibility JSON
    print(f"\n{'='*80}")
    print("Loading Compatible Versions from JSON")
    print(f"{'='*80}")
    print(f"Compatibility JSON: {compatibility_json_path}")

    # Create a temporary tracer instance just to load versions
    temp_tracer = LibraryDependencyTracer(target_script, package_name, "temp", None, depth_limit)
    versions = temp_tracer.load_compatible_versions(Path(compatibility_json_path))

    if not versions:
        print("Error: No compatible versions found in JSON file")
        sys.exit(1)

    # Set default output directory if not provided
    if output_dir is None:
        target_script_dir = Path(target_script).parent
        output_dir = target_script_dir / f"{package_name}_api_log"
    else:
        output_dir = Path(output_dir)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print("Library Dependency Tracer - Multi-Version Analysis")
    print(f"{'='*80}")
    print(f"Target script: {target_script}")
    print(f"Package: {package_name}")
    print(f"Versions: {', '.join(versions)}")
    print(f"Output directory: {output_dir}")
    print(f"Depth limit: {depth_limit}")
    print(f"{'='*80}\n")

    # Process each version
    all_version_results = {}

    for version in versions:
        try:
            # Process this single version
            api_logs = setup_environment_and_trace(
                target_script, package_name, version, str(output_dir), depth_limit
            )
            all_version_results[version] = api_logs
            print(f"\n✓ Version {version} completed successfully")
        except Exception as e:
            print(f"\n✗ Error processing version {version}: {e}")
            import traceback
            traceback.print_exc()
            continue
        finally:
            # Clean up the virtual environment after each version
            print(f"\nCleaning up virtual environment for version {version}...")
            subprocess.run(['rm', '-rf', '.venv'], check=False)
            # Clear sys.path from venv entries
            sys.path = [p for p in sys.path if '.venv' not in p]

    # Final cleanup (just to be safe)
    print(f"\nFinal cleanup...")
    subprocess.run(['rm', '-rf', '.venv'], check=False)

    # Aggregate and save results
    if all_version_results:
        aggregate_and_save_results(all_version_results, output_dir, package_name, target_script)
    else:
        print("\nNo results to aggregate.")

    print(f"\n{'='*80}")
    print("Library Dependency Tracing Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
