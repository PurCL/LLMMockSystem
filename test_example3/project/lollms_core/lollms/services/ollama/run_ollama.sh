#!/bin/bash

cd ~/ollama

# Set the OLLAMA_HOST address
OLLAMA_HOST="0.0.0.0:11434"

# Start the OLLAMA server
OLLAMA_MODELS=./models ./ollama serve &

# Wait for all background processes to finish
wait