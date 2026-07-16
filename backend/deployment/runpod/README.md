# Temporary RunPod GPU pilot

This directory documents the reproducible, short-lived model comparison. It is not
the final production deployment.

## Fixed safety envelope

- one on-demand GPU, never Spot or a reservation;
- 48 GB GPU allow-list: A40, RTX A6000, RTX 6000 Ada, or L40S;
- hourly price cap from the project prompt;
- 50 GB container disk plus 100 GB Pod volume (150 GB total);
- image `runpod/pytorch:1.0.7-cu1281-torch280-ubuntu2404`;
- model cache, reports, and repository under `/workspace`; ephemeral runtime venv
  under `/opt` on the faster container disk;
- only port `8765/http` is public; vLLM remains on `127.0.0.1:18001`
  because port 8001 is reserved by the RunPod template nginx;
- no subtitle text in API access logs;
- temporary Chrome-extension-only CORS regex, request-size limit, 30 requests/minute,
  two concurrent backend requests, and a 45-second provider timeout.

The public proxy is suitable only for this time-bounded pilot. CORS is not
authentication, a token embedded in an extension is not secret, and the in-memory
rate limiter is not distributed. A production deployment needs a dedicated ingress,
installation quotas or short-lived tokens, and shared rate limiting.

## Explicit model provisioning

`install_runtime.sh` installs software but no weights. `serve_model.sh` is the sole
operator action that may cause vLLM/Hugging Face to fetch weights, and it refuses
anything outside this exact allow-list:

| Model | Revision | License | Advertised size |
| --- | --- | --- | ---: |
| `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | Apache-2.0 | 19.3 GB |
| `Qwen/Qwen3-14B` | `40c069824f4251a91eefaf281ebe4c544efd3e18` | Apache-2.0 | 29.6 GB |

Weights stay on the RunPod volume and are never downloaded to the developer PC.
The API backend itself never downloads a model.

## Comparison procedure

1. Create the bounded Pod and upload the uncommitted working tree over SSH.
2. Run `bash backend/deployment/runpod/install_runtime.sh /workspace/sublingo`.
3. Record `nvidia-smi`, the resolved runtime lock, disk use, GPU price, and start time.
4. Start one allow-listed model with
   `bash backend/deployment/runpod/serve_model.sh <model> <revision>`; wait for
   `http://127.0.0.1:18001/v1/models`.
5. Run the multilingual evaluator with one warmup and three repeats.
6. Stop vLLM, confirm GPU memory is released, then repeat on the same Pod with the
   other model and identical evaluator arguments.
7. Select on strict JSON validity first, then segmentation/POS/romanization quality,
   p95 latency, throughput, and estimated cost.
8. Start only the selected model and
   `bash backend/deployment/runpod/start_api.sh <model> <revision>`; expose FastAPI
   through the RunPod proxy and build the staging extension against that URL.
9. After the manual YouTube result, delete the Pod (including its Pod volume), confirm
   zero Pods/endpoints, and check local background processes.

The evaluation report is retained in the local working tree before teardown. No
commit or push occurs until the real YouTube test has been reported.
