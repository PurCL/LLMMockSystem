# install_hook.py
import os
import shutil
import glob
import sys

sp_dirs = glob.glob(".venv/lib/python*/site-packages")
if not sp_dirs:
    print("❌ Error: .venv folder not found. Please ensure you are in the project root directory.")
    sys.exit(1)

site_packages = sp_dirs[0]

# Copy core files into the virtual environment
for file in ["src/llm_mock_hook.py", "src/llm_client.py"]:
    if not os.path.exists(file):
        print(f"❌ Error: {file} not found.")
        sys.exit(1)
    shutil.copy(file, site_packages)

# Write .pth startup entry
pth_path = os.path.join(site_packages, "000_mock.pth")
with open(pth_path, "w") as f:
    f.write("import llm_mock_hook\n")

print(f"✅ Successfully implanted Auto-Heal Hook into: {site_packages}")
print("====================================================")
print("🎉 Installation complete! You can now activate the virtual environment and run your project directly:")
print("source .venv/bin/activate")
print("python -m uvicorn app.main:app")
print("====================================================")