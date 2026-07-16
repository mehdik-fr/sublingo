#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="${1:-/workspace/sublingo}"
VIRTUAL_ENVIRONMENT="${SUBLINGO_REMOTE_VENV:-/opt/sublingo-venv}"
ARTIFACT_DIRECTORY="${SUBLINGO_PILOT_ARTIFACTS:-/workspace/pilot-artifacts}"

if [[ ! -f "${REPOSITORY_ROOT}/backend/requirements.txt" ]]; then
  echo "Sublingo repository not found at ${REPOSITORY_ROOT}" >&2
  exit 2
fi

mkdir -p "$(dirname "${VIRTUAL_ENVIRONMENT}")" /workspace/huggingface /workspace/vllm-cache "${ARTIFACT_DIRECTORY}"
python -m venv --system-site-packages "${VIRTUAL_ENVIRONMENT}"
"${VIRTUAL_ENVIRONMENT}/bin/python" -m pip install --upgrade pip uv

# Qwen recommends a current vLLM build for Qwen3.5. The exact resolved versions are
# recorded after installation so a successful pilot can be reproduced later.
"${VIRTUAL_ENVIRONMENT}/bin/uv" pip install \
  --python "${VIRTUAL_ENVIRONMENT}/bin/python" \
  --extra-index-url https://wheels.vllm.ai/nightly \
  --upgrade \
  "ninja==1.13.0" \
  "vllm>=0.13.0" \
  -r "${REPOSITORY_ROOT}/backend/requirements.txt"

"${VIRTUAL_ENVIRONMENT}/bin/python" -m pip freeze \
  > "${ARTIFACT_DIRECTORY}/runtime-lock.txt"
"${VIRTUAL_ENVIRONMENT}/bin/python" - <<'PY'
import torch
import vllm

print(f"vllm={vllm.__version__}")
print(f"torch={torch.__version__}")
print(f"cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
PY
