#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import glob
import re

# 1. Set environment variable to suppress uv cross-disk hardlink warnings
os.environ["UV_LINK_MODE"] = "copy"

def main():
    req_file = sys.argv[1] if len(sys.argv) > 1 else None
    python_version = sys.argv[2] if len(sys.argv) > 2 else None

    # Convert req_file to absolute path before saving to environment variable
    if req_file:
        req_file = os.path.abspath(req_file)

    print(f"🧹 1. Destroying the old environment...")
    shutil.rmtree(".venv", ignore_errors=True)

    print(f"🌱 2. Rebuilding the virtual environment at lightning speed using uv...")
    # Build uv venv command with optional --python argument
    uv_cmd = ["uv", "venv"]
    if python_version:
        uv_cmd.extend(["--python", python_version])
        print(f"   🐍 Using Python version: {python_version}")
    uv_cmd.append(".venv")
    subprocess.run(uv_cmd, check=True)

    # =====================================================================
    # 🎯 Core Logic: Install exact versions from requirements.txt
    # =====================================================================
    packages_to_install = []

    # Install exact versions from requirements.txt (no Claude SDK)
    print(f"🔍 3. Installing all packages with exact versions from {req_file}...")
    if req_file and os.path.isfile(req_file):
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                packages_to_install.append(line)
    else:
        print("❌ Error: No requirements.txt provided.")
        sys.exit(1)

    print(f"\n📦 4. Installing {len(packages_to_install)} packages with strict version requirements...")

    # Install packages
    cmd = ["uv", "pip", "install", "--python", ".venv"] + packages_to_install
    subprocess.run(cmd, check=True)

    print("\n🪝 5. Remounting the LLM dependency interceptor...")
    sp_dirs = glob.glob(".venv/lib/python*/site-packages")
    if not sp_dirs:
        print("❌ Error: .venv/lib/python*/site-packages not found.")
        sys.exit(1)

    site_packages = sp_dirs[0]

    # Use llm_real_hook.py for API tracing
    hook_file = "llm_real_hook.py"
    files_to_copy = [hook_file]
    print(f"🎯 Injecting {hook_file} (API tracing mode)")

    for file_to_copy in files_to_copy:
        if not os.path.exists(file_to_copy):
            print(f"⚠️ Warning: {file_to_copy} not found. Ensure you are running this in the project root.")
        else:
            shutil.copy(file_to_copy, site_packages)
            print(f"  ✅ Copied {file_to_copy} to {site_packages}")

    # =====================================================================
    # 🎯 Core Logic: Inject requirements and mapping file paths into .pth
    # =====================================================================
    pth_path = os.path.join(site_packages, "000_mock.pth")
    with open(pth_path, "w", encoding="utf-8") as f:
        f.write("import os; ")
        if req_file and os.path.isfile(req_file):
            # req_file is already absolute path
            f.write(f"os.environ['MOCK_REQ_FILE'] = r'{req_file}'; ")

        # Inject mapping file path
        mapping_file = "pypi_import_mapping.json"
        if os.path.exists(mapping_file):
            abs_mapping = os.path.abspath(mapping_file)
            f.write(f"os.environ['MOCK_MAPPING_FILE'] = r'{abs_mapping}'; ")

        # Import llm_real_hook
        f.write("import llm_real_hook\n")

    print(f"✅ Successfully implanted {hook_file} into: {site_packages}")
    print("\n====================================================")
    print("✨ Environment reset complete!")
    print("📝 API calls will be traced and logged to .api_calls.json")
    print("👉 You can now activate it by running: source .venv/bin/activate")
    print("====================================================")

if __name__ == "__main__":
    main()