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
    # Convert req_file to absolute path before saving to environment variable
    if req_file:
        req_file = os.path.abspath(req_file)
    whitelist_file = "whitelist.txt"

    print("🧹 1. Destroying the old environment...")
    shutil.rmtree(".venv", ignore_errors=True)

    print("🌱 2. Rebuilding the virtual environment at lightning speed using uv...")
    subprocess.run(["uv", "venv", ".venv"], check=True)

    # =====================================================================
    # 🎯 Core Logic: Dynamically read the standalone whitelist.txt configuration
    # =====================================================================
    ignored_modules = set()
    if os.path.exists(whitelist_file):
        with open(whitelist_file, "r", encoding="utf-8") as f:
            for line in f:
                # Remove comments and strip whitespace
                line = line.split('#')[0].strip()
                if line:
                    ignored_modules.add(line.lower().replace("-", "_"))
        print(f"📖 Loaded {len(ignored_modules)} whitelisted modules from {whitelist_file}")
    else:
        print(f"⚠️ Warning: {whitelist_file} not found. Operating without a whitelist!")

    packages_to_install = ["claude-agent-sdk", "psycopg2-binary"]

    if req_file and os.path.isfile(req_file):
        print(f"🔍 3. Analyzing {req_file} against the whitelist...")
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                match = re.match(r'^([A-Za-z0-9_\.-]+)', line)
                if match:
                    pkg_name = match.group(1)
                    pkg_name_normalized = pkg_name.lower().replace("-", "_")
                    
                    if pkg_name_normalized in ignored_modules:
                        print(f"  ✅ Match Found: Adding '{line}' to installation queue.")
                        packages_to_install.append(line)
    else:
        print("ℹ️ No requirements.txt provided or file not found. Proceeding with baseline default.")

    # -------------------------------------------------------------------------
    # Gentle installation: Install whitelisted packages and allow natural 
    # dependency resolution by pip to ensure framework stability.
    # -------------------------------------------------------------------------
    print("\n📦 4. Installing core testing tools, Agent dependencies, and matched underlying frameworks...")
    cmd = ["uv", "pip", "install", "--python", ".venv"] + packages_to_install
    subprocess.run(cmd, check=True)

    print("\n🪝 5. Remounting the LLM dependency auto-healing interceptor...")
    sp_dirs = glob.glob(".venv/lib/python*/site-packages")
    if not sp_dirs:
        print("❌ Error: .venv/lib/python*/site-packages not found.")
        sys.exit(1)

    site_packages = sp_dirs[0]

    for file_to_copy in ["llm_mock_hook.py", "llm_client.py"]:
        if not os.path.exists(file_to_copy):
            print(f"⚠️ Warning: {file_to_copy} not found. Ensure you are running this in the project root.")
        else:
            shutil.copy(file_to_copy, site_packages)

    # =====================================================================
    # 🎯 Core Logic: Inject both requirements and whitelist paths into .pth
    # =====================================================================
    pth_path = os.path.join(site_packages, "000_mock.pth")
    with open(pth_path, "w", encoding="utf-8") as f:
        f.write("import os; ")
        if req_file and os.path.isfile(req_file):
            # req_file is already absolute path
            f.write(f"os.environ['MOCK_REQ_FILE'] = r'{req_file}'; ")
        
        abs_whitelist = os.path.abspath(whitelist_file)
        f.write(f"os.environ['MOCK_WHITELIST_FILE'] = r'{abs_whitelist}'; ")
        
        f.write("import llm_mock_hook\n")

    print(f"✅ Successfully implanted Auto-Heal Hook into: {site_packages}")
    print("\n====================================================")
    print("✨ Golden baseline environment reset complete!")
    print("👉 You can now activate it by running: source .venv/bin/activate")
    print("====================================================")

if __name__ == "__main__":
    main()