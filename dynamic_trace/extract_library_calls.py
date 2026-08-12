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
import time
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

        # Store import records by library
        # Structure: {library_name: [import_record1, import_record2, ...]}
        self.library_imports = defaultdict(list)

        # Load PyPI import mapping from JSON file
        self.module_to_package = self._load_pypi_import_mapping()

    def _setup_venv(self, work_dir: str, venv_name: str = '.venv') -> Tuple[bool, str]:
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

    def _install_package(self, package_name: str, venv_path: str, version: Optional[str] = None) -> Tuple[bool, str]:
        """
        Install a package in venv

        Args:
            package_name: Import name of package
            venv_path: Path to venv
            version: Version number (optional)

        Returns:
            (Success flag, Error message)
        """
        # Convert import_name to PyPI package name if mapping exists
        if package_name in self.module_to_package:
            pypi_pkg_name = self.module_to_package[package_name]
            print(f"  [Mapping] Using PyPI package name '{pypi_pkg_name}' for import name '{package_name}'")
        else:
            pypi_pkg_name = package_name

        pip_path = os.path.join(venv_path, 'bin', 'pip')

        if version:
            package_spec = f"{pypi_pkg_name}=={version}"
        else:
            package_spec = pypi_pkg_name

        pip_install_env = {
            'PATH': f"{os.path.join(venv_path, 'bin')}:{os.environ.get('PATH', '')}",
            'HOME': os.environ.get('HOME', ''),
            'VIRTUAL_ENV': venv_path,
            'PYTHONHOME': '',
            'PYTHONPATH': '',
            'PYTHONUSERBASE': '',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'PIP_CONFIG_FILE': '/dev/null',
            'PIP_REQUIRE_VIRTUALENV': '1',
            'PIP_NO_INPUT': '1',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'PIP_QUIET': '1',
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
        }

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    [pip_path, 'install', package_spec],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=pip_install_env,
                )

                if result.returncode != 0:
                    stderr_lower = result.stderr.lower()

                    permanent_errors = [
                        "resolutionimpossible",
                        "conflict",
                        "no matching distribution",
                        "could not find a version"
                    ]

                    if any(error in stderr_lower for error in permanent_errors):
                        return False, f"Package conflict or not found for {package_spec}:\n{result.stderr}"

                    if attempt == max_retries:
                        return False, f"Failed to install {package_spec} after {max_retries} attempts:\n{result.stderr}"

                    time.sleep(3)
                    continue

                return True, ""

            except subprocess.TimeoutExpired:
                if attempt == max_retries:
                    return False, f"Timeout while installing {package_spec} after {max_retries} attempts"
                time.sleep(3)
                continue

            except Exception as e:
                if attempt == max_retries:
                    return False, f"Error installing package after {max_retries} attempts: {str(e)}"
                time.sleep(3)
                continue

        return False, "Installation failed"

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
        
            # Pattern 1: cat > file.py << EOF
            pattern1 = r"cat\s+>\s+(\S+\.py)\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\2"
            for match in re.finditer(pattern1, content, re.DOTALL):
                filename, delimiter, code = match.groups()
                python_blocks.append((filename, code))
            
            # Pattern 2: python3 << EOF (direct execution)
            pattern2 = r"python3\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\1"
            for match in re.finditer(pattern2, content, re.DOTALL):
                delimiter, code = match.groups()
                python_blocks.append(("inline_python", code))
                
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

    def _extract_imports(self, tree: ast.AST, filename: str) -> Tuple[Dict[str, str], List[Dict]]:
        """
        Extract import statements and build import mapping.

        Returns:
            Tuple of (imports_dict, import_records)
            - imports_dict: mapping for resolving names in code
            - import_records: list of import records for API log generation
        """
        imports = {}
        import_records = []
        script_dir = self.script_path.parent if self.script_path.is_file() else self.script_path

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = alias.name

                    # Record the import if it's a target package
                    mod_name = alias.name
                    if mod_name and not self._is_local_import(mod_name, script_dir):
                        top_level_pkg = mod_name.split('.')[0]
                        import_records.append({
                            "type": "import",
                            "downstream_module": mod_name,
                            "downstream_package": top_level_pkg,
                            "file": filename,
                            "lineno": node.lineno
                        })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if alias.name == '*':
                        imports['*'] = module
                    else:
                        name = alias.asname if alias.asname else alias.name
                        imports[name] = f"{module}.{alias.name}" if module else alias.name

                # Record the from import if it's from an external library
                if module and not self._is_local_import(module, script_dir):
                    names = [alias.name for alias in node.names]
                    top_level_pkg = module.split('.')[0]
                    import_records.append({
                        "type": "from_import",
                        "downstream_module": module,
                        "downstream_package": top_level_pkg,
                        "imported_names": names,
                        "file": filename,
                        "lineno": node.lineno
                    })

        return imports, import_records

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
        return top_level

        # if self._is_target_package(module_name):
        #     # Return the matching package name from target_packages with original case
        #     for target_pkg in self.target_packages:
        #         if target_pkg.lower() == top_level.lower():
        #             return target_pkg
        # return None

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

    def _generate_trace_script(self, script: str) -> str:
        """
        Generate Python script that traces API calls during execution

        Args:
            script: Python code to trace

        Returns:
            Complete tracing script content
        """
        import base64

        # Encode the script to avoid any quote/escape issues
        encoded_script = base64.b64encode(script.encode('utf-8')).decode('ascii')

        trace_script = '''#!/usr/bin/env python3
import sys
import os
import json
import base64
import inspect
from collections import defaultdict

user_file_paths = set()

# Store traced API calls by package
traced_calls = defaultdict(list)

def tracer(frame, event, arg):
    if event != 'call':
        return tracer

    func_name = frame.f_code.co_name
    
    # Filter out module initialization noise
    if func_name == '<module>':
        return tracer

    callee_mod = frame.f_globals.get("__name__", "")
    if not callee_mod or callee_mod.startswith("namedtuple_"):
        return tracer

    # 1. Dynamically get which package the currently executing API belongs to
    current_pkg = callee_mod.split('.')[0]

    if current_pkg in sys.stdlib_module_names:
        return tracer

    caller_frame = frame.f_back
    caller_file = None
    caller_line = None
    caller_mod = "__main__"

    if caller_frame:
        caller_mod = caller_frame.f_globals.get("__name__", caller_mod)        
        caller_file = caller_frame.f_code.co_filename
        caller_line = caller_frame.f_lineno

    if not caller_file:
        return tracer

    # Absolute path whitelist check (fixed self.tracer error)
    if os.path.abspath(caller_file) not in user_file_paths:
        return tracer

    # ==============================================================
    # 3. Extract real API name and record (using ultimate weapon __qualname__)
    # ==============================================================
    is_instance_method = False
    cls_obj = None

    if 'self' in frame.f_locals:
        cls_obj = frame.f_locals['self'].__class__
        is_instance_method = True
    elif 'cls' in frame.f_locals:
        cls_obj = frame.f_locals['cls']
        if not isinstance(cls_obj, type):
            cls_obj = None

    # Core: Get the real function object through reflection and extract __qualname__ with lineage info
    qualname = None
    if cls_obj:
        func_obj = getattr(cls_obj, func_name, None)
    else:
        func_obj = frame.f_globals.get(func_name)

    if func_obj:
        qualname = getattr(func_obj, '__qualname__', None)

    # ==========================================================
    # 🛑 Iron Wall Interception 1: Never let any closure slip through!
    # If it's an internal closure function, discard it immediately - don't let it enter the fallback logic!
    # ==========================================================
    if qualname and '<locals>' in qualname:
        return tracer

    # ==========================================================
    # 🛑 Iron Wall Interception 2: Check the module's global namespace registry!
    # Verify if it really exists in the current module's global variables.
    # This perfectly intercepts hidden internal functions whose qualname was disguised by @wraps.
    # ==========================================================
    if qualname:
        root_obj_name = qualname.split('.')[0]
        if root_obj_name not in frame.f_globals:
            return tracer
    else:
        if func_name not in frame.f_globals:
            return tracer

    # Construct API signature
    if qualname:
        # If it's a method inside a class, qualname will contain '.' (e.g., 'ChatOpenAI.get_num_tokens_from_messages' or 'BaseModel.__init__')
        if is_instance_method and '.' in qualname:
            # Compatible with anonymous instantiation check script: add () before the last dot
            parts = qualname.rsplit('.', 1)
            api_path = f"{callee_mod}.{parts[0]}().{parts[1]}"
        else:
            api_path = f"{callee_mod}.{qualname}"
    else:
        # Fallback: If qualname is not available (rare C extensions or special cases), fall back to regular concatenation
        class_name = cls_obj.__name__ if cls_obj else ""
        if class_name:
            if func_name == '__init__':
                api_path = f"{callee_mod}.{class_name}"
            elif is_instance_method:
                api_path = f"{callee_mod}.{class_name}().{func_name}"
            else:
                api_path = f"{callee_mod}.{class_name}.{func_name}"
        else:
            api_path = f"{callee_mod}.{func_name}"

    # ==============================================================
    # 4. Extract arguments (Smart Default Filtering)
    # ==============================================================
    try:
        # === 4.1 Dynamically get the real function object and extract official signature ===
        # func_name was already obtained via frame.f_code.co_name in previous code
        func_obj = None
        if 'self' in frame.f_locals:
            func_obj = getattr(frame.f_locals['self'].__class__, func_name, None)
        elif 'cls' in frame.f_locals:
            cls_obj = frame.f_locals['cls']
            if isinstance(cls_obj, type):
                func_obj = getattr(cls_obj, func_name, None)
        else:
            func_obj = frame.f_globals.get(func_name)

        sig = None
        if func_obj:
            try:
                sig = inspect.signature(func_obj)
            except Exception:
                pass
        # ================================================

        arg_info = inspect.getargvalues(frame)
        args_dict = {}

        for arg_name in arg_info.args:
            if arg_name in ('self', 'cls'):
                continue

            val = arg_info.locals.get(arg_name)

            # === 4.2 Core magic: Smart default parameter filtering ===
            if sig and arg_name in sig.parameters:
                param = sig.parameters[arg_name]
                # Check if this parameter has a default value
                if param.default is not inspect.Parameter.empty:
                    try:
                        # If current runtime value equals default value, it's likely not explicitly passed by user - discard it!
                        if val == param.default:
                            continue
                    except Exception:
                        # Prevent exceptions from special objects that overrode __eq__ (like Numpy) during comparison
                        pass
            # ======================================

            try:
                args_dict[arg_name] = repr(val)
            except:
                args_dict[arg_name] = "<unrepresentable>"

        if arg_info.varargs:
            val = arg_info.locals.get(arg_info.varargs)
            try:
                args_dict[arg_info.varargs] = repr(val)
            except:
                args_dict[arg_info.varargs] = "<unrepresentable>"

        if arg_info.keywords:
            val = arg_info.locals.get(arg_info.keywords)
            try:
                args_dict[arg_info.keywords] = repr(val)
            except:
                args_dict[arg_info.keywords] = "<unrepresentable>"
                
    except Exception as e:
        args_dict = {"error": f"Failed to extract args: {str(e)}"}

    call_record = {
        "api": api_path,
        "caller": f"{caller_mod}.user_code", 
        "caller_file": caller_file,
        "args": args_dict,
        "line": caller_line
    }

    # Store the traced call in the global traced_calls dictionary
    traced_calls[current_pkg].append(call_record)

    # Return the tracer function for continued tracing
    return tracer

# User code to execute
def main():
    try:
        user_script_path = os.path.abspath("user_script.py")
        global user_file_paths
        user_file_paths.add(user_script_path)

        # Decode the base64-encoded script
        encoded_script = "<<<ENCODED_SCRIPT>>>"
        user_code = base64.b64decode(encoded_script).decode('utf-8')

        sys.settrace(tracer)
        exec(compile(user_code, user_script_path, 'exec'))
    except ModuleNotFoundError as e:
        # Format error output to stderr for outer layer regex to capture precisely
        sys.stderr.write(f"ModuleNotFoundError: No module named '{e.name}'\\n")
        sys.exit(2)
    except Exception as e:
        # Allow the script to continue even if execution fails
        sys.stderr.write(f"Warning: Script execution error: {str(e)}\\n")
    finally:
        sys.settrace(None)
        # Output traced calls as JSON
        for pkg, calls in traced_calls.items():
            if calls:
                for call in calls:
                    print(f"[TRACE]{json.dumps(call)}")

if __name__ == "__main__":
    main()
'''
        return trace_script.replace("<<<ENCODED_SCRIPT>>>", encoded_script)

    def _run_trace_script(self, script_content: str, venv_path: str) -> Tuple[bool, str, str]:
        """
        Run the trace script in the specified venv

        Args:
            script_content: Complete script to execute
            venv_path: Path to virtual environment

        Returns:
            (success, stdout, stderr)
        """
        python_path = os.path.join(venv_path, 'bin', 'python')

        # Write script to temporary file
        script_file = os.path.join(os.path.dirname(venv_path), 'trace_script.py')

        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            os.chmod(script_file, 0o755)

            # Run script
            result = subprocess.run(
                [python_path, script_file],
                capture_output=True,
                text=True,
                timeout=300
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            return False, "", "Timeout during script execution"
        except Exception as e:
            return False, "", f"Error running trace script: {str(e)}"
        finally:
            # Clean up script file
            if os.path.exists(script_file):
                os.remove(script_file)

    def _parse_trace_output(self, stdout: str, filename: str):
        """
        Parse the trace output and populate library_calls and library_imports

        Args:
            stdout: Output from trace script
            filename: Name of the source file
        """
        for line in stdout.split('\n'):
            if not line.startswith('[TRACE]'):
                continue

            json_str = line.replace('[TRACE]', '').strip()
            try:
                call_record = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            api_path = call_record.get('api', '')
            args_dict = call_record.get('args', {})
            caller = call_record.get('caller', 'unknown')
            lineno = call_record.get('line', 0)

            # Determine which package this belongs to
            package = self._get_package_from_module(api_path)
            if not package:
                continue

            # Store the call with its arguments
            # Convert args_dict back to args/kwargs format
            args = []
            kwargs = {}
            for key, val in args_dict.items():
                if key not in ['self', 'cls']:
                    kwargs[key] = {'type': 'expression', 'value': val}

            self.library_calls[package][api_path].append({
                'args': args,
                'kwargs': kwargs,
                'line': lineno,
                'file': filename
            })

    def extract_calls(self):
        """Main extraction function using dynamic tracing"""
        print(f"\n{'='*60}")
        print(f"Extracting Library Calls from: {self.script_path}")
        print(f"{'='*60}\n")

        # Extract Python code from script
        python_blocks = self._extract_script_content(self.script_path)

        # Step 1: Collect all imports from code (AST-based)
        # print("Step 1: Collecting all imports from code...")
        # all_imports = self._collect_all_imports(python_blocks)
        # print(f"Found {len(all_imports)} unique imported packages")

        # Step 2: Filter to only installable packages
        # print("\nStep 2: Filtering installable packages...")
        # self.target_packages = self._filter_installable_packages(all_imports)
        # print(f"\nTarget packages ({len(self.target_packages)}): {sorted(self.target_packages)}")

        # if not self.target_packages:
        #     print("\nNo installable third-party packages found!")
        #     return

        # Step 3: Extract import records using AST
        # print(f"\nStep 3: Extracting import records using AST...")
        # for filename, code in python_blocks:
        #     tree = self._parse_ast(code, filename)
        #     if not tree:
        #         continue

        #     imports, import_records = self._extract_imports(tree, filename)

        #     # Process import records
        #     for import_record in import_records:
        #         package = import_record['downstream_package']
        #         # Only keep imports for target packages
        #         if package in self.target_packages:
        #             self.library_imports[package].append(import_record)

        # Step 4: Create venv and extract API calls via dynamic tracing
        # Note: Dynamic tracing uses caller-based filtering (is_user_code)
        # instead of TARGET_PACKAGES
        # print(f"\nStep 4: Extracting API calls via dynamic tracing...")

        # Create a temporary venv for tracing
        import tempfile
        import shutil
        work_dir = tempfile.mkdtemp(prefix="extract_api_calls_")
        venv_path = os.path.join(work_dir, '.venv')

        try:
            # Create venv
            print("  Creating virtual environment...")
            success, error = self._setup_venv(work_dir, '.venv')
            if not success:
                print(f"  ✗ Failed to create venv: {error}")
                return
            print("  ✓ Virtual environment created")

            # Process each Python block
            for filename, code in python_blocks:
                print(f"\n  Tracing: {filename}")

                # Execute with retries for missing packages
                max_retries = 10
                attempt = 0

                while attempt < max_retries:
                    # Generate trace script
                    script_content = self._generate_trace_script(code)

                    # Run script
                    success, stdout, stderr = self._run_trace_script(
                        script_content=script_content,
                        venv_path=venv_path
                    )

                    if success:
                        # Parse trace output
                        self._parse_trace_output(stdout, filename)
                        print(f"  ✓ Successfully traced {filename}")
                        break

                    # Check for missing packages
                    missing_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr)

                    if missing_match:
                        missing_pkg = missing_match.group(1)
                        print(f"  [Attempt {attempt+1}/{max_retries}] Missing package: '{missing_pkg}', installing...")

                        install_success, error_msg = self._install_package(
                            package_name=missing_pkg,
                            venv_path=venv_path,
                        )

                        if install_success:
                            print(f"  ✓ Installed {missing_pkg}, retrying...")
                            attempt += 1
                            continue
                        else:
                            print(f"  ✗ Failed to install {missing_pkg}: {error_msg}")
                            break
                    else:
                        print(f"  ✗ Trace failed: {stderr[:2000]}")
                        break

                if attempt >= max_retries:
                    print(f"  ✗ Max retries reached for {filename}")

        finally:
            # Clean up temporary directory
            shutil.rmtree(work_dir, ignore_errors=True)

        # Print summary
        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\nExtracted {total_calls} library calls from {len(self.library_calls)} libraries")

    def save_api_logs(self):
        """Save API calls and imports for each library to separate Python scripts with deduplication"""
        print(f"\n{'='*60}")
        print("Saving API Logs")
        print(f"{'='*60}\n")

        # Merge all libraries from both calls and imports
        all_libraries = set(self.library_calls.keys()) | set(self.library_imports.keys())

        for library in all_libraries:
            # Create a set to track unique API calls
            unique_apis = set()
            api_call_records = []

            # Process API function calls
            api_calls = self.library_calls.get(library, {})
            for api_name, call_list in sorted(api_calls.items()):
                for call_info in call_list:
                    # Create a unique signature for deduplication
                    args_tuple = tuple(self._format_arg_for_code(arg) for arg in call_info['args'])
                    kwargs_tuple = tuple(sorted((k, self._format_arg_for_code(v))
                                               for k, v in call_info['kwargs'].items()))
                    signature = ('call', api_name, args_tuple, kwargs_tuple)

                    # Only add if not already seen
                    if signature not in unique_apis:
                        unique_apis.add(signature)
                        api_call_records.append({
                            'type': 'call',
                            'api': api_name,
                            'args': call_info['args'],
                            'kwargs': call_info['kwargs'],
                            'source_file': call_info['file'],
                            'line': call_info['line']
                        })

            # Process import records
            seen_imports = set()
            import_records = self.library_imports.get(library, [])
            for import_record in import_records:
                import_type = import_record['type']
                downstream_module = import_record['downstream_module']

                if import_type == 'from_import':
                    # For from_import, include imported_names in signature
                    imported_names = tuple(sorted(import_record['imported_names']))
                    signature = ('from_import', downstream_module, imported_names)
                else:
                    # For import, just use module name
                    signature = ('import', downstream_module)

                # Only add if not already seen
                if signature not in seen_imports:
                    seen_imports.add(signature)
                    api_call_records.append({
                        'type': import_type,
                        'api': downstream_module,
                        'imported_names': import_record.get('imported_names', []),
                        'source_file': import_record['file'],
                        'line': import_record['lineno']
                    })

            # Generate Python script for this library
            output_file = self.api_log_dir / f"{library}_apis.py"
            total_unique = len(unique_apis) + len(seen_imports)
            self._write_api_log_script(output_file, library, api_call_records)
            print(f"Generated: {output_file} ({total_unique} unique API calls/imports)")

    def _write_api_log_script(self, output_file: Path, library: str,
                             api_call_records: List[Dict]):
        """Write API calls and imports to a Python script file"""
        with open(output_file, 'w') as f:
            # Write header comments
            f.write(f'# API calls in library: None\n')
            f.write(f'# Discovered from: {self.script_path.name}\n')
            f.write(f'# Target package: None\n')
            f.write(f'# Total unique API calls: {len(api_call_records)}\n')
            f.write(f'\n')

            # Write each API call or import with its metadata
            for api_id, record in enumerate(api_call_records, 1):
                record_type = record.get('type', 'call')
                api_name = record['api']

                # Write API metadata in the required format
                f.write(f'# API ID: {api_id}\n')
                f.write(f'# Found in versions: None\n')
                f.write(f'# Type: {record_type}\n')
                f.write(f'# Target: {api_name}\n')
                f.write(f'# Call chain: None\n')

                # Generate different code based on type
                if record_type == 'call':
                    # Format arguments
                    args_str_list = []
                    for arg in record['args']:
                        args_str_list.append(self._format_arg_for_code(arg))

                    kwargs_str_list = []
                    for k, v in record['kwargs'].items():
                        kwargs_str_list.append(f"{k}={self._format_arg_for_code(v)}")

                    all_args = ', '.join(args_str_list + kwargs_str_list)

                    # Write the actual API call
                    f.write(f'{api_name}({all_args})\n')

                elif record_type == 'from_import':
                    # For from_import, generate importlib code to check each imported name
                    imported_names = record.get('imported_names', [])
                    f.write(f"mod = importlib.import_module('{api_name}')\n")
                    for name in imported_names:
                        f.write(f"if not hasattr(mod, '{name}'): raise ImportError(\"cannot import name '{name}' from '{api_name}'\")\n")

                elif record_type == 'import':
                    # For import, use dynamic import to verify compatibility
                    f.write(f"importlib.import_module('{api_name}')\n")

                else:
                    f.write(f"# Unknown API type: {record_type}\n")

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