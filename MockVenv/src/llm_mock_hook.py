# src/llm_mock_hook.py
import sys
import os
import json
import types
import traceback
from importlib.machinery import ModuleSpec
import subprocess
import socket
import time
import atexit
import importlib.metadata

# =====================================================================
# 🐳 Dynamic Infrastructure: Auto-detect free ports and spin up a real PostgreSQL container
# =====================================================================
def _get_free_port():
    """Detect and return an available free port on the local machine"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def _wait_for_db_ready(container_name, timeout=20):
    """Poll pg_isready via docker exec to ensure the database is truly ready to accept connections"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = subprocess.run(
            ["docker", "exec", container_name, "pg_isready", "-U", "postgres"],
            capture_output=True
        )
        if res.returncode == 0:
            return True
        time.sleep(0.5)
    return False

def _cleanup_container(container_name):
    """Cleanup hook upon process exit to destroy the temporary container"""
    print(f"\n[⚙️ Ghost Engine] Process exiting, destroying temporary database container {container_name}...")
    subprocess.run(["docker", "stop", container_name], capture_output=True, check=False)

def _setup_dynamic_mock_db():
    # Prevent Uvicorn's worker processes from repeatedly spinning up containers
    if os.environ.get("_DYNAMIC_DB_STARTED"):
        return

    # 1. Strict Docker availability test
    try:
        # Using 'docker ps' not only checks if the command exists but also if the Daemon is running
        res = subprocess.run(["docker", "ps"], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("[⚙️ Ghost Engine] ⚠️ 'docker' command not found! PATH environment variable might not include ~/.local/bin")
        return
    except subprocess.CalledProcessError as e:
        print(f"[⚙️ Ghost Engine] ⚠️ Docker command found, but unable to connect to Daemon!\nError message: {e.stderr.strip()}")
        print("[⚙️ Ghost Engine] 💡 Tip: If using Rootless Docker, ensure you have run: systemctl --user start docker")
        print("[⚙️ Ghost Engine] 💡 Tip: And ensure DOCKER_HOST is set (e.g., export DOCKER_HOST=unix:///run/user/1000/docker.sock)")
        return
    except Exception as e:
        print(f"[⚙️ Ghost Engine] ⚠️ Unknown error occurred during Docker detection: {e}")
        return

    # 2. Database spin-up logic (If you reach here, your Rootless Docker is fully operational)
    port = _get_free_port()
    container_name = f"llm-mock-postgres-{port}"
    
    print(f"[⚙️ Ghost Engine] 🎯 Free port {port} locked, spinning up PostgreSQL container using Docker...")
    
    cmd = [
        "docker", "run", "-d", "--rm",
        "--name", container_name,
        "-e", "POSTGRES_USER=postgres",
        "-e", "POSTGRES_PASSWORD=changethis",
        "-e", "POSTGRES_DB=app",
        "-p", f"{port}:5432",
        "postgres:14"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        atexit.register(_cleanup_container, container_name)
    except subprocess.CalledProcessError as e:
        print(f"[⚙️ Ghost Engine] ⚠️ Container startup failed: {e.stderr.decode('utf-8')}")
        return

    print("[⚙️ Ghost Engine] ⏳ Waiting for PostgreSQL engine to initialize...")
    if _wait_for_db_ready(container_name):
        print(f"[⚙️ Ghost Engine] ✅ Database ready! Dynamically binding environment variables (Port: {port})...")
        os.environ["POSTGRES_SERVER"] = "localhost"
        os.environ["POSTGRES_PORT"] = str(port)
        os.environ["POSTGRES_USER"] = "postgres"
        os.environ["POSTGRES_PASSWORD"] = "changethis"
        os.environ["POSTGRES_DB"] = "app"
        
        db_url = f"postgresql+psycopg2://postgres:changethis@localhost:{port}/app"
        os.environ["SQLALCHEMY_DATABASE_URI"] = db_url
        os.environ["DATABASE_URL"] = db_url
        os.environ["_DYNAMIC_DB_STARTED"] = "1"
    else:
        print("[⚙️ Ghost Engine] ❌ Database startup timeout!")
        return

# Execute spin-up logic immediately
_setup_dynamic_mock_db()

STATE_FILE = ".mock_state.json"
mock_state = {"env": {}, "mocked_imports": {}, "core_imports": {}}

if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            mock_state = json.load(f)
    except Exception:
        pass

# =====================================================================
# 📦 Real Dependency Scanner: Record all core libraries installed in the current venv and their versions
# =====================================================================
def _record_core_imports():
    """Scan the real installed packages in the virtual environment and record them in core_imports"""
    try:
        # Get all installed packages and their versions in the current environment
        installed_packages = {
            dist.metadata["Name"]: dist.version 
            for dist in importlib.metadata.distributions()
        }
        
        # To prevent useless disk writes on every startup, only write when the dependency list changes
        if mock_state.get("core_imports") != installed_packages:
            mock_state["core_imports"] = installed_packages
            with open(STATE_FILE, "w") as f:
                json.dump(mock_state, f, indent=4)
    except Exception as e:
        print(f"[⚙️ Ghost Engine] ⚠️ Failed to record core dependencies: {e}")

# Execute scan immediately
_record_core_imports()

for key, value in mock_state.get("env", {}).items():
    if key not in os.environ:
        os.environ[key] = str(value)

# =====================================================================
# 📦 Dependency Recorder: Organize API Responses under Package dimensions
# =====================================================================
def _record_mocked_import(fullname):
    """Record the mocked package and initialize its api_responses container"""
    base_name = fullname.split('.')[0] # Extract top-level package name
    
    if base_name not in mock_state["mocked_imports"]:
        mock_state["mocked_imports"][base_name] = {"api_responses": {}}
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(mock_state, f, indent=4)
        except Exception:
            pass


# =====================================================================
# 🛡️ Underlying Framework Whitelist (Optional dependencies that absolutely MUST NOT be auto-mocked)
# =====================================================================
IGNORED_MODULES = {
    # Testing and system fundamentals
    'pytest', '_pytest', 'pluggy', 'mock', 'unittest',
    
    # Network and async underlying frameworks
    'brotli', 'brotlicffi', 'backports', 'h2', 'socksio', 'trio',
    'ujson', 'orjson', 'uvloop', 'httptools', 'websockets', 'watchfiles',
    'colorama', 'dotenv', 'yaml', 'jinja2', 'cryptography', 'sniffio'
    
    # 🚨 Format validation suites for Claude SDK / jsonschema / OpenAPI, etc.
    'zstandard', 'fqdn', 'rfc3987', 'rfc3339_validator', 'webcolors',
    'jsonpointer', 'uri_template', 'isoduration', 'jsonschema',
    'rfc3986_validator', 'rfc3987_syntax', 'strict_rfc3339', 'aniso8601', 'rich', 'anyio'
}

# =====================================================================
# 📸 1. Logical Signature Recorder
# =====================================================================
_recent_mock_calls = []

def _get_logical_signature(name, args=None, kwargs=None):
    """Generate logical signature: e.g., 'psycopg.paramstyle' or 'cursor.execute("SELECT...")'"""
    if args is None and kwargs is None:
        return name # Attribute access path
    
    # Method call: Includes parameter serialization
    # Limit length to prevent overly large Keys while maintaining basic parameter distinction
    arg_reprs = [repr(a)[:50] for a in (args or [])]
    kwarg_reprs = [f"{k}={repr(v)[:50]}" for k, v in (kwargs or {}).items()]
    signature = f"{name}({', '.join(arg_reprs + kwarg_reprs)})"
    return signature

def _track_and_get_mock(sig_key):
    _recent_mock_calls.append(sig_key)
    if len(_recent_mock_calls) > 100: 
        _recent_mock_calls.pop(0)

    # Extract top-level package name from the first segment of the logical signature (e.g., 'psycopg.cursor...' -> 'psycopg')
    root_pkg = sig_key.split('.')[0].split('(')[0]
    
    # Accurately look for responses under the package's dedicated namespace
    res = mock_state.get("mocked_imports", {}).get(root_pkg, {}).get("api_responses", {})
    
    # 1. Full logical signature match (exact match including parameters)
    if sig_key in res: 
        return res[sig_key]
        
    # 2. Downgrade match: Extract base API path
    base_name = sig_key.split('(')[0]
    
    # Try matching unparenthesized version (for attributes)
    if base_name in res: 
        return res[base_name]
        
    # Try matching empty parenthesis version (perfectly catching generic patches generated by Claude)
    if f"{base_name}()" in res: 
        return res[f"{base_name}()"]
        
    # 3. Ultimate downgrade: Ignore preceding module names entirely, just look at the final method name
    api_name = base_name.split('.')[-1]
    if api_name in res:
        return res[api_name]
    if f"{api_name}()" in res:
        return res[f"{api_name}()"]
            
    return None

# =====================================================================
# 👻 2. Static Ghost Engine (Logic-Driven Version)
# =====================================================================
class LLMMockProxy(str):
    def __new__(cls, name):
        return super().__new__(cls, "") # Default is still an empty string

    def __init__(self, name):
        self._name = name
        
    def __getattr__(self, item):
        if item in ('__path__', '__file__', '__spec__', '__class__', '__mro__', '__name__'):
            if item == '__name__': return self._name
            raise AttributeError(item)
            
        full_path = f"{self._name}.{item}"
        sig_key = _get_logical_signature(full_path) # Record variable name path
        
        mock_val = _track_and_get_mock(sig_key)
        if mock_val is not None:
            return mock_val
            
        if "Error" in item or "Exception" in item:
            class MockException(Exception): pass
            MockException.__name__ = item
            return MockException
            
        if item.startswith('__') and item.endswith('__'):
            raise AttributeError(item)
            
        return LLMMockProxy(full_path)
        
    def __call__(self, *args, **kwargs):
        sig_key = _get_logical_signature(self._name, args, kwargs) # Record API + parameters
        mock_val = _track_and_get_mock(sig_key)
        if mock_val is not None:
            return mock_val
        return LLMMockProxy(self._name)
        
    def __iter__(self): yield LLMMockProxy(f"{self._name}_item")
    def __getitem__(self, key): return LLMMockProxy(f"{self._name}[{key}]")
    def __len__(self): return 1
    def __bool__(self): return True
    def __str__(self): return ""
    def __repr__(self): return f"<StaticGhost: {self._name}>"

class GhostModule(types.ModuleType):
    def __getattr__(self, name):
        full_path = f"{self.__name__}.{name}"
        sig_key = _get_logical_signature(full_path) # 🚀 Uniformly use logical signature
        
        mock_val = _track_and_get_mock(sig_key)
        if mock_val is not None:
            return mock_val
            
        if "Error" in name or "Exception" in name:
            class MockException(Exception): pass
            MockException.__name__ = name
            return MockException
            
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
            
        return LLMMockProxy(full_path)

class GhostLoader:
    def __init__(self, fullname): self.fullname = fullname
    def create_module(self, spec):
        mod = GhostModule(self.fullname)
        mod.__path__ = []
        return mod
    def exec_module(self, module):
        module.__dict__.update({'__path__': []})

class GhostFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith('_') or fullname in sys.builtin_module_names:
            return None
            
        base_name = fullname.split('.')[0]
        
        # 🚨 Core Fix: Absolutely DO NOT mock Python official standard libraries!
        # This allows msvcrt to pass through normally, trigger ImportError, and force Python to obediently take the Linux branch
        if hasattr(sys, 'stdlib_module_names') and base_name in sys.stdlib_module_names:
            return None
            
        # Exclude underlying Web/Async frameworks that must never be auto-mocked
        if base_name in IGNORED_MODULES:
            return None
            
        print(f"[⚙️ Ghost Engine] Auto-pretending successful import of uninstalled package: '{fullname}'")

        # 🚨 New: Record intercepted packages and carve out their dedicated namespace in the state file
        _record_mocked_import(fullname)

        return ModuleSpec(fullname, GhostLoader(fullname))

# Mount at the very end; only packages not found in the real environment will fall into this black hole
sys.meta_path.append(GhostFinder())

# =====================================================================
# 🚑 3. Auto-Healing Mechanism & State Update
# =====================================================================
def _update_state_and_save(patch):
    """Receive patch from LLM and automatically distribute it to the corresponding Package's territory"""
    print(f"✨ [Fix Successful] Missing items detected and patch generated: {patch}")
    
    if "env" in patch:
        mock_state.setdefault("env", {}).update(patch["env"])
        
    if "api_responses" in patch:
        for sig_key, value in patch["api_responses"].items():
            # Intelligent routing: Infer which top-level package this API belongs to
            root_pkg = sig_key.split('.')[0].split('(')[0]
            
            # Forcefully ensure the package's directory tree exists
            pkg_entry = mock_state.setdefault("mocked_imports", {}).setdefault(root_pkg, {})
            api_dict = pkg_entry.setdefault("api_responses", {})
            
            # Archive write
            api_dict[sig_key] = value

    # Directly compatible if LLM smartly outputted a new hierarchical structure
    if "mocked_imports" in patch:
        for pkg_name, pkg_data in patch["mocked_imports"].items():
            pkg_entry = mock_state.setdefault("mocked_imports", {}).setdefault(pkg_name, {})
            if "api_responses" in pkg_data:
                pkg_entry.setdefault("api_responses", {}).update(pkg_data["api_responses"])
                
    with open(STATE_FILE, "w") as f:
        json.dump(mock_state, f, indent=4)
    print(f"✅ Patch smartly routed and written to {STATE_FILE}.")

_original_excepthook = sys.excepthook

def _mock_excepthook(exc_type, exc_value, exc_traceback):
    _original_excepthook(exc_type, exc_value, exc_traceback)
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)): return
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)[-30:])

    print(f"\n[🤖 LLM Mock] Process crashed! Handing over to Claude (with recent API interception recordings)...")
    try:
        import llm_client
        patch = llm_client.analyze_crash(tb_str, _recent_mock_calls)
        if patch.get("env") or patch.get("api_responses"):
            _update_state_and_save(patch)
        else:
            print("❌ [Fix Failed] Agent failed to identify a remediation plan.")
    except Exception as e: print(f"⚠️ [System Error]: {e}")

