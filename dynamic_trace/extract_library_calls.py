#!/usr/bin/env python3
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
import trace_generator
import base64


class LibraryCallExtractor:
    """Extracts and organizes library API calls from user scripts using Dynamic Tracing"""

    def __init__(self, script_path: str, api_log_dir: str, requirements: str):
        self.script_path = Path(script_path)
        self.api_log_dir = Path(api_log_dir)
        self.requirements = Path(requirements)

        # Create api_log directory
        self.api_log_dir.mkdir(exist_ok=True, parents=True)

        # Store API calls by library
        # Structure: {library_name: {api_call: [(args_list, kwargs_dict), ...]}}
        self.library_calls = defaultdict(lambda: defaultdict(list))

        # Load PyPI import mapping from JSON file
        self.module_to_package = self._load_pypi_import_mapping()

        # Track execution time
        self.execution_time = 0

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

    def _install_requirements(self, requirements_file: str, venv_path: str) -> Tuple[bool, str]:
        """Install packages from requirements.txt in venv"""
        pip_path = os.path.join(venv_path, 'bin', 'pip')

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

        try:
            result = subprocess.run(
                [pip_path, 'install', '-r', requirements_file],
                capture_output=True,
                text=True,
                timeout=300,
                env=pip_install_env,
            )

            if result.returncode != 0:
                return False, f"Failed to install requirements:\n{result.stderr}"

            return True, ""
        except Exception as e:
            return False, f"Error installing requirements: {str(e)}"

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
            pattern1 = r"cat\s+>\s+['\"]?([^'\"]+\.py)['\"]?\s+<<\s*'?(\w+)'?\s*\n(.*?)\n\2"
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

    def _get_package_from_module(self, module_name: str) -> Optional[str]:
        """Extract the package name (filtering out standard library)"""
        if not module_name:
            return None
        top_level = module_name.split('.')[0]
        # Skip PyPI validation if it's already filtered as stdlib in tracer
        if not self._is_valid_pypi_package(top_level):
            return None

        pypi_name = self.module_to_package.get(top_level, top_level)

        return pypi_name

    def _is_valid_pypi_package(self, package_name: str) -> bool:
        """
        Check if a package exists on PyPI using its JSON API.
        """
        import urllib.request
        import urllib.error

        if package_name in ['google', 'opentelemetry', 'upath', 'importlib_metadata']:
            return False

        pypi_name = self.module_to_package.get(package_name, package_name)
        url = f"https://pypi.org/pypi/{pypi_name}/json"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            return True
        except Exception as e:
            print(f"  [PyPI Check Warning] Network error checking '{pypi_name}': {e}. Assuming valid.")
            return True

    def _generate_trace_script(self, script: str) -> str:
        """Generate Python script that traces API calls utilizing trace_generator"""
        encoded_script = base64.b64encode(script.encode('utf-8')).decode('ascii')
        
        # 极简调用，彻底消除维护负担
        return trace_generator.get_script_trace_code(encoded_script)

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

            is_success = (result.returncode == 0) or ('[TRACE]' in result.stdout)
            return is_success, result.stdout, result.stderr
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
            args_list = call_record.get('args_list', [])
            kwargs_dict = call_record.get('kwargs_dict', {})
            lineno = call_record.get('line', 0)

            package = self._get_package_from_module(api_path)
            if not package:
                continue

            self.library_calls[package][api_path].append({
                'args_list': args_list,
                'kwargs_dict': kwargs_dict,
                'line': lineno,
                'file': filename
            })

    def extract_calls(self):
        """Main extraction function using ONLY dynamic tracing"""
        print(f"\n{'='*60}")
        print(f"Extracting Library Calls from: {self.script_path}")
        print(f"{'='*60}\n")

        # Start timing (excluding pip install)
        start_time = time.time()

        python_blocks = self._extract_script_content(self.script_path)
        work_dir = tempfile.mkdtemp(prefix="extract_api_calls_")
        venv_path = os.path.join(work_dir, '.venv')

        pip_install_time = 0

        try:
            print("  Creating virtual environment...")
            success, error = self._setup_venv(work_dir, '.venv')
            if not success:
                print(f"  ✗ Failed to create venv: {error}")
                return
            print("  ✓ Virtual environment created")

            print(f"  Installing requirements from: {self.requirements}")
            pip_start = time.time()
            success, error = self._install_requirements(str(self.requirements), venv_path)
            pip_install_time += time.time() - pip_start
            if not success:
                print(f"  ✗ Failed to install requirements: {error}")
                return
            print("  ✓ Requirements installed")

            for filename, code in python_blocks:
                print(f"\n  Tracing: {filename}")
                script_content = self._generate_trace_script(code)
                success, stdout, stderr = self._run_trace_script(script_content, venv_path)

                if success:
                    self._parse_trace_output(stdout, filename)
                    print(f"  ✓ Successfully traced {filename}")
                else:
                    print(f"  ✗ Trace failed: {stderr}")

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        total_calls = sum(len(calls) for lib_calls in self.library_calls.values()
                         for calls in lib_calls.values())
        print(f"\nExtracted {total_calls} library calls from {len(self.library_calls)} libraries")

        # Calculate elapsed time excluding pip install
        total_elapsed = time.time() - start_time
        execution_time = total_elapsed - pip_install_time
        self.execution_time = execution_time
        print(f"\n{'='*60}")
        print(f"Execution time (excluding pip install): {execution_time:.2f} seconds")
        print(f"{'='*60}")

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
                    args_tuple = tuple(call_info['args_list'])
                    kwargs_tuple = tuple(sorted((k, v) for k, v in call_info['kwargs_dict'].items()))
                    signature = ('call', api_name, args_tuple, kwargs_tuple)

                    if signature not in unique_apis:
                        unique_apis.add(signature)
                        api_call_records.append({
                            'api': api_name,
                            'args_list': call_info['args_list'],
                            'kwargs_dict': call_info['kwargs_dict'],
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

                args_str_list = record['args_list']
                kwargs_str_list = [f"{k}={v}" for k, v in record['kwargs_dict'].items()]
                all_args = ', '.join(args_str_list + kwargs_str_list)

                f.write(f'{api_name}({all_args})\n\n')


def main():
    if len(sys.argv) < 4:
        print("Usage: python extract_library_calls.py <script_path> <api_log_dir> <requirements>")
        print()
        print("Arguments:")
        print("  script_path  - Path to the script to analyze (can be .py or .sh)")
        print("  api_log_dir  - Directory to save API logs")
        print("  requirements - Path to requirements.txt file")
        sys.exit(1)

    script_path = sys.argv[1]
    api_log_dir = sys.argv[2]
    requirements = sys.argv[3]

    extractor = LibraryCallExtractor(script_path, api_log_dir, requirements)
    extractor.extract_calls()
    extractor.save_api_logs()

    print(f"\n{'='*60}")
    print("Library Call Extraction Complete!")
    print(f"API logs saved to: {api_log_dir}")
    print(f"Execution time (excluding pip install): {extractor.execution_time:.2f} seconds")
    print(f"{'='*60}")

    # Output execution time for parent process to capture
    print(f"EXTRACT_EXECUTION_TIME:{extractor.execution_time:.2f}")


if __name__ == "__main__":
    main()