#!/usr/bin/env python3
"""
Script to test all compatible version combinations from pyright results.

This script:
1. Parses all *_version_compatibility.json files in results/
2. Extracts compatible versions for each package
3. Tests combinations by installing packages and running exploit
4. Records success/failure for each combination

Usage examples:
    # Test only core packages (keras, tensorflow, numpy) - Recommended
    python3 get_all_compatible_versions_final.py --mode core

    # Test random sample of 50 combinations
    python3 get_all_compatible_versions_final.py --mode sample --sample-size 50

    # Test with detailed output
    python3 get_all_compatible_versions_final.py --mode core --verbose
"""

import json
import os
import subprocess
import itertools
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys
import argparse

# Configuration
# Use relative path from script location
PYRIGHT_DIR = Path(__file__).parent.resolve()
BASE_DIR = PYRIGHT_DIR.parent
RESULTS_DIR = PYRIGHT_DIR / "results"
VENV_PATH = BASE_DIR / ".venv"
PYTHON_BIN = VENV_PATH / "bin" / "python"
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
EXPLOIT_SCRIPT = BASE_DIR / "run_exploit.sh"

# Core packages that are most likely to affect exploit success
CORE_PACKAGES = ["keras", "tensorflow", "numpy"]

def parse_compatibility_files(only_core: bool = False) -> Dict[str, List[str]]:
    """
    Parse all *_version_compatibility.json files and extract compatible versions.
    """
    compatible_versions = {}

    print(f"[*] Scanning {RESULTS_DIR} for compatibility files...")

    for json_file in RESULTS_DIR.glob("*_version_compatibility.json"):
        package_name = json_file.stem.replace("_version_compatibility", "")

        # Skip if only_core and not a core package
        if only_core and package_name not in CORE_PACKAGES:
            continue

        print(f"[*] Processing {json_file.name}...")

        with open(json_file, 'r') as f:
            data = json.load(f)

        # Extract compatible versions
        compatible = []
        for result in data.get("results", []):
            if result.get("status") == "compatible":
                compatible.append(result["version"])

        if compatible:
            compatible_versions[package_name] = compatible
            print(f"    Found {len(compatible)} compatible versions for {package_name}")
        else:
            print(f"    WARNING: No compatible versions found for {package_name}")

    return compatible_versions

