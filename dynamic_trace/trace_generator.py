"""
Unified Trace Script Generator
Provides dynamically assembled tracing scripts for both Script-level and Boundary-level tracing.
Constructs scripts using string blocks to avoid runtime overhead inside sys.settrace.
"""

# ==========================================
# BLOCK 1: Imports and Utils
# ==========================================
BLOCK_IMPORTS = r'''#!/usr/bin/env python3
import sys
import os
import json
import base64
import inspect
import re
import importlib
import pickle
from unittest.mock import MagicMock
import threading
'''

BLOCK_SAFE_REPR = r'''
def safe_repr(val):
    try:
        if val is None or isinstance(val, (int, float, bool, str)):
            return repr(val)

        if isinstance(val, (list, tuple)):
            cleaned_elements = [safe_repr(v) for v in val]
            if isinstance(val, tuple):
                if len(cleaned_elements) == 1:
                    return f"({cleaned_elements[0]},)"
                return f"({', '.join(cleaned_elements)})"
            return f"[{', '.join(cleaned_elements)}]"
            
        if isinstance(val, dict):
            parts = [f"{safe_repr(k)}: {safe_repr(v)}" for k, v in val.items()]
            return f"{{{', '.join(parts)}}}"

        if isinstance(val, set):
            cleaned_elements = [safe_repr(v) for v in val]
            if not cleaned_elements:
                return "set()"
            return f"{{{', '.join(cleaned_elements)}}}"

        return '"<Unserializable_Object>"'
    except Exception:
        return '"<Unserializable_Object>"'
'''

# ==========================================
# BLOCK 2: Tracer Core Structure
# ==========================================
BLOCK_TRACER_HEADER = r'''
def create_tracer(<<<PARAMS>>>):
    recorded_apis = set()

    def tracer(frame, event, arg):
        if event != 'call':
            return tracer

        func_name = frame.f_code.co_name
        if func_name == '<module>':
            return tracer

        caller_frame = frame.f_back
        if not caller_frame:
            return tracer

        caller_mod = caller_frame.f_globals.get("__name__", "")
        if not caller_mod:
            return tracer

        raw_callee_mod = frame.f_globals.get("__name__", "")
        if not raw_callee_mod or raw_callee_mod.startswith("namedtuple_"):
            return tracer
            
        current_pkg = raw_callee_mod.split('.')[0]
        caller_file = caller_frame.f_code.co_filename
        caller_line = caller_frame.f_lineno
'''

# ==========================================
# BLOCK 3: Boundary Detection Strategies (Mutually Exclusive)
# ==========================================
BLOCK_FILTER_SCRIPT = r'''
        if current_pkg in sys.stdlib_module_names:
            return tracer
        if not caller_file or os.path.abspath(caller_file) not in user_file_paths:
            return tracer
'''

BLOCK_FILTER_BOUNDARY = r'''
        if not (caller_mod.startswith(source_pkg) and not raw_callee_mod.startswith(source_pkg)):
            return tracer
'''

# ==========================================
# BLOCK 4: Function Resolution & Path Assembly
# ==========================================
BLOCK_FUNC_RESOLUTION = r'''
        is_instance_method = False
        cls_obj = None

        if 'self' in frame.f_locals:
            cls_obj = frame.f_locals['self'].__class__
            is_instance_method = True
        elif 'cls' in frame.f_locals:
            cls_obj = frame.f_locals['cls']
            if not isinstance(cls_obj, type):
                cls_obj = None

        func_obj_trace = None
        if cls_obj:
            func_obj_trace = getattr(cls_obj, func_name, None)
            if not func_obj_trace:
                cls_obj = None
                is_instance_method = False
        else:
            func_obj_trace = frame.f_globals.get(func_name)

        qualname = getattr(func_obj_trace, '__qualname__', None) if func_obj_trace else None

        if qualname and '<locals>' in qualname:
            return tracer

        if qualname:
            root_obj_name = qualname.split('.')[0]
            if root_obj_name not in frame.f_globals:
                return tracer
        else:
            if func_name not in frame.f_globals:
                return tracer

        if qualname:
            if is_instance_method and '.' in qualname:
                parts = qualname.rsplit('.', 1)
                if parts[1] == '__init__':
                    api_signature = f"{raw_callee_mod}.{parts[0]}"
                else:
                    api_signature = f"{raw_callee_mod}.{parts[0]}().{parts[1]}"
            else:
                api_signature = f"{raw_callee_mod}.{qualname}"
        else:
            class_name = cls_obj.__name__ if cls_obj else ""
            if class_name:
                if func_name == '__init__':
                    api_signature = f"{raw_callee_mod}.{class_name}"
                elif is_instance_method:
                    api_signature = f"{raw_callee_mod}.{class_name}().{func_name}"
                else:
                    api_signature = f"{raw_callee_mod}.{class_name}.{func_name}"
            else:
                api_signature = f"{raw_callee_mod}.{func_name}"
'''

