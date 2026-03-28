import json
import os
import sys
import urllib.request
import llm_client  # 💡 Direct integration with our refactored LLM service hub

# =====================================================================
# ⚙️ Configuration
# =====================================================================
# Mapping internal import names to official PyPI package names
PYPI_NAME_MAP = {
    "jwt": "PyJWT",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv"
}

# =====================================================================
# 📦 PyPI Fetcher & Deductive Logic
# =====================================================================
def get_pypi_versions(package_name):
    """Fetch all available versions for a package in real-time via the PyPI API."""
    pypi_name = PYPI_NAME_MAP.get(package_name, package_name)
    print(f"🔍 Fetching all versions for '{pypi_name}' from PyPI...")
    
    url = f"https://pypi.org/pypi/{pypi_name}/json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            # Filter out pre-release versions (alpha, beta, rc) to ensure baseline stability
            versions = [v for v in data["releases"].keys() if "rc" not in v and "b" not in v and "a" not in v]
            return sorted(versions, reverse=True)
    except Exception as e:
        print(f"⚠️ Failed to fetch versions for '{pypi_name}': {e}")
        return []

def infer_versions_from_llm(package_name, api_features):
    """
    Call the abstracted LLM Client to deduce an array of compatible versions 
    based on the intercepted API features.
    """
    pypi_name = PYPI_NAME_MAP.get(package_name, package_name)
    all_versions = get_pypi_versions(pypi_name)
    
    if not all_versions: 
        return []
    if not api_features: 
        return all_versions

    print(f"🧠 [LLM Engine] Analyzing API signatures & features for '{package_name}'...")

    # The prompt explicitly asks the LLM to filter versions based on the kwargs and usage
    prompt = f"""You are an expert Python Dependency Resolution Engine.

Target Package: {pypi_name}
All Available Versions on PyPI: {all_versions}
Observed API Features & Usage:
{json.dumps(api_features, indent=2)}

TASK:
Filter the "All Available Versions" list to ONLY include versions where this exact API usage is mathematically valid and will not raise an exception. (e.g. If an obsolete kwarg is used, exclude newer versions that removed it).

Example output: ["1.7.1", "1.7.0"]
"""

    # 💡 Elegant one-line call to our LLM service hub
    valid_versions = llm_client.infer_versions(prompt)
    
    if valid_versions:
        print(f"   ✅ [LLM Insight] Constrained from {len(all_versions)} down to {len(valid_versions)} compatible versions.")
        return valid_versions
        
    # Fallback strategy: if inference fails or returns empty, assume all stable versions
    return all_versions

# =====================================================================
# 🚀 Main Execution Flow
# =====================================================================
def main():
    print("="*50)
    print("🧠 LLM-Driven Dependency Resolver")
    print("="*50)

    default_state_path = ".mock_state.json"
    
    # Handle command line arguments or interactive inputs
    if len(sys.argv) > 1:
        state_file = sys.argv[1]
    else:
        user_state = input(f"📂 Please enter the path to .mock_state.json\n[Press Enter to use '{default_state_path}']: ").strip()
        state_file = user_state if user_state else default_state_path

    if not os.path.exists(state_file):
        print(f"\n❌ File not found: {state_file}")
        return

    with open(state_file, "r") as f:
        state = json.load(f)

    core_imports = state.get("core_imports", {})
    mocked_imports = state.get("mocked_imports", {})

    print("\n📦 Scanning dependencies and consulting LLM...")
    
    # Dictionary to store the resolved configuration for the JSON output
    resolved_config = {
        "core_imports": core_imports,
        "resolved_mock_imports": {}
    }
    
    # Ignore specific internal/framework modules that shouldn't be mocked
    ignored_mocks = ["sitecustomize", "org", "org.python", "a2wsgi", "cython"]
    
    for pkg, info in mocked_imports.items():
        if pkg in ignored_mocks: 
            continue
            
        features = info.get("api_features", {})
        versions = infer_versions_from_llm(pkg, features)
        
        if versions: 
            pypi_name = PYPI_NAME_MAP.get(pkg, pkg)
            # Record the specific version numbers (lists all if there are multiple)
            resolved_config["resolved_mock_imports"][pypi_name] = versions
            print(f"   ✅ '{pypi_name}': Locked in {len(versions)} compatible versions (Latest safe: {versions[0]})")

    # =================================================================
    # 💾 Output the Resolved Versions JSON
    # =================================================================
    config_output_path = "resolved_versions.json"
    with open(config_output_path, "w") as f:
        json.dump(resolved_config, f, indent=4)
        
    print(f"\n🎉 [Success] Package versions configuration saved to '{config_output_path}'!")

if __name__ == "__main__":
    main()