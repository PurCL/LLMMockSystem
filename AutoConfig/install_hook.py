# src/auto_install_hook.py
import sys
import os
import traceback
import subprocess
import shutil

_original_excepthook = sys.excepthook

def install_and_restart(packages):
    """Install packages in the current venv and restart the entire process, supporting uv for fast installation"""
    if not packages:
        return False
        
    print(f"\n[📦 Auto-Heal] Missing dependencies detected, preparing to install: {', '.join(packages)}")
    try:
        if shutil.which("uv"):
            print("[⚙️ Engine Check] uv fast package manager found, enabling full-speed installation mode...")
            cmd = ["uv", "pip", "install"] + packages
        else:
            cmd = [sys.executable, "-m", "pip", "install"] + packages

        subprocess.check_call(cmd)
        print(f"[✅ Auto-Heal] {packages} installed successfully! Hot-restarting process...\n" + "="*50)
        
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"[❌ Auto-Heal] Dependency installation failed: {e}")
        return False
    except Exception as e:
        print(f"[❌ Auto-Heal] Process restart failed: {e}")
        return False

def is_dependency_error(exc_type, exc_value):
    """Intelligently determine if it's a missing dependency error (including exceptions wrapped by third-party libraries)"""
    if issubclass(exc_type, ImportError): return True
    
    # Check exception chain (The above exception was the direct cause...)
    if getattr(exc_value, "__cause__", None) and isinstance(exc_value.__cause__, ImportError): return True
    if getattr(exc_value, "__context__", None) and isinstance(exc_value.__context__, ImportError): return True
    
    # Check error text characteristics (fallback mechanism)
    msg = str(exc_value).lower()
    if "pip install" in msg or "not installed" in msg or "no module named" in msg: return True
    
    return False

def _dependency_excepthook(exc_type, exc_value, exc_traceback):
    _original_excepthook(exc_type, exc_value, exc_traceback)
    
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)): 
        return
        
    if is_dependency_error(exc_type, exc_value):
        # Pass the complete traceback to the LLM, ensuring it can see key prompts like 'pip install pwdlib[argon2]'
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"\n[🤖 LLM Interception] Suspected missing dependency error caught! Handing over to Claude for intelligent analysis...")
        
        try:
            import llm_client
            packages = llm_client.analyze_missing_deps(tb_str)
            if packages:
                install_and_restart(packages)
            else:
                print("❌ [Fix Failed] Agent could not identify the packages to install.")
        except Exception as e: 
            print(f"⚠️ [System Error]: {e}")

sys.excepthook = _dependency_excepthook

# =====================================================================
# HTTP 500 Route-Level Interception
# =====================================================================
try:
    from starlette.routing import Route
    _original_route_handle = Route.handle

    async def _mock_route_handle(self, scope, receive, send):
        try:
            await _original_route_handle(self, scope, receive, send)
        except Exception as e:
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            print("\n" + "🔥"*25)
            print("🚨 [HTTP 500 Crash Stack Trace]")
            print(tb_str.strip())
            print("🔥"*25 + "\n")
            
            if is_dependency_error(type(e), e):
                print(f"[🤖 LLM Interception] Missing dependency triggered within route, handing over to Claude for analysis...")
                try:
                    import llm_client
                    packages = llm_client.analyze_missing_deps(tb_str)
                    if packages:
                        install_and_restart(packages)
                    else:
                        print("❌ [Fix Failed] Agent could not identify the packages to install.")
                except Exception as ex: 
                    print(f"⚠️ [System Error]: {ex}")
            
            os._exit(1)

    Route.handle = _mock_route_handle
    print("[LLM Auto-Fix] Route-level dependency auto-healing interceptor is ready.", file=sys.stderr)
except ImportError:
    pass