sys.excepthook = _mock_excepthook

try:
    from starlette.routing import Route
    _original_route_handle = Route.handle

    async def _mock_route_handle(self, scope, receive, send):
        try:
            await _original_route_handle(self, scope, receive, send)
        except Exception as e:
            import traceback
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__)[-30:])
            
            # 🚨 New: Show the raw 500 error stack trace before handing over to the LLM!
            print("\n" + "🔥"*25)
            print("🚨 [HTTP 500 Crash Stack Trace Live View]")
            print(tb_str.strip())
            print("🔥"*25 + "\n")
            
            print(f"[🤖 LLM Mock] Forwarding the above crash info and API recordings to Claude...")
            try:
                import llm_client
                patch = llm_client.analyze_crash(tb_str, _recent_mock_calls)
                if patch.get("env") or patch.get("api_responses"):
                    _update_state_and_save(patch)
                    print("🛑 [LLM Mock] Patch generated! Forcefully terminating server. Please press [Up Arrow + Enter] to restart!")  
                else:
                    print("❌ [Fix Failed] Agent failed to identify a remediation plan.")
            except Exception as ex: 
                print(f"⚠️ [System Error]: {ex}")
            
            import os
            os._exit(1)

    Route.handle = _mock_route_handle
    print("[LLM Mock] Route-level 500 error auto-healing interceptor is ready.")
except ImportError:
    pass