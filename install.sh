#!/bin/bash
set -e

echo "==========================================================="
echo "   COGNITION COIN - NODE BOOTSTRAP SCRIPT (v0.3)"
echo "==========================================================="

echo "[*] Ensuring root privileges are available..."
sudo -v

echo "[*] Installing base system dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-venv python3-pip build-essential cmake wget curl pciutils

# 2. GPU Detection & CUDA setup
if lspci | grep -i nvidia > /dev/null; then
    echo "[*] NVIDIA GPU detected."
    if ! command -v nvcc > /dev/null; then
        echo "[*] CUDA Toolkit not found in PATH."
        echo "[*] Attempting to install nvidia-cuda-toolkit via APT..."
        sudo apt-get install -y nvidia-cuda-toolkit
        
        # Check if it succeeded
        if command -v nvcc > /dev/null; then
            echo "[*] CUDA Toolkit installed successfully."
        else
            echo "[!] WARNING: nvcc still not found. Llama.cpp might fall back to CPU."
        fi
    else
        echo "[*] CUDA Toolkit is already installed."
    fi
    export CMAKE_ARGS="-DGGML_CUDA=on"
else
    echo "[*] No NVIDIA GPU detected. Proceeding with CPU-only installation."
    export CMAKE_ARGS=""
fi

# 3. Clone Repository
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

# 4. Python Environment
echo "[*] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 5. Install Python dependencies
echo "[*] Installing Python requirements (This may take a while if compiling Llama.cpp)..."
# We run pip through the venv explicitly
venv/bin/python3 -m pip install -U pip
CMAKE_ARGS="${CMAKE_ARGS}" venv/bin/python3 -m pip install -r requirements.txt

echo "==========================================================="
echo " INSTALLATION COMPLETE!"
echo " The system is primed. To start the miner, run:"
echo ""
echo "   cd cognition-node"
echo "   source venv/bin/activate"
echo "   python core_node.py node --mine"
echo ""
echo " * Note: On first run, the node will automatically download"
echo "   the 4.6GB Llama-3 model file. Please be patient."
echo "==========================================================="
