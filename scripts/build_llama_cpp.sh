#!/usr/bin/env bash
#
# Build llama.cpp from source (mirrors the DataCamp tutorial).
# Prefer `gemma-qat-bench build`; this script is here for reference / CI.
#
# Usage:
#   scripts/build_llama_cpp.sh [SOURCE_DIR] [--cpu]
#
set -euo pipefail

SRC_DIR="${1:-third_party/llama.cpp}"
CUDA_FLAG="ON"
if [[ "${2:-}" == "--cpu" ]]; then
  CUDA_FLAG="OFF"
fi

echo ">> Installing build prerequisites (needs sudo/apt on Debian/Ubuntu)"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y pciutils build-essential cmake curl libcurl4-openssl-dev
fi

if [[ ! -d "${SRC_DIR}" ]]; then
  echo ">> Cloning llama.cpp into ${SRC_DIR}"
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "${SRC_DIR}"
fi

echo ">> Configuring (GGML_CUDA=${CUDA_FLAG})"
cmake "${SRC_DIR}" -B "${SRC_DIR}/build" \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_CUDA="${CUDA_FLAG}"

echo ">> Building"
cmake --build "${SRC_DIR}/build" \
  --config Release \
  -j \
  --clean-first \
  --target llama-cli llama-mtmd-cli llama-server llama-gguf-split

echo ">> Done. Server binary:"
ls -1 "${SRC_DIR}/build/bin/llama-server"
