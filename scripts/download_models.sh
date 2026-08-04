#!/usr/bin/env bash
#
# Download the non-QAT and QAT Gemma 4 12B GGUF variants (UD-Q4_K_XL).
# Prefer `gemma-qat-bench download`; this script is here for reference.
#
set -euo pipefail

DEST="${1:-models}"

pip install -U "huggingface_hub[hf_xet]" hf-xet hf_transfer
export HF_XET_HIGH_PERFORMANCE=1

echo ">> Downloading non-QAT model"
hf download unsloth/gemma-4-12b-it-GGUF \
  --local-dir "${DEST}/gemma-4-12b-it-GGUF" \
  --include "*mmproj-BF16*" \
  --include "*UD-Q4_K_XL*"

echo ">> Downloading QAT model"
hf download unsloth/gemma-4-12B-it-qat-GGUF \
  --local-dir "${DEST}/gemma-4-12B-it-qat-GGUF" \
  --include "*mmproj-BF16*" \
  --include "*UD-Q4_K_XL*"

echo ">> Done."
ls -1 "${DEST}"