def setup_venv():
    """Setup fresh virtual environment and install base requirements."""
    print("\n" + "="*80)
    print("[*] Setting up virtual environment")
    print("="*80)

    # Remove existing venv
    if VENV_PATH.exists():
        print(f"[*] Removing existing venv at {VENV_PATH}")
        subprocess.run(["rm", "-rf", str(VENV_PATH)], check=False)

    # Create new venv
    print(f"[*] Creating new venv with python3...", flush=True)
    result = subprocess.run(
        ["python3", "-m", "venv", str(VENV_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create venv: {result.stderr}")
    print("    ✓ venv created")

    # Install base requirements without deps
    print(f"[*] Installing base requirements (this may take a minute)...", flush=True)
    cmd = [
        "pip", "install",
        "--no-deps",
        "-r", str(REQUIREMENTS_FILE)
    ]
    result = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode != 0:
        print(f"    Error: {result.stderr}")
        raise RuntimeError(f"Failed to install base requirements")
    print("    ✓ base requirements installed")

    print("[+] Virtual environment setup complete\n")

def install_package_version(package_name: str, version: str, verbose: bool = True) -> bool:
    """
    Install a specific package version.
    """
    if verbose:
        print(f"    Installing {package_name}=={version}...", end=" ", flush=True)

    cmd = [
        "pip", "install",
        "--no-deps",
        f"{package_name}=={version}"
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            env={**os.environ, 'VIRTUAL_ENV': str(VENV_PATH)},
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            if verbose:
                print("✓")
            return True
        else:
            if verbose:
                print(f"✗ (rc={result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        if verbose:
            print("✗ (timeout)")
        return False
    except Exception as e:
        if verbose:
            print(f"✗ (error: {e})")
        return False

def run_exploit(verbose: bool = True) -> Tuple[bool, str, str]:
    """
    Run the exploit script and check if it succeeds.
    """
    if verbose:
        print("    Running exploit script...", end=" ", flush=True)

    try:
        # Run the exploit script with python aliased to venv python
        env = os.environ.copy()
        env["PATH"] = f"{VENV_PATH / 'bin'}:{env['PATH']}"

        result = subprocess.run(
            ["bash", str(EXPLOIT_SCRIPT)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )

        stdout = result.stdout
        stderr = result.stderr

        # Check for exploit success markers
        success = ("exploit successful" in stdout.lower() or
                  "exploitation successful" in stdout.lower() or
                  "[+] Exploit succeeded" in stdout or
                  "SUCCESS" in stdout)

        if verbose:
            if success:
                print("✓ SUCCESS")
            else:
                print("✗ FAILED")

        return success, stdout, stderr

    except subprocess.TimeoutExpired:
        if verbose:
            print("✗ TIMEOUT")
        return False, "", "Timeout after 120 seconds"
    except Exception as e:
        if verbose:
            print(f"✗ ERROR: {e}")
        return False, "", str(e)

def test_version_combination(
    combo: Dict[str, str],
    combo_index: int,
    total_combos: int,
    verbose: bool = True
) -> Dict:
    """
    Test a specific version combination.
    """
    if verbose:
        print("\n" + "="*80)
        print(f"[*] Testing combination {combo_index}/{total_combos}")
        print("="*80)
        print("Version combination:")
        for pkg, ver in sorted(combo.items()):
            print(f"  - {pkg}: {ver}")
        print()
    else:
        combo_str = ", ".join(f"{p}={v}" for p, v in sorted(combo.items()))
        print(f"[{combo_index}/{total_combos}] {combo_str[:80]}...", end=" ", flush=True)

    result = {
        "combination_index": combo_index,
        "versions": combo,
        "installation_success": True,
        "failed_packages": [],
        "exploit_success": False,
        "exploit_stdout": "",
        "exploit_stderr": "",
        "timestamp": datetime.now().isoformat()
    }

    # Install each package version
    if verbose:
        print("[*] Installing packages:")
    for package_name, version in sorted(combo.items()):
        if not install_package_version(package_name, version, verbose):
            result["installation_success"] = False
            result["failed_packages"].append(f"{package_name}=={version}")

    # If installation failed, skip exploit test
    if not result["installation_success"]:
        if verbose:
            print(f"\n[!] Skipping exploit test due to installation failures")
        else:
            print("INSTALL_FAIL")
        return result

    # Run exploit
    if verbose:
        print("\n[*] Running exploit:")
    success, stdout, stderr = run_exploit(verbose)

    result["exploit_success"] = success
    result["exploit_stdout"] = stdout
    result["exploit_stderr"] = stderr

    if not verbose:
        status = "SUCCESS ✓" if success else "FAIL ✗"
        print(status)

    return result

def save_results(output_file: Path, all_results: List[Dict],
                 success_count: int, failure_count: int,
                 total_combos: int, test_mode: str):
    """Save results to JSON file."""
    output_data = {
        "test_info": {
            "cve": "CVE-2026-1462",
            "test_date": datetime.now().isoformat(),
            "base_directory": str(BASE_DIR),
            "test_mode": test_mode,
            "total_combinations": total_combos,
            "tested_so_far": len(all_results)
        },
        "summary": {
            "successful_exploits": success_count,
            "failed_exploits": failure_count,
            "success_rate": f"{success_count/len(all_results)*100:.2f}%" if all_results else "0%"
        },
        "results": all_results
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Test compatible version combinations for CVE-2026-1462",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test core packages only (recommended):
  %(prog)s --mode core

  # Test 100 random combinations:
  %(prog)s --mode sample --sample-size 100

  # Test with verbose output:
  %(prog)s --mode core --verbose
        """
    )

    parser.add_argument(
        "--mode",
        choices=["all", "core", "sample"],
        default="core",
        help="Test mode: 'all' (all packages), 'core' (keras/tensorflow/numpy), 'sample' (random)"
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Number of random combinations in sample mode (default: 100)"
    )

    parser.add_argument(
        "--max-combos",
        type=int,
        default=100000,
        help="Maximum combinations before warning (default: 100000)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output for each test"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (default: auto-generated)"
    )

    args = parser.parse_args()

    print("="*80)
    print("CVE-2026-1462 Compatible Version Combination Tester")
    print("="*80)
    print(f"Base directory: {BASE_DIR}")
    print(f"Mode: {args.mode}")
    print()

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = PYRIGHT_DIR / f"exploit_test_results_{args.mode}_{timestamp}.json"

    print(f"Output file: {output_file}\n")

    # Parse compatibility files
    only_core = (args.mode == "core")
    compatible_versions = parse_compatibility_files(only_core)

    if not compatible_versions:
        print("\n[!] ERROR: No compatible versions found!")
        sys.exit(1)

    print("\n" + "="*80)
    print("Summary of compatible versions:")
    print("="*80)
    for pkg, versions in sorted(compatible_versions.items()):
        print(f"{pkg}: {len(versions)} versions")

    # Calculate total combinations
    total_combos = 1
    for versions in compatible_versions.values():
        total_combos *= len(versions)

    print(f"\n[*] Total possible combinations: {total_combos:,}")

    # Determine which combinations to test
    if args.mode == "sample":
        num_tests = min(args.sample_size, total_combos)
        print(f"[*] Will test {num_tests} random samples")
    elif total_combos > args.max_combos:
        print(f"\n[!] WARNING: {total_combos:,} combinations exceed max ({args.max_combos:,})")
        print(f"[!] Consider using --mode core or --mode sample")
        print(f"[!] Or increase --max-combos limit")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        num_tests = total_combos
    else:
        num_tests = total_combos
        print(f"[*] Will test all {num_tests:,} combinations")

    # Setup virtual environment
    setup_venv()

    # Generate combinations to test
    print("\n" + "="*80)
    print("[*] Generating version combinations...")
    print("="*80)

    package_names = sorted(compatible_versions.keys())
    version_lists = [compatible_versions[pkg] for pkg in package_names]

    if args.mode == "sample":
        # Generate random sample without materializing all combinations
        print("[*] Generating random sample...", flush=True)
        combinations_to_test = []

        # Generate random combinations
        for _ in range(num_tests):
            # Randomly select one version for each package
            combo_tuple = tuple(random.choice(versions) for versions in version_lists)
            combinations_to_test.append(combo_tuple)

        print(f"[+] Generated {len(combinations_to_test)} random combinations")
    else:
        # Test all combinations
        print("[*] Generating all combinations...", flush=True)
        combinations_to_test = list(itertools.product(*version_lists))
        print(f"[+] Generated {len(combinations_to_test)} combinations")

    all_results = []
    success_count = 0
    failure_count = 0

    print(f"\n[*] Starting tests...\n")

    # Test each combination
    for i, version_tuple in enumerate(combinations_to_test, 1):
        combo = dict(zip(package_names, version_tuple))

        result = test_version_combination(combo, i, num_tests, args.verbose)
        all_results.append(result)

        if result["exploit_success"]:
            success_count += 1
        else:
            failure_count += 1

        # Save results periodically (every 10 tests)
        if i % 10 == 0:
            save_results(output_file, all_results, success_count, failure_count,
                        total_combos, args.mode)
            print(f"    [Progress saved: {i}/{num_tests}, Success rate: {success_count/i*100:.1f}%]")

    # Final save
    save_results(output_file, all_results, success_count, failure_count,
                total_combos, args.mode)

    # Print final summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Total combinations tested: {len(all_results)}")
    print(f"Successful exploits: {success_count}")
    print(f"Failed exploits: {failure_count}")
    if all_results:
        print(f"Success rate: {success_count/len(all_results)*100:.2f}%")
    print(f"\nResults saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
