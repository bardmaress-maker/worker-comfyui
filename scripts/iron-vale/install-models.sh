#!/usr/bin/env bash
# Populate a RunPod Network Volume with every model the Iron Vale panel
# workflow needs.
#
# WHERE TO RUN THIS: on a temporary RunPod **Pod** with the network volume
# attached, not on the serverless worker. Pods mount the volume at /workspace;
# serverless workers see the same volume at /runpod-volume. This script
# auto-detects which one it's on, so just run it:
#
#     bash install-models.sh
#
# Override the target explicitly if needed:
#     VOLUME_ROOT=/workspace bash install-models.sh
#
# Total download: ~36 GB. Safe to re-run -- wget -c resumes partial files and
# completed files are skipped after a size check.

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate the volume
# ---------------------------------------------------------------------------
if [ -n "${VOLUME_ROOT:-}" ]; then
  ROOT="$VOLUME_ROOT"
elif [ -d /runpod-volume ]; then
  ROOT=/runpod-volume
elif [ -d /workspace ]; then
  ROOT=/workspace
else
  echo "ERROR: no network volume found at /runpod-volume or /workspace." >&2
  echo "Attach the volume, or set VOLUME_ROOT=/path explicitly." >&2
  exit 1
fi
echo "Using volume root: $ROOT"

# These directory names are what our workflow's loaders resolve against; see
# extra_model_paths.iron-vale.yaml. Do not rename them.
mkdir -p "$ROOT/models/unet" "$ROOT/models/vae" "$ROOT/models/clip"

# ---------------------------------------------------------------------------
# fetch <url> <dest-path> <expected-bytes>
# ---------------------------------------------------------------------------
# Verifies size after download. A truncated model file otherwise fails much
# later and much more confusingly (at ComfyUI load time, as a safetensors
# header error), so it's worth catching here.
fetch() {
  local url="$1" dest="$2" expected="$3"
  local name; name="$(basename "$dest")"

  if [ -f "$dest" ]; then
    local have; have=$(stat -c%s "$dest" 2>/dev/null || echo 0)
    if [ "$have" = "$expected" ]; then
      echo "OK (already present, size verified): $name"
      return 0
    fi
    echo "Resuming partial/mismatched download: $name (have $have, want $expected)"
  fi

  echo "Downloading $name ..."
  wget -c --progress=dot:giga -O "$dest" "$url"

  local got; got=$(stat -c%s "$dest" 2>/dev/null || echo 0)
  if [ "$got" != "$expected" ]; then
    echo "ERROR: $name is $got bytes, expected $expected." >&2
    echo "Delete it and re-run, or check the URL." >&2
    exit 1
  fi
  echo "OK: $name ($got bytes)"
}

# ---------------------------------------------------------------------------
# The three models
# ---------------------------------------------------------------------------
# All URLs and byte sizes below were verified live (HTTP 200 + Content-Length
# checked directly) on 2026-08-19, not copied from documentation.

# 1. Diffusion model -- UNETLoader (node 70) in panel_reference_edit_workflow.json
#    Phr00t's Qwen-Image-Edit-Rapid-AIO, SFW v23. This is the upstream source
#    for the CivitAI listing of the same name.
fetch \
  "https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO/resolve/main/v23/Qwen-Rapid-AIO-SFW-v23.safetensors" \
  "$ROOT/models/unet/Qwen-Rapid-AIO-SFW-v23.safetensors" \
  28431840023

# 2. VAE -- VAELoader (node 37)
fetch \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors" \
  "$ROOT/models/vae/qwen_image_vae.safetensors" \
  253806246

# 3. Text encoder / CLIP -- CLIPLoader (node 69)
fetch \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
  "$ROOT/models/clip/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
  9384670680

echo
echo "All models installed. Final layout:"
find "$ROOT/models" -type f \( -name '*.safetensors' -o -name '*.ckpt' \) -printf '  %p (%s bytes)\n'
echo
echo "Next: attach this volume to the serverless endpoint"
echo "(Advanced -> Select Network Volume). To confirm the worker sees them,"
echo "set NETWORK_VOLUME_DEBUG=true on the endpoint and send any request."
