#!/bin/bash

PATH="$HOME/miniconda3/bin:$PATH"
export PATH
echo "Initializing conda"
$HOME/miniconda3/bin/conda init --all
echo "Initializing vllm with:"
echo "host :$1"
echo "port :$2"
cd MotionCtrl
source activate motion_ctrl && python -m app --share 

# Wait for all background processes to finish
wait