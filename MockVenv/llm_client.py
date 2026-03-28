import asyncio
import os
import json
import threading
import re
from claude_agent_sdk import query, ClaudeAgentOptions

# Global environment configuration
os.environ['CLAUDE_CODE_USE_BEDROCK'] = '1'
os.environ['AWS_REGION'] = 'us-east-1'

# =====================================================================
# ⚙️ Core Async Runner
# =====================================================================
def _run_sync(async_func, *args, **kwargs):
    """Universal sync-to-async executor. Isolates the event loop to prevent RuntimeError."""
    result_container = []

    def _run_in_isolated_loop():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(async_func(*args, **kwargs))
            result_container.append(("SUCCESS", res))
        except Exception as ex:
            result_container.append(("ERROR", str(ex)))
        finally:
            try: loop.close()
            except: pass

    t = threading.Thread(target=_run_in_isolated_loop)
    t.daemon = True 
    t.start()
    
    while t.is_alive():
        t.join(0.1)
        
    if result_container:
        status, value = result_container[0]
        if status == "SUCCESS": return value
        else: raise Exception(value)
    raise Exception("Thread execution failed without returning a result.")

# =====================================================================
# 🛠️ Base LLM Communication Channel
# =====================================================================
async def _ask_claude(prompt: str, system_prompt: str) -> str:
    options = ClaudeAgentOptions(
        model='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        system_prompt=system_prompt,
        allowed_tools=[], 
        permission_mode='acceptEdits',
        cwd=os.getcwd(),
        max_turns=3
    )

    final_result = ''
    async for message in query(prompt=prompt, options=options):
        if type(message).__name__ == "ResultMessage" and message.result:
            final_result = message.result
            
    return final_result

# =====================================================================
# 🚀 Business Logic 1: Dynamic API Feature Generation (For llm_mock_hook.py)
# =====================================================================
def API_feature(traceback_text: str, recent_calls: list = None) -> dict:
    if recent_calls is None: recent_calls = []
    recent_calls_str = "\n".join(recent_calls[-30:]) if recent_calls else "None"
    
    # System prompt explicitly demands JSON only
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a machine-to-machine API. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
        "Output ONLY a single JSON object. No markdown blocks, no explanations."
    )
    prompt = f"Traceback:\n{traceback_text}\n\nRecent Logical API Calls:\n{recent_calls_str}"

    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt)
        
        # Clean and parse the JSON response
        clean_value = raw_response.strip()
        clean_value = re.sub(r'^```json\s*', '', clean_value)
        clean_value = re.sub(r'\s*```$', '', clean_value)
        match = re.search(r'\{.*\}', clean_value, re.DOTALL)
        res_str = match.group(0) if match else clean_value
        
        return json.loads(res_str)
    except Exception as e:
        print(f"[LLM Client Warning] API feature generation failed: {e}")
        return {}

# =====================================================================
# 🚀 Business Logic 2: Dependency Version Inference (For generate_dockerfiles.py)
# =====================================================================
def infer_versions(prompt: str) -> list:
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a machine-to-machine API. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
        "Output ONLY a single JSON array of strings representing compatible versions. "
        "Do NOT wrap it in markdown blockquotes (like ```json)."
    )
    
    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt)
        
        # Clean and parse the JSON array response
        clean_value = raw_response.strip()
        clean_value = re.sub(r'^```[a-zA-Z]*\n', '', clean_value)
        clean_value = re.sub(r'\n```$', '', clean_value)
        match = re.search(r'\[.*\]', clean_value, re.DOTALL)
        res_str = match.group(0) if match else clean_value
        
        valid_versions = json.loads(res_str)
        if isinstance(valid_versions, list):
            return valid_versions
        raise ValueError("LLM did not return a valid list.")
    except Exception as e:
        print(f"   ❌ [LLM Error] Failed to infer versions: {e}")
        return []