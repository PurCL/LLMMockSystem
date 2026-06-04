# MockVenv Manager - VSCode Extension

A VSCode extension for managing MockVenv hooked environments for CVE analysis.

## Features

- Automatically detects `run_exploit.sh` files in CVE project directories
- Interactive UI for specifying `requirements.txt` file
- One-click build of hooked environments using MockVenv
- Executes `python3 main.py --reset --requirements <path>` in the MockVenv directory

## Installation

### 1. Install Dependencies

Navigate to the extension directory and install dependencies:

```bash
cd /home/jian1000/data3/LLMMockSystem/MockVenv/vscode-extension
npm install
```

### 2. Compile TypeScript

Compile the TypeScript code:

```bash
npm run compile
```

### 3. Install Extension in VSCode

You have two options:

#### Option A: Install from VSIX (Recommended)

1. Package the extension:
```bash
npm install -g @vscode/vsce
vsce package
```

2. In VSCode, go to Extensions (Ctrl+Shift+X)
3. Click the "..." menu at the top
4. Select "Install from VSIX..."
5. Choose the generated `.vsix` file

#### Option B: Development Mode

1. Open the extension directory in VSCode:
```bash
code /home/jian1000/data3/LLMMockSystem/MockVenv/vscode-extension
```

2. Press `F5` to launch a new VSCode window with the extension loaded

## Usage

### Step 1: Open a CVE Project

Navigate to a CVE project directory that contains:
- `run_exploit.sh`
- `requirements.txt`

Example: `~/data3/LLMMockSystem/cve/2026/library/CVE-2026-1462`

### Step 2: Open run_exploit.sh

Open the `run_exploit.sh` file in VSCode.

### Step 3: Build Hooked Environment

There are two ways to trigger the build:

#### Method 1: Context Menu
1. Right-click in the editor
2. Select "MockVenv: Build Hooked Environment"

#### Method 2: Command Palette
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "MockVenv: Build Hooked Environment"
3. Press Enter

### Step 4: Configure Requirements

A webview panel will open with two steps:

1. **Specify requirements.txt**:
   - The default path will be the `requirements.txt` in the same directory as `run_exploit.sh`
   - Click "Change requirements.txt" if you want to use a different file

2. **Build Hooked Environment**:
   - Review the command that will be executed
   - Click "Build Hooked Environment" to start the build
   - A terminal will open showing the build progress

## How It Works

When you click "Build Hooked Environment", the extension:

1. Changes directory to `/home/jian1000/data3/LLMMockSystem/MockVenv`
2. Executes: `python3 main.py --reset --requirements <your_requirements_path>`
3. The MockVenv tool will:
   - Destroy the old `.venv` environment
   - Rebuild a new virtual environment using `uv`
   - Install exact versions from requirements.txt
   - Inject `llm_real_hook.py` for API call tracking

## Requirements

- VSCode version 1.80.0 or higher
- Node.js and npm installed
- Python 3 installed
- MockVenv properly set up at `/home/jian1000/data3/LLMMockSystem/MockVenv`

## Troubleshooting

### Extension not showing up

Make sure you've compiled the TypeScript code:
```bash
npm run compile
```

### Command not appearing in context menu

The command only appears when you have `run_exploit.sh` open in the editor.

### Build fails

Check the terminal output for error messages. Common issues:
- requirements.txt not found
- Python 3 not available
- MockVenv directory not accessible

## Future Features

- Support for additional MockVenv commands (--resolve, --fix)
- Progress tracking within the webview
- Error handling and notifications
- Configuration options for MockVenv path

## Development

### Project Structure

```
vscode-extension/
├── src/
│   └── extension.ts       # Main extension code
├── out/                   # Compiled JavaScript (generated)
├── package.json          # Extension manifest
├── tsconfig.json        # TypeScript configuration
└── README.md           # This file
```

### Building

```bash
npm run compile
```

### Watching for changes

```bash
npm run watch
```

### Debugging

Press `F5` in VSCode to launch the Extension Development Host.

## License

MIT
