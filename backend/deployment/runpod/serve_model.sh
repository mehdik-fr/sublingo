#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-}"
REVISION="${2:-}"
VIRTUAL_ENVIRONMENT="${SUBLINGO_REMOTE_VENV:-/opt/sublingo-venv}"

case "${MODEL}@${REVISION}" in
  "Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a")
    EXTRA_ARGUMENTS=(--language-model-only)
    ;;
  "Qwen/Qwen3-14B@40c069824f4251a91eefaf281ebe4c544efd3e18")
    EXTRA_ARGUMENTS=()
    ;;
  *)
    echo "Refusing a model or revision outside the reviewed pilot allow-list" >&2
    exit 2
    ;;
esac

if [[ ! -x "${VIRTUAL_ENVIRONMENT}/bin/vllm" ]]; then
  echo "Run install_runtime.sh before serving a model" >&2
  exit 2
fi

export CUDA_VISIBLE_DEVICES=0
export PATH="${VIRTUAL_ENVIRONMENT}/bin:${PATH}"
export HF_HOME="${HF_HOME:-/workspace/huggingface}"
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-/workspace/vllm-cache}"
export TOKENIZERS_PARALLELISM=true

exec "${VIRTUAL_ENVIRONMENT}/bin/vllm" serve "${MODEL}" \
  --revision "${REVISION}" \
  --served-model-name "${MODEL}" \
  --host 127.0.0.1 \
  --port 18001 \
  --dtype auto \
  --max-model-len 8192 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.90 \
  --enable-prefix-caching \
  "${EXTRA_ARGUMENTS[@]}"
