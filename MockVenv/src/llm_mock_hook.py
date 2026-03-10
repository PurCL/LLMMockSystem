# src/llm_mock_hook.py
import sys
import os
import json
import types
import traceback
from importlib.machinery import ModuleSpec

STATE_FILE = ".mock_state.json"
mock_state = {"env": {}, "api_responses": {}}

if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            mock_state = json.load(f)
    except Exception:
        pass

for key, value in mock_state.get("env", {}).items():
    if key not in os.environ:
        os.environ[key] = str(value)

# =====================================================================
# 🛡️ 底层框架白名单 (绝对不能自动 Mock 的可选依赖)
# =====================================================================
IGNORED_MODULES = {
    # 测试与系统底层
    'pytest', '_pytest', 'pluggy', 'mock', 'unittest',
    
    # 网络与异步底层框架
    'brotli', 'brotlicffi', 'backports', 'h2', 'socksio', 'trio',
    'ujson', 'orjson', 'uvloop', 'httptools', 'websockets', 'watchfiles',
    'colorama', 'dotenv', 'yaml', 'jinja2', 'cryptography',
    
    # 🚨 Claude SDK / jsonschema / OpenAPI 等底层库的格式校验全家桶
    'zstandard', 'fqdn', 'rfc3987', 'rfc3339_validator', 'webcolors',
    'jsonpointer', 'uri_template', 'isoduration', 'jsonschema',
    'rfc3986_validator', 'rfc3987_syntax', 'strict_rfc3339', 'aniso8601'
}

# =====================================================================
# 📸 1. 逻辑签名记录仪
# =====================================================================
_recent_mock_calls = []

def _get_logical_signature(name, args=None, kwargs=None):
    """生成逻辑签名：例如 'psycopg.paramstyle' 或 'cursor.execute("SELECT...")'"""
    if args is None and kwargs is None:
        return name # 属性访问路径
    
    # 方法调用：包含参数序列化
    # 限制长度防止 Key 过大，同时保证基本的参数区分度
    arg_reprs = [repr(a)[:50] for a in (args or [])]
    kwarg_reprs = [f"{k}={repr(v)[:50]}" for k, v in (kwargs or {}).items()]
    signature = f"{name}({', '.join(arg_reprs + kwarg_reprs)})"
    return signature

def _track_and_get_mock(sig_key):
    _recent_mock_calls.append(sig_key)
    if len(_recent_mock_calls) > 100: 
        _recent_mock_calls.pop(0)
    
    res = mock_state.get("api_responses", {})
    
    # 1. 完整逻辑签名匹配 (连同参数一起精确命中)
    if sig_key in res: 
        return res[sig_key]
        
    # 2. 降级匹配: 提取基础 API 路径
    base_name = sig_key.split('(')[0]
    
    # 尝试匹配无括号版 (针对属性)
    if base_name in res: 
        return res[base_name]
        
    # 尝试匹配带空括号版 (完美接住 Claude 刚才生成的泛型补丁)
    if f"{base_name}()" in res: 
        return res[f"{base_name}()"]
        
    # 3. 终极降级: 连前面的模块名都不管了，只看最后的方法名
    api_name = base_name.split('.')[-1]
    if api_name in res:
        return res[api_name]
    if f"{api_name}()" in res:
        return res[f"{api_name}()"]
            
    return None

# =====================================================================
# 👻 2. 静态幽灵引擎 (逻辑驱动版)
# =====================================================================
class LLMMockProxy(str):
    def __new__(cls, name):
        return super().__new__(cls, "") # 默认依然是空字符串

    def __init__(self, name):
        self._name = name
        
    def __getattr__(self, item):
        if item in ('__path__', '__file__', '__spec__', '__class__', '__mro__', '__name__'):
            if item == '__name__': return self._name
            raise AttributeError(item)
            
        full_path = f"{self._name}.{item}"
        sig_key = _get_logical_signature(full_path) # 记录变量名路径
        
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
        sig_key = _get_logical_signature(self._name, args, kwargs) # 记录 API+参数
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
        sig_key = _get_logical_signature(full_path) # 🚀 统一使用逻辑签名
        
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
        
        # 🚨 核心修复：绝对不能 Mock Python 官方标准库！
        # 这样 msvcrt 就会被正常放行并报 ImportError，Python 就会乖乖走 Linux 分支了
        if hasattr(sys, 'stdlib_module_names') and base_name in sys.stdlib_module_names:
            return None
            
        # 排除那些绝不能自动 Mock 的底层 Web/异步框架
        if base_name in IGNORED_MODULES:
            return None
            
        print(f"[⚙️ 幽灵引擎] 自动假装成功导入未安装包: '{fullname}'")
        return ModuleSpec(fullname, GhostLoader(fullname))

# 挂载到最后，只有真实环境找不到的包才会落入黑洞
sys.meta_path.append(GhostFinder())

# =====================================================================
# 🚑 3. 自愈机制与状态更新
# =====================================================================
def _update_state_and_save(patch):
    print(f"✨ [修复成功] 发现缺失项并已生成补丁: {patch}")
    new_state = {
        "env": mock_state.get("env", {}),
        "api_responses": mock_state.get("api_responses", {})
    }
    new_state["env"].update(patch.get("env", {}))
    new_state["api_responses"].update(patch.get("api_responses", {}))
    
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=4)
    print(f"✅ 补丁已写入 {STATE_FILE}。")

_original_excepthook = sys.excepthook

def _mock_excepthook(exc_type, exc_value, exc_traceback):
    _original_excepthook(exc_type, exc_value, exc_traceback)
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)): return
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)[-30:])

    print(f"\n[🤖 LLM Mock] 进程崩溃！移交 Claude (附带最近 API 拦截录像)...")
    try:
        import llm_client
        patch = llm_client.analyze_crash(tb_str, _recent_mock_calls)
        if patch.get("env") or patch.get("api_responses"):
            _update_state_and_save(patch)
        else:
            print("❌ [修复失败] Agent 未能识别修复方案。")
    except Exception as e: print(f"⚠️ [系统错误]: {e}")

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
            
            # 🚨 新增：在移交大模型之前，先把 500 错误栈原原本本地展示给你看！
            print("\n" + "🔥"*25)
            print("🚨 [HTTP 500 崩溃栈现场直击]")
            print(tb_str.strip())
            print("🔥"*25 + "\n")
            
            print(f"[🤖 LLM Mock] 正在将上述崩溃信息与 API 录像移交 Claude...")
            try:
                import llm_client
                patch = llm_client.analyze_crash(tb_str, _recent_mock_calls)
                if patch.get("env") or patch.get("api_responses"):
                    _update_state_and_save(patch)
                    print("🛑 [LLM Mock] 补丁已生成！正在强行终止服务器，请直接按 [上箭头 + Enter] 重启！")  
                else:
                    print("❌ [修复失败] Agent 未能识别修复方案。")
            except Exception as ex: 
                print(f"⚠️ [系统错误]: {ex}")
            
            import os
            os._exit(1)

    Route.handle = _mock_route_handle
    print("[LLM Mock] 接口级别 500 错误自愈拦截器已就绪。")
except ImportError:
    pass