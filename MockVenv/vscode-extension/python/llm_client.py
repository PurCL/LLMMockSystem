import asyncio
import os
import json
import threading
import re
import traceback
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
            # Capture full exception details for better debugging
            error_details = f"{str(ex)}\n\nFull traceback:\n{traceback.format_exc()}"
            result_container.append(("ERROR", error_details))
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
async def _ask_claude(prompt: str, system_prompt: str, disable_write: bool = False, cwd: str = None) -> str:
    """
    Base async function to communicate with Claude.

    Args:
        prompt: The user prompt/query
        system_prompt: System instructions for Claude
        disable_write: If True, disables Write and other file creation tools
        cwd: Optional working directory for Claude Code (default: current directory)

    Returns:
        The final text response from Claude
    """
    # Check prompt size to avoid issues
    prompt_size = len(prompt)
    if prompt_size > 1000000:  # 1MB
        print(f"⚠️  Warning: Prompt is very large ({prompt_size} bytes), this may cause issues")

    # If prompt is too large, raise error early
    if prompt_size > 500000:  # 500KB limit for safety
        raise Exception(f"Prompt too large: {prompt_size} bytes (max 500KB). Please reduce trace file or project files size.")

    # Use provided cwd or default to current directory
    working_dir = cwd if cwd else os.getcwd()

    # Base configuration
    options_dict = {
        'model': 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'system_prompt': system_prompt,
        'allowed_tools': [],
        'permission_mode': 'acceptEdits',
        'cwd': working_dir,
        'max_turns': 3
    }

    # If write is disabled, add disallowed tools
    if disable_write:
        options_dict['disallowed_tools'] = [
            'Write',           # Prevent creating/overwriting files
            'Edit',            # Prevent editing existing files
            'NotebookEdit',    # Prevent editing notebooks
            'Bash',            # Prevent bash commands that could write files
        ]

    options = ClaudeAgentOptions(**options_dict)

    final_result = ''
    try:
        async for message in query(prompt=prompt, options=options):
            if type(message).__name__ == "ResultMessage" and message.result:
                final_result = message.result
    except Exception as e:
        # Provide more context about the error
        error_msg = f"Claude Agent SDK error: {str(e)}\nPrompt size: {prompt_size} bytes"
        # Try to extract more details from the exception
        if hasattr(e, '__cause__') and e.__cause__:
            error_msg += f"\nCause: {str(e.__cause__)}"
        raise Exception(error_msg) from e

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
def infer_versions(prompt: str, testscript_dir: str = None) -> list:
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a machine-to-machine API. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
        "Output ONLY a single JSON array of strings representing ALL compatible versions. "
        "Your goal is to return a BROAD VERSION RANGE, not just one or two versions. "
        "Include ALL versions that support the observed API patterns. "
        "Do NOT wrap it in markdown blockquotes (like ```json).\n\n"
        "IMPORTANT: If you need to generate test scripts or demo files to verify version compatibility, "
        "you MAY write them to the current working directory (testscript/). "
        "However, you MUST still return the JSON array in your final response. "
        "Do NOT generate documentation files (README.md, docs, etc.) or Dockerfiles."
    )

    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt, cwd=testscript_dir)

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