# ==========================================
# BLOCK 5: Arguments Extraction
# ==========================================
BLOCK_ARG_EXTRACTION = r'''
        if api_signature not in recorded_apis:
            recorded_apis.add(api_signature)

            try:
                try:
                    sig_trace = inspect.signature(func_obj_trace) if func_obj_trace else None
                except Exception:
                    sig_trace = None

                arg_info = inspect.getargvalues(frame)
                args_list = []
                kwargs_dict = {}

                # 探测函数是否带有 *args (不定长位置参数)
                has_varargs = bool(arg_info.varargs)

                for arg_name in arg_info.args:
                    if arg_name in ('self', 'cls'):
                        continue
                    val = arg_info.locals.get(arg_name)

                    is_pos_only = False
                    is_kw_only = False
                    if sig_trace and arg_name in sig_trace.parameters:
                        param = sig_trace.parameters[arg_name]
                        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                            is_pos_only = True
                        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                            is_kw_only = True
                        
                        if param.default is not inspect.Parameter.empty:
                            try:
                                if val == param.default:
                                    # [修复点 1]：如果它被迫要走位置参数(args_list)，绝不能跳过默认值，否则会导致坑位缺失
                                    if not is_pos_only and not (has_varargs and not is_kw_only):
                                        continue
                            except Exception:
                                pass
                    
                    # [核心修复 2]：只要函数带有 *args，它前面的所有非 keyword-only 参数必须锁死在 args_list 中
                    if is_pos_only or (has_varargs and not is_kw_only):
                        args_list.append(safe_repr(val))
                    else:
                        kwargs_dict[arg_name] = safe_repr(val)

                if has_varargs:
                    varargs_val = arg_info.locals.get(arg_info.varargs)
                    if isinstance(varargs_val, (tuple, list)):
                        for v in varargs_val:
                            args_list.append(safe_repr(v))

                if arg_info.keywords:
                    kwargs_val = arg_info.locals.get(arg_info.keywords)
                    if isinstance(kwargs_val, dict):
                        for k, v in kwargs_val.items():
                            kwargs_dict[k] = safe_repr(v)
                            
                # [修复点 3]：Python 的 getargvalues 会漏掉显式定义的 KEYWORD_ONLY 参数，需要从 locals 里找回补齐
                if sig_trace:
                    for param_name, param in sig_trace.parameters.items():
                        if param.kind == inspect.Parameter.KEYWORD_ONLY:
                            if param_name in arg_info.locals:
                                val = arg_info.locals[param_name]
                                if param.default is not inspect.Parameter.empty:
                                    try:
                                        if val == param.default:
                                            continue
                                    except Exception:
                                        pass
                                kwargs_dict[param_name] = safe_repr(val)
                    
            except Exception as e:
                args_list = []
                kwargs_dict = {"error": f"Failed to extract args: {str(e)}"}
'''

# ==========================================
# BLOCK 6: Logging Formatting (Mutually Exclusive)
# ==========================================
BLOCK_LOGGING_SCRIPT = r'''
            call_record = {
                "api": api_signature,
                "caller": f"{caller_mod}.user_code", 
                "caller_file": caller_file,
                "args_list": args_list,
                "kwargs_dict": kwargs_dict,
                "line": caller_line
            }
            print(f"[TRACE]{json.dumps(call_record)}", flush=True)

        return tracer
    return tracer
'''

BLOCK_LOGGING_BOUNDARY = r'''
            call_record = {
                "type": "call",
                "downstream_package": current_pkg,
                "downstream_api": api_signature,
                "called_by": f"{caller_mod}.{caller_frame.f_code.co_name}",
                "args_list": args_list,
                "kwargs_dict": kwargs_dict
            }
            print(f"[BOUNDARY_CALL]{json.dumps(call_record)}", flush=True)

        return tracer
    return tracer
'''

# ==========================================
# BLOCK 7: Main Execution Runners
# ==========================================
BLOCK_MAIN_SCRIPT = r'''
def main():
    try:
        user_script_path = os.path.abspath("user_script.py")
        user_file_paths = {user_script_path}

        encoded_script = "<<<ENCODED_SCRIPT>>>"
        user_code = base64.b64decode(encoded_script).decode('utf-8')

        tracer = create_tracer(user_file_paths=user_file_paths)
        threading.settrace(tracer)
        sys.settrace(tracer)
        
        globals_dict = {'__name__': '__main__'}
        exec(compile(user_code, user_script_path, 'exec'), globals_dict)
        
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

BLOCK_MAIN_BOUNDARY = r'''
def get_api_object(api_path: str, tracer_func=None):
    def traced_import(mod_name):
        original_trace = sys.gettrace()
        if tracer_func:
            sys.settrace(tracer_func)
        try:
            return importlib.import_module(mod_name)
        finally:
            if tracer_func:
                sys.settrace(original_trace)

    parts = api_path.split('.')
    if len(parts) == 1:
        return traced_import(parts[0].replace('()', ''))

    for i in range(len(parts) - 1, 0, -1):
        mod_name = '.'.join(parts[:i])
        attr_parts = parts[i:]
        try:
            obj = traced_import(mod_name)
            for attr in attr_parts:
                clean_attr = attr.replace('()', '')
                obj = getattr(obj, clean_attr)
            return obj
        except (ModuleNotFoundError, AttributeError):
            continue
            
    return traced_import(api_path.replace('()', ''))

