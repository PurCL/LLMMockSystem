#!/usr/bin/env python3
import ast
import os
import sys
import re
import subprocess
import importlib.util
import importlib.metadata
import json
import multiprocessing
import functools
import time
import sqlite3
import hashlib
import shutil
import inspect
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict

# ============================================================
# 模块 1: API解析模块 - 从apis.py文件提取信息
# ============================================================


class APIParser:
    """负责解析*_apis.py文件，提取package名称和API信息"""

    @staticmethod
    def parse_api_file(api_file_path: str) -> Dict[str, Any]:
        """
        解析*_apis.py文件

        Args:
            api_file_path: apis.py文件的路径

        Returns:
            {
                'package': str,           # package名称
                'api_calls': List[Dict]   # API调用列表
            }
        """
        with open(api_file_path, 'r') as f:
            content = f.read()

        # 提取package名称
        package_match = re.search(r'API Calls for (\w+)', content)
        if package_match:
            package_name = package_match.group(1)
        else:
            filename = Path(api_file_path).stem
            package_name = filename.replace('_apis', '')

        # 解析所有API calls
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
        """解析单个API定义"""
        i = start_index

        # 解析 API ID
        api_id_match = re.match(r'# API ID:\s*(\d+)', lines[i].strip())
        api_id = api_id_match.group(1) if api_id_match else None
        i += 2  # 跳过空行

        # 解析 Type (call 或 attribute)
        api_type = "call"
        if i < len(lines) and lines[i].strip().startswith('# Type:'):
            api_type = lines[i].strip().replace('# Type:', '').strip()
            i += 1

        # 解析 API名称
        api_name = None
        if i < len(lines) and lines[i].strip().startswith('# API:'):
            api_name = lines[i].strip().replace('# API:', '').strip()
            i += 1

        # 解析 caller信息
        caller_info = "unknown"
        if i < len(lines):
            caller_line = lines[i].strip()
            if caller_line.startswith('# Call chain:'):
                caller_info = caller_line.replace('# Call chain:', '').strip()
                if caller_info == 'None':
                    caller_info = 'unknown'
                i += 1
            elif caller_line.startswith('# Attribute access'):
                caller_info = caller_line.replace('# Attribute access', '').strip()
                if caller_info.startswith('('):
                    caller_info = caller_info[1:-1] if caller_info.endswith(')') else caller_info[1:]
                if not caller_info or caller_info == 'None':
                    caller_info = 'attribute access'
                i += 1

        # 解析实际的调用代码
        api_call = None
        if i < len(lines):
            call_line = lines[i].strip()
            if call_line and not call_line.startswith('#'):
                is_attribute = api_type == "attribute"
                is_decorator = call_line.startswith('@')

                if is_attribute:
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
                        'is_attribute': is_attribute
                    }
                i += 1

        return {
            'api_call': api_call,
            'next_index': i
        }

    @staticmethod
    def _parse_call_line(call_line: str) -> Tuple[List, Dict]:
        """解析API调用代码，提取args和kwargs"""
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
        """将AST节点转换为Python值"""
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

