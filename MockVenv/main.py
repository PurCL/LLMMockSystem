#!/usr/bin/env python3
"""
MockVenv Main Entry Point

This script provides a command-line interface to access three core functionalities:
1. Reset Environment: Create a mock virtual environment from a requirements.txt file
2. Resolve Dependencies: Analyze .mock_state.json to generate resolved version configurations
3. Fix Environment: Analyze exploit failures and identify package version issues

Usage:
    python main.py --reset --mode <mock|real> --requirements <path_to_requirements.txt>
    python main.py --resolve --mode <mock|real> [path_to_state.json]
    python main.py --fix --requirements <path_to_requirements.txt> --project <path_to_project> --exploit <exploit_scripts>
    python main.py --help
"""

import sys
import os
import argparse
import subprocess
import json
import re


def reset_environment(requirements_path, mode='mock', python_version=None):
    """
    Create a virtual environment based on the provided requirements.txt file.

    Args:
        requirements_path: Path to the requirements.txt file
        mode: Environment mode - 'mock' (default) or 'real'
        python_version: Optional Python version to use (e.g., '3.10', '3.11')

    This function calls reset_env.py to:
    - Destroy the old .venv environment
    - Rebuild a new virtual environment using uv
    - Install packages based on mode:
      * mock mode: Install whitelisted packages + Claude SDK + inject llm_mock_hook.py
      * real mode: Install exact versions from requirements.txt + inject llm_real_hook.py
    """
    print("=" * 60)
    print(f"🔄 RESET ENVIRONMENT MODE ({mode.upper()})")
    print("=" * 60)

    if not os.path.exists(requirements_path):
        print(f"❌ Error: Requirements file not found: {requirements_path}")
        sys.exit(1)

    if mode not in ['mock', 'real']:
        print(f"❌ Error: Invalid mode '{mode}'. Must be 'mock' or 'real'")
        sys.exit(1)

    print(f"📋 Using requirements file: {requirements_path}")
    print(f"📂 Target directory: {os.getcwd()}")
    print(f"🎯 Mode: {mode}")
    if python_version:
        print(f"🐍 Python version: {python_version}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reset_script = os.path.join(script_dir, "reset_env.py")

    if not os.path.exists(reset_script):
        print(f"❌ Error: reset_env.py not found at: {reset_script}")
        sys.exit(1)

    # Execute reset_env.py with the requirements file path, mode, and optional python version
    cmd = [sys.executable, reset_script, requirements_path, mode]
    if python_version:
        cmd.append(python_version)

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Environment reset completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during environment reset: {e}")
        sys.exit(1)


def fix_environment(requirements_path, mode, project_path, exploit_scripts):
    """
    Analyze exploit failures and identify package version issues using Claude Code.

    Args:
        requirements_path: Path to the requirements.txt file
        mode: 'real' mode (required for fix)
        project_path: Path to the project directory
        exploit_scripts: List of paths to exploit scripts

    This function:
    - Reads the .api_calls.json trace from .venv directory
    - Analyzes why exploits failed using Claude Code (llm_client)
    - Identifies which package versions are causing issues
    - Focus ONLY on package version problems
    """
    print("=" * 60)
    print("🔧 FIX ENVIRONMENT MODE - Exploit Analysis")
    print("=" * 60)

    if not os.path.exists(requirements_path):
        print(f"❌ Error: Requirements file not found: {requirements_path}")
        sys.exit(1)

    if not os.path.exists(project_path):
        print(f"❌ Error: Project path not found: {project_path}")
        sys.exit(1)

    if mode != 'real':
        print(f"❌ Error: Fix mode only supports 'real' mode, got: {mode}")
        sys.exit(1)

    requirements_path = os.path.abspath(requirements_path)
    project_path = os.path.abspath(project_path)

    print(f"📋 Requirements file: {requirements_path}")
    print(f"📂 Project path: {project_path}")
    print(f"🎯 Mode: {mode}")
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
        import glob

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

    analysis_prompt += """

## Analysis Task

### Step 1: Identify the Expected Exploit Execution Path
Based on the project source code and exploit scripts, trace the COMPLETE execution path that would lead to successful exploit:
- Which API endpoints are called?
- Which functions are invoked in sequence?
- What key operations should occur (e.g., query parsing, sandbox escape, command execution)?
- Which package versions/features are required at each step?

### Step 2: Compare with Actual Failed Execution Path
Analyze the .api_calls.json trace to identify:
- Where did the execution path diverge from the expected path?
- Which expected API calls are MISSING from the trace?
- Which APIs behaved differently than expected?
- Are there error indicators in the trace?

### Step 3: Identify Package Version Root Causes
For each divergence point, determine:
- Which package is responsible for the missing/changed behavior?
- What specific version introduced or removed the required feature?
- Which EXACT version would restore the expected behavior?

### Step 4: Generate Recommendations
Provide SPECIFIC package versions that would fix each identified issue.

## Output Format

You MUST provide your response in the following EXACT JSON format (no markdown, no explanations outside the JSON):

```json
{
  "summary": "Brief overview of the execution path divergence",
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
      "current_version": "current version from requirements.txt",
      "recommended_version": "specific version that would work (EXACT version number)",
      "issue": "what's wrong with current version (be specific about API changes)",
      "reason": "why this version would fix the issue (explain how it enables the expected path)",
      "evidence_from_trace": "specific evidence from .api_calls.json or missing calls"
    }
  ],
  "root_cause": "Detailed explanation of why the exploit failed (focus on version-specific changes)",
  "recommended_actions": [
    "Specific action 1 with exact version numbers",
    "Specific action 2"
  ]
}
```

## Important Constraints
- **CRITICAL**: Analyze the execution PATH, not just individual APIs
- Compare expected vs actual execution flow systematically
- Focus ONLY on package version problems that affect the execution path
- Provide EXACT version numbers (e.g., "5.2" not ">=5.0" or "older version")
- For each recommended version, explain HOW it fixes the path divergence
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

                # Update with recommended versions
                updated_reqs = original_reqs.copy()
                changes_made = []

                for package in analysis_data['packages']:
                    pkg_name = package['name']
                    recommended_ver = package['recommended_version']
                    current_ver = package.get('current_version', 'unknown')

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

                    # Strategy 4: Exact match (case-sensitive fallback)
                    if not original_pkg_name and pkg_name in original_reqs:
                        original_pkg_name = pkg_name

                    if original_pkg_name:
                        # Use the original case from requirements.txt
                        updated_reqs[original_pkg_name] = recommended_ver
                        changes_made.append(f"  ✓ {original_pkg_name}: {current_ver} → {recommended_ver}")
                        print(f"  ✓ {original_pkg_name}: {current_ver} → {recommended_ver}")
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
            import traceback
            traceback.print_exc()

    except ImportError as e:
        print(f"❌ Error importing llm_client: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Fix mode analysis complete!")
    print("=" * 60)


def resolve_dependencies(mock_state_path=None, mode='mock', requirements_path=None, project_path=None, use_llm=True, python_version=None, num_dockerfiles="1"):
    """
    Analyze the .mock_state.json or .api_calls.json file to generate resolved version configurations.

    Args:
        mock_state_path: Optional path to .mock_state.json or .api_calls.json file
                        If not provided, defaults based on mode:
                        - mock mode: .venv/.mock_state.json
                        - real mode: .venv/.api_calls.json
        mode: 'mock' or 'real' - determines which file to read and how to process
        requirements_path: Optional path to requirements.txt file for package constraints
        project_path: Optional path to project directory for Docker volume mounting
        use_llm: If True (default), use LLM to generate Dockerfile content. If False, use template.
        python_version: Optional Python version to use for validation (e.g., '3.10', '3.11')
        num_dockerfiles: Number of Dockerfiles to generate: 'all' for all combinations, or a number (default: "1")

    This function calls resolve_dependencies.py to:
    - Read the state file containing intercepted API features
    - Query PyPI for available package versions
    - Use LLM inference to filter compatible versions
    - Generate resolved_versions.json with the final configuration
    """
    print("=" * 60)
    print(f"🔍 RESOLVE DEPENDENCIES MODE ({mode.upper()})")
    print("=" * 60)

    # Default path if not specified
    if mock_state_path is None:
        if mode == 'real':
            mock_state_path = os.path.join(os.getcwd(), ".venv", ".api_calls.json")
        else:
            mock_state_path = os.path.join(os.getcwd(), ".venv", ".mock_state.json")
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

    # Execute resolve_dependencies.py with the state file path, mode, requirements path, project path, use_llm, and python_version
    cmd = [sys.executable, resolve_script, mock_state_path, mode]
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
  # Reset environment with a requirements.txt file (mock mode, default)
  python main.py --reset --mode mock --requirements /path/to/requirements.txt

  # Reset environment in real mode (exact versions from requirements.txt)
  python main.py --reset --mode real --requirements /path/to/requirements.txt

  # Reset environment with a specific Python version
  python main.py --reset --mode mock --requirements /path/to/requirements.txt --python 3.10

  # Fix mode: Analyze exploit failures and identify package version issues
  python main.py --fix --requirements /path/to/requirements.txt --project /path/to/project --exploit /path/to/exploit1.sh,/path/to/exploit2.sh

  # Resolve dependencies using default .mock_state.json location (mock mode)
  python main.py --resolve --mode mock

  # Resolve dependencies using .api_calls.json location (real mode)
  python main.py --resolve --mode real

  # Resolve dependencies using custom state file path
  python main.py --resolve --mode mock /path/to/.mock_state.json
  python main.py --resolve --mode real /path/to/.api_calls.json

  # Resolve dependencies with custom requirements.txt file
  python main.py --resolve --mode real --requirements /path/to/requirements.txt

  # Resolve dependencies with project path for Docker volume mounting
  # Note: In 'real' mode, template-based Dockerfile generation is used by default
  python main.py --resolve --mode real --requirements /path/to/requirements.txt --project /path/to/project

  # Resolve dependencies in mock mode (uses LLM by default)
  python main.py --resolve --mode mock --requirements /path/to/requirements.txt --project /path/to/project

  # Force template-based generation in any mode with --no-llm flag
  python main.py --resolve --mode mock --no-llm
        """
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=['mock', 'real'],
        required=False,
        help="Environment mode: 'mock' for mock environment with Claude SDK, 'real' for real environment with exact package versions (required for --reset and --resolve)"
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
        help="Reset the virtual environment (requires --mode and --requirements)"
    )

    group.add_argument(
        "--resolve",
        nargs="?",
        const=True,
        metavar="STATE_FILE",
        help="Resolve dependencies from .mock_state.json or .api_calls.json (requires --mode, optional: specify custom path)"
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
        help="Force template-based Dockerfile generation (default behavior in 'real' mode, optional override in 'mock' mode)"
    )

    parser.add_argument(
        "--dockerfiles",
        type=str,
        metavar="NUMBER",
        default="1",
        help="Number of Dockerfiles to generate: 'all' for all combinations, or a number (default: 1)"
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
        if args.mode:
            parser.error("--fix cannot be used with --mode. Use only '--fix --requirements <file> --project <path> --exploit <scripts>'.")

        # Parse exploit scripts (comma-separated)
        exploit_scripts = [script.strip() for script in args.exploit.split(',')]

        # Mode is always 'real' for fix
        fix_environment(args.requirements, 'real', args.project, exploit_scripts)
    elif args.reset:
        if not args.mode:
            parser.error("--reset requires the --mode argument (mock or real).")
        if not args.requirements:
            parser.error("--reset requires the --requirements argument to specify the requirements file.")
        reset_environment(args.requirements, mode=args.mode, python_version=args.python)
    elif args.resolve:
        if not args.mode:
            parser.error("--resolve requires the --mode argument (mock or real).")
        # Determine if LLM should be used based on mode and user flags
        # In 'real' mode: default to template-based generation (use_llm=False)
        # In 'mock' mode: default to LLM-based generation (use_llm=True)
        # User can override with --no-llm flag in any mode
        if args.no_llm:
            use_llm = False
        else:
            # Default behavior based on mode
            use_llm = (args.mode == 'mock')

        # If args.resolve is True (no path provided), use default path
        if args.resolve is True:
            resolve_dependencies(mode=args.mode, requirements_path=args.requirements, project_path=args.project, use_llm=use_llm, python_version=args.python, num_dockerfiles=args.dockerfiles)
        else:
            # Custom path provided
            resolve_dependencies(args.resolve, mode=args.mode, requirements_path=args.requirements, project_path=args.project, use_llm=use_llm, python_version=args.python, num_dockerfiles=args.dockerfiles)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
