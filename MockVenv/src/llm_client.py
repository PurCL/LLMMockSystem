# src/llm_client.py

import asyncio
import os
import json
import threading
import re
from claude_agent_sdk import query, ClaudeAgentOptions

os.environ['CLAUDE_CODE_USE_BEDROCK'] = '1'
os.environ['AWS_REGION'] = 'us-east-1'

async def _ask_claude_to_patch(traceback_text: str, recent_calls: list) -> str:
    recent_calls_str = "\n".join(recent_calls[-30:]) if recent_calls else "None"
    
    options = ClaudeAgentOptions(
        model='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        system_prompt=(
            "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
            "You are a machine-to-machine API. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
            "Analyze the crash and provide a JSON patch for the mock environment.\n\n"
            "RULES:\n"
            "1. Output ONLY a single JSON object. No markdown blocks, no explanations.\n"
            "2. If a mocked API returned an empty string causing Regex/Assertion failure, provide a realistic string.\n"
            "3. METHOD vs ATTRIBUTE EXPLICITNESS: If the traceback fails on a method call, your key MUST include parentheses (e.g., 'cursor.fetchall()'). If it fails on a property access, DO NOT use parentheses (e.g., 'cursor.description').\n"
            "4. STRICT SCHEMA ALIGNMENT: If you are mocking a database row (e.g., for fetchone() or fetchall()), you MUST ensure the order and data types of the values STRICTLY MATCH the columns defined in 'cursor.description'. Do not mix up emails, booleans, UUIDs, and password hashes! For example, if description is [id, email, is_active], your row MUST be [\"uuid-str\", \"a@b.com\", true] in that EXACT order.\n\n"
            "SCHEMA:\n"
            '{"env": {"KEY": "VAL"}, "api_responses": {"LOGICAL_PATH": VALUE}}\n'
        ),
        allowed_tools=[], 
        permission_mode='acceptEdits',
        cwd=os.getcwd(),
        max_turns=3
    )

    prompt = f"Traceback:\n{traceback_text}\n\nRecent Logical API Calls:\n{recent_calls_str}"
    
    final_result = '{"env": {}, "api_responses": {}}'
    async for message in query(prompt=prompt, options=options):
        if type(message).__name__ == "ResultMessage" and message.result:
            final_result = message.result
            
    return final_result

def analyze_crash(traceback_text: str, recent_calls: list = None) -> dict:
    if recent_calls is None: recent_calls = []
    result_container = []

    def _run_in_isolated_loop():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(_ask_claude_to_patch(traceback_text, recent_calls))
            result_container.append(("SUCCESS", res))
        except Exception as ex:
            result_container.append(("ERROR", str(ex)))
        finally:
            try: loop.close()
            except: pass

    try:
        t = threading.Thread(target=_run_in_isolated_loop)
        t.daemon = True 
        t.start()
        
        while t.is_alive():
            t.join(0.1)
            
        if result_container:
            status, value = result_container[0]
            if status == "SUCCESS":
                # 🚀 强化解析：提取 JSON 并剥离可能的 Markdown 标记
                clean_value = value.strip()
                # 移除 ```json 和 ```
                clean_value = re.sub(r'^```json\s*', '', clean_value)
                clean_value = re.sub(r'\s*```$', '', clean_value)
                
                # 尝试再次用正则抠出最外层大括号
                match = re.search(r'\{.*\}', clean_value, re.DOTALL)
                res_str = match.group(0) if match else clean_value
                
                try:
                    return json.loads(res_str)
                except Exception as json_err:
                    print("\n" + "!"*60)
                    print(f"🚨 [LLM Client 调试] JSON 解析依然失败！")
                    print(f"📌 解析文本: {res_str}")
                    print(f"📦 完整原始文本:\n{value}")
                    print("!"*60 + "\n")
                    return {"env": {}, "api_responses": {}}
            else:
                raise Exception(value)
        return {"env": {}, "api_responses": {}}
    except Exception as e:
        print(f"[LLM Client] 系统级故障: {e}")
        return {"env": {}, "api_responses": {}}