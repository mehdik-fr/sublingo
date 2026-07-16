#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-}"
REVISION="${2:-}"
REPOSITORY_ROOT="${3:-/workspace/sublingo}"
VIRTUAL_ENVIRONMENT="${SUBLINGO_REMOTE_VENV:-/opt/sublingo-venv}"

case "${MODEL}@${REVISION}" in
  "Qwen/Qwen3.5-9B@c202236235762e1c871ad0ccb60c8ee5ba337b9a"|\
  "Qwen/Qwen3-14B@40c069824f4251a91eefaf281ebe4c544efd3e18") ;;
  *)
    echo "Refusing a model or revision outside the reviewed pilot allow-list" >&2
    exit 2
    ;;
esac

export PYTHONPATH="${REPOSITORY_ROOT}/backend"
export PATH="${VIRTUAL_ENVIRONMENT}/bin:${PATH}"
export SUBLINGO_ENVIRONMENT="staging"
export SUBLINGO_ANALYSIS_PROVIDER="vllm"
export SUBLINGO_VLLM_BASE_URL="http://127.0.0.1:18001"
export SUBLINGO_VLLM_MODEL="${MODEL}"
export SUBLINGO_VLLM_REVISION="${REVISION}"
export SUBLINGO_VLLM_TIMEOUT_SECONDS="${SUBLINGO_VLLM_TIMEOUT_SECONDS:-45}"
export SUBLINGO_VLLM_MAX_TOKENS="${SUBLINGO_VLLM_MAX_TOKENS:-4096}"
export SUBLINGO_VLLM_MAX_CONCURRENCY="${SUBLINGO_VLLM_MAX_CONCURRENCY:-2}"
export SUBLINGO_ALLOWED_ORIGINS="${SUBLINGO_ALLOWED_ORIGINS:-}"
if [[ -z "${SUBLINGO_ALLOWED_ORIGIN_REGEX+x}" ]]; then
  export SUBLINGO_ALLOWED_ORIGIN_REGEX='^chrome-extension://[a-p]{32}$'
fi
export SUBLINGO_MAX_REQUEST_BODY_BYTES="${SUBLINGO_MAX_REQUEST_BODY_BYTES:-262144}"
export SUBLINGO_RATE_LIMIT_REQUESTS_PER_MINUTE="${SUBLINGO_RATE_LIMIT_REQUESTS_PER_MINUTE:-30}"

cd "${REPOSITORY_ROOT}/backend"
exec "${VIRTUAL_ENVIRONMENT}/bin/python" -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8765 \
  --no-access-log \
  --timeout-keep-alive 5
