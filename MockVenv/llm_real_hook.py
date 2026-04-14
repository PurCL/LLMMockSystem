#!/usr/bin/env python3
import os
import sys
import json
import re
import threading
import atexit
from pathlib import Path

# =====================================================================
# 💾 State Management & Path Resolution
# =====================================================================
print(f"[⚙️ Ghost Engine] Execution mode: REAL (Trace-based)")

# 自动检测激活的虚拟环境路径
venv_path = os.environ.get("VIRTUAL_ENV")

# 兜底机制：如果没有 VIRTUAL_ENV 环境变量，但 sys.prefix 显示在虚拟环境中
if not venv_path and sys.prefix != getattr(sys, "base_prefix", sys.prefix):
    venv_path = sys.prefix

if venv_path:
    # 固定保存在 .venv 目录下
    API_LOG_FILE = os.path.join(venv_path, ".api_calls.json")
else:
    # 如果没有使用虚拟环境，则退回到当前目录的绝对路径
    API_LOG_FILE = os.path.abspath(".api_calls.json")

print(f"[⚙️ Ghost Engine] API log file: {API_LOG_FILE}")

# API call log for real mode
api_call_signatures = set()  # Fast lookup for existing signatures
log_lock = threading.Lock()  # Thread-safe logging

# Initialize log file (create empty file if it doesn't exist)
if not os.path.exists(API_LOG_FILE):
    try:
        with open(API_LOG_FILE, "w", encoding="utf-8") as f:
            pass  # Create empty file
    except Exception:
        pass

# =====================================================================
# 🎯 Fetch Requirements and Whitelist configuration paths from env
# =====================================================================
ALLOWED_MOCKS = set()
REQUIRED_PACKAGES = set()
req_file = os.environ.get("MOCK_REQ_FILE")

# =====================================================================
# 🗺️ PyPI Package Name to Import Name Mapping
# =====================================================================
KNOWN_ALIASES = {}

# Try to get mapping file path from environment variable first
MAPPING_FILE = os.environ.get("MOCK_MAPPING_FILE")

if MAPPING_FILE and os.path.exists(MAPPING_FILE):
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            KNOWN_ALIASES = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load mapping file: {e}")
else:
    raise FileNotFoundError(f"Mapping file not found at expected location: {MAPPING_FILE}")

def _resolve_import_name(pkg_name):
    """
    Resolve PyPI package name to actual import name.
    Try multiple normalization strategies to find the correct alias.

    Args:
        pkg_name: The package name to resolve (could be PyPI name or import name)

    Returns:
        The resolved import name, or the original name if no mapping found
    """
    # Normalize the package name for lookup
    normalized = pkg_name.lower().replace('-', '_')

    # Try direct lookup with normalized name
    if normalized in KNOWN_ALIASES:
        resolved = KNOWN_ALIASES[normalized]
        return resolved

    # Try with hyphen version
    hyphenated = pkg_name.lower().replace('_', '-')
    if hyphenated in KNOWN_ALIASES:
        resolved = KNOWN_ALIASES[hyphenated]
        return resolved

    # Try original case-insensitive lookup
    for key, value in KNOWN_ALIASES.items():
        if key.lower() == pkg_name.lower():
            return value

    # No mapping found, return original name
    return pkg_name

if req_file and os.path.exists(req_file):
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            # Extract the package name (ignoring version specifiers like ==, >=, etc.)
            match = re.match(r'^([A-Za-z0-9_\.-]+)', line)
            if match:
                raw_pkg = match.group(1)
                REQUIRED_PACKAGES.add(raw_pkg)  # Keep the exact PyPI name for version lookup

                # Normalize for internal mock routing (e.g., PyYAML -> pyyaml)
                pkg_normalized = raw_pkg.lower().replace('-', '_')
                ALLOWED_MOCKS.add(pkg_normalized)

                # Use the comprehensive resolver to find import name
                import_name = _resolve_import_name(raw_pkg)
                if import_name != raw_pkg and import_name != pkg_normalized:
                    ALLOWED_MOCKS.add(import_name)

