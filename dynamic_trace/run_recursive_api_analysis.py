#!/usr/bin/env python3
"""
Recursive API Analysis Pipeline
This script automates the process of:
1. Extracting library calls from a script
2. Verifying package version compatibility (包含trace功能)
3. Recursively processing newly discovered APIs until depth limit reached

Usage:
    python3 run_recursive_api_analysis.py <script_path> <api_log_dir>

Example:
    python3 run_recursive_api_analysis.py /path/to/run_exploit.sh /path/to/api_log
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import shutil


class RecursiveAPIAnalyzer:
    """Main controller for recursive API analysis pipeline"""

    def __init__(self, script_path: str, api_log_dir: str, max_depth: int = 10):
        self.script_path = Path(script_path).absolute()
        self.api_log_dir = Path(api_log_dir).absolute()
        self.max_depth = max_depth
        self.base_dir = Path(__file__).parent.absolute()

        # Track processed directories to avoid infinite loops
        self.processed_dirs = set()

    def run_command(self, cmd: List[str], description: str, cwd: Path = None) -> Tuple[bool, str, str]:
        """Execute a shell command and return success status and output"""
        print(f"\n{'='*60}")
        print(f"{description}")
        print(f"{'='*60}")
        print(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(cwd) if cwd else None,
                timeout=1800  # 30 minutes timeout
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr, file=sys.stderr)

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after 30 minutes"
            print(error_msg, file=sys.stderr)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            print(error_msg, file=sys.stderr)
            return False, "", error_msg

    def step1_extract_library_calls(self) -> bool:
        """Step 1: Extract library calls from the script"""
        print(f"\n{'#'*60}")
        print("STEP 1: Extract Library Calls")
        print(f"{'#'*60}")

        # Remove existing api_log_dir
        if self.api_log_dir.exists():
            print(f"Removing existing directory: {self.api_log_dir}")
            shutil.rmtree(self.api_log_dir)

        cmd = [
            'python3',
            str(self.base_dir / 'extract_library_calls.py'),
            str(self.script_path),
            str(self.api_log_dir)
        ]

        success, stdout, stderr = self.run_command(
            cmd,
            "Extracting library API calls from script"
        )

        if not success:
            print("❌ Failed to extract library calls")
            return False

        print("✓ Successfully extracted library calls")
        return True

    def find_api_files(self, directory: Path) -> List[Path]:
        """Find all *_apis.py files in a directory"""
        api_files = list(directory.glob("*_apis.py"))
        return sorted(api_files)

    def step2_verify_compatibility(self, api_file: Path) -> Tuple[bool, Path]:
        """Step 2: Verify package version compatibility (包含trace功能)"""
        package_name = api_file.stem.replace('_apis', '')

        print(f"\n{'#'*60}")
        print(f"STEP 2: Verify Version Compatibility for {package_name}")
        print(f"{'#'*60}")

        cmd = [
            'python3',
            str(self.base_dir / 'verify_compatible_package_versions.py'),
            str(api_file)
        ]

        success, stdout, stderr = self.run_command(
            cmd,
            f"Verifying compatible versions for {package_name} (包含trace)"
        )

        if not success:
            print(f"❌ Failed to verify compatibility for {package_name}")
            return False, None

        # Find the generated compatibility JSON
        compatibility_json = api_file.parent / f"{package_name}_compatibility_results.json"

        if not compatibility_json.exists():
            print(f"❌ Compatibility JSON not found: {compatibility_json}")
            return False, None

        print(f"✓ Successfully generated compatibility JSON: {compatibility_json.name}")
        return True, compatibility_json

    def check_api_log_generated(self, api_file: Path) -> Tuple[bool, Path]:
        """检查是否生成了下游API log目录"""
        package_name = api_file.stem.replace('_apis', '')
        output_dir = api_file.parent / f"{package_name}_api_log"

        if output_dir.exists() and output_dir.is_dir():
            return True, output_dir
        else:
            return False, None

    def process_directory(self, directory: Path, depth: int) -> None:
        """Recursively process a directory containing *_apis.py files"""

        # Check depth limit
        if depth >= self.max_depth:
            print(f"\n⚠️ Reached maximum depth limit ({self.max_depth})")
            return

        # Avoid processing the same directory twice
        dir_key = str(directory.absolute())
        if dir_key in self.processed_dirs:
            print(f"\n⚠️ Already processed directory: {directory}")
            return

        self.processed_dirs.add(dir_key)

        print(f"\n{'='*80}")
        print(f"PROCESSING DIRECTORY (Depth {depth}): {directory}")
        print(f"{'='*80}")

        # Find all *_apis.py files
        api_files = self.find_api_files(directory)

        if not api_files:
            print(f"No *_apis.py files found in {directory}")
            return

        print(f"Found {len(api_files)} API files to process:")
        for api_file in api_files:
            print(f"  - {api_file.name}")

        # Track newly created directories for recursive processing
        new_directories = []

        # Process each API file
        for api_file in api_files:
            print(f"\n{'*'*80}")
            print(f"Processing API file: {api_file.name}")
            print(f"{'*'*80}")

            # Extract package name
            package_name = api_file.stem.replace('_apis', '')

            # if package_name != 'keras' and package_name != 'tensorflow':
            #     print(f"⚠️ Skipping {package_name} as it is not 'keras' or 'tensorflow'")
            #     continue

            # Step 2: Verify compatibility (包含trace功能)
            success, compatibility_json = self.step2_verify_compatibility(api_file)
            if not success:
                print(f"⚠️ Skipping {api_file.name} due to compatibility verification failure")
                continue

            # 检查是否生成了下游API log
            has_api_log, output_dir = self.check_api_log_generated(api_file)

            if has_api_log and output_dir:
                # Check the output directory for new API files
                new_api_files = self.find_api_files(output_dir)
                if new_api_files:
                    print(f"✓ Found {len(new_api_files)} new API files in {output_dir.name}")
                    new_directories.append(output_dir)
                else:
                    print(f"⚠️ No new API files generated in {output_dir.name}")
            else:
                print(f"⚠️ No API log directory generated for {package_name}")

        # Recursively process new directories
        if new_directories:
            print(f"\n{'='*80}")
            print(f"Found {len(new_directories)} new directories to process")
            print(f"{'='*80}")

            for new_dir in new_directories:
                self.process_directory(new_dir, depth + 1)
        else:
            print(f"\n{'='*80}")
            print(f"No new directories generated at depth {depth}")
            print(f"{'='*80}")

    def generate_final_report(self) -> None:
        """Generate a final summary report"""
        print(f"\n{'#'*80}")
        print("FINAL SUMMARY REPORT")
        print(f"{'#'*80}\n")

        print(f"Script analyzed: {self.script_path}")
        print(f"API log directory: {self.api_log_dir}")
        print(f"Maximum depth: {self.max_depth}")
        print(f"Directories processed: {len(self.processed_dirs)}")

        print(f"\n{'#'*80}")
        print("Analysis complete!")
        print(f"{'#'*80}")

    def run(self) -> bool:
        """Main entry point - orchestrates the entire pipeline"""
        print(f"\n{'#'*80}")
        print("RECURSIVE API ANALYSIS PIPELINE")
        print(f"{'#'*80}")
        print(f"Script: {self.script_path}")
        print(f"API Log Directory: {self.api_log_dir}")
        print(f"Max Depth: {self.max_depth}")
        print(f"{'#'*80}\n")

        # Step 1: Extract library calls
        if not self.step1_extract_library_calls():
            print("\n❌ Pipeline failed at Step 1")
            return False

        # Check if any API files were generated
        api_files = self.find_api_files(self.api_log_dir)
        if not api_files:
            print(f"\n⚠️ No API files generated in {self.api_log_dir}")
            return False

        print(f"\n✓ Initial extraction generated {len(api_files)} API files")

        # Start recursive processing from depth 0
        self.process_directory(self.api_log_dir, depth=0)

        # Generate final report
        self.generate_final_report()

        return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 run_recursive_api_analysis.py <script_path> <api_log_dir> [max_depth]")
        print()
        print("Arguments:")
        print("  script_path  - Path to the script to analyze (e.g., run_exploit.sh)")
        print("  api_log_dir  - Directory to store API logs")
        print("  max_depth    - Optional: Maximum recursion depth (default: 10)")
        print()
        print("Example:")
        print("  python3 run_recursive_api_analysis.py \\")
        print("    /home/user/run_exploit.sh \\")
        print("    /home/user/pyright/api_log")
        print()
        print("Description:")
        print("  This script automates the entire API analysis pipeline:")
        print("  1. Extracts library calls from the target script")
        print("  2. Verifies version compatibility for each library (包含trace功能)")
        print("  3. Recursively processes newly discovered APIs")
        sys.exit(1)

    script_path = sys.argv[1]
    api_log_dir = sys.argv[2]
    max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    # Validate inputs
    if not Path(script_path).exists():
        print(f"❌ Error: Script not found: {script_path}")
        sys.exit(1)

    # Create analyzer and run
    analyzer = RecursiveAPIAnalyzer(script_path, api_log_dir, max_depth)
    success = analyzer.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
