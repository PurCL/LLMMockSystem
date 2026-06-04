import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    console.log('🎯 MockVenv Manager extension is now active');
    vscode.window.showInformationMessage('MockVenv Manager 扩展已激活');

    let disposable = vscode.commands.registerCommand('mockvenv.buildHookedEnvironment', async () => {
        console.log('🔨 Command triggered: mockvenv.buildHookedEnvironment');

        // Get the active text editor
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            console.error('❌ No active editor found');
            vscode.window.showErrorMessage('No active editor found');
            return;
        }

        // Get the directory containing current file
        const currentFile = editor.document.fileName;
        const workingDir = path.dirname(currentFile);
        const fileName = path.basename(currentFile);
        console.log(`📄 Current file: ${currentFile}`);
        console.log(`📛 File name: ${fileName}`);
        console.log(`📁 Working directory: ${workingDir}`);

        // Check if file ends with .sh
        if (!fileName.endsWith('.sh')) {
            console.error(`❌ Current file is not a .sh file: ${fileName}`);
            vscode.window.showErrorMessage('Current file must be a .sh file');
            return;
        }

        // Check if requirements.txt exists in the same directory
        const requirementsPath = path.join(workingDir, 'requirements.txt');
        console.log(`🔍 Checking for requirements.txt at: ${requirementsPath}`);

        if (!fs.existsSync(requirementsPath)) {
            console.error(`❌ requirements.txt not found at: ${requirementsPath}`);
            vscode.window.showErrorMessage('requirements.txt not found in the same directory');
            return;
        }

        console.log('✅ requirements.txt found');

        // Create and show webview panel
        console.log('🌐 Creating webview panel...');
        const panel = vscode.window.createWebviewPanel(
            'mockvenvBuilder',
            'MockVenv: Build Hooked Environment',
            vscode.ViewColumn.One,
            {
                enableScripts: true
            }
        );

        // Set webview content
        console.log('📝 Setting webview content...');
        panel.webview.html = getWebviewContent(requirementsPath, workingDir, currentFile, fileName);
        console.log('✅ Webview panel created successfully');

        // Handle messages from the webview
        panel.webview.onDidReceiveMessage(
            async message => {
                console.log(`📨 Received message from webview: ${message.command}`);

                switch (message.command) {
                    case 'buildEnvironment':
                        console.log(`🔨 Building environment with requirements: ${requirementsPath}`);
                        // Pass the file information that was captured before webview opened
                        await buildHookedEnvironment(requirementsPath, currentFile, workingDir, panel, context);
                        break;

                    default:
                        console.warn(`⚠️ Unknown command: ${message.command}`);
                }
            },
            undefined,
            context.subscriptions
        );
    });

    context.subscriptions.push(disposable);
}