# =====================================================================
# 🎯 Module Filtering
# =====================================================================
def _should_trace_module(module_name):
    """Check if a module should be traced based on ALLOWED_MOCKS"""
    if not module_name:
        return False

    if not ALLOWED_MOCKS:
        return False

    base_name = module_name.split('.')[0]

    # Blacklist of modules that should never be traced
    NEVER_TRACE = {
        # Python standard library
        'typing', 'typing_extensions', 'types', 'abc', 'collections',
        'functools', 'inspect', 'sys', 'os', 'builtins', 'io',
        're', 'threading', 'json', 'pathlib', 'atexit', 'enum',
        'dataclasses', 'datetime', 'warnings', 'logging', 'copy',
        'weakref', 'contextvars', 'asyncio', 'importlib',

        # Our hook system
        'llm_real_hook', 'llm_mock_hook', 'llm_client',

        # Pydantic internal modules (often too noisy)
        'pydantic_core', 'pydantic._internal', 'pydantic.fields',
        'pydantic.main', 'pydantic.types', 'pydantic.validators',

        # Starlette/FastAPI internal modules (only trace high-level APIs)
        'starlette._utils', 'starlette.datastructures', 'starlette.types',
        'starlette.concurrency', 'starlette.background',
        'fastapi._compat', 'fastapi.datastructures', 'fastapi.utils',
    }

    # Check if module is in blacklist
    # if base_name in NEVER_TRACE or module_name in NEVER_TRACE:
    #     return False

    # Skip internal submodules (anything with _internal or starting with _)
    # if '._internal' in module_name or '._{' in module_name:
    #     return False

    # Skip if any part of the module path starts with underscore
    # if any(part.startswith('_') for part in module_name.split('.')):
    #     return False

    # Check direct match
    if base_name in ALLOWED_MOCKS:
        return True

    # Check if any required package resolves to this import name
    for req_pkg in REQUIRED_PACKAGES:
        resolved_import = _resolve_import_name(req_pkg)
        if resolved_import == base_name:
            return True

    return False