# =====================================================================
# 🚀 Business Logic 3: Dockerfile & README Generation (For resolve_dependencies.py)
# =====================================================================
def generate_dockerfile_content(combination: dict, base_image: str = "python:3.11-slim", project_path: str = None) -> dict:
    """
    Use LLM to generate Dockerfile and README content (WITHOUT writing files).

    Args:
        combination: dict {package_name: version}
        base_image: Docker base image to use
        project_path: Optional path to project directory for volume mounting

    Returns:
        dict with keys:
            - 'dockerfile': str (Dockerfile content)
            - 'readme_section': str (README section for this configuration)
    """
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a machine-to-machine API. YOU MUST NOT WRITE ANY FILES.\n"
        "You MUST NOT use Write, Edit, or any file writing tools.\n"
        "Output ONLY a single JSON object with the following structure:\n"
        "{\n"
        '  "dockerfile": "string containing the complete Dockerfile content",\n'
        '  "readme_section": "string containing the README section for this configuration"\n'
        "}\n"
        "Do NOT wrap it in markdown blockquotes (like ```json)."
    )

    # Build the prompt with package information
    packages_list = '\n'.join([f"  - {pkg}=={ver}" for pkg, ver in combination.items()])

    prompt = f"""Generate a Dockerfile and README section for the following configuration:

Base Image: {base_image}
Packages to install (with --no-deps flag):
{packages_list}

{"Project Path: " + project_path if project_path else "No project path specified"}

Requirements:
1. Dockerfile should:
   - Use FROM {base_image}
   - Set WORKDIR /app
   - Install packages with --no-deps flag (no transitive dependencies)
   - Use CMD ["tail", "-f", "/dev/null"] to keep container running
   - DO NOT include any application startup commands
   - The container should stay alive so users can exec into it

2. README section should include:
   - Configuration summary (which packages and versions)
   - Build command example
   - Run command examples:
     * Background run: docker run -d <image>
     * Interactive access: docker run -it <image> /bin/bash
     * Exec into running container: docker exec -it <container_id> /bin/bash
   - {"Volume mount instructions with absolute path: " + project_path if project_path else "Note that users can mount volumes as needed"}
   - Important notes about --no-deps flag
   - Emphasize that the container is meant for manual interaction, not automatic execution

Output as JSON with keys "dockerfile" and "readme_section".
"""

    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt, disable_write=True)

        # Clean and parse the JSON response
        clean_value = raw_response.strip()
        clean_value = re.sub(r'^```json\s*', '', clean_value)
        clean_value = re.sub(r'^```\s*', '', clean_value)
        clean_value = re.sub(r'\s*```$', '', clean_value)
        match = re.search(r'\{.*\}', clean_value, re.DOTALL)
        res_str = match.group(0) if match else clean_value

        result = json.loads(res_str)

        # Validate the response structure
        if not isinstance(result, dict) or 'dockerfile' not in result or 'readme_section' not in result:
            raise ValueError("LLM response missing required keys")

        return result

    except Exception as e:
        print(f"   ❌ [LLM Error] Failed to generate Dockerfile content: {e}")
        # Fallback: return empty template
        return {
            "dockerfile": f"FROM {base_image}\nWORKDIR /app\n# Error generating content\n",
            "readme_section": "# Configuration failed to generate\n"
        }


# =====================================================================
# 🚀 Business Logic 4: API Pattern Analysis (For resolve_dependencies.py)
# =====================================================================
def analyze_api_patterns(prompt: str, testscript_dir: str = None) -> dict:
    """
    Use LLM to analyze API patterns and provide version constraint hints.

    This is a general-purpose analyzer that works for any package by leveraging
    LLM's knowledge of package version histories and API evolution patterns.

    Args:
        prompt: The analysis prompt containing package info and API signatures
        testscript_dir: Optional directory for test scripts (if Claude Code needs to write files)

    Returns:
        dict with keys:
            - 'detected_patterns': list of pattern strings
            - 'version_constraints': suggested constraint or None
            - 'confidence': 'high', 'medium', or 'low'
            - 'reasoning': explanation string
    """
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a machine-to-machine API. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
        "Output ONLY a single JSON object with the following structure:\n"
        "{\n"
        '  "detected_patterns": ["list of patterns"],\n'
        '  "version_constraints": "constraint string or null",\n'
        '  "confidence": "high/medium/low",\n'
        '  "reasoning": "explanation"\n'
        "}\n"
        "Do NOT wrap it in markdown blockquotes (like ```json).\n\n"
        "IMPORTANT: If you need to generate test scripts or demo files to verify API patterns, "
        "you MAY write them to the current working directory (testscript/). "
        "However, you MUST still return the JSON object in your final response. "
        "Do NOT generate documentation files (README.md, docs, etc.) or Dockerfiles."
    )

    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt, cwd=testscript_dir)

        # Clean and parse the JSON response
        clean_value = raw_response.strip()
        clean_value = re.sub(r'^```json\s*', '', clean_value)
        clean_value = re.sub(r'^```\s*', '', clean_value)
        clean_value = re.sub(r'\s*```$', '', clean_value)
        match = re.search(r'\{.*\}', clean_value, re.DOTALL)
        res_str = match.group(0) if match else clean_value

        result = json.loads(res_str)

        # Validate the response structure
        required_keys = ['detected_patterns', 'version_constraints', 'confidence', 'reasoning']
        if not isinstance(result, dict) or not all(key in result for key in required_keys):
            raise ValueError("LLM response missing required keys")

        # Ensure detected_patterns is a list
        if not isinstance(result['detected_patterns'], list):
            result['detected_patterns'] = []

        # Normalize confidence to lowercase
        if isinstance(result['confidence'], str):
            result['confidence'] = result['confidence'].lower()

        return result

    except Exception as e:
        print(f"   ❌ [LLM Error] Failed to analyze API patterns: {e}")
        # Fallback: return low confidence result
        return {
            "detected_patterns": [],
            "version_constraints": None,
            "confidence": "low",
            "reasoning": f"Analysis failed: {e}"
        }


