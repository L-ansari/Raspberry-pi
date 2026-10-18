#!/usr/bin/env bash
# One-time setup for the Raspberry Pi 3 (64-bit Raspberry Pi OS Lite recommended).
# Builds llama.cpp and downloads Qwen2.5-0.5B-Instruct (Q4_K_M). Takes ~20-40 min on a Pi 3.
set -euo pipefail

cd "$(dirname "$0")"

echo "== Installing build tools =="
sudo apt-get update
sudo apt-get install -y git cmake build-essential curl

echo "== Building llama.cpp (this is the slow part) =="
if [ ! -d llama.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp
fi
cd llama.cpp
cmake -B build -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
# -j2 rather than -j4: 1 GB of RAM is not enough for four parallel compiles
cmake --build build --config Release -j2 --target llama-cli llama-completion 2>/dev/null \
  || cmake --build build --config Release -j2 --target llama-cli
cd ..

echo "== Downloading model (~400 MB) =="
mkdir -p models
MODEL=models/qwen2.5-0.5b-instruct-q4_k_m.gguf
if [ ! -f "$MODEL" ]; then
  curl -L -o "$MODEL" \
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
fi

echo
echo "Done. Try it with:"
echo "  python3 summarize_stats.py sample.csv"
echo
echo "Optional: free more RAM by setting GPU memory to 16 MB in 'sudo raspi-config'"
echo "(Performance Options -> GPU Memory), then reboot."