# Module-level constant for standard library modules (Optimization 5)
COMMON_STDLIB = {
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


class DynamicDependencyTracer:
    """Traces dynamic API calls using sys.settrace"""

    def __init__(self, target_packages: Set[str], source_package: str):
        """
        Initialize dynamic tracer

        Args:
            target_packages: Set of third-party dependency libraries to monitor (e.g. {'tensorflow', 'torch', 'numpy'})
            source_package: Current target library being executed (e.g. 'keras')
        """
        self.target_packages = target_packages
        self.source_package = source_package
        # Structure: {library_name: {api_path: [call_info, ...]}}
        self.library_calls = defaultdict(lambda: defaultdict(list))
        self.call_chain = []

    def trace_dispatch(self, frame, event, arg):
        """Trace function that gets called for every function call and return"""
        # We only care about function enter (call) and exit (return)
        if event == 'call':
            module_name = frame.f_globals.get("__name__", "")
            if not module_name:
                return self.trace_dispatch

            func_name = frame.f_code.co_name
            top_level = module_name.split('.')[0]

            # Maintain call stack
            self.call_chain.append(f"{module_name}.{func_name}")

            # Core filtering logic: if entering target third-party library, and not source library itself
            if top_level in self.target_packages and top_level != self.source_package:
                full_api_path = f"{module_name}.{func_name}"

                # Use inspect to capture runtime argument types
                args_dict = {}
                try:
                    arg_info = inspect.getargvalues(frame)
                    for a in arg_info.args:
                        val = arg_info.locals.get(a)
                        # To avoid memory overflow from serializing large objects (like Tensors), only record type or key attributes
                        args_dict[a] = f"<{type(val).__name__}>"
                except Exception:
                    pass

                self.library_calls[top_level][full_api_path].append({
                    'call_chain': list(self.call_chain),
                    'args': args_dict,
                    'kwargs': {}  # Can be extended to capture kwargs if needed
                })

        elif event == 'return':
            if self.call_chain:
                self.call_chain.pop()

        return self.trace_dispatch

    def __enter__(self):
        """Enable global tracing"""
        sys.settrace(self.trace_dispatch)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disable global tracing"""
        sys.settrace(None)


def load_pypi_import_mapping(mapping_file="pypi_import_mapping.json"):
    """
    Load PyPI package name to import name mapping from JSON file and reverse it.
    This is the same mapping used in resolve_dependencies.py for package alias resolution.

    Args:
        mapping_file: Path to the JSON mapping file

    Returns:
        dict: {import_name: pypi_package_name}
    """
    if not os.path.exists(mapping_file):
        print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")
        return {}

    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        # Reverse the mapping: {import_name: pypi_package_name}
        reversed_mapping = {import_name: pypi_name for pypi_name, import_name in mapping.items()}
        print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file}")
        return reversed_mapping
    except Exception as e:
        print(f"⚠️ Failed to load mapping file {mapping_file}: {e}")
        return {}

    def trace_dependencies(self):
        """Main tracing function - analyzes the target script dynamically using sys.settrace"""
        import runpy

        print(f"\n{'='*60}")
        print("Tracing Library Dependencies (Dynamic Execution Version)")
        print(f"{'='*60}\n")

        if not self.target_script.exists():
            print(f"Error: Target script not found: {self.target_script}")
            return

        # Step 1: Collect imports to determine target_packages
        print("Step 1: Collecting target packages from static analysis...")
        all_imports = self._collect_all_imports_from_package(self.package_path)
        self.target_packages = self._filter_installable_packages(all_imports)

        if not self.target_packages:
            print("No installable third-party packages found!")
            return

        print(f"Target packages to monitor: {sorted(self.target_packages)}")

        # Step 2: Dynamically execute target script with sys.settrace enabled
        print(f"\nStep 2: Dynamically executing and tracing script: {self.target_script}")

        # Instantiate dynamic tracer
        dynamic_tracer = DynamicDependencyTracer(self.target_packages, self.package_name)

        try:
            # Enter tracing context
            with dynamic_tracer:
                # Run the target test script using runpy
                runpy.run_path(str(self.target_script), run_name="__main__")
        except Exception as e:
            print(f"Warning: Script execution encountered an error (which is common): {e}")

        # Step 3: Merge dynamically captured results into existing data structures
        self.library_calls = dynamic_tracer.library_calls

        # Print summary
        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\n{'='*60}")
        print(f"Discovered {total_calls} dynamic API calls across {len(self.library_calls)} libraries")
        for lib in sorted(self.library_calls.keys()):
            call_count = sum(len(calls) for calls in self.library_calls[lib].values())
            print(f"  - {lib}: {call_count} calls")
        print(f"{'='*60}")

    def save_api_logs(self):
        """Save API logs with newly discovered calls - returns dict of library->api calls for aggregation"""
        print(f"\n{'='*60}")
        print(f"Processing API Logs for version {self.version}")
        print(f"{'='*60}\n")

        if not self.library_calls and not self.library_attributes:
            print("No API calls or attribute accesses discovered")
            return {}

        # Return the library calls and attribute accesses for aggregation
        result = {}

        # Add function calls
        for library, api_calls in self.library_calls.items():
            if library not in result:
                result[library] = []
            for api_name, call_list in api_calls.items():

                # ==================== 新增：静态过滤逻辑 ====================
                if not self._validate_api_statically(api_name):
                    print(f"  [Filter Out] Dropped version-overfitted API (not found statically): {api_name}")
                    continue
                # ==========================================================

                for call_info in call_list:
                    # Format the API call - for dynamic tracing, we simplify the format
                    args_str = ', '.join([f"{k}={v}" for k, v in call_info['args'].items()])
                    api_call_str = f"{api_name}({args_str})"

                    result[library].append({
                        'api_call': api_call_str,
                        'api_name': api_name,
                        'api_type': 'call',
                        'source_api': 'dynamic_trace',
                        'call_chain': call_info.get('call_chain', []),
                        'args': call_info['args'],
                        'kwargs': call_info['kwargs']
                    })

        # Add attribute accesses
        for library, attr_accesses in self.library_attributes.items():
            if library not in result:
                result[library] = []
            for attr_name, access_list in attr_accesses.items():
                for access_info in access_list:
                    result[library].append({
                        'api_call': attr_name,
                        'api_name': attr_name,
                        'api_type': 'attribute',
                        'source_api': access_info.get('source', 'unknown'),
                        'call_chain': [],
                        'args': [],
                        'kwargs': {}
                    })

        # Output intermediate result: API logs being saved
        print(f"\n[Intermediate Output] API Logs for version {self.version}:")
        print(f"{'='*60}")
        print(f"Total libraries with calls: {len(result)}")
        for library in sorted(result.keys()):
            print(f"\nLibrary: {library}")
            print(f"  Total API entries: {len(result[library])}")
            call_count = sum(1 for api in result[library] if api['api_type'] == 'call')
            attr_count = sum(1 for api in result[library] if api['api_type'] == 'attribute')
            print(f"  Function calls: {call_count}")
            print(f"  Attribute accesses: {attr_count}")
            # Show a few examples
            examples = result[library][:3]
            if examples:
                print(f"  Examples:")
                for ex in examples:
                    print(f"    - {ex['api_call']} (type: {ex['api_type']})")
        print(f"{'='*60}\n")

        return result


def setup_environment_and_trace_worker(args):
    """
    Worker function for multiprocessing - processes a single version with full isolation.

    Each version gets:
    - Its own isolated directory (version_<version>)
    - Its own virtual environment with --clear and --copies flags
    - Completely isolated environment variables
    - All runtime information saved in its directory
    - Automatic cleanup of version directory after processing completes
    """
    target_script, package_name, version, output_dir, worker_id, work_dir = args

    # Create a version-specific directory for complete isolation
    safe_version = version.replace('/', '_').replace(':', '_')
    # Convert to absolute path to avoid path issues
    work_dir_abs = os.path.abspath(work_dir)
    version_dir = os.path.join(work_dir_abs, f'version_{safe_version}')
    venv_name = '.venv'
    venv_path = os.path.join(version_dir, venv_name)

    print(f"\n{'='*80}")
    print(f"[Worker {worker_id}] Processing version: {version}")
    print(f"[Worker {worker_id}] Work directory: {work_dir}")
    print(f"[Worker {worker_id}] Version directory: {version_dir}")
    print(f"[Worker {worker_id}] Venv path: {venv_path}")
    print(f"{'='*80}\n")

    try:
        # Step 1: Create version-specific directory
        print(f"[Worker {worker_id}] Step 1: Creating isolated version directory...")
        os.makedirs(version_dir, exist_ok=True)
        print(f"[Worker {worker_id}] ✓ Version directory created")

        # Step 2: Create virtual environment with full isolation
        print(f"[Worker {worker_id}] Step 2: Creating isolated virtual environment...")

        # Remove existing venv if it exists (with retries for filesystem delays)
        if os.path.exists(venv_path):
            for attempt in range(3):
                try:
                    shutil.rmtree(venv_path, ignore_errors=False, onerror=handle_remove_readonly)
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"[Worker {worker_id}] Warning: Failed to remove venv after 3 attempts, forcing removal...")
                        try:
                            shutil.rmtree(venv_path, ignore_errors=True)
                        except:
                            pass
                        break
                    time.sleep(0.5)

        # Build minimal isolated environment for venv creation
        venv_creation_env = {
            'PATH': os.environ.get('PATH', ''),
            'HOME': os.environ.get('HOME', ''),
            'USER': os.environ.get('USER', ''),
            'LOGNAME': os.environ.get('LOGNAME', ''),
            # Clear all Python-related variables to prevent interference
            'PYTHONHOME': '',
            'PYTHONPATH': '',
            'PYTHONUSERBASE': '',
            'PYTHONSTARTUP': '',
            'PYTHONOPTIMIZE': '',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            # Language settings
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
        }

        # Create new venv with --clear and --copies flags for complete isolation
        result = subprocess.run(
            ['python3', '-m', 'venv', '--clear', '--copies', venv_path],
            capture_output=True,
            text=True,
            timeout=120,
            env=venv_creation_env
        )
        if result.returncode != 0:
            print(f"[Worker {worker_id}] Error creating virtual environment: {result.stderr}")
            return (version, {}, set())
        # Wait a moment for filesystem to sync
        time.sleep(0.5)

        # Verify that the python executable exists (with retries)
        python_path = os.path.join(venv_path, 'bin', 'python')
        python_found = False
        for attempt in range(5):
            if os.path.exists(python_path):
                python_found = True
                break
            print(f"[Worker {worker_id}]   Waiting for python executable to appear (attempt {attempt+1}/5)...")
            time.sleep(1)

        if not python_found:
            print(f"[Worker {worker_id}] ✗ Error: Python executable not found at {python_path}")
            print(f"[Worker {worker_id}]   Venv creation may have failed silently")
            print(f"[Worker {worker_id}]   Stdout: {result.stdout}")
            print(f"[Worker {worker_id}]   Stderr: {result.stderr}")
            return (version, {}, set())

        print(f"[Worker {worker_id}] ✓ Isolated virtual environment created")
        print(f"[Worker {worker_id}]   Python path: {python_path}")

        # Step 3: Install package without dependencies using isolated pip
        print(f"[Worker {worker_id}] Step 3: Installing {package_name}=={version} (without dependencies)...")

        pip_path = os.path.join(venv_path, 'bin', 'pip')

        # Verify pip exists
        if not os.path.exists(pip_path):
            print(f"[Worker {worker_id}] ✗ Error: pip not found at {pip_path}")
            return (version, {}, set())

        tmp_dir = os.path.join(version_dir, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)

        # Build completely isolated environment for pip
        pip_install_env = {
            # Essential paths
            'PATH': f"{os.path.join(venv_path, 'bin')}:{os.environ.get('PATH', '')}",
            'HOME': os.environ.get('HOME', ''),
            'USER': os.environ.get('USER', ''),
            'LOGNAME': os.environ.get('LOGNAME', ''),

            # Virtual environment
            'VIRTUAL_ENV': venv_path,

            # Python isolation - clear all Python variables
            'PYTHONHOME': '',
            'PYTHONPATH': '',
            'PYTHONUSERBASE': '',
            'PYTHONSTARTUP': '',
            'PYTHONOPTIMIZE': '',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',

            # Pip isolation - clear all pip configuration
            'PIP_CONFIG_FILE': '/dev/null',
            'PIP_REQUIRE_VIRTUALENV': '1',
            'PIP_NO_INPUT': '1',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'PIP_NO_CACHE_DIR': '1',
            'PIP_ISOLATED': '1',
            'PIP_NO_COLOR': '1',
            'PIP_QUIET': '0',

            # Temp directory
            'TMPDIR': tmp_dir,
            'TEMP': tmp_dir,
            'TMP': tmp_dir,

            # Language settings
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
        }

        result = subprocess.run(
            [pip_path, 'install', '--no-deps', '--isolated', f'{package_name}=={version}'],
            capture_output=True,
            text=True,
            timeout=300,
            env=pip_install_env
        )
        if result.returncode != 0:
            print(f"[Worker {worker_id}] Error installing package: {result.stderr}")
            return (version, {}, set())
        print(f"[Worker {worker_id}] ✓ Package {package_name}=={version} installed")

        # Step 4: Trace dependencies using isolated Python
        print(f"[Worker {worker_id}] Step 4: Tracing dependencies in isolated environment...")

        python_path = os.path.join(venv_path, 'bin', 'python')

        # Verify python executable exists before using it
        if not os.path.exists(python_path):
            print(f"[Worker {worker_id}] ✗ Error: Python executable not found at {python_path}")
            return (version, {}, set())

        # Build completely isolated environment for tracing
        trace_env = {
            # Essential paths
            'PATH': f"{os.path.join(venv_path, 'bin')}:{os.environ.get('PATH', '')}",
            'HOME': os.environ.get('HOME', ''),
            'USER': os.environ.get('USER', ''),
            'LOGNAME': os.environ.get('LOGNAME', ''),
            'SHELL': os.environ.get('SHELL', ''),

            # Virtual environment isolation
            'VIRTUAL_ENV': venv_path,

            # Python isolation - explicitly clear all Python-related variables
            'PYTHONHOME': '',
            'PYTHONPATH': '',
            'PYTHONUSERBASE': '',
            'PYTHONSTARTUP': '',
            'PYTHONOPTIMIZE': '',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'PYTHONPYCACHEPREFIX': os.path.join(version_dir, '__pycache__'),
            'PYTHONHASHSEED': '0',

            # Temp directory isolation
            'TMPDIR': tmp_dir,
            'TEMP': tmp_dir,
            'TMP': tmp_dir,

            # Language and encoding
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'LC_ALL': os.environ.get('LC_ALL', 'C.UTF-8'),
        }

        try:
            # Create a tracer script that will be executed in the isolated environment
            tracer_script_path = os.path.join(version_dir, 'run_tracer.py')
            tracer_result_path = os.path.join(version_dir, 'tracer_result.json')

            # Get the path to the main script file for imports
            main_script_path = os.path.abspath(__file__)

            # Write the tracer execution script
            tracer_script_content = f'''
import sys
import os
import json

# Add the main script directory to sys.path for imports
sys.path.insert(0, {repr(os.path.dirname(main_script_path))})

# Import the necessary classes
from trace_library_dependencies import LibraryDependencyTracer

# Create tracer instance - this will now use the venv's Python environment
tracer = LibraryDependencyTracer(
    {repr(target_script)},
    {repr(package_name)},
    {repr(version)},
    {repr(output_dir)},
)

# Run tracing
tracer.trace_dependencies()
api_logs = tracer.save_api_logs()
target_packages = list(tracer.target_packages)

# Save results to JSON file
result = {{
    'api_logs': api_logs,
    'target_packages': target_packages
}}

with open({repr(tracer_result_path)}, 'w') as f:
    json.dump(result, f, indent=2)

print("\\n[Tracer] Results saved to:", {repr(tracer_result_path)})
'''

            with open(tracer_script_path, 'w') as f:
                f.write(tracer_script_content)

            print(f"[Worker {worker_id}]   Created tracer script: {tracer_script_path}")
            print(f"[Worker {worker_id}]   Executing in isolated environment...")

            # Execute the tracer script in the isolated environment
            result = subprocess.run(
                [python_path, tracer_script_path],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
                env=trace_env,
                cwd=version_dir
            )

            if result.returncode != 0:
                print(f"[Worker {worker_id}] ✗ Error running tracer script:")
                print(f"[Worker {worker_id}]   Return code: {result.returncode}")
                print(f"[Worker {worker_id}]   Stderr: {result.stderr}")
                print(f"[Worker {worker_id}]   Stdout: {result.stdout}")
                return (version, {}, set())

            # Print the output from the tracer
            if result.stdout:
                print(f"[Worker {worker_id}] Tracer output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"[Worker {worker_id}]   {line}")

            # Read the results from the JSON file
            if not os.path.exists(tracer_result_path):
                print(f"[Worker {worker_id}] ✗ Error: Tracer result file not found: {tracer_result_path}")
                return (version, {}, set())

            with open(tracer_result_path, 'r') as f:
                tracer_result = json.load(f)

            api_logs = tracer_result.get('api_logs', {})
            target_packages = set(tracer_result.get('target_packages', []))

            print(f"[Worker {worker_id}] ✓ Version {version} traced successfully")
            print(f"[Worker {worker_id}]   API logs: {len(api_logs)} libraries")
            print(f"[Worker {worker_id}]   Target packages: {len(target_packages)} packages")
            return (version, api_logs, target_packages)

        except subprocess.TimeoutExpired:
            print(f"[Worker {worker_id}] ⚠ Warning: Tracing timeout for version {version}")
            return (version, {}, set())
        except (ModuleNotFoundError, ImportError) as e:
            print(f"[Worker {worker_id}] ⚠ Warning: Module import error for version {version}: {e}")
            print(f"[Worker {worker_id}]   This is likely due to missing binary dependencies.")
            return (version, {}, set())
        except Exception as e:
            print(f"[Worker {worker_id}] ⚠ Warning: Unexpected error during tracing: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return (version, {}, set())

    except Exception as e:
        print(f"[Worker {worker_id}] ✗ Error processing version {version}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return (version, {}, set())
    finally:
        # Clean up this version's directory after processing
        print(f"[Worker {worker_id}] Cleaning up version directory: {version_dir}")
        try:
            shutil.rmtree(version_dir, ignore_errors=False, onerror=handle_remove_readonly)
            print(f"[Worker {worker_id}] ✓ Version directory cleaned up successfully")
        except Exception as e:
            print(f"[Worker {worker_id}] ⚠ Warning: Failed to clean up version directory: {e}")
            # Force removal with ignore_errors if normal removal fails
            try:
                shutil.rmtree(version_dir, ignore_errors=True)
                print(f"[Worker {worker_id}] ✓ Version directory force-cleaned successfully")
            except:
                pass


def aggregate_and_save_results(all_version_results: Dict[str, Dict[str, List[Dict]]],
                               output_dir: Path, package_name: str, target_script: str, versions: List[str],
                               all_target_packages: Set[str] = None):
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

    # Output intermediate result: aggregated data summary
    print(f"\n[Intermediate Output] Aggregated Data Summary:")
    print(f"{'='*80}")
    print(f"Total libraries: {len(aggregated_data)}")
    for library_name in sorted(aggregated_data.keys()):
        print(f"\nLibrary: {library_name}")
        print(f"  Total unique APIs: {len(aggregated_data[library_name])}")
        print(f"  Versions with this library: {len(version_mapping[library_name])}")
        # Show version distribution
        for version in sorted(version_mapping[library_name].keys()):
            api_count = len(version_mapping[library_name][version])
            print(f"    - Version {version}: {api_count} APIs")
    print(f"{'='*80}\n")

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
            versions_found = sorted(api_info['versions'])
            api_type = api_data.get('api_type', 'call')

            lines.append(f"# API ID: {api_id}")
            lines.append(f"# Found in versions: {', '.join(versions_found)}")
            lines.append(f"# Type: {api_type}")
            lines.append(f"# API: {api_data['api_name']}")

            if api_type == 'attribute':
                lines.append(f"# Attribute access (discovered during import)")
            elif api_data.get('call_chain'):
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

    # Generate version_compatibility.json files for target packages not in library_calls
    if all_target_packages:
        print(f"\nGenerating version compatibility files for target packages...")

        # Find packages in target_packages but not in library_calls
        libraries_with_calls = set(aggregated_data.keys())
        packages_without_calls = all_target_packages - libraries_with_calls

        for library_name in sorted(packages_without_calls):
            # Create the version_compatibility.json file
            compatibility_file = output_dir / f"{library_name}_version_compatibility.json"

            # Build version_combinations list
            version_combinations = []
            for version in versions:
                version_combinations.append({
                    "target_version": str(version),
                    "dependency_version": "ALL",
                    "supported_api_ids": []
                })

            # Build the JSON structure
            compatibility_data = {
                "type": "dependency_compatibility",
                "package_name": library_name,
                "version_combinations": version_combinations
            }

            # Write the compatibility file
            with open(compatibility_file, 'w') as f:
                json.dump(compatibility_data, f, indent=2)

            print(f"Created: {compatibility_file} (target package without API calls)")

    print(f"\n{'='*80}")
    print("Aggregation complete!")
    print(f"{'='*80}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python trace_library_dependencies.py <target_script> <version1> [version2 ...] [--output_dir <dir>]")
        print()
        print("Arguments:")
        print("  target_script         - Path to the *_apis.py file to analyze (e.g., 'keras_apis.py')")
        print("  version1 version2 ... - One or more version strings to analyze (e.g., '2.12.0', '2.12.0rc0', '2.13.0')")
        print("  --output_dir <dir>    - Optional: Directory to save API logs (default: ./<package_name>_api_log)")
        print()
        print("Example:")
        print("  python3 trace_library_dependencies.py api_log/keras_apis.py 2.12.0 2.12.0rc0 2.13.0")
        print("  python3 trace_library_dependencies.py api_log/tensorflow_apis.py 2.12.0 2.12.0rc0 --output_dir ./output")
        print("  python3 trace_library_dependencies.py api_log/keras_apis.py 2.12.0")
        sys.exit(1)

    # Parse arguments
    target_script = sys.argv[1]
    # Convert to absolute path to ensure it works in any working directory
    target_script = os.path.abspath(target_script)

    # Extract package name from the target script filename using APIParser
    try:
        parsed_data = APIParser.parse_api_file(target_script)
        package_name = parsed_data['package']
        print(f"Automatically detected package name: {package_name}")
    except Exception as e:
        print(f"Error: Failed to parse package name from {target_script}: {e}")
        print("Please ensure the target_script is a valid *_apis.py file.")
        sys.exit(1)

    # Optional arguments
    output_dir = None
    versions = []

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--output_dir':
            if i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --output_dir requires a value")
                sys.exit(1)
        else:
            # Treat as a version string
            versions.append(arg)
            i += 1

    if not versions:
        print("Error: At least one version must be specified")
        sys.exit(1)

    # Set default output directory if not provided
    if output_dir is None:
        target_script_dir = Path(target_script).parent
        output_dir = target_script_dir / f"{package_name}_api_log"
    else:
        output_dir = Path(output_dir)

    # Convert to absolute path to avoid path construction issues
    output_dir = output_dir.resolve()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine number of processes
    num_processes = int(multiprocessing.cpu_count() / 4)
    print(f"\n{'='*80}")
    print("Library Dependency Tracer - Multi-Version Analysis (Fully Isolated)")
    print(f"{'='*80}")
    print(f"Target script: {target_script}")
    print(f"Package: {package_name}")
    print(f"Versions ({len(versions)}): {', '.join(versions)}")
    print(f"Output directory: {output_dir}")
    print(f"Number of processes: {num_processes}")
    print(f"{'='*80}\n")

    # Prepare arguments for worker processes
    worker_args_list = [
        (target_script, package_name, version, str(output_dir), i, str(work_dir))
        for i, version in enumerate(versions)
    ]

    # Process versions in parallel using multiprocessing
    all_version_results = {}
    all_target_packages = set()

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(setup_environment_and_trace_worker, worker_args_list)

    # Process results from all workers
    for version, api_logs, target_packages in results:
        # Always collect target_packages, regardless of whether there are API calls
        all_target_packages.update(target_packages)

        # Only save api_logs if they're non-empty
        if api_logs:
            all_version_results[version] = api_logs

    # Aggregate and save results
    # Call aggregate_and_save_results if we have either API calls OR target packages
    if all_version_results or all_target_packages:
        aggregate_and_save_results(all_version_results, output_dir, package_name, target_script,
                                  versions, all_target_packages)
    else:
        print("\nNo results to aggregate.")

    # Clean up work directory (each version directory was already cleaned by its worker)
    print(f"\n{'='*80}")
    print("Cleaning up work directory...")
    print(f"{'='*80}")
    print(f"Work directory: {work_dir}")
    try:
        # Remove the work_dir itself (should be empty or nearly empty now)
        shutil.rmtree(str(work_dir), ignore_errors=False, onerror=handle_remove_readonly)
        print("✓ Work directory cleaned up successfully")
    except Exception as e:
        print(f"⚠ Warning: Failed to clean up work directory: {e}")
        # Force removal with ignore_errors if normal removal fails
        try:
            shutil.rmtree(str(work_dir), ignore_errors=True)
            print("✓ Work directory force-cleaned successfully")
        except:
            pass

    print(f"\n{'='*80}")
    print("Library Dependency Tracing Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
