# src/llm_client.py

import asyncio
import os
import json
import threading
import re
from claude_agent_sdk import query, ClaudeAgentOptions

os.environ['CLAUDE_CODE_USE_BEDROCK'] = '1'
os.environ['AWS_REGION'] = 'us-east-1'

async def _ask_claude_for_deps(traceback_text: str) -> str:
    options = ClaudeAgentOptions(
        model='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        system_prompt=(
            "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
            "You are an AI assistant resolving Python dependency errors.\n"
            "Analyze the traceback to identify missing packages.\n"
            "CRITICAL: Translate the missing import name to the correct PyPI package name (e.g., 'import yaml' -> 'PyYAML', 'import cv2' -> 'opencv-python').\n\n"
            "RULES:\n"
            "1. Output ONLY a single JSON object. No markdown, no explanations.\n"
            "2. If it's a missing dependency, provide the correct pip package name in a list.\n"
            "3. If no dependency is missing, return an empty list.\n\n"
            "SCHEMA:\n"
            '{"packages_to_install": ["package_name"]}\n'
        ),
        allowed_tools=[], 
        permission_mode='acceptEdits',
        cwd=os.getcwd(),
        max_turns=3
    )

    prompt = f"Traceback:\n{traceback_text}"
    
    final_result = '{"packages_to_install": []}'
    async for message in query(prompt=prompt, options=options):
        if type(message).__name__ == "ResultMessage" and message.result:
            final_result = message.result
            
    return final_result

def analyze_missing_deps(traceback_text: str) -> list:
    """分析崩溃栈，返回需要安装的包名列表"""
    result_container = []

    def _run_in_isolated_loop():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(_ask_claude_for_deps(traceback_text))
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
                clean_value = value.strip()
                clean_value = re.sub(r'^```json\s*', '', clean_value)
                clean_value = re.sub(r'\s*```$', '', clean_value)
                
                match = re.search(r'\{.*\}', clean_value, re.DOTALL)
                res_str = match.group(0) if match else clean_value
                
                try:
                    data = json.loads(res_str)
                    return data.get("packages_to_install", [])
                except Exception as json_err:
                    print(f"🚨 [LLM Client 调试] JSON 解析失败: {res_str}")
                    return []
            else:
                print(f"🚨 [LLM Client] 请求失败: {value}")
        return []
    except Exception as e:
        print(f"[LLM Client] 系统级故障: {e}")
        return []