# =====================================================================
# 📝 API Call Logging
# =====================================================================
def _log_api_call(api_signature, args_info=None, kwargs_info=None):
    """Log API call signature in real mode (thread-safe)"""
    # Skip if already logged
    if api_signature in api_call_signatures:
        return

    with log_lock:
        # Double-check after acquiring lock
        if api_signature in api_call_signatures:
            return

        api_call_signatures.add(api_signature)

        # Build the function call string with actual parameter values
        # Format: function_name(arg1=value1, arg2=value2, kwarg1=value1)
        params = []

        # Add positional arguments
        if args_info and isinstance(args_info, dict):
            for key, value in args_info.items():
                # Format value as Python literal
                if isinstance(value, str):
                    # Escape quotes and format as string literal
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    params.append(f'{key}="{escaped_value}"')
                elif isinstance(value, (int, float, bool, type(None))):
                    params.append(f'{key}={value}')
                else:
                    # For complex types, use the string representation
                    escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
                    params.append(f'{key}="{escaped_value}"')

        # Add keyword arguments
        if kwargs_info and isinstance(kwargs_info, dict):
            for key, value in kwargs_info.items():
                if isinstance(value, str):
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    params.append(f'{key}="{escaped_value}"')
                elif isinstance(value, (int, float, bool, type(None))):
                    params.append(f'{key}={value}')
                else:
                    escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
                    params.append(f'{key}="{escaped_value}"')

        # Build the final function call string
        params_str = ', '.join(params)
        call_string = f"{api_signature}({params_str})\n"

        # Append to file without reading it first
        try:
            with open(API_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(call_string)
                f.flush()  # Force flush to disk immediately
                os.fsync(f.fileno())  # Ensure OS writes to disk
            # Reduced verbosity - only print for the first few calls
            if len(api_call_signatures) <= 20:
                print(f"📝 [API Log] Recorded: {call_string.strip()}")
        except Exception as e:
            print(f"⚠️ [API Log] Failed to write log: {e}")

# =====================================================================
# 🔍 Caller Detection - Check if call is from user code
# =====================================================================
def _is_called_from_user_code(current_frame):
    """
    Check if the current library function is being called directly from user code.

    Returns True if the caller is from user code (not site-packages).
    Returns False if the caller is from another library (internal library call).
    """
    # Walk up the call stack to find the caller
    caller_frame = current_frame.f_back

    while caller_frame is not None:
        caller_filename = caller_frame.f_code.co_filename

        # Skip our hook system
        if caller_filename and ('llm_real_hook.py' in caller_filename or
                                 'llm_mock_hook.py' in caller_filename or
                                 'llm_client.py' in caller_filename):
            caller_frame = caller_frame.f_back
            continue

        # Check if caller is from site-packages (library code)
        if caller_filename:
            try:
                caller_path = Path(caller_filename).resolve()
                # If caller is in site-packages, this is an internal library call
                if 'site-packages' in caller_path.parts:
                    return False
                # If caller is in standard library (lib/python3.x/)
                if any(part.startswith('python3.') for part in caller_path.parts):
                    if 'site-packages' not in caller_path.parts:
                        return False
                # If we reach here, caller is likely user code
                return True
            except Exception:
                pass

        # Move to next frame in stack
        caller_frame = caller_frame.f_back

    # If we can't determine, default to False (don't log)
    return False

# =====================================================================
# 🔍 Trace Function - The Heart of the Instrumentation
# =====================================================================
def _trace_calls(frame, event, arg):
    """
    Trace function that intercepts all function calls in the Python VM.

    This function is called by the Python interpreter for every function call,
    line execution, return, and exception. We only care about 'call' events.

    IMPROVED: Now only logs calls that are made directly from user code,
    not internal library-to-library calls.
    """
    if event != 'call':
        return _trace_calls

    # Get the code object
    code = frame.f_code
    filename = code.co_filename
    func_name = code.co_name

    # Skip internal Python files, site-packages hooks, and standard library
    if not filename or filename.startswith('<'):
        return _trace_calls

    # Skip module initialization calls (this is a major source of noise)
    if func_name == '<module>':
        return _trace_calls

    # Convert to Path for easier manipulation
    try:
        file_path = Path(filename).resolve()
    except Exception:
        return _trace_calls

    # Skip files in our hook system
    if 'llm_real_hook.py' in filename or 'llm_mock_hook.py' in filename or 'llm_client.py' in filename:
        return _trace_calls

    # Check if this is a library function (in site-packages)
    is_library_function = 'site-packages' in file_path.parts

    if not is_library_function:
        # This is user code - we don't trace user code, only library calls
        return _trace_calls

    # Try to determine the module name from the frame
    module_name = frame.f_globals.get('__name__', '')

    # Check if we should trace this module
    if not _should_trace_module(module_name):
        return _trace_calls

    # ✨ NEW: Check if this call is from user code (not internal library call)
    # if not _is_called_from_user_code(frame):
    #     return _trace_calls

    # Skip magic methods and private functions (they're usually internal)
    if func_name.startswith('__') and func_name.endswith('__'):
        return _trace_calls

    if func_name.startswith('_'):
        return _trace_calls

    # Skip common internal/utility functions that aren't real API calls
    SKIP_FUNC_NAMES = {
        'model_validate', 'model_dump', 'dict', 'copy', 'update',
        'get', 'set', 'pop', 'items', 'keys', 'values',
        'append', 'extend', 'remove', 'clear',
    }
    if func_name in SKIP_FUNC_NAMES:
        return _trace_calls

    # Get the full function path
    # Try to get the class name if this is a method
    if 'self' in frame.f_locals:
        try:
            class_name = frame.f_locals['self'].__class__.__name__
            full_path = f"{module_name}.{class_name}.{func_name}"
        except Exception:
            full_path = f"{module_name}.{func_name}"
    elif 'cls' in frame.f_locals:
        try:
            class_name = frame.f_locals['cls'].__name__
            full_path = f"{module_name}.{class_name}.{func_name}"
        except Exception:
            full_path = f"{module_name}.{func_name}"
    else:
        full_path = f"{module_name}.{func_name}"

    # Get argument information - extract actual values instead of just counts
    try:
        args_count = code.co_argcount
        varnames = code.co_varnames[:args_count]

        # Extract actual argument values from frame locals
        args_dict = {}
        kwargs_dict = {}

        for var in varnames:
            if var not in ('self', 'cls') and var in frame.f_locals:
                try:
                    val = frame.f_locals[var]
                    # Serialize the value safely
                    if isinstance(val, (str, int, float, bool, type(None))):
                        args_dict[var] = val
                    elif isinstance(val, (list, tuple, dict)):
                        # Truncate large collections
                        args_dict[var] = str(val)[:100] + ('...' if len(str(val)) > 100 else '')
                    else:
                        args_dict[var] = f"<{type(val).__name__}>"
                except Exception:
                    args_dict[var] = "<unprintable>"

        # Get kwargs (keyword-only arguments)
        kwonlyargs = code.co_kwonlyargcount
        if kwonlyargs > 0:
            kwonly_varnames = code.co_varnames[args_count:args_count + kwonlyargs]
            for var in kwonly_varnames:
                if var in frame.f_locals:
                    try:
                        val = frame.f_locals[var]
                        if isinstance(val, (str, int, float, bool, type(None))):
                            kwargs_dict[var] = val
                        elif isinstance(val, (list, tuple, dict)):
                            kwargs_dict[var] = str(val)[:100] + ('...' if len(str(val)) > 100 else '')
                        else:
                            kwargs_dict[var] = f"<{type(val).__name__}>"
                    except Exception:
                        kwargs_dict[var] = "<unprintable>"

        # Log the call with actual argument values
        _log_api_call(full_path, args_info=args_dict, kwargs_info=kwargs_dict)
    except Exception:
        # If we can't get arg info, just log the signature without details
        _log_api_call(full_path)

    return _trace_calls

# =====================================================================
# 🎯 Install the Trace Hook
# =====================================================================
def _install_trace_hook():
    """Install the trace function to monitor all calls"""
    sys.settrace(_trace_calls)
    # Also set trace for all new threads
    threading.settrace(_trace_calls)
    print("[⚙️ Ghost Engine] Trace hook installed successfully!")
    print("[⚙️ Ghost Engine] All API calls to target modules will be logged.")

# =====================================================================
# 🧹 Cleanup on Exit
# =====================================================================
def _save_on_exit():
    """Print summary when the program exits"""
    print(f"\n[⚙️ Ghost Engine] Logged {len(api_call_signatures)} unique API calls to {API_LOG_FILE}")

atexit.register(_save_on_exit)

# =====================================================================
# 🚀 Auto-activate Tracing
# =====================================================================
_install_trace_hook()

print("[⚙️ Ghost Engine] Real mode hook ready!")
print(f"[⚙️ Ghost Engine] Tracing {len(ALLOWED_MOCKS)} target modules/packages")