async function buildHookedEnvironment(requirementsPath: string, shFilePath: string, workingDir: string, panel: vscode.WebviewPanel, context: vscode.ExtensionContext) {
    console.log('🚀 Starting buildHookedEnvironment function');
    console.log(`   Requirements path: ${requirementsPath}`);
    console.log(`   Shell file path: ${shFilePath}`);
    console.log(`   Working directory: ${workingDir}`);

    // Send status update
    panel.webview.postMessage({
        command: 'updateStatus',
        status: 'Building hooked environment...'
    });

    // Get the Python scripts directory from the extension
    const pythonScriptsDir = path.join(context.extensionPath, 'python');
    console.log(`   Python scripts directory: ${pythonScriptsDir}`);

    // Check if Python scripts directory exists
    if (!fs.existsSync(pythonScriptsDir)) {
        console.error(`❌ Python scripts directory not found: ${pythonScriptsDir}`);
        vscode.window.showErrorMessage(`Python scripts directory not found: ${pythonScriptsDir}`);
        panel.webview.postMessage({
            command: 'updateStatus',
            status: `Error: Python scripts directory not found at ${pythonScriptsDir}`
        });
        return;
    }

    const mainPyPath = path.join(pythonScriptsDir, 'main.py');
    if (!fs.existsSync(mainPyPath)) {
        console.error(`❌ main.py not found: ${mainPyPath}`);
        vscode.window.showErrorMessage(`main.py not found: ${mainPyPath}`);
        panel.webview.postMessage({
            command: 'updateStatus',
            status: `Error: main.py not found at ${mainPyPath}`
        });
        return;
    }

    // Build the command - run in the working directory
    const command = `cd "${workingDir}" && python3 "${mainPyPath}" --reset --requirements "${requirementsPath}" && source .venv/bin/activate && bash "${shFilePath}"`;
    console.log(`📝 Command to execute: ${command}`);

    // Create terminal and run command
    console.log('🖥️ Creating terminal...');
    const terminal = vscode.window.createTerminal({
        name: 'MockVenv Builder & Runner',
        cwd: workingDir
    });

    terminal.show();
    console.log('✅ Terminal created and shown');

    terminal.sendText(command);
    console.log('✅ Command sent to terminal');

    // Update status
    panel.webview.postMessage({
        command: 'updateStatus',
        status: 'Building environment and executing script. Check terminal output for progress.'
    });

    vscode.window.showInformationMessage('Building hooked environment and executing script. Check terminal for progress.');
    console.log('✅ buildHookedEnvironment function completed');
}

function getWebviewContent(defaultRequirementsPath: string, workingDir: string, shFilePath: string, shFileName: string): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MockVenv Builder</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
        }

        h1 {
            color: var(--vscode-foreground);
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 10px;
        }

        .section {
            margin: 30px 0;
        }

        .info-box {
            background-color: var(--vscode-textBlockQuote-background);
            border-left: 4px solid var(--vscode-textLink-foreground);
            padding: 15px;
            margin: 15px 0;
        }

        .path-display {
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            font-family: var(--vscode-editor-font-family);
            word-break: break-all;
        }

        button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 12px 24px;
            margin: 10px 5px 10px 0;
            cursor: pointer;
            border-radius: 2px;
            font-size: 16px;
            font-weight: bold;
        }

        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .status {
            margin-top: 20px;
            padding: 15px;
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            display: none;
        }

        .status.show {
            display: block;
        }

        .label {
            font-weight: bold;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 MockVenv: Build Hooked Environment</h1>

        <div class="info-box">
            <strong>Working Directory:</strong>
            <div class="path-display">${workingDir}</div>
        </div>

        <div class="section">
            <h2>Shell Script</h2>
            <div class="label">Script to execute:</div>
            <div class="path-display">${shFileName}</div>
        </div>

        <div class="section">
            <h2>Requirements File</h2>
            <div class="label">Using requirements.txt:</div>
            <div class="path-display">${defaultRequirementsPath}</div>
        </div>

        <div class="section">
            <h2>Build and Run Command</h2>
            <p>This will execute the following command:</p>
            <div class="path-display">
                cd ${workingDir}<br>
                python3 [extension]/python/main.py --reset --requirements ${defaultRequirementsPath}<br>
                source .venv/bin/activate<br>
                bash ${shFilePath}
            </div>

            <button id="buildBtn">🔨 Build Environment & Run Script</button>
        </div>

        <div class="status" id="statusDiv">
            <strong>Status:</strong>
            <div id="statusText"></div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        // Build environment button
        document.getElementById('buildBtn').addEventListener('click', () => {
            vscode.postMessage({
                command: 'buildEnvironment'
            });
        });

        // Listen for messages from extension
        window.addEventListener('message', event => {
            const message = event.data;

            switch (message.command) {
                case 'updateStatus':
                    const statusDiv = document.getElementById('statusDiv');
                    const statusText = document.getElementById('statusText');
                    statusDiv.classList.add('show');
                    statusText.textContent = message.status;
                    break;
            }
        });
    </script>
</body>
</html>`;
}

export function deactivate() {
    console.log('👋 MockVenv Manager extension is now deactivated');
}
