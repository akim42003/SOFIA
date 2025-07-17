#!/bin/bash

# Activate conda environment if it exists
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    if conda env list | grep -q "sofia"; then
        conda activate sofia2
    fi
fi

# Check if PyQt6 is installed
if ! python -c "import PyQt6" 2>/dev/null; then
    echo "PyQt6 not found. Installing..."
    pip install PyQt6
fi

# Check if pyaudio is installed
if ! python -c "import pyaudio" 2>/dev/null; then
    echo "PyAudio not found. Installing..."
    pip install pyaudio
fi

# Run the invisible SOFIA UI
echo "Starting Invisible SOFIA..."
python sofia_transparent.py
