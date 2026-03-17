import json
import os
import sys
import urllib.request
import itertools
import math

# Mapping import names to PyPI package names
PYPI_NAME_MAP = {
    "jwt": "PyJWT",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv"
}

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

def infer_versions_from_llm(package_name, api_responses):
    """
    Simulated LLM Deduction Engine.
    In a full production environment, this passes the `api_responses` to Claude.
    For this deterministic demo, it perfectly mimics the LLM's logic for PyJWT.
    """
    pypi_name = PYPI_NAME_MAP.get(package_name, package_name)
    all_versions = get_pypi_versions(pypi_name)
    
    if not all_versions:
        return []

    print(f"🧠 [LLM Engine] Analyzing execution traces for '{package_name}'...")
    traces = str(api_responses)

    # =================================================================
    # 💡 LLM DEDUCTION LOGIC: SIGNATURE & FEATURE MATCHING
    # =================================================================
    if pypi_name == "PyJWT":
        if "verify=False" in traces:
            print(f"   🎯 [LLM Insight] Detected legacy signature: 'verify=False'")
            print(f"   🎯 [LLM Insight] In PyJWT >= 2.0.0, 'verify' is deprecated and 'algorithms' is strictly required.")
            print(f"   🎯 [LLM Insight] DEDUCTION: Environment MUST be constrained to PyJWT < 2.0.0 to execute successfully.")
            
            # Filter out versions >= 2.0.0
            valid_versions = []
            for v in all_versions:
                try:
                    major_version = int(v.split('.')[0])
                    if major_version < 2:
                        valid_versions.append(v)
                except ValueError:
                    continue
                    
            print(f"   ✅ Constrained from {len(all_versions)} versions down to {len(valid_versions)} compatible versions.")
            return valid_versions
            
    # Default fallback: if no specific API constraints violate modern versions
    print(f"   💡 [LLM Insight] No strict API breaking changes detected in traces. Returning all stable versions.")
    return all_versions

def generate_dockerfile(combo_index, core_deps, mock_deps_combo, output_dir, project_path):
    """Generate a Dockerfile and return the exact build and run commands."""
    filename = f"Dockerfile.mock.{combo_index}"
    filepath = os.path.join(output_dir, filename)
    image_tag = f"mock-env-{combo_index}"
    db_container = f"mock-db-{combo_index}"
    
    # 💡 Force legacy builder
    build_cmd = f"DOCKER_BUILDKIT=0 docker build -t {image_tag} -f {filepath} {project_path}"
    
    # 🚀 Fix: Keep on a single line to prevent breaking Dockerfile comments
    run_cmd = f"docker network create mock-net || true && docker run -d --rm --name {db_container} --network mock-net -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=changethis -e POSTGRES_DB=app postgres:14 && sleep 3 && docker run -d -p 8000:8000 --name {image_tag}-container --network mock-net -e DATABASE_URL=\"postgresql+psycopg2://postgres:changethis@{db_container}:5432/app\" {image_tag}"
    
    core_str = " ".join([f"{pkg}=={ver}" for pkg, ver in core_deps.items() if pkg not in PYPI_NAME_MAP.values()])
    mock_str = " ".join([f"{PYPI_NAME_MAP.get(pkg, pkg)}=={ver}" for pkg, ver in mock_deps_combo if ver])
    
    content = f"""# =====================================================================
# 🚀 HOW TO EXECUTE THIS ENVIRONMENT
# =====================================================================
# 1. Build the image:
#    {build_cmd}
#
# 2. Run the environment (Database + App):
#    {run_cmd}
# =====================================================================

FROM python:3.11-slim

WORKDIR /app

# 💡 Suppress interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system-level dependencies cleanly
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 1. Strictly install Core Imports
RUN pip install --no-cache-dir {core_str}

# 2. Install Mocked Imports combinations (Inferred by LLM)
"""
    if mock_str:
        content += f"RUN pip install --no-cache-dir {mock_str}\n"
        
    content += """
# 3. Copy project files
COPY . /app/

# Default startup command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    with open(filepath, "w") as f:
        f.write(content)
        
    return filepath, build_cmd, run_cmd

def main():
    print("="*50)
    print("🐳 Dockerfile Matrix Generation Engine")
    print("="*50)

    default_state_path = ".mock_state.json"
    default_project_path = "."
    
    if len(sys.argv) > 1:
        state_file = sys.argv[1]
        project_path = sys.argv[2] if len(sys.argv) > 2 else default_project_path
    else:
        user_state = input(f"📂 Please enter the path to .mock_state.json\n[Press Enter to use '{default_state_path}']: ").strip()
        state_file = user_state if user_state else default_state_path
        
        user_proj = input(f"\n📁 Please enter the Project Directory to copy into the Docker image\n[Press Enter to use current directory '{default_project_path}']: ").strip()
        project_path = user_proj if user_proj else default_project_path

    if not os.path.exists(state_file):
        print(f"\n❌ File not found: {state_file}")
        return

    with open(state_file, "r") as f:
        state = json.load(f)

    core_imports = state.get("core_imports", {})
    mocked_imports = state.get("mocked_imports", {})

    print("\n📦 Scanning dependencies...")
    mocked_versions_space = []
    
    # Ignore internal/built-in modules that might have been accidentally mocked
    ignored_mocks = ["sitecustomize", "org", "org.python", "a2wsgi", "cython"]
    ignored_mocks = []
    
    for pkg, info in mocked_imports.items():
        if pkg in ignored_mocks: 
            continue
            
        versions = infer_versions_from_llm(pkg, info.get("api_responses", {}))
        
        if versions: 
            mocked_versions_space.append([(pkg, v) for v in versions])
            pypi_name = PYPI_NAME_MAP.get(pkg, pkg)
            print(f"   ✅ '{pypi_name}': Locked in {len(versions)} compatible versions (Latest safe: {versions[0]})")

    total_combos = math.prod([len(v) for v in mocked_versions_space]) if mocked_versions_space else 1

    print(f"\n🎯 Total targeted combinations: {total_combos}")
    user_input = input("🔢 Enter the number of Dockerfiles to generate (Default 1, or 'all'): ").strip()
    num_to_generate = total_combos if user_input.lower() == 'all' else (int(user_input) if user_input.isdigit() else 1)

    output_dir = "mock_dockerfiles"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n🚀 Starting generation...")
    for i, mock_combo in enumerate(itertools.product(*mocked_versions_space)):
        if i >= num_to_generate: break
        
        filepath, build_cmd, run_cmd = generate_dockerfile(i + 1, core_imports, mock_combo, output_dir, project_path)
        print(f"  [+] Generated: {filepath}")
        
        if i == 0:
            print(f"\n      🛠️  Build it: {build_cmd}")
            print(f"      🚀 Run it:   {run_cmd}\n")

    print(f"🎉 Successfully generated inside './{output_dir}/'!")

if __name__ == "__main__":
    main()