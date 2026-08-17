#!/usr/bin/env python3
"""
Recursive API Analysis Pipeline
This script automates the process of:
1. Extracting library calls from a script
2. Verifying package version compatibility
3. Recursively processing newly discovered APIs until depth limit reached
4. Extracting version compatibility results
5. Running end-to-end verification tests

Usage:
    python3 run_recursive_api_analysis.py <script_path> --CVE <cve_id> --requirements <requirements_file>

Example:
    python3 run_recursive_api_analysis.py /path/to/run_exploit.sh --CVE CVE-2026-1462 --requirements requirements.txt
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import shutil
import time
import requests


class RecursiveAPIAnalyzer:
    """Main controller for recursive API analysis pipeline"""

    def __init__(self, script_path: str, cve_id: str, max_depth: int = 10, package: str = None, versions: List[str] = None, vulnerable_packages: Dict[str, List[str]] = None, requirements: str = None):
        self.script_path = Path(script_path).absolute()
        self.cve_id = cve_id
        self.api_log_dir = Path(f"{cve_id}_api_log").absolute()
        self.max_depth = max_depth
        self.base_dir = Path(__file__).parent.absolute()
        self.package = package
        self.versions = versions
        self.vulnerable_packages = vulnerable_packages or {}
        self.requirements = requirements

        # Track processed directories to avoid infinite loops
        self.processed_dirs = set()

        # Load PyPI import mapping
        self.pypi_import_mapping = self._load_pypi_import_mapping(
            str(self.base_dir / "pypi_import_mapping.json")
        )

    def _load_pypi_import_mapping(self, mapping_file: str) -> Dict[str, str]:
        """Load PyPI import mapping"""
        if not os.path.exists(mapping_file):
            print(f"Warning: pypi_import_mapping.json not found at {mapping_file}")
            return {}

        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                original_mapping = json.load(f)

            # Reverse mapping: {import_name: pypi_package_name}
            reversed_mapping = {}
            for pypi_name, import_name in original_mapping.items():
                reversed_mapping[import_name] = pypi_name

            print(f"[Mapping Loader] Loaded {len(reversed_mapping)} package mappings from {mapping_file}")
            return reversed_mapping
        except Exception as e:
            print(f"Warning: Failed to load mapping file {mapping_file}: {e}")
            return {}

    def get_pypi_package_name(self, import_name: str) -> str:
        """
        Get package name on PyPI (may differ from import name)

        Args:
            import_name: Name used when importing in Python (case-sensitive)
                        Example: 'PIL', 'OpenSSL', 'cv2'

        Returns:
            Package name on PyPI (used for pip install and PyPI API queries)
            Example: 'Pillow', 'pyOpenSSL', 'opencv-python'

        Note:
            If not found in mapping, returns original import_name
            No case conversion or - to _ replacement is performed
        """
        if import_name in self.pypi_import_mapping:
            pypi_name = self.pypi_import_mapping[import_name]
            print(f"[Mapping] Using PyPI package name '{pypi_name}' for import name '{import_name}'")
            return pypi_name
        # Return original name without any conversion
        return import_name

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
            str(self.api_log_dir),
            str(self.requirements)
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
        """Step 2: Verify package version compatibility"""
        package_name = api_file.stem.replace('_apis', '')

        print(f"\n{'#'*60}")
        print(f"STEP 2: Verify Version Compatibility for {package_name}")
        print(f"{'#'*60}")

        cmd = [
            'python3',
            str(self.base_dir / 'verify_compatible_package_versions.py'),
            str(api_file)
        ]

        # Get PyPI package name for version matching
        pypi_package_name = self.get_pypi_package_name(package_name)

        # Check if this is the specific package and add --versions parameter
        # First check vulnerable_packages dict, then fall back to package/versions
        # Use pypi_package_name for matching
        if self.vulnerable_packages and pypi_package_name in self.vulnerable_packages:
            cmd.extend(['--versions'] + self.vulnerable_packages[pypi_package_name])
        elif self.package and self.versions and pypi_package_name == self.package:
            cmd.extend(['--versions'] + self.versions)

        success, stdout, stderr = self.run_command(
            cmd,
            f"Verifying compatible versions for {package_name}"
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
        """Check if downstream API log directory was generated"""
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

            # Step 2: Verify compatibility
            success, compatibility_json = self.step2_verify_compatibility(api_file)
            if not success:
                print(f"⚠️ Skipping {api_file.name} due to compatibility verification failure")
                continue

            # Check if downstream API log was generated
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Recursive API Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python3 run_recursive_api_analysis.py /home/user/run_exploit.sh --CVE CVE-2026-1462 --requirements requirements.txt
  python3 run_recursive_api_analysis.py /home/user/run_exploit.sh --CVE CVE-2026-1462 --requirements requirements.txt --max_depth 5
  python3 run_recursive_api_analysis.py /home/user/run_exploit.sh --CVE CVE-2026-1462 --requirements requirements.txt --package keras --versions 2.10.0 2.9.0
  python3 run_recursive_api_analysis.py /home/user/run_exploit.sh --CVE CVE-2026-1462 --requirements requirements.txt --vulnerable-file /path/to/vulnerable.json

Description:
  This script automates the entire API analysis pipeline:
  1. Extracts library calls from the target script
  2. Verifies version compatibility for each library
  3. Recursively processes newly discovered APIs
  4. Extracts version compatibility results to {CVE}-compatibility.json
  5. Records timing statistics to {CVE}-statistics.json
  6. Runs end-to-end verification tests and saves results to {CVE}-exploit_test_results.json

  The API logs will be automatically stored in {CVE}_api_log directory.
        """
    )

    parser.add_argument('script_path', type=str, help='Path to the script to analyze (e.g., run_exploit.sh)')
    parser.add_argument('--CVE', type=str, required=True, help='CVE identifier (e.g., CVE-2026-1462)')
    parser.add_argument('--max_depth', type=int, default=10, help='Maximum recursion depth (default: 10)')
    parser.add_argument('--package', type=str, help='Specific package name to apply version filtering')
    parser.add_argument('--versions', nargs='+', type=str, help='List of versions to test for the specified package')
    parser.add_argument('--vulnerable-file', type=str, help='Path to JSON file containing vulnerable packages (format: {"package": ["version1", "version2"]})')
    parser.add_argument('--requirements', type=str, required=True, help='Path to requirements.txt file')

    args = parser.parse_args()

    # Validate parameter constraints
    # --package and --versions must appear together
    if (args.package is not None) != (args.versions is not None):
        print(f"❌ Error: --package and --versions must be used together")
        sys.exit(1)

    # --package/--versions and --vulnerable-file are mutually exclusive
    if (args.package is not None or args.versions is not None) and args.vulnerable_file is not None:
        print(f"❌ Error: --package/--versions and --vulnerable-file are mutually exclusive")
        sys.exit(1)

    # Validate inputs
    if not Path(args.script_path).exists():
        print(f"❌ Error: Script not found: {args.script_path}")
        sys.exit(1)

    if not Path(args.requirements).exists():
        print(f"❌ Error: Requirements file not found: {args.requirements}")
        sys.exit(1)

    # Load vulnerable packages from JSON file if provided
    vulnerable_packages = None
    if args.vulnerable_file:
        vulnerable_file_path = Path(args.vulnerable_file)
        if not vulnerable_file_path.exists():
            print(f"❌ Error: Vulnerable file not found: {args.vulnerable_file}")
            sys.exit(1)

        try:
            with open(vulnerable_file_path, 'r', encoding='utf-8') as f:
                vulnerable_packages = json.load(f)

            # Validate JSON structure
            if not isinstance(vulnerable_packages, dict):
                print(f"❌ Error: Vulnerable file must contain a JSON object (dict)")
                sys.exit(1)

            for pkg, versions in vulnerable_packages.items():
                if not isinstance(versions, list):
                    print(f"❌ Error: Versions for package '{pkg}' must be a list")
                    sys.exit(1)

            print(f"✓ Loaded {len(vulnerable_packages)} vulnerable packages from {args.vulnerable_file}")

        except json.JSONDecodeError as e:
            print(f"❌ Error: Failed to parse JSON file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: Failed to read vulnerable file: {e}")
            sys.exit(1)

    # Start timing
    start_time = time.time()

    # Create analyzer and run
    analyzer = RecursiveAPIAnalyzer(
        args.script_path,
        args.CVE,
        args.max_depth,
        args.package,
        args.versions,
        vulnerable_packages,
        args.requirements
    )
    success = analyzer.run()

    if not success:
        print("\n❌ RecursiveAPIAnalyzer failed")
        sys.exit(1)

    # Run extract_version_compatibility.py
    print(f"\n{'#'*80}")
    print("Running extract_version_compatibility.py")
    print(f"{'#'*80}")

    compatibility_output = f"{args.CVE}-compatibility.json"
    extract_cmd = [
        'python3',
        'extract_version_compatibility.py',
        str(analyzer.api_log_dir),
        compatibility_output
    ]

    print(f"Command: {' '.join(extract_cmd)}")
    try:
        result = subprocess.run(
            extract_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.absolute()),
            timeout=1800
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"\n❌ extract_version_compatibility.py failed with return code {result.returncode}")
            sys.exit(1)

        print(f"✓ Successfully generated {compatibility_output}")

    except Exception as e:
        print(f"\n❌ Error running extract_version_compatibility.py: {e}")
        sys.exit(1)

    # Record elapsed time
    elapsed_time = time.time() - start_time

    # Save statistics
    statistics_output = f"{args.CVE}-statistics.json"
    statistics = {
        "CVE": args.CVE,
        "script_path": str(args.script_path),
        "api_log_dir": str(analyzer.api_log_dir),
        "elapsed_time_seconds": elapsed_time,
        "elapsed_time_formatted": f"{elapsed_time:.2f}s"
    }

    try:
        with open(statistics_output, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Statistics saved to {statistics_output}")
        print(f"Total elapsed time: {elapsed_time:.2f} seconds")
    except Exception as e:
        print(f"\n⚠️ Warning: Failed to save statistics: {e}")

    # Run end_to_end_verify_version_combinations.py
    print(f"\n{'#'*80}")
    print("Running end_to_end_verify_version_combinations.py")
    print(f"{'#'*80}")

    exploit_test_output = f"{args.CVE}-exploit_test_results.json"
    verify_cmd = [
        'python3',
        'end_to_end_verify_version_combinations.py',
        args.script_path,
        compatibility_output,
        '-n', '10',
        '-o', exploit_test_output
    ]

    print(f"Command: {' '.join(verify_cmd)}")
    try:
        result = subprocess.run(
            verify_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.absolute()),
            timeout=3600  # 1 hour timeout for testing
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"\n❌ end_to_end_verify_version_combinations.py failed with return code {result.returncode}")
            sys.exit(1)

        print(f"✓ Successfully generated {exploit_test_output}")

    except Exception as e:
        print(f"\n❌ Error running end_to_end_verify_version_combinations.py: {e}")
        sys.exit(1)

    print(f"\n{'#'*80}")
    print("ALL STEPS COMPLETED SUCCESSFULLY!")
    print(f"{'#'*80}")
    print(f"Generated files:")
    print(f"  - {compatibility_output}")
    print(f"  - {statistics_output}")
    print(f"  - {exploit_test_output}")

    sys.exit(0)


if __name__ == "__main__":
    main()
