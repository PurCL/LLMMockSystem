"""
Library Call Extractor (Dynamic Trace Edition)
Extracts all library API calls from a script and organizes them by library.
Saves unique API calls for each library in separate Python scripts under api_log directory.
"""

import os
import sys
import re
import importlib
import importlib.util
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import tempfile
import shutil


class LibraryCallExtractor:
    """Extracts and organizes library API calls from user scripts using Dynamic Tracing"""

    def __init__(self, script_path: str, api_log_dir: str):
        self.script_path = Path(script_path)
        self.api_log_dir = Path(api_log_dir)

        # Create api_log directory
        self.api_log_dir.mkdir(exist_ok=True, parents=True)

        # Store API calls by library
        # Structure: {library_name: {api_call: [(kwargs), ...]}}
        self.library_calls = defaultdict(lambda: defaultdict(list))

        # Load PyPI import mapping from JSON file
        self.module_to_package = self._load_pypi_import_mapping()

    def _setup_venv(self, work_dir: str, venv_name: str = '.venv') -> Tuple[bool, str]:
        """Create isolated virtual environment"""
        try:
            venv_path = os.path.join(work_dir, venv_name)
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

            result = subprocess.run(
                ['python3', '-m', 'venv', '--clear', venv_path],
                capture_output=True,
                text=True,
                timeout=120,
                env=venv_creation_env
            )

            if result.returncode != 0:
                return False, f"Failed to create venv: {result.stderr}"

            pip_path = os.path.join(venv_path, 'bin', 'pip')
            if not os.path.exists(pip_path):
                return False, f"Venv created but pip not found at {pip_path}"

            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Timeout while creating venv"
        except Exception as e:
            return False, f"Error creating venv: {str(e)}"

    def _install_package(self, package_name: str, venv_path: str, version: Optional[str] = None) -> Tuple[bool, str]:
        """Install a package in venv"""
        if package_name in self.module_to_package:
            pypi_pkg_name = self.module_to_package[package_name]
            print(f"  [Mapping] Using PyPI package name '{pypi_pkg_name}' for import name '{package_name}'")
        else:
            pypi_pkg_name = package_name

        pip_path = os.path.join(venv_path, 'bin', 'pip')
        package_spec = f"{pypi_pkg_name}=={version}" if version else pypi_pkg_name

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
                        "resolutionimpossible", "conflict",
                        "no matching distribution", "could not find a version"
                    ]
                    if any(error in stderr_lower for error in permanent_errors):
                        return False, f"Package conflict or not found for {package_spec}:\n{result.stderr}"

                    if attempt == max_retries:
                        return False, f"Failed to install {package_spec} after {max_retries} attempts:\n{result.stderr}"

                    time.sleep(3)
                    continue

                return True, ""
            except Exception as e:
                if attempt == max_retries:
                    return False, f"Error installing package after {max_retries} attempts: {str(e)}"
                time.sleep(3)
                continue

        return False, "Installation failed"

    def _load_pypi_import_mapping(self) -> Dict[str, str]:
        """Load PyPI import mapping from JSON file"""
        script_dir = Path(__file__).parent
        mapping_file = script_dir / "pypi_import_mapping.json"

        if not mapping_file.exists():
            print(f"⚠️ Warning: pypi_import_mapping.json not found at {mapping_file}")
            return {}

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                original_mapping = json.load(f)
            reversed_mapping = {import_name: pypi_name for pypi_name, import_name in original_mapping.items()}
            print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file.name}")
            return reversed_mapping
        except Exception as e:
            print(f"⚠️ Failed to load mapping file {mapping_file}: {e}")
            return {}

    def _extract_script_content(self, script_path: Path) -> List[Tuple[str, str]]:
        """Extract Python code from script (handles both .py and .sh with heredoc)"""
        if script_path.suffix == '.sh':
            with open(script_path, 'r') as f:
                content = f.read()

            python_blocks = []
            pattern1 = r"cat\s+>\s+(\S+\.py)\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\2"
            for match in re.finditer(pattern1, content, re.DOTALL):
                filename, delimiter, code = match.groups()
                python_blocks.append((filename, code))
            
            pattern2 = r"python3\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\1"
            for match in re.finditer(pattern2, content, re.DOTALL):
                delimiter, code = match.groups()
                python_blocks.append(("inline_python", code))
                
            return python_blocks
        else:
            with open(script_path, 'r') as f:
                return [(str(script_path.name), f.read())]

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of Python standard library"""
        top_level_name = module_name.split('.')[0]
        return top_level_name in sys.stdlib_module_names

    def _get_package_from_module(self, module_name: str) -> Optional[str]:
        """Extract the package name (filtering out standard library)"""
        if not module_name:
            return None
        top_level = module_name.split('.')[0]
        if self._is_stdlib_module(top_level):
            return None
        return top_level

    def _generate_trace_script(self, script: str) -> str:
        """Generate Python script that traces API calls during execution using Raw String"""
        import base64
        encoded_script = base64.b64encode(script.encode('utf-8')).decode('ascii')

        # Using raw string (r''') to prevent escaping issues with \n
        trace_script = r'''#!/usr/bin/env python3
import sys
import os
import json
import base64
import inspect
import re

user_file_paths = set()
recorded_calls = set()

def safe_repr(val):
    try:
        val_type = type(val).__name__
        if any(keyword in val_type for keyword in ["Tensor", "Variable", "DataFrame", "Series", "ndarray"]):
            shape = getattr(val, 'shape', '?')
            dtype = getattr(val, 'dtype', '?')
            return f"<{val_type}: shape={shape}, dtype={dtype}>"
        
        s = repr(val)
        
        # Core fix: Clean memory addresses to ensure absolute consistency
        if '<function ' in s or '<object ' in s or '<class ' in s or '<bound method ' in s:
            s = re.sub(r' at 0x[0-9a-fA-F]+>', '>', s)

        return s
    except Exception:
        return "<unrepresentable>"

def tracer(frame, event, arg):
    if event != 'call':
        return tracer

    func_name = frame.f_code.co_name
    if func_name == '<module>':
        return tracer

    callee_mod = frame.f_globals.get("__name__", "")
    if not callee_mod or callee_mod.startswith("namedtuple_"):
        return tracer

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

    if os.path.abspath(caller_file) not in user_file_paths:
        return tracer

    is_instance_method = False
    cls_obj = None

    if 'self' in frame.f_locals:
        cls_obj = frame.f_locals['self'].__class__
        is_instance_method = True
    elif 'cls' in frame.f_locals:
        cls_obj = frame.f_locals['cls']
        if not isinstance(cls_obj, type):
            cls_obj = None

    if cls_obj:
        func_obj = getattr(cls_obj, func_name, None)
    else:
        func_obj = frame.f_globals.get(func_name)

    qualname = getattr(func_obj, '__qualname__', None) if func_obj else None

    # Iron Wall Interception 1: Never let closures slip through!
    if qualname and '<locals>' in qualname:
        return tracer

    # Iron Wall Interception 2: Check module's global namespace registry!
    if qualname:
        root_obj_name = qualname.split('.')[0]
        if root_obj_name not in frame.f_globals:
            return tracer
    else:
        if func_name not in frame.f_globals:
            return tracer

    # Construct perfect API signature
    if qualname:
        if is_instance_method and '.' in qualname:
            parts = qualname.rsplit('.', 1)
            api_path = f"{callee_mod}.{parts[0]}().{parts[1]}"
        else:
            api_path = f"{callee_mod}.{qualname}"
    else:
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

    try:
        sig = None
        if func_obj:
            try:
                sig = inspect.signature(func_obj)
            except Exception:
                pass

        arg_info = inspect.getargvalues(frame)
        args_dict = {}

        for arg_name in arg_info.args:
            if arg_name in ('self', 'cls'):
                continue
            val = arg_info.locals.get(arg_name)

            if sig and arg_name in sig.parameters:
                param = sig.parameters[arg_name]
                if param.default is not inspect.Parameter.empty:
                    try:
                        if val == param.default:
                            continue
                    except Exception:
                        pass
            
            args_dict[arg_name] = safe_repr(val)

        if arg_info.varargs:
            val = arg_info.locals.get(arg_info.varargs)
            args_dict[arg_info.varargs] = safe_repr(val)

        if arg_info.keywords:
            val = arg_info.locals.get(arg_info.keywords)
            args_dict[arg_info.keywords] = safe_repr(val)
                
    except Exception as e:
        args_dict = {"error": f"Failed to extract args: {str(e)}"}

    call_record = {
        "api": api_path,
        "caller": f"{caller_mod}.user_code", 
        "caller_file": caller_file,
        "args": args_dict,
        "line": caller_line
    }

    # Dedup and Stream output
    dedup_key = f"{api_path}@{caller_line}"
    if dedup_key not in recorded_calls:
        recorded_calls.add(dedup_key)
        print(f"[TRACE]{json.dumps(call_record)}", flush=True)

    return tracer

def main():
    try:
        user_script_path = os.path.abspath("user_script.py")
        global user_file_paths
        user_file_paths.add(user_script_path)

        encoded_script = "<<<ENCODED_SCRIPT>>>"
        user_code = base64.b64decode(encoded_script).decode('utf-8')

        sys.settrace(tracer)
        exec(compile(user_code, user_script_path, 'exec'))
    except ModuleNotFoundError as e:
        sys.stderr.write(f"ModuleNotFoundError: No module named '{e.name}'\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"Warning: Script execution error: {str(e)}\n")
    finally:
        sys.settrace(None)

if __name__ == "__main__":
    main()
'''
        return trace_script.replace("<<<ENCODED_SCRIPT>>>", encoded_script)

    def _run_trace_script(self, script_content: str, venv_path: str) -> Tuple[bool, str, str]:
        """Run the trace script in the specified venv"""
        python_path = os.path.join(venv_path, 'bin', 'python')
        script_file = os.path.join(os.path.dirname(venv_path), 'trace_script.py')

        try:
            with open(script_file, 'w') as f:
                f.write(script_content)
            os.chmod(script_file, 0o755)

            result = subprocess.run(
                [python_path, script_file],
                capture_output=True,
                text=True,
                timeout=300
            )

            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout during script execution"
        except Exception as e:
            return False, "", f"Error running trace script: {str(e)}"
        finally:
            if os.path.exists(script_file):
                os.remove(script_file)

    def _parse_trace_output(self, stdout: str, filename: str):
        """Parse trace stream and populate library_calls"""
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
            lineno = call_record.get('line', 0)

            package = self._get_package_from_module(api_path)
            if not package:
                continue

            kwargs = {}
            for key, val in args_dict.items():
                if key not in ['self', 'cls']:
                    kwargs[key] = val

            self.library_calls[package][api_path].append({
                'kwargs': kwargs,
                'line': lineno,
                'file': filename
            })

    def extract_calls(self):
        """Main extraction function using ONLY dynamic tracing"""
        print(f"\n{'='*60}")
        print(f"Extracting Library Calls from: {self.script_path}")
        print(f"{'='*60}\n")

        python_blocks = self._extract_script_content(self.script_path)
        work_dir = tempfile.mkdtemp(prefix="extract_api_calls_")
        venv_path = os.path.join(work_dir, '.venv')

        try:
            print("  Creating virtual environment...")
            success, error = self._setup_venv(work_dir, '.venv')
            if not success:
                print(f"  ✗ Failed to create venv: {error}")
                return
            print("  ✓ Virtual environment created")

            for filename, code in python_blocks:
                print(f"\n  Tracing: {filename}")
                max_retries = 10
                attempt = 0

                while attempt < max_retries:
                    script_content = self._generate_trace_script(code)
                    success, stdout, stderr = self._run_trace_script(script_content, venv_path)

                    if success:
                        self._parse_trace_output(stdout, filename)
                        print(f"  ✓ Successfully traced {filename}")
                        break

                    combined_output = stderr + "\n" + stdout
                    missing_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", combined_output)

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
            shutil.rmtree(work_dir, ignore_errors=True)

        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\nExtracted {total_calls} library calls from {len(self.library_calls)} libraries")

    def save_api_logs(self):
        """Save API calls for each library to separate Python scripts with deduplication"""
        print(f"\n{'='*60}")
        print("Saving API Logs")
        print(f"{'='*60}\n")

        for library, api_calls in self.library_calls.items():
            unique_apis = set()
            api_call_records = []

            for api_name, call_list in sorted(api_calls.items()):
                for call_info in call_list:
                    # Our args_dict already holds fully rendered safe strings
                    kwargs_tuple = tuple(sorted((k, v) for k, v in call_info['kwargs'].items()))
                    signature = ('call', api_name, kwargs_tuple)

                    if signature not in unique_apis:
                        unique_apis.add(signature)
                        api_call_records.append({
                            'api': api_name,
                            'kwargs': call_info['kwargs'],
                            'source_file': call_info['file'],
                            'line': call_info['line']
                        })

            output_file = self.api_log_dir / f"{library}_apis.py"
            self._write_api_log_script(output_file, library, api_call_records)
            print(f"Generated: {output_file} ({len(unique_apis)} unique API calls)")

    def _write_api_log_script(self, output_file: Path, library: str, api_call_records: List[Dict]):
        """Write API calls to a Python script file"""
        with open(output_file, 'w') as f:
            f.write(f'# API calls in library: {library}\n')
            f.write(f'# Discovered from: {self.script_path.name}\n')
            f.write(f'# Total unique API calls: {len(api_call_records)}\n\n')

            for api_id, record in enumerate(api_call_records, 1):
                api_name = record['api']

                f.write(f'# API ID: {api_id}\n')
                f.write(f'# Found in versions: None\n')
                f.write(f'# Type: call\n')
                f.write(f'# Target: {api_name}\n')
                f.write(f'# Call chain: None\n')

                # We map all variables to kwargs format natively since we extract by name via inspect
                kwargs_str_list = [f"{k}={v}" for k, v in record['kwargs'].items()]
                all_args = ', '.join(kwargs_str_list)

                f.write(f'{api_name}({all_args})\n\n')


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_library_calls.py <script_path> <api_log_dir>")
        print()
        print("Arguments:")
        print("  script_path - Path to the script to analyze (can be .py or .sh)")
        print("  api_log_dir - Directory to save API logs")
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