def generate_mock_kwargs(func_obj):
    kwargs = {}
    try:
        sig = inspect.signature(func_obj)
        for name, param in sig.parameters.items():
            if param.default == inspect.Parameter.empty and param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                kwargs[name] = MagicMock()
    except Exception:
        pass
    return kwargs

def sanitize_execution_args(func_obj, args_list, kwargs_dict):
    try:
        sig = inspect.signature(func_obj)
        bound_args = list(args_list)
        remaining_kwargs = kwargs_dict.copy()
        
        for name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                if name in remaining_kwargs:
                    bound_args.append(remaining_kwargs.pop(name))
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                if name in remaining_kwargs:
                    var_args = remaining_kwargs.pop(name)
                    if isinstance(var_args, (list, tuple)):
                        bound_args.extend(var_args)
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                if name in remaining_kwargs:
                    var_kwargs = remaining_kwargs.pop(name)
                    if isinstance(var_kwargs, dict):
                        remaining_kwargs.update(var_kwargs)
        return bound_args, remaining_kwargs
    except Exception:
        return args_list, kwargs_dict

def main():
    api_path = <<<CALLEE>>>
    source_pkg = <<<PACKAGE>>>
    args = pickle.loads(base64.b64decode("<<<ARGS_B64>>>"))
    kwargs = pickle.loads(base64.b64decode("<<<KWARGS_B64>>>"))

    tracer = create_tracer(source_pkg=source_pkg)

    def execute_with_trace(*run_args, **run_kwargs):
        original_trace = sys.gettrace()
        try:
            threading.settrace(tracer)
            sys.settrace(tracer)
            func_obj(*run_args, **run_kwargs)
            return True, "Execution completed normally"
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}"
        finally:
            sys.settrace(original_trace)

    try:
        func_obj = get_api_object(api_path, tracer)
    except Exception as e:
        sys.stderr.write(f"Import error: {str(e)}\n")
        sys.exit(3)

    if func_obj is None or not callable(func_obj):
        sys.stderr.write(f"{api_path} is not callable or not found\n")
        sys.exit(1)

    clean_args, clean_kwargs = sanitize_execution_args(func_obj, args, kwargs)
    success, msg = execute_with_trace(*clean_args, **clean_kwargs)

    if not success:
        sys.stderr.write(f"Original args failed with: {msg}. Retrying with MagicMock...\n")
        mock_kwargs = generate_mock_kwargs(func_obj)
        success_mock, msg_mock = execute_with_trace(**mock_kwargs)

        if not success_mock:
            sys.stderr.write(f"Mock args also failed with: {msg_mock}\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
'''


# ==========================================
# PUBLIC API: Assembly Methods
# ==========================================

def get_script_trace_code(encoded_script: str) -> str:
    """Assembles the tracing script tailored for extract_library_calls (Script Execution)"""
    tracer_code = (
        BLOCK_IMPORTS +
        BLOCK_SAFE_REPR +
        BLOCK_TRACER_HEADER.replace("<<<PARAMS>>>", "user_file_paths=None") +
        BLOCK_FILTER_SCRIPT +
        BLOCK_FUNC_RESOLUTION +
        BLOCK_ARG_EXTRACTION +
        BLOCK_LOGGING_SCRIPT +
        BLOCK_MAIN_SCRIPT
    )
    return tracer_code.replace("<<<ENCODED_SCRIPT>>>", encoded_script)

def get_boundary_trace_code(callee: str, package: str, args_b64: str, kwargs_b64: str) -> str:
    """Assembles the tracing script tailored for verify_compatible_package_versions (Boundary Inspection)"""
    tracer_code = (
        BLOCK_IMPORTS +
        BLOCK_SAFE_REPR +
        BLOCK_TRACER_HEADER.replace("<<<PARAMS>>>", "source_pkg=None") +
        BLOCK_FILTER_BOUNDARY +
        BLOCK_FUNC_RESOLUTION +
        BLOCK_ARG_EXTRACTION +
        BLOCK_LOGGING_BOUNDARY +
        BLOCK_MAIN_BOUNDARY
    )
    
    return tracer_code.replace(
        "<<<CALLEE>>>", repr(callee)
    ).replace(
        "<<<PACKAGE>>>", repr(package)
    ).replace(
        "<<<ARGS_B64>>>", args_b64
    ).replace(
        "<<<KWARGS_B64>>>", kwargs_b64
    )