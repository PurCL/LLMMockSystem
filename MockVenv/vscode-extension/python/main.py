#!/usr/bin/env python3
"""
MockVenv Main Entry Point

This script provides a command-line interface to access three core functionalities:
1. Reset Environment: Create a virtual environment from a requirements.txt file
2. Resolve Dependencies: Analyze .api_calls.json to generate resolved version configurations
3. Fix Environment: Analyze exploit failures and identify package version issues

Usage:
    python main.py --reset --requirements <path_to_requirements.txt>
    python main.py --resolve [path_to_state.json]
    python main.py --fix --requirements <path_to_requirements.txt> --project <path_to_project> --exploit <exploit_scripts>
    python main.py --help
"""

import sys
import os
import argparse
import subprocess
import json
import re
import traceback
import glob
from datetime import datetime
import shutil


def reset_environment(requirements_path, python_version=None):
    """
    Create a virtual environment based on the provided requirements.txt file.

    Args:
        requirements_path: Path to the requirements.txt file
        python_version: Optional Python version to use (e.g., '3.10', '3.11')

    This function calls reset_env.py to:
    - Destroy the old .venv environment
    - Rebuild a new virtual environment using uv
    - Install exact versions from requirements.txt + inject llm_real_hook.py
    """
    print("=" * 60)
    print(f"🔄 RESET ENVIRONMENT")
    print("=" * 60)

    if not os.path.exists(requirements_path):
        print(f"❌ Error: Requirements file not found: {requirements_path}")
        sys.exit(1)

    print(f"📋 Using requirements file: {requirements_path}")
    print(f"📂 Target directory: {os.getcwd()}")
    if python_version:
        print(f"🐍 Python version: {python_version}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reset_script = os.path.join(script_dir, "reset_env.py")

    if not os.path.exists(reset_script):
        print(f"❌ Error: reset_env.py not found at: {reset_script}")
        sys.exit(1)

    # Execute reset_env.py with the requirements file path and optional python version
    cmd = [sys.executable, reset_script, requirements_path]
    if python_version:
        cmd.append(python_version)

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Environment reset completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during environment reset: {e}")
        sys.exit(1)


def fix_environment(requirements_path, project_path, exploit_scripts):
    """
    Analyze exploit failures and identify package version issues using Claude Code.

    Args:
        requirements_path: Path to the requirements.txt file
        project_path: Path to the project directory
        exploit_scripts: List of paths to exploit scripts

    This function:
    - Reads the .api_calls.json trace from .venv directory
    - Analyzes why exploits failed using Claude Code (llm_client)
    - Identifies which package versions are causing issues
    - Focus ONLY on package version problems
    """
    print("=" * 60)
    print("🔧 FIX ENVIRONMENT - Exploit Analysis")
    print("=" * 60)

    if not os.path.exists(requirements_path):
        print(f"❌ Error: Requirements file not found: {requirements_path}")
        sys.exit(1)

    # Check if user is mistakenly using fixed_requirements.txt as input
    requirements_basename = os.path.basename(requirements_path)
    if requirements_basename == "fixed_requirements.txt":
        print(f"⚠️ WARNING: You are using 'fixed_requirements.txt' as input!")
        print(f"💡 This will cause circular references. You should use the ORIGINAL requirements.txt instead.")
        print(f"💡 Example: --requirements requirements.txt (not fixed_requirements.txt)")
        user_input = input("\n❓ Do you want to continue anyway? (yes/no): ").strip().lower()
        if user_input not in ['yes', 'y']:
            print("❌ Aborted by user")
            sys.exit(1)

    if not os.path.exists(project_path):
        print(f"❌ Error: Project path not found: {project_path}")
        sys.exit(1)

    requirements_path = os.path.abspath(requirements_path)
    project_path = os.path.abspath(project_path)

    # Check if fix_log directory exists
    fix_log_dir = os.path.join(os.getcwd(), "fix_log")
    previous_fix_attempts = ""

    if os.path.exists(fix_log_dir) and os.path.isdir(fix_log_dir):
        # Check if there are any log files in the directory
        log_files = [f for f in os.listdir(fix_log_dir) if f.endswith('.txt') or f.endswith('.log') or f.endswith('.md')]

        if log_files:
            print("\n" + "=" * 60)
            print("📂 Found existing fix_log directory with previous attempts")
            print("=" * 60)
            print(f"Found {len(log_files)} previous fix attempt(s)")

            # Ask user if they want to clear the log
            while True:
                user_input = input("\n❓ Do you want to clear the fix log history? (yes/no): ").strip().lower()
                if user_input in ['yes', 'y']:
                    print("🧹 Clearing fix_log directory...")
                    shutil.rmtree(fix_log_dir)
                    os.makedirs(fix_log_dir, exist_ok=True)
                    print("✅ Fix log cleared")
                    break
                elif user_input in ['no', 'n']:
                    print("📖 Reading previous fix attempts to avoid rollback...")

                    # Read all log files and concatenate them
                    all_logs = []
                    for log_file in sorted(log_files):
                        log_path = os.path.join(fix_log_dir, log_file)
                        try:
                            with open(log_path, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                                all_logs.append(f"## Previous Fix Attempt: {log_file}\n\n{log_content}\n")
                            print(f"  ✓ Loaded: {log_file}")
                        except Exception as e:
                            print(f"  ⚠️ Failed to read {log_file}: {e}")

                    if all_logs:
                        previous_fix_attempts = "\n".join(all_logs)
                        print(f"✅ Loaded {len(all_logs)} previous fix attempt(s)")
                    break
                else:
                    print("❌ Please enter 'yes' or 'no'")
    else:
        # Create fix_log directory if it doesn't exist
        os.makedirs(fix_log_dir, exist_ok=True)
        print(f"✅ Created fix_log directory: {fix_log_dir}")

    print(f"📋 Requirements file: {requirements_path}")
    print(f"📂 Project path: {project_path}")
    print(f"🔍 Exploit scripts: {', '.join(exploit_scripts)}")

    # Get trace file path
    venv_dir = os.path.join(os.getcwd(), ".venv")
    trace_file = os.path.join(venv_dir, ".api_calls.json")

    if not os.path.exists(trace_file):
        print(f"❌ Error: Trace file not found: {trace_file}")
        print(f"💡 Hint: Make sure to run the project first to generate the trace")
        sys.exit(1)

    print(f"\n📊 Reading trace file: {trace_file}")

    # Read trace file
    try:
        with open(trace_file, 'r') as f:
            trace_data = f.read()
        print(f"✅ Trace file loaded ({len(trace_data)} bytes)")

        # If trace file is too large (>100KB), truncate it to avoid token limits
        MAX_TRACE_SIZE = 100 * 1024  # 100KB (reduced from 500KB)
        if len(trace_data) > MAX_TRACE_SIZE:
            print(f"⚠️  Trace file too large ({len(trace_data)} bytes), truncating to {MAX_TRACE_SIZE} bytes")
            # Keep first and last portions
            first_half = trace_data[:MAX_TRACE_SIZE // 2]
            last_half = trace_data[-MAX_TRACE_SIZE // 2:]
            trace_data = first_half + "\n\n... [TRUNCATED FOR SIZE] ...\n\n" + last_half
            print(f"✅ Trace truncated to {len(trace_data)} bytes")
    except Exception as e:
        print(f"❌ Error reading trace file: {e}")
        sys.exit(1)

    # Verify exploit scripts exist
    missing_exploits = []
    for exploit in exploit_scripts:
        if not os.path.exists(exploit):
            missing_exploits.append(exploit)

    if missing_exploits:
        print(f"❌ Error: Exploit scripts not found:")
        for exploit in missing_exploits:
            print(f"   - {exploit}")
        sys.exit(1)

    # Read exploit scripts
    exploit_contents = {}
    for exploit in exploit_scripts:
        try:
            with open(exploit, 'r') as f:
                exploit_contents[exploit] = f.read()
            print(f"✅ Loaded exploit: {exploit}")
        except Exception as e:
            print(f"❌ Error reading exploit {exploit}: {e}")
            sys.exit(1)

    # Read requirements.txt
    try:
        with open(requirements_path, 'r') as f:
            requirements_data = f.read()
        print(f"✅ Loaded requirements.txt")
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🤖 Analyzing exploit failures with Claude Code...")
    print("=" * 60)

    # Read project source code to understand exploit execution path
    print(f"\n📂 Analyzing project source code...")
    project_files_content = {}
    try:
        # Find key files in the project that are likely involved in exploit execution
        # Search for Python files in the project
        search_patterns = [
            os.path.join(project_path, "**/*.py"),
            os.path.join(project_path, "**/views.py"),
            os.path.join(project_path, "**/query.py"),
            os.path.join(project_path, "**/utils.py"),
        ]

        found_files = set()
        for pattern in search_patterns:
            for file_path in glob.glob(pattern, recursive=True):
                # Limit to reasonable file size (< 100KB)
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < 100 * 1024:
                        found_files.add(file_path)
                except Exception:
                    pass

        # Read up to 5 most relevant files (reduced from 10)
        MAX_FILE_SIZE = 20 * 1024  # Limit individual files to 20KB
        for file_path in list(found_files)[:5]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    relative_path = os.path.relpath(file_path, project_path)
                    content = f.read()
                    # Truncate if too large
                    if len(content) > MAX_FILE_SIZE:
                        content = content[:MAX_FILE_SIZE] + "\n... [FILE TRUNCATED] ..."
                    project_files_content[relative_path] = content
                print(f"  ✓ Loaded: {relative_path}")
            except Exception as e:
                print(f"  ⚠️ Failed to read {file_path}: {e}")

    except Exception as e:
        print(f"  ⚠️ Warning: Could not analyze project files: {e}")

    # Prepare analysis prompt for Claude Code
    analysis_prompt = f"""# Exploit Failure Analysis - Execution Path Comparison

## Context
You are analyzing why security exploits FAILED in a Python project. Your task is to:
1. **Analyze the project source code** to understand the EXPECTED SUCCESSFUL exploit execution path
2. **Compare with the actual API call trace** to identify where the execution deviated
3. **Identify which package version issues** caused the path divergence
4. **Recommend specific package versions** that would enable the successful exploit path

## Input Data

### 1. Requirements.txt (Current Package Versions)
```
{requirements_data}
```

### 2. Project Source Code (Successful Exploit Path)
The following files show how the exploit SHOULD execute successfully:
"""

    for file_path, content in project_files_content.items():
        analysis_prompt += f"""
#### File: {file_path}
```python
{content[:3000]}  # Truncate to 3KB per file (reduced from 5KB)
```
"""

    analysis_prompt += f"""

### 3. API Call Trace (.api_calls.json - Failed Execution Path)
The following trace shows which APIs were ACTUALLY called during failed execution:
```
{trace_data}
```

### 4. Exploit Scripts (Attack Vector)
"""

    for exploit_path, exploit_content in exploit_contents.items():
        analysis_prompt += f"""
#### Exploit: {os.path.basename(exploit_path)}
```bash
{exploit_content}
```
"""

    # Add previous fix attempts if available
    if previous_fix_attempts:
        analysis_prompt += f"""

### 5. Previous Fix Attempts
**IMPORTANT**: The following are previous fix attempts that were already tried.
Please carefully review these attempts and DO NOT suggest the same fixes again.
Learn from what has been tried before and avoid rollback.

{previous_fix_attempts}
"""

    analysis_prompt += """

## Analysis Task

### Step 1: Identify the Error Type
First, determine if this is a ModuleNotFoundError (missing package) or a version incompatibility issue:
- **ModuleNotFoundError**: A required Python module/package is completely missing and needs to be ADDED
- **Version Incompatibility**: An existing package has the wrong version and needs to be UPDATED

### Step 2: For ModuleNotFoundError - Identify Missing Packages
If the error is "ModuleNotFoundError: No module named 'xxx'":
- Extract the missing module name (e.g., 'pkg_resources', 'setuptools', etc.)
- Determine the PyPI package name that provides this module
- Recommend adding this NEW package to requirements.txt (DO NOT modify existing package versions)

### Step 3: For Version Issues - Identify the Expected Exploit Execution Path
Based on the project source code and exploit scripts, trace the COMPLETE execution path that would lead to successful exploit:
- Which API endpoints are called?
- Which functions are invoked in sequence?
- What key operations should occur (e.g., query parsing, sandbox escape, command execution)?
- Which package versions/features are required at each step?

### Step 4: Compare with Actual Failed Execution Path
Analyze the .api_calls.json trace to identify:
- Where did the execution path diverge from the expected path?
- Which expected API calls are MISSING from the trace?
- Which APIs behaved differently than expected?
- Are there error indicators in the trace?

### Step 5: Identify Package Version Root Causes
For each divergence point, determine:
- Which package is responsible for the missing/changed behavior?
- What specific version introduced or removed the required feature?
- Which EXACT version would restore the expected behavior?

### Step 6: Generate Recommendations
Provide SPECIFIC recommendations based on error type:
- For ModuleNotFoundError: Add NEW packages to requirements.txt
- For version issues: Update existing package versions

## Output Format

You MUST provide your response in the following EXACT JSON format (no markdown, no explanations outside the JSON):

```json
{
  "error_type": "ModuleNotFoundError or VersionIncompatibility",
  "summary": "Brief overview of the error or execution path divergence",
  "expected_exploit_path": [
    "Step 1: Description of expected execution",
    "Step 2: Next expected step",
    "..."
  ],
  "actual_execution_path": [
    "Step 1: What actually happened",
    "Step 2: Where divergence occurred",
    "..."
  ],
  "path_divergence_points": [
    {
      "step": "Description of divergence",
      "expected": "What should have happened",
      "actual": "What actually happened",
      "related_package": "package_name"
    }
  ],
  "packages": [
    {
      "name": "package_name",
      "current_version": "current version from requirements.txt OR null if not installed",
      "recommended_version": "specific version that would work (EXACT version number)",
      "action": "add or update",
      "issue": "what's wrong (missing package or wrong version - be specific)",
      "reason": "why this version/package would fix the issue",
      "evidence_from_trace": "specific evidence from .api_calls.json or missing calls"
    }
  ],
  "root_cause": "Detailed explanation of why the exploit failed",
  "recommended_actions": [
    "Specific action 1 with exact version numbers or package names",
    "Specific action 2"
  ]
}
```

## Important Constraints
- **CRITICAL**: Distinguish between ModuleNotFoundError (add new package) and version issues (update existing package)
- For ModuleNotFoundError: Set "action": "add" and "current_version": null
- For version issues: Set "action": "update" and provide current version
- Provide EXACT version numbers (e.g., "5.2" not ">=5.0" or "older version")
- Use evidence from the API trace to support your analysis
- If the trace is empty or minimal, it indicates early execution failure
- MUST return valid JSON format as shown above
"""

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Import llm_client
    sys.path.insert(0, script_dir)
    try:
        from llm_client import _ask_claude, _run_sync

        # Check final prompt size before sending
        final_prompt_size = len(analysis_prompt)
        print(f"\n📊 Final prompt size: {final_prompt_size:,} bytes")
        if final_prompt_size > 400000:
            print(f"⚠️  WARNING: Prompt is very large and may fail!")
            print(f"💡 Consider reducing trace file size or project files")

        print("\n📡 Sending analysis request to Claude Code...")
        print("   This may take a few minutes...\n")

        # Use Claude Code to analyze
        system_prompt = """You are a Python package dependency expert specializing in security vulnerability analysis.
Your task is to analyze exploit failures and identify package version issues.
Be thorough, specific, and provide actionable recommendations.
Focus exclusively on package version-related problems.
You MUST return ONLY valid JSON format without any markdown or additional text."""

        analysis_result = _run_sync(_ask_claude, analysis_prompt, system_prompt)

        print("\n" + "=" * 60)
        print("📋 ANALYSIS RESULTS")
        print("=" * 60)
        print(analysis_result)
        print("=" * 60)

        # Parse the JSON result
        try:
            # Clean the response to extract JSON
            clean_result = analysis_result.strip()
            # Remove markdown code blocks if present
            clean_result = re.sub(r'^```json\s*', '', clean_result)
            clean_result = re.sub(r'^```\s*', '', clean_result)
            clean_result = re.sub(r'\s*```$', '', clean_result)
            # Extract JSON object
            match = re.search(r'\{.*\}', clean_result, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                json_str = clean_result

            analysis_data = json.loads(json_str)

            # Save detailed analysis to file
            analysis_file = os.path.join(venv_dir, "exploit_analysis.txt")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("EXPLOIT FAILURE ANALYSIS - PACKAGE VERSION ISSUES\n")
                f.write("=" * 80 + "\n\n")
                f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
                f.write("\n\n" + "=" * 80 + "\n")

            print(f"\n✅ Analysis saved to: {analysis_file}")

            # Generate new requirements.txt
            if analysis_data.get('packages'):
                print("\n" + "=" * 60)
                print("📝 GENERATING NEW REQUIREMENTS.TXT")
                print("=" * 60)

                # Load PyPI import mapping
                mapping_file = os.path.join(script_dir, "pypi_import_mapping.json")
                pypi_import_mapping = {}
                if os.path.exists(mapping_file):
                    try:
                        with open(mapping_file, "r", encoding="utf-8") as f:
                            pypi_import_mapping = json.load(f)
                        print(f"✅ Loaded {len(pypi_import_mapping)} package mappings from {mapping_file}")
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to load mapping file: {e}")
                else:
                    print(f"⚠️ Warning: Mapping file not found at {mapping_file}")

                # Create reverse mapping: import_name -> pypi_name
                import_to_pypi = {}
                for pypi_name, import_name in pypi_import_mapping.items():
                    import_to_pypi[import_name.lower()] = pypi_name
                    # Also add normalized versions for lookup
                    import_to_pypi[import_name.lower().replace('_', '-')] = pypi_name
                    import_to_pypi[import_name.lower().replace('-', '_')] = pypi_name

                # Parse original requirements
                original_reqs = {}
                # Create a mapping from normalized package names to original case
                pkg_name_mapping = {}
                for line in requirements_data.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' in line:
                            pkg_name, pkg_version = line.split('==', 1)
                            pkg_name = pkg_name.strip()
                            original_reqs[pkg_name] = pkg_version.strip()
                            # Store normalized mapping for case-insensitive lookup
                            normalized = pkg_name.lower().replace('_', '-')
                            pkg_name_mapping[normalized] = pkg_name
                            # Also store underscore version
                            pkg_name_mapping[pkg_name.lower().replace('-', '_')] = pkg_name
                        else:
                            # Handle lines without version specifier
                            pkg_name = line.strip()
                            original_reqs[pkg_name] = None
                            normalized = pkg_name.lower().replace('_', '-')
                            pkg_name_mapping[normalized] = pkg_name
                            pkg_name_mapping[pkg_name.lower().replace('-', '_')] = pkg_name

                # Update with recommended versions or add new packages
                updated_reqs = original_reqs.copy()
                changes_made = []

                for package in analysis_data['packages']:
                    pkg_name = package['name']
                    recommended_ver = package['recommended_version']
                    current_ver = package.get('current_version', 'unknown')
                    action = package.get('action', 'update')  # Default to 'update' for backward compatibility

                    # Try to resolve the package name using multiple strategies
                    original_pkg_name = None

                    # Strategy 1: Direct normalized match
                    normalized = pkg_name.lower().replace('_', '-')
                    if normalized in pkg_name_mapping:
                        original_pkg_name = pkg_name_mapping[normalized]

                    # Strategy 2: Try underscore version
                    if not original_pkg_name:
                        normalized_underscore = pkg_name.lower().replace('-', '_')
                        if normalized_underscore in pkg_name_mapping:
                            original_pkg_name = pkg_name_mapping[normalized_underscore]

                    # Strategy 3: Check if pkg_name is an import name, convert to PyPI name
                    if not original_pkg_name:
                        pkg_name_lower = pkg_name.lower()
                        if pkg_name_lower in import_to_pypi:
                            pypi_name = import_to_pypi[pkg_name_lower]
                            # Now look for the PyPI name in our requirements
                            pypi_normalized = pypi_name.lower().replace('_', '-')
                            if pypi_normalized in pkg_name_mapping:
                                original_pkg_name = pkg_name_mapping[pypi_normalized]
                                print(f"  🗺️ Resolved import name '{pkg_name}' → PyPI name '{pypi_name}'")
                            else:
                                # If not in requirements, use the PyPI name for adding
                                if action == 'add':
                                    original_pkg_name = pypi_name
                                    print(f"  🗺️ Resolved import name '{pkg_name}' → PyPI name '{pypi_name}' (will be added)")

                    # Strategy 4: Exact match (case-sensitive fallback)
                    if not original_pkg_name and pkg_name in original_reqs:
                        original_pkg_name = pkg_name

                    # Strategy 5: If action is 'add' and package not found, use pkg_name as-is
                    if not original_pkg_name and action == 'add':
                        original_pkg_name = pkg_name

                    if original_pkg_name:
                        if action == 'add':
                            # Add new package
                            if original_pkg_name in updated_reqs:
                                # Package already exists - check if version needs updating
                                if updated_reqs[original_pkg_name] != recommended_ver:
                                    print(f"  ⚠️ Package '{original_pkg_name}' already exists in requirements.txt, updating version: {updated_reqs[original_pkg_name]} → {recommended_ver}")
                                    changes_made.append(f"  ✓ {original_pkg_name}: {updated_reqs[original_pkg_name]} → {recommended_ver} (updated)")
                                    updated_reqs[original_pkg_name] = recommended_ver
                                else:
                                    print(f"  ℹ️ Package '{original_pkg_name}' already exists with correct version {recommended_ver}, skipping")
                            else:
                                changes_made.append(f"  ✓ {original_pkg_name}: ADDED → {recommended_ver}")
                                updated_reqs[original_pkg_name] = recommended_ver
                                print(f"  ✓ {original_pkg_name}: ADDED with version {recommended_ver}")
                        else:
                            # Update existing package
                            updated_reqs[original_pkg_name] = recommended_ver
                            changes_made.append(f"  ✓ {original_pkg_name}: {current_ver} → {recommended_ver}")
                            print(f"  ✓ {original_pkg_name}: {current_ver} → {recommended_ver}")
                    else:
                        if action == 'add':
                            print(f"  ⚠️ Warning: Could not resolve package name '{pkg_name}' for adding")
                        else:
                            print(f"  ⚠️ Warning: Package '{pkg_name}' not found in original requirements.txt")

                # Generate new requirements.txt content
                new_requirements = []
                for pkg_name, pkg_version in sorted(updated_reqs.items()):
                    if pkg_version:
                        new_requirements.append(f"{pkg_name}=={pkg_version}")
                    else:
                        new_requirements.append(pkg_name)

                new_requirements_content = '\n'.join(new_requirements)

                # Check if any changes were actually made
                if not changes_made:
                    print("\n⚠️ No changes were made to requirements.txt - all packages already have the recommended versions.")
                    print(f"💡 Hint: The input file '{requirements_path}' may already contain the correct versions.")
                    print(f"💡 If you're experiencing issues, check if you're using the correct input requirements.txt file.")
                else:
                    # Save new requirements.txt to project root directory
                    new_requirements_path = os.path.join(os.getcwd(), "fixed_requirements.txt")
                    with open(new_requirements_path, 'w', encoding='utf-8') as f:
                        f.write("# Fixed requirements.txt generated by MockVenv\n")
                        f.write("# Original file: " + requirements_path + "\n")
                        f.write("# Changes made:\n")
                        for change in changes_made:
                            f.write("#   " + change + "\n")
                        f.write("\n")
                        f.write(new_requirements_content)

                    print(f"\n✅ New requirements.txt saved to: {new_requirements_path}")
                    print(f"\n📋 Summary of changes:")
                    for change in changes_made:
                        print(change)

                # Save fix log with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = f"fix_attempt_{timestamp}.md"
                log_path = os.path.join(fix_log_dir, log_filename)

                print(f"\n📝 Saving fix attempt log...")
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Fix Attempt Log - {timestamp}\n\n")
                    f.write(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("## Summary\n\n")
                    f.write(f"{analysis_data.get('summary', 'No summary available')}\n\n")

                    f.write("## Error Type\n\n")
                    f.write(f"{analysis_data.get('error_type', 'Unknown')}\n\n")

                    f.write("## Root Cause\n\n")
                    f.write(f"{analysis_data.get('root_cause', 'No root cause identified')}\n\n")

                    f.write("## Requirements.txt Modifications\n\n")
                    if changes_made:
                        f.write("The following changes were made to requirements.txt:\n\n")
                        for change in changes_made:
                            f.write(f"- {change.strip()}\n")
                        f.write("\n")
                    else:
                        f.write("No changes were made to requirements.txt.\n\n")

                    f.write("## Package Details and Rationale\n\n")
                    if analysis_data.get('packages'):
                        for package in analysis_data['packages']:
                            f.write(f"### Package: {package['name']}\n\n")
                            f.write(f"- **Action**: {package.get('action', 'update')}\n")
                            f.write(f"- **Current Version**: {package.get('current_version', 'N/A')}\n")
                            f.write(f"- **Recommended Version**: {package['recommended_version']}\n")
                            f.write(f"- **Issue**: {package['issue']}\n")
                            f.write(f"- **Reason**: {package['reason']}\n")
                            if package.get('evidence_from_trace'):
                                f.write(f"- **Evidence**: {package['evidence_from_trace']}\n")
                            f.write("\n")
                    else:
                        f.write("No package modifications were recommended.\n\n")

                    f.write("## Recommended Actions\n\n")
                    if analysis_data.get('recommended_actions'):
                        for idx, action in enumerate(analysis_data['recommended_actions'], 1):
                            f.write(f"{idx}. {action}\n")
                        f.write("\n")
                    else:
                        f.write("No specific actions recommended.\n\n")

                    f.write("## Expected vs Actual Execution Path\n\n")
                    if analysis_data.get('expected_exploit_path'):
                        f.write("### Expected Exploit Path\n\n")
                        for idx, step in enumerate(analysis_data['expected_exploit_path'], 1):
                            f.write(f"{idx}. {step}\n")
                        f.write("\n")

                    if analysis_data.get('actual_execution_path'):
                        f.write("### Actual Execution Path\n\n")
                        for idx, step in enumerate(analysis_data['actual_execution_path'], 1):
                            f.write(f"{idx}. {step}\n")
                        f.write("\n")

                    if analysis_data.get('path_divergence_points'):
                        f.write("### Path Divergence Points\n\n")
                        for idx, divergence in enumerate(analysis_data['path_divergence_points'], 1):
                            f.write(f"#### Divergence {idx}\n\n")
                            f.write(f"- **Step**: {divergence.get('step', 'N/A')}\n")
                            f.write(f"- **Expected**: {divergence.get('expected', 'N/A')}\n")
                            f.write(f"- **Actual**: {divergence.get('actual', 'N/A')}\n")
                            f.write(f"- **Related Package**: {divergence.get('related_package', 'N/A')}\n")
                            f.write("\n")

                    f.write("---\n\n")
                    f.write("*This log was automatically generated by MockVenv fix mode.*\n")

                print(f"✅ Fix attempt log saved to: {log_path}")

            else:
                print("\n⚠️ No package version issues identified. No new requirements.txt generated.")

        except json.JSONDecodeError as e:
            print(f"\n⚠️ Warning: Could not parse JSON response: {e}")
            print(f"Raw response saved to exploit_analysis.txt")
            # Save raw analysis to file
            analysis_file = os.path.join(venv_dir, "exploit_analysis.txt")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("EXPLOIT FAILURE ANALYSIS - PACKAGE VERSION ISSUES\n")
                f.write("=" * 80 + "\n\n")
                f.write(analysis_result)
                f.write("\n\n" + "=" * 80 + "\n")

            print(f"\n✅ Analysis saved to: {analysis_file}")
        except Exception as e:
            print(f"\n⚠️ Warning: Error processing analysis results: {e}")
            traceback.print_exc()

    except ImportError as e:
        print(f"❌ Error importing llm_client: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Fix mode analysis complete!")
    print("=" * 60)


def resolve_dependencies(mock_state_path=None, requirements_path=None, project_path=None, use_llm=True, python_version=None, num_dockerfiles="1", cve_id=None):
    """
    Analyze the .api_calls.json file to generate resolved version configurations.

    Args:
        mock_state_path: Optional path to .api_calls.json file
                        If not provided, defaults to .venv/.api_calls.json
        requirements_path: Optional path to requirements.txt file for package constraints
        project_path: Optional path to project directory for Docker volume mounting
        use_llm: If True (default), use LLM to generate Dockerfile content. If False, use template.
        python_version: Optional Python version to use for validation (e.g., '3.10', '3.11')
        num_dockerfiles: Number of Dockerfiles to generate: 'all' for all combinations, or a number (default: "1")
        cve_id: Optional CVE ID (e.g., 'CVE-2026-1462') to filter validated versions based on CVE website info

    This function calls resolve_dependencies.py to:
    - Read the state file containing intercepted API features
    - Query PyPI for available package versions
    - Use LLM inference to filter compatible versions
    - Generate resolved_versions.json with the final configuration
    """
    print("=" * 60)
    print(f"🔍 RESOLVE DEPENDENCIES")
    print("=" * 60)

    # Default path if not specified
    if mock_state_path is None:
        mock_state_path = os.path.join(os.getcwd(), ".venv", ".api_calls.json")
        print(f"📂 Using default state path: {mock_state_path}")
    else:
        print(f"📂 Using custom state path: {mock_state_path}")

    if not os.path.exists(mock_state_path):
        print(f"❌ Error: State file not found: {mock_state_path}")
        print(f"💡 Hint: Run the reset environment first or provide a valid path")
        sys.exit(1)

    # Default requirements.txt path if not specified
    if requirements_path is None:
        requirements_path = os.path.join(os.getcwd(), "requirements.txt")
        if os.path.exists(requirements_path):
            print(f"📋 Using default requirements file: {requirements_path}")
        else:
            print(f"⚠️ No requirements.txt found at default location")
            requirements_path = ""
    else:
        if os.path.exists(requirements_path):
            print(f"📋 Using custom requirements file: {requirements_path}")
        else:
            print(f"❌ Error: Requirements file not found: {requirements_path}")
            sys.exit(1)

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resolve_script = os.path.join(script_dir, "resolve_dependencies.py")

    if not os.path.exists(resolve_script):
        print(f"❌ Error: resolve_dependencies.py not found at: {resolve_script}")
        sys.exit(1)

    # Execute resolve_dependencies.py with the state file path, requirements path, project path, use_llm, python_version, num_dockerfiles, and cve_id
    cmd = [sys.executable, resolve_script, mock_state_path]
    if requirements_path:
        cmd.append(requirements_path)
    else:
        cmd.append("")  # Empty placeholder for requirements_path

    if project_path:
        cmd.append(project_path)
    else:
        cmd.append("")  # Empty placeholder for project_path

    # Add use_llm parameter
    cmd.append('true' if use_llm else 'false')

    # Add python_version parameter
    if python_version:
        cmd.append(python_version)
    else:
        cmd.append("")  # Empty placeholder for python_version

    # Add num_dockerfiles parameter
    cmd.append(num_dockerfiles)

    # Add cve_id parameter
    if cve_id:
        cmd.append(cve_id)
    else:
        cmd.append("")  # Empty placeholder for cve_id

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Dependency resolution completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during dependency resolution: {e}")
        sys.exit(1)


def print_banner():
    """Print the welcome banner with tool information."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              🎯 MockVenv Management Tool 🎯              ║
║                                                          ║
║  A comprehensive tool for managing mock virtual          ║
║  environments and resolving Python dependencies          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point with argument parsing and mode selection."""
    print_banner()

    parser = argparse.ArgumentParser(
        description="MockVenv Management Tool - Reset environments and resolve dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset environment with a requirements.txt file
  python main.py --reset --requirements /path/to/requirements.txt

  # Reset environment with a specific Python version
  python main.py --reset --requirements /path/to/requirements.txt --python 3.10

  # Fix mode: Analyze exploit failures and identify package version issues
  python main.py --fix --requirements /path/to/requirements.txt --project /path/to/project --exploit /path/to/exploit1.sh,/path/to/exploit2.sh

  # Resolve dependencies using default .api_calls.json location
  python main.py --resolve

  # Resolve dependencies using custom state file path
  python main.py --resolve /path/to/.api_calls.json

  # Resolve dependencies with custom requirements.txt file
  python main.py --resolve --requirements /path/to/requirements.txt

  # Resolve dependencies with project path for Docker volume mounting
  python main.py --resolve --requirements /path/to/requirements.txt --project /path/to/project

  # Force template-based generation with --no-llm flag
  python main.py --resolve --no-llm
        """
    )

    parser.add_argument(
        "--requirements",
        type=str,
        metavar="REQUIREMENTS_FILE",
        help="Path to requirements.txt file (required for --reset and --fix, optional for --resolve)"
    )

    parser.add_argument(
        "--python",
        type=str,
        metavar="PYTHON_VERSION",
        help="Python version to use for the virtual environment (e.g., '3.10', '3.11', 'python3.10')"
    )

    parser.add_argument(
        "--exploit",
        type=str,
        metavar="EXPLOIT_SCRIPTS",
        help="Comma-separated paths to exploit scripts (required for --fix, e.g., /path/to/exploit1.sh,/path/to/exploit2.sh)"
    )

    # Create mutually exclusive group for the three main operations
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--reset",
        action="store_true",
        help="Reset the virtual environment (requires --requirements)"
    )

    group.add_argument(
        "--resolve",
        nargs="?",
        const=True,
        metavar="STATE_FILE",
        help="Resolve dependencies from .api_calls.json (optional: specify custom path)"
    )

    group.add_argument(
        "--fix",
        action="store_true",
        help="Analyze exploit failures and identify package version issues (requires --requirements, --project, and --exploit)"
    )

    parser.add_argument(
        "--project",
        type=str,
        metavar="PROJECT_PATH",
        help="Path to project directory (required for --fix, optional for --resolve with Docker volume mounting)"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force template-based Dockerfile generation"
    )

    parser.add_argument(
        "--dockerfiles",
        type=str,
        metavar="NUMBER",
        default="1",
        help="Number of Dockerfiles to generate: 'all' for all combinations, or a number (default: 1)"
    )

    parser.add_argument(
        "--cve",
        type=str,
        metavar="CVE_ID",
        help="Optional CVE ID (e.g., CVE-2026-1462) to filter validated versions based on CVE website information"
    )

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate operation based on user input
    if args.fix:
        # Fix mode: Analyze exploit failures and identify package version issues
        if not args.requirements:
            parser.error("--fix requires the --requirements argument to specify the requirements file.")
        if not args.project:
            parser.error("--fix requires the --project argument to specify the project directory.")
        if not args.exploit:
            parser.error("--fix requires the --exploit argument to specify exploit scripts (comma-separated).")

        # Parse exploit scripts (comma-separated)
        exploit_scripts = [script.strip() for script in args.exploit.split(',')]

        fix_environment(args.requirements, args.project, exploit_scripts)
    elif args.reset:
        if not args.requirements:
            parser.error("--reset requires the --requirements argument to specify the requirements file.")
        reset_environment(args.requirements, python_version=args.python)
    elif args.resolve:
        # Determine if LLM should be used based on user flags
        use_llm = not args.no_llm

        # If args.resolve is True (no path provided), use default path
        if args.resolve is True:
            resolve_dependencies(requirements_path=args.requirements, project_path=args.project, use_llm=use_llm, python_version=args.python, num_dockerfiles=args.dockerfiles, cve_id=args.cve)
        else:
            # Custom path provided
            resolve_dependencies(args.resolve, requirements_path=args.requirements, project_path=args.project, use_llm=use_llm, python_version=args.python, num_dockerfiles=args.dockerfiles, cve_id=args.cve)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
