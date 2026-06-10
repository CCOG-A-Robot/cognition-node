#!/bin/bash
set -e

echo "==========================================================="
echo "   COGNITION COIN - NODE BOOTSTRAP SCRIPT (v0.4)"
echo "==========================================================="

# --- Preflight Checks ---

# 1. Disk space check (~7GB needed: 1.5GB deps + repo + 4.6GB model)
AVAIL_KB=$(df / --output=avail 2>/dev/null | tail -1)
AVAIL_GB=$(( AVAIL_KB / 1024 / 1024 ))
if [ "$AVAIL_GB" -lt 10 ]; then
    echo "[!] WARNING: Only ${AVAIL_GB}GB free on /. At least 10GB recommended."
    echo "    Installation may fail partway through due to disk space."
    echo "    Press Ctrl+C to abort, or wait 5 seconds to continue..."
    sleep 5
fi

# 2. RAM check (Llama-3-8B Q4_K_M needs ~6GB + OS overhead)
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))
if [ "$TOTAL_RAM_GB" -lt 8 ]; then
    echo "[!] WARNING: ${TOTAL_RAM_GB}GB RAM detected. This node requires 8GB+ to load the Llama-3-8B model."
    echo "    The miner will crash with an out-of-memory error on startup."
    echo "    Press Ctrl+C to abort, or wait 5 seconds to continue..."
    sleep 5
fi

# 3. Root privileges
if command -v sudo &>/dev/null; then
    echo "[*] Ensuring root privileges are available..."
    sudo -v
else
    echo "[*] Running as root (sudo not available)."
    # We need root for apt; if we're not root and there's no sudo, bail.
    if [ "$(id -u)" -ne 0 ]; then
        echo "[!] FATAL: Neither root nor sudo available. Install as root or install sudo first."
        exit 1
    fi
fi

# --- System Dependencies ---
echo "[*] Installing base system dependencies..."
SUDO=""
command -v sudo &>/dev/null && SUDO="sudo"
$SUDO apt-get update || echo "[!] apt update had issues — continuing anyway (stale repo sources may show warnings)"
$SUDO apt-get install -y git python3 python3-venv python3-pip python-is-python3 build-essential cmake wget curl pciutils

# --- GPU Detection & CUDA Setup ---
if lspci 2>/dev/null | grep -i nvidia > /dev/null; then
    echo "[*] NVIDIA GPU detected."
    if ! command -v nvcc > /dev/null; then
        echo "[*] CUDA Toolkit not found in PATH."
        echo "[*] Attempting to install nvidia-cuda-toolkit via APT..."
        $SUDO apt-get install -y nvidia-cuda-toolkit

        # Check if it succeeded
        if command -v nvcc > /dev/null; then
            echo "[*] CUDA Toolkit installed successfully."
        else
            echo "[!] WARNING: nvcc still not found. Llama.cpp will use CPU."
            echo "    For GPU acceleration, install CUDA manually from:"
            echo "    https://developer.nvidia.com/cuda-downloads"
        fi
    fi
    # Ensure CUDA binaries are in PATH for the pip compile step
    export PATH="/usr/local/cuda/bin:$PATH"
    export CMAKE_ARGS="-DGGML_CUDA=on"
    echo "[*] CUDA enabled. Compiling llama.cpp with GPU support..."
else
    echo "[*] No NVIDIA GPU detected. Proceeding with CPU-only installation."
    echo "    This will run the miner on CPU — significantly slower than GPU."
    export CMAKE_ARGS=""
fi

# --- Clone Repository ---
if [ ! -d "cognition-node" ]; then
    echo "[*] Cloning repository..."
    git clone https://github.com/CCOG-A-Robot/cognition-node.git
else
    echo "[*] Repository already exists. Pulling latest changes..."
    cd cognition-node
    git pull origin main
    cd ..
fi

cd cognition-node

# --- Python Virtual Environment ---
echo "[*] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# --- Install Python Dependencies ---
echo "[*] Installing Python requirements..."
echo "    This may take 5-30 minutes if llama.cpp needs to compile from source."
echo "    (If a pre-built wheel is available, it will be much faster.)"
venv/bin/python3 -m pip install -U pip --progress-bar on
CMAKE_ARGS="${CMAKE_ARGS}" venv/bin/python3 -m pip install -r requirements.txt --progress-bar on

# --- Download Model ---
echo "[*] Checking Llama-3 model..."
MODEL_DIR="models"
MODEL_FILE="llama-3-8b.gguf"
LLM_MODEL_PATH="${MODEL_DIR}/${MODEL_FILE}"

if [ ! -f "$LLM_MODEL_PATH" ]; then
    echo "    Model not found locally. Downloading 4.6GB model from HuggingFace..."
    echo "    (This may take 10-60 minutes depending on your internet speed.)"
    echo ""
    mkdir -p "$MODEL_DIR"
    venv/bin/python3 -c "
import sys
sys.argv = ['dummy']  # suppress any argparse noise
from huggingface_hub import hf_hub_download
from tqdm import tqdm
import os

model_path = hf_hub_download(
    repo_id='bartowski/Meta-Llama-3-8B-Instruct-GGUF',
    filename='Meta-Llama-3-8B-Instruct-Q4_K_M.gguf',
    local_dir='${MODEL_DIR}',
)
# Rename to canonical name
canonical = '${LLM_MODEL_PATH}'
if model_path != canonical and os.path.exists(model_path):
    os.rename(model_path, canonical)
    print(f'[*] Model saved to {canonical}')
else:
    print(f'[*] Model ready at {model_path}')
"
    echo "    Model download complete."
else
    echo "    Model already present: $(du -h "$LLM_MODEL_PATH" | cut -f1)"
fi

# --- Validate Installation ---
echo ""
echo "[*] Validating installation..."
if venv/bin/python3 -c "import ecdsa, fastapi, uvicorn, pydantic, llama_cpp, huggingface_hub, cryptography; print('    All Python imports OK')" 2>/dev/null; then
    IMPORT_OK=true
else
    echo "[!] Some Python imports failed. Check requirements above."
    IMPORT_OK=false
fi

if [ -f "$LLM_MODEL_PATH" ]; then
    MODEL_SIZE=$(du -h "$LLM_MODEL_PATH" | cut -f1)
    echo "    Model file OK (${MODEL_SIZE})"
    MODEL_OK=true
else
    echo "[!] Model file not found at ${LLM_MODEL_PATH}"
    MODEL_OK=false
fi

# --- Final Output ---
echo ""
echo "==========================================================="
echo " INSTALLATION COMPLETE!"
echo ""
if [ "$IMPORT_OK" = true ] && [ "$MODEL_OK" = true ]; then
    echo " ✅ System fully primed. To start mining:"
else
    echo " ⚠️  Installed with issues (see warnings above)."
    echo "    To start (may fail on first run):"
fi
echo ""
echo "   cd cognition-node"
echo "   source venv/bin/activate"
echo "   python3 core_node.py node --mine"
echo ""
echo " If you encounter problems, start without --mine first:"
echo ""
echo "   python3 core_node.py node"
echo ""
echo " This will sync the chain; Ctrl+C after sync, then add --mine."
echo "==========================================================="