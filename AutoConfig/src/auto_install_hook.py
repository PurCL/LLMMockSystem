# src/auto_install_hook.py
import sys
import os
import traceback
import subprocess
import shutil

_original_excepthook = sys.excepthook

def install_and_restart(packages):
    """在当前 venv 安装包并重启整个进程，支持 uv 极速安装"""
    if not packages:
        return False
        
    print(f"\n[📦 自动自愈] 检测到缺失依赖，准备安装: {', '.join(packages)}")
    try:
        if shutil.which("uv"):
            print("[⚙️ 引擎检测] 发现 uv 极速包管理器，启用全速安装模式...")
            cmd = ["uv", "pip", "install"] + packages
        else:
            cmd = [sys.executable, "-m", "pip", "install"] + packages

        subprocess.check_call(cmd)
        print(f"[✅ 自动自愈] {packages} 安装完成！正在热重启进程...\n" + "="*50)
        
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"[❌ 自动自愈] 依赖安装失败: {e}")
        return False
    except Exception as e:
        print(f"[❌ 自动自愈] 进程重启失败: {e}")
        return False

def is_dependency_error(exc_type, exc_value):
    """智能判断是否为依赖缺失错误（包括被第三方库包装的异常）"""
    if issubclass(exc_type, ImportError): return True
    
    # 检查异常链 (The above exception was the direct cause...)
    if getattr(exc_value, "__cause__", None) and isinstance(exc_value.__cause__, ImportError): return True
    if getattr(exc_value, "__context__", None) and isinstance(exc_value.__context__, ImportError): return True
    
    # 检查报错文本特征 (兜底机制)
    msg = str(exc_value).lower()
    if "pip install" in msg or "not installed" in msg or "no module named" in msg: return True
    
    return False

def _dependency_excepthook(exc_type, exc_value, exc_traceback):
    _original_excepthook(exc_type, exc_value, exc_traceback)
    
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)): 
        return
        
    if is_dependency_error(exc_type, exc_value):
        # 传递完整报错栈给大模型，确保其能看到 'pip install pwdlib[argon2]' 这种关键提示
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"\n[🤖 LLM 拦截] 捕获到疑似依赖缺失错误！移交 Claude 智能解析...")
        
        try:
            import llm_client
            packages = llm_client.analyze_missing_deps(tb_str)
            if packages:
                install_and_restart(packages)
            else:
                print("❌ [修复失败] Agent 未能识别需要安装的包。")
        except Exception as e: 
            print(f"⚠️ [系统错误]: {e}")

sys.excepthook = _dependency_excepthook

# =====================================================================
# HTTP 500 路由级别拦截
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
            print("🚨 [HTTP 500 崩溃栈现场直击]")
            print(tb_str.strip())
            print("🔥"*25 + "\n")
            
            if is_dependency_error(type(e), e):
                print(f"[🤖 LLM 拦截] 接口内触发依赖缺失，移交 Claude 解析...")
                try:
                    import llm_client
                    packages = llm_client.analyze_missing_deps(tb_str)
                    if packages:
                        install_and_restart(packages)
                    else:
                        print("❌ [修复失败] Agent 未能识别需要安装的包。")
                except Exception as ex: 
                    print(f"⚠️ [系统错误]: {ex}")
            
            os._exit(1)

    Route.handle = _mock_route_handle
    print("[LLM Auto-Fix] 接口级别依赖自愈拦截器已就绪。", file=sys.stderr)
except ImportError:
    pass