# =====================================================================
# 🚀 Business Logic 5: LLM-Guided Version Selection Based on Docker Build Errors
# =====================================================================
def suggest_next_version_combination(
    error_message: str,
    failed_combinations: list,
    available_versions: dict,
    packages: list
) -> dict:
    """
    Use LLM to analyze Docker build error and suggest the next version combination to try.

    Args:
        error_message: The Docker build error message
        failed_combinations: List of previously failed combinations [{"pkg1": "ver1", ...}, ...]
        available_versions: Dict of {package_name: [list of available versions]}
        packages: List of package names to generate combination for

    Returns:
        dict with keys:
            - 'combination': dict {package_name: version} - the suggested next combination
            - 'reasoning': str - explanation of why this combination was chosen
            - 'confidence': str - 'high', 'medium', or 'low'
    """
    sys_prompt = (
        "SYSTEM: [STRICT_JSON_ONLY_MODE]\n"
        "You are a Python package dependency expert. YOU MUST NOT WRITE ANY EXPLANATORY TEXT.\n"
        "Output ONLY a single JSON object with the following structure:\n"
        "{\n"
        '  "combination": {"package1": "version1", "package2": "version2", ...},\n'
        '  "reasoning": "explanation of why this combination should work",\n'
        '  "confidence": "high/medium/low"\n'
        "}\n"
        "Do NOT wrap it in markdown blockquotes (like ```json).\n\n"
        "CRITICAL RULES:\n"
        "1. Start with the NEWEST compatible versions first (highest version numbers)\n"
        "2. When a build fails, analyze the error to identify which package(s) caused the issue\n"
        "3. Only downgrade the problematic package(s), keep others at their current versions\n"
        "4. Never suggest a combination that has already been tried\n"
        "5. Consider version compatibility constraints between packages\n"
        "6. The combination MUST include ALL packages listed in the available_versions"
    )

    # Build the prompt
    prompt = f"""Analyze this Docker build error and suggest the next package version combination to try.

## Docker Build Error:
```
{error_message}
```

## Previously Failed Combinations:
"""

    for idx, combo in enumerate(failed_combinations, 1):
        prompt += f"\nAttempt {idx}:\n"
        for pkg, ver in combo.items():
            prompt += f"  - {pkg}=={ver}\n"

    prompt += "\n## Available Versions for Each Package:\n"
    for pkg in packages:
        versions = available_versions.get(pkg, [])
        prompt += f"\n{pkg}:\n"
        prompt += f"  Available versions (newest to oldest): {', '.join(versions[:10])}"
        if len(versions) > 10:
            prompt += f" ... ({len(versions)} total)"
        prompt += "\n"

    prompt += """

## Your Task:
1. Analyze the error message to identify which package version caused the failure
2. Suggest the next version combination to try that:
   - Has NOT been tried before
   - Addresses the identified compatibility issue
   - Uses the NEWEST possible versions while avoiding the problematic combination
   - Includes ALL packages listed above

Return your suggestion as a JSON object with the structure specified in the system prompt.
"""

    try:
        raw_response = _run_sync(_ask_claude, prompt, sys_prompt, disable_write=True)

        # Clean and parse the JSON response
        clean_value = raw_response.strip()
        clean_value = re.sub(r'^```json\s*', '', clean_value)
        clean_value = re.sub(r'^```\s*', '', clean_value)
        clean_value = re.sub(r'\s*```$', '', clean_value)
        match = re.search(r'\{.*\}', clean_value, re.DOTALL)
        res_str = match.group(0) if match else clean_value

        result = json.loads(res_str)

        # Validate the response structure
        if not isinstance(result, dict) or 'combination' not in result:
            raise ValueError("LLM response missing 'combination' key")

        if not isinstance(result['combination'], dict):
            raise ValueError("'combination' must be a dict")

        # Ensure all packages are included
        missing_packages = set(packages) - set(result['combination'].keys())
        if missing_packages:
            raise ValueError(f"Missing packages in combination: {missing_packages}")

        # Set defaults for optional fields
        if 'reasoning' not in result:
            result['reasoning'] = "No reasoning provided"
        if 'confidence' not in result:
            result['confidence'] = "medium"

        return result

    except Exception as e:
        print(f"   ❌ [LLM Error] Failed to suggest next combination: {e}")
        # Fallback: return the first untried combination with newest versions
        combination = {pkg: available_versions[pkg][0] for pkg in packages if available_versions.get(pkg)}
        return {
            "combination": combination,
            "reasoning": f"Fallback selection (LLM failed: {e})",
            "confidence": "low"
        }