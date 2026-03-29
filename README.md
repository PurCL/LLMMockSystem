# Vulnerability Research Tools

This repository contains a collection of tools for automated vulnerability research, dependency management, and security testing. The primary focus is on identifying vulnerable dependency versions and testing exploit scenarios.

## Directory Structure

### 📦 AutoConfig
An automatic dependency installation tool that monitors program execution and automatically installs missing dependencies when they are detected during runtime. This tool helps streamline the development and testing process by eliminating manual dependency management.

**Key Features:**
- Runtime dependency detection
- Automatic installation of missing packages
- Reduces manual configuration overhead

---

### 🔍 baseline
A baseline tool built on Claude Code that uses a trial-and-error approach to infer all possible version numbers that can trigger vulnerabilities. This tool serves as a comparison benchmark for our LLM-based mock tools.

**Key Features:**
- Iterative version testing approach
- Comprehensive vulnerability version discovery
- Benchmark for comparison with LLM-based approaches

---

### 🤖 MockVenv
An LLM-based tool that mocks APIs and infers package versions based on API features. This is the primary research tool that uses machine learning to intelligently predict vulnerable dependency combinations.

**Key Features:**
- LLM-powered API mocking
- Feature-based version inference
- Intelligent vulnerability prediction

See [MockVenv/README.md](MockVenv/README.md) for detailed documentation.

---

### 🧪 test_example1 & test_example2
Test examples containing vulnerability scenarios for testing and validation purposes. Each test example includes:

- **`project/`**: Source code of the vulnerable application
- **`requirements.txt`**: A specific combination of dependency versions that can trigger vulnerabilities
- **`start_server.sh`**: Script to start the application server
- **`run_exploit.sh`**: Script to trigger and demonstrate the vulnerability

These examples serve as test cases for validating the effectiveness of the vulnerability detection and version inference tools.

---

## Usage

### Running Test Examples

1. Navigate to a test example directory:
   ```bash
   cd test_example1
   ```

2. Start the vulnerable server:
   ```bash
   ./start_server.sh
   ```

3. In another terminal, run the exploit:
   ```bash
   ./run_exploit.sh
   ```

### Using MockVenv

Please refer to the [MockVenv documentation](MockVenv/README.md) for detailed usage instructions.

---

## Project Goals

This project aims to:
- Automate the discovery of vulnerable dependency versions
- Compare traditional trial-and-error approaches with LLM-based inference
- Provide tools for security researchers to identify and test vulnerability scenarios
- Streamline the dependency management process during security testing

---

## Contributing

Contributions are welcome! Please ensure that any new test examples follow the established structure with `project/`, `requirements.txt`, `start_server.sh`, and `run_exploit.sh`.

---

## License

[Add your license information here]
