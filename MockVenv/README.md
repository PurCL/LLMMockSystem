# MockVenv Management Tool

A comprehensive command-line tool for managing mock virtual environments and resolving Python dependencies using LLM-powered analysis.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Reset Environment](#reset-environment)
  - [Resolve Dependencies](#resolve-dependencies)
- [File Structure](#file-structure)
- [Workflow](#workflow)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

MockVenv is a tool that provides two core functionalities:

1. **Environment Reset**: Creates a mock virtual environment based on a `requirements.txt` file, installing only whitelisted packages and injecting LLM-powered mock hooks.

2. **Dependency Resolution**: Analyzes captured API usage patterns from `.mock_state.json` and uses LLM inference to determine compatible package versions.

## ✨ Features

- **Fast Environment Setup**: Uses `uv` for lightning-fast virtual environment creation
- **Intelligent Whitelisting**: Only installs packages that match the whitelist configuration
- **LLM-Powered Analysis**: Leverages language models to infer compatible package versions based on actual API usage
- **Automatic Hook Injection**: Seamlessly integrates mock hooks into the virtual environment
- **PyPI Integration**: Real-time version fetching from the Python Package Index
- **Comprehensive Logging**: Detailed output for debugging and monitoring

## 🔧 Prerequisites

Before using MockVenv, ensure you have the following installed:

- **Python 3.7+**: The tool requires Python 3.7 or higher
- **uv**: Fast Python package installer (install via: `pip install uv`)
- **Internet Connection**: Required for PyPI API access and LLM inference

## 📦 Installation

No installation required! Simply ensure you're in the MockVenv directory and have the required dependencies installed:

```bash
cd /path/to/MockVenv
pip install uv
```

## 🚀 Usage

The main entry point is `main.py`, which provides a command-line interface with two primary modes:

### Reset Environment

Creates a fresh mock virtual environment from a requirements.txt file.

**Syntax:**
```bash
python main.py --reset <path_to_requirements.txt>
```

**What it does:**
1. Destroys any existing `.venv` directory
2. Creates a new virtual environment using `uv`
3. Reads `whitelist.txt` to determine which packages to install
4. Installs whitelisted packages from your requirements.txt
5. Injects LLM mock hooks (`llm_mock_hook.py` and `llm_client.py`)
6. Creates a `.pth` file to enable automatic hook loading

**Output:**
- A ready-to-use `.venv` directory with mock hooks installed
- Activate with: `source .venv/bin/activate`

### Resolve Dependencies

Analyzes API usage patterns to determine compatible package versions and generates Dockerfiles for testing.

**Syntax:**
```bash
# Use default path (.venv/.mock_state.json)
python main.py --resolve

# Use custom path
python main.py --resolve /path/to/.mock_state.json
```

**What it does:**
1. Reads the `.mock_state.json` file containing intercepted API features
2. For each mocked import, fetches available versions from PyPI
3. Uses LLM inference to filter versions compatible with the observed API usage
4. Generates `resolved_versions.json` with the final configuration
5. Interactively generates Dockerfiles for different package version combinations
6. Creates a README with detailed usage instructions in the `generated_dockerfiles/` directory

**Output:**
- `resolved_versions.json`: Contains package names mapped to compatible versions
- `generated_dockerfiles/`: Directory containing generated Dockerfiles and usage instructions
  - `Dockerfile_1`, `Dockerfile_2`, etc.: Docker configurations for different package combinations
  - `README.md`: Detailed instructions on how to build and use the containers

**Docker Container Design:**
The generated Dockerfiles create containers that:
- Install only the specified package versions with `--no-deps` flag (no transitive dependencies)
- Stay running in the background using `CMD ["tail", "-f", "/dev/null"]`
- Allow manual interaction via `docker exec` or interactive mode
- Do NOT automatically execute any application code
- Enable you to enter the container and run your tests/applications manually

**Using the Generated Dockerfiles:**
```bash
# Build a Docker image
cd generated_dockerfiles
docker build -f Dockerfile_1 -t myapp:v1 .

# Run in background and exec into it
docker run -d --name myapp_container myapp:v1
docker exec -it myapp_container /bin/bash

# Or run directly in interactive mode
docker run -it --rm myapp:v1 /bin/bash

# With volume mounting (to access your project files)
docker run -it --rm -v /path/to/project:/app/project myapp:v1 /bin/bash
```

## 📁 File Structure

```
MockVenv/
├── main.py                    # Main entry point (this tool)
├── README.md                  # This documentation
├── reset_env.py              # Environment reset implementation
├── resolve_dependencies.py   # Dependency resolution implementation
├── llm_mock_hook.py          # Mock hook implementation
├── llm_client.py             # LLM client for inference
└── whitelist.txt             # Whitelisted packages configuration
```

## 🔄 Workflow

### Typical Usage Flow

1. **Prepare your requirements.txt**
   ```
   flask==2.0.1
   requests==2.28.0
   PyJWT==2.4.0
   ```

2. **Reset the environment**
   ```bash
   python main.py --reset requirements.txt
   ```

3. **Activate and run your application**
   ```bash
   source .venv/bin/activate
   python your_app.py
   ```
   During execution, the mock hooks will intercept import attempts and capture API usage.

4. **Resolve dependencies**
   ```bash
   python main.py --resolve
   ```
   This analyzes the captured data and generates version constraints.

5. **Review results**
   ```bash
   cat resolved_versions.json
   ```

## 📖 Examples

### Example 1: Complete Vulnerability Analysis Workflow (test_example1)

This example demonstrates how to use MockVenv to analyze a JWT authentication vulnerability where a missing `pyjwt` dependency is automatically mocked by the LLM system.

#### Step 1: Build the Virtual Environment

First, navigate to the MockVenv directory and create a virtual environment with the test example's requirements:

```bash
cd /path/to/MockVenv
python3 main.py --reset ../test_example1/requirements.txt
```

This will:
- Create a new `.venv` directory
- Install whitelisted packages from requirements.txt
- Inject LLM mock hooks into the environment

#### Step 2: Activate the Virtual Environment

```bash
source .venv/bin/activate
```

#### Step 3: Start the Vulnerable Server

Open a terminal, navigate to the test_example1 directory, and start the server:

```bash
cd ../test_example1
./start_server.sh
```

This will:
- Start a PostgreSQL database container
- Launch the FastAPI backend server on a dynamic port
- Save the port number to `/tmp/llm_mock_server_port.txt` for the exploit script

#### Step 4: Run the Exploit Script (First Attempt)

Open a **second terminal**, run the exploit:

```bash
cd /path/to/test_example1
./run_exploit.sh
```

**What happens:**
- The exploit script reads the server port from `/tmp/llm_mock_server_port.txt`
- When the server tries to decode JWT tokens, it encounters a missing `pyjwt` dependency
- The LLM mock system intercepts the import failure
- The LLM analyzes the API usage and generates a mock implementation
- The mock state is saved to `.venv/.mock_state.json`

**Expected behavior:** The exploit may fail or partially succeed because the mocked JWT implementation needs refinement.

#### Step 5: Run Server and Exploit Again (Second Attempt)

1. Stop the server in the first terminal (Ctrl+C)
2. Restart the server: `./start_server.sh`
3. In the second terminal, run the exploit again: `./run_exploit.sh`

**What happens:**
- The server now uses the cached mock implementation from `.mock_state.json`
- The JWT token is successfully decoded using the mocked `pyjwt` functionality
- The command injection vulnerability is successfully triggered
- A file `PWNED_BY_JWT_BASH.txt` is created, confirming the exploit

#### Step 6: Resolve Dependencies with LLM Inference

Now that the system has captured the actual API usage patterns, use LLM inference to determine which real `pyjwt` versions would be compatible:

```bash
cd /path/to/MockVenv
python3 main.py --resolve
```

**What happens:**
- Reads `.venv/.mock_state.json` containing captured JWT API features
- Queries PyPI for all available `pyjwt` versions
- Uses LLM to analyze which versions support the observed API usage
- Generates `resolved_versions.json` with compatible version lists

#### Step 7: Review Results

```bash
cat resolved_versions.json
```

This file shows which `pyjwt` versions could have been used to trigger this vulnerability, enabling comprehensive security analysis.

#### Summary

This workflow demonstrates:
- **Automatic API mocking**: Missing dependencies are handled transparently by LLM
- **Iterative refinement**: Mock implementations improve with usage
- **Vulnerability research**: Identify which package versions enable specific attack vectors
- **Dynamic port management**: Server and exploit scripts communicate via temporary files

---

### Example 2: Semver API Analysis Workflow (test_example2)

This example demonstrates how to use MockVenv to analyze applications with missing dependencies, specifically focusing on the `semver` library API. The workflow shows how the LLM mock system handles API discovery and version resolution.

#### Step 1: Build the Mock Virtual Environment

Navigate to the MockVenv directory and create a virtual environment with test_example2's requirements:

```bash
cd /path/to/MockVenv
python3 main.py --reset ../test_example2/requirements.txt
```

This will:
- Create a new `.venv` directory
- Install whitelisted packages from requirements.txt
- Inject LLM mock hooks to intercept missing imports

#### Step 2: Activate the Mock Environment

```bash
source .venv/bin/activate
```

#### Step 3: Start the Server (First Attempt)

Navigate to the test_example2 directory and start the server:

```bash
cd ../test_example2
./start_server.sh
```

**Expected behavior:** The server will fail with a `semver` API not found error because:
- The `semver` package is not in the whitelist
- The LLM mock system intercepts the import but doesn't have API information yet
- The application cannot proceed without knowing the correct `semver` API

#### Step 4: Prompt LLM to Query the API

At this point, the LLM mock system needs information about the `semver` API. The system will:
- Query the LLM to understand the `semver` library's API structure
- Capture the API features being used by the application
- Store this information in `.venv/.mock_state.json`

The mock state file now contains the discovered `semver` API patterns.

#### Step 5: Restart the Server (Second Attempt)

With the API information now cached, restart the server:

```bash
./start_server.sh
```

**What happens:**
- The server loads the cached `semver` API mock from `.mock_state.json`
- The mocked implementation provides the necessary API surface
- The application runs successfully with the mocked `semver` library

#### Step 6: Trigger the Exploit

Execute the exploit script to test the vulnerability:

```bash
./run_exploit.sh
```

This demonstrates that the application works correctly with the mocked `semver` dependency.

#### Step 7: Resolve Dependencies with LLM Inference

Now use LLM inference to determine which real `semver` versions are compatible with the observed API usage:

```bash
cd /path/to/MockVenv
python3 main.py --resolve
```

**What happens:**
- Reads `.venv/.mock_state.json` containing captured `semver` API features
- Queries PyPI for all available `semver` versions
- Uses LLM to analyze which versions support the observed API usage patterns
- Generates `resolved_versions.json` with compatible version lists

#### Step 8: Review Results

```bash
cat resolved_versions.json
```

This file shows which `semver` versions are compatible with your application's API usage, enabling you to:
- Identify the minimum required version
- Test against multiple compatible versions
- Understand version-specific API differences

#### Summary

This workflow demonstrates:
- **API Discovery**: LLM system learns library APIs through query and usage
- **Progressive Enhancement**: Mock implementations improve through iterative runs
- **Version Analysis**: Determine compatible package versions based on actual API usage
- **Dependency Resolution**: Resolve version constraints without manual testing

---

## 🐛 Troubleshooting

### Common Issues

**Issue: "uv command not found"**
```bash
# Solution: Install uv
pip install uv
```

**Issue: "File not found: reset_env.py"**
```bash
# Solution: Ensure you're in the MockVenv directory
cd /path/to/MockVenv
python main.py --reset requirements.txt
```

**Issue: ".mock_state.json not found"**
- Ensure you've run your application with the mock environment activated
- Check the default path: `.venv/.mock_state.json`
- Provide a custom path if the file is elsewhere

**Issue: "Permission denied"**
```bash
# Solution: Make main.py executable (optional)
chmod +x main.py
./main.py --reset requirements.txt
```

### Debug Mode

For more detailed output, you can modify the scripts or examine log files:

```bash
# Check if virtual environment was created
ls -la .venv/

# Verify mock hooks are installed
ls .venv/lib/python*/site-packages/llm_*.py

# Check the .pth file
cat .venv/lib/python*/site-packages/000_mock.pth
```

## 📝 Configuration Files

### whitelist.txt

Controls which packages are eligible for installation. Format:
```
# Comment lines start with #
requests
flask
django
PyJWT  # JWT authentication
```

### .mock_state.json

Generated automatically during application execution. Contains:
- `core_imports`: Successfully imported modules
- `mocked_imports`: Failed imports with captured API features

### resolved_versions.json

Generated by the resolve command. Contains:
- `core_imports`: Original core imports
- `resolved_mock_imports`: Package names mapped to compatible version lists

## 🔒 Security Notes

- The tool modifies your Python environment by injecting hooks
- Only use in development/testing environments
- Review the whitelist before running in production scenarios
- The LLM client may send API usage patterns for analysis

## 📄 License

This tool is part of the LLMMockSystem project.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the generated log files
3. Examine `.venv/.mock_state.json` for captured data
4. Verify `whitelist.txt` contains expected packages

---

**Happy Mocking! 🎭**
