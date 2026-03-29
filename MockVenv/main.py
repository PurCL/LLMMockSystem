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


def reset_environment(requirements_path):
    """
    Create a mock virtual environment based on the provided requirements.txt file.

    Args:
        requirements_path: Path to the requirements.txt file

    This function calls reset_env.py to:
    - Destroy the old .venv environment
    - Rebuild a new virtual environment using uv
    - Install whitelisted packages from requirements.txt
    - Inject LLM mock hooks into the environment
    """
    print("=" * 60)
    print("🔄 RESET ENVIRONMENT MODE")
    print("=" * 60)

    if not os.path.exists(requirements_path):
        print(f"❌ Error: Requirements file not found: {requirements_path}")
        sys.exit(1)

    print(f"📋 Using requirements file: {requirements_path}")
    print(f"📂 Target directory: {os.getcwd()}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reset_script = os.path.join(script_dir, "reset_env.py")

    if not os.path.exists(reset_script):
        print(f"❌ Error: reset_env.py not found at: {reset_script}")
        sys.exit(1)

    # Execute reset_env.py with the requirements file path as argument
    try:
        subprocess.run([sys.executable, reset_script, requirements_path], check=True)
        print("\n✅ Environment reset completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during environment reset: {e}")
        sys.exit(1)


def resolve_dependencies(mock_state_path=None):
    """
    Analyze the .mock_state.json file to generate resolved version configurations.

    Args:
        mock_state_path: Optional path to .mock_state.json file
                        If not provided, defaults to .venv/.mock_state.json

    This function calls resolve_dependencies.py to:
    - Read the mock state file containing intercepted API features
    - Query PyPI for available package versions
    - Use LLM inference to filter compatible versions
    - Generate resolved_versions.json with the final configuration
    """
    print("=" * 60)
    print("🔍 RESOLVE DEPENDENCIES MODE")
    print("=" * 60)

    # Default path if not specified
    if mock_state_path is None:
        mock_state_path = os.path.join(os.getcwd(), ".venv", ".mock_state.json")
        print(f"📂 Using default mock state path: {mock_state_path}")
    else:
        print(f"📂 Using custom mock state path: {mock_state_path}")

    if not os.path.exists(mock_state_path):
        print(f"❌ Error: Mock state file not found: {mock_state_path}")
        print(f"💡 Hint: Run the reset environment first or provide a valid path")
        sys.exit(1)

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resolve_script = os.path.join(script_dir, "resolve_dependencies.py")

    if not os.path.exists(resolve_script):
        print(f"❌ Error: resolve_dependencies.py not found at: {resolve_script}")
        sys.exit(1)

    # Execute resolve_dependencies.py with the mock state file path
    try:
        subprocess.run([sys.executable, resolve_script, mock_state_path], check=True)
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
  python main.py --reset /path/to/requirements.txt

  # Resolve dependencies using default .mock_state.json location
  python main.py --resolve

  # Resolve dependencies using custom .mock_state.json path
  python main.py --resolve /path/to/.mock_state.json
        """
    )

    # Create mutually exclusive group for the two main operations
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--reset",
        metavar="REQUIREMENTS_FILE",
        type=str,
        help="Reset the virtual environment using the specified requirements.txt file"
    )

    group.add_argument(
        "--resolve",
        nargs="?",
        const=True,
        metavar="MOCK_STATE_FILE",
        help="Resolve dependencies from .mock_state.json (optional: specify custom path)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate operation based on user input
    if args.reset:
        reset_environment(args.reset)
    elif args.resolve:
        # If args.resolve is True (no path provided), use default path
        if args.resolve is True:
            resolve_dependencies()
        else:
            # Custom path provided
            resolve_dependencies(args.resolve)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
