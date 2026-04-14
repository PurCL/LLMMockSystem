#!/bin/sh
# This script installs Ollama on Linux.
# It detects the current operating system architecture and installs the appropriate version of Ollama.

cd ~/

set -eu

status() { echo ">>> $*" >&2; }
error() { echo "ERROR $*"; exit 1; }
warning() { echo "WARNING: $*"; }

OLLAMA_DIR=~/ollama
echo ""
if [ ! -d $OLLAMA_DIR ]; then
    mkdir $OLLAMA_DIR
    echo "Folder $OLLAMA_DIR created successfully!"
else
    echo "Folder $OLLAMA_DIR already exists."
fi

available() { command -v $1 >/dev/null; }
require() {
    local MISSING=''
    for TOOL in $*; do
        if ! available $TOOL; then
            MISSING="$MISSING $TOOL"
        fi
    done

    echo $MISSING
}

[ "$(uname -s)" = "Linux" ] || error 'This script is intended to run on Linux only.'

ARCH=$(uname -m)
case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) error "Unsupported architecture: $ARCH" ;;
esac

KERN=$(uname -r)
case "$KERN" in
    *icrosoft*WSL2 | *icrosoft*wsl2) ;;
    *icrosoft) error "Microsoft WSL1 is not currently supported. Please upgrade to WSL2 with 'wsl --set-version <distro> 2'" ;;
    *) ;;
esac


NEEDS=$(require curl awk grep sed tee xargs)
if [ -n "$NEEDS" ]; then
    status "ERROR: The following tools are required but missing:"
    for NEED in $NEEDS; do
        echo "  - $NEED"
    done
    exit 1
fi

status "Downloading ollama..."
curl --fail --show-error --location --progress-bar -o $OLLAMA_DIR/ollama "https://ollama.ai/download/ollama-linux-$ARCH"

status "Installing ollama to OLLAMA_DIR..."


install_success() { 
    status 'The Ollama API is now available at 0.0.0.0:11434.'
    status 'Install complete. Run "ollama" from the command line.'
}
chmod +x $OLLAMA_DIR/ollama
trap install_success EXIT
