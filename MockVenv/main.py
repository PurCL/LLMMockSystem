#!/usr/bin/env python3
"""
MockVenv Main Entry Point

This script provides a command-line interface to access two core functionalities:
1. Reset Environment: Create a mock virtual environment from a requirements.txt file
2. Resolve Dependencies: Analyze .mock_state.json to generate resolved version configurations

Usage:
    python main.py --reset <path_to_requirements.txt>
    python main.py --resolve [path_to_mock_state.json]
    python main.py --help
"""

import sys
import os
import argparse
import subprocess


def reset_environment(requirements_path, mode='mock'):
    """
    Create a virtual environment based on the provided requirements.txt file.

    Args:
        requirements_path: Path to the requirements.txt file
        mode: Environment mode - 'mock' (default) or 'real'

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

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reset_script = os.path.join(script_dir, "reset_env.py")

    if not os.path.exists(reset_script):
        print(f"❌ Error: reset_env.py not found at: {reset_script}")
        sys.exit(1)

    # Execute reset_env.py with the requirements file path and mode as arguments
    try:
        subprocess.run([sys.executable, reset_script, requirements_path, mode], check=True)
        print("\n✅ Environment reset completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during environment reset: {e}")
        sys.exit(1)


def resolve_dependencies(mock_state_path=None, mode='mock', requirements_path=None, project_path=None, use_llm=True):
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

    # Execute resolve_dependencies.py with the state file path, mode, requirements path, project path, and use_llm
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
  python main.py --reset /path/to/requirements.txt

  # Reset environment in real mode (exact versions from requirements.txt)
  python main.py --reset /path/to/requirements.txt --mode real

  # Resolve dependencies using default .mock_state.json location (mock mode)
  python main.py --resolve

  # Resolve dependencies using .api_calls.json location (real mode)
  python main.py --resolve --mode real

  # Resolve dependencies using custom state file path
  python main.py --resolve /path/to/.mock_state.json
  python main.py --resolve /path/to/.api_calls.json --mode real

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

    # Create mutually exclusive group for the two main operations
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--reset",
        action="store_true",
        help="Reset the virtual environment (requires --requirements file path)"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=['mock', 'real'],
        default='mock',
        help="Environment mode: 'mock' (default) for mock environment with Claude SDK, 'real' for real environment with exact package versions"
    )

    parser.add_argument(
        "--requirements",
        type=str,
        metavar="REQUIREMENTS_FILE",
        help="Path to requirements.txt file for package constraints (used with --resolve)"
    )

    parser.add_argument(
        "--project",
        type=str,
        metavar="PROJECT_PATH",
        help="Path to project directory for Docker volume mounting (used with --resolve)"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Force template-based Dockerfile generation (default behavior in 'real' mode, optional override in 'mock' mode)"
    )

    group.add_argument(
        "--resolve",
        nargs="?",
        const=True,
        metavar="STATE_FILE",
        help="Resolve dependencies from .mock_state.json or .api_calls.json (optional: specify custom path)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate operation based on user input
    if args.reset:
        if not args.requirements:
            parser.error("--reset requires the --requirements argument to specify the requirements file.")
        reset_environment(args.requirements, mode=args.mode)
    elif args.resolve:
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
            resolve_dependencies(mode=args.mode, requirements_path=args.requirements, project_path=args.project, use_llm=use_llm)
        else:
            # Custom path provided
            resolve_dependencies(args.resolve, mode=args.mode, requirements_path=args.requirements, project_path=args.project, use_llm=use_llm)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
