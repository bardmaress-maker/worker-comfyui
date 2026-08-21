# JupyterLab cell — download models to the network volume

Run this on a **RunPod Pod with the network volume attached** (the volume is at `/workspace`
there; the serverless worker later sees the same files at `/runpod-volume`).

All URLs verified live — HTTP 200 + `Content-Length` checked — on 2026-08-21.

## One cell, copy-paste

```bash
%%bash
set -e
ROOT=/workspace
mkdir -p $ROOT/models/unet $ROOT/models/vae $ROOT/models/clip

# Diffusion model -- UNETLoader  (26.48 GB)
wget -c --progress=dot:giga \
  -O $ROOT/models/unet/Qwen-Rapid-AIO-SFW-v23.safetensors \
  "https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO/resolve/main/v23/Qwen-Rapid-AIO-SFW-v23.safetensors"

# Text encoder -- CLIPLoader     (8.74 GB)
wget -c --progress=dot:giga \
  -O $ROOT/models/clip/qwen_2.5_vl_7b_fp8_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

# VAE -- VAELoader               (0.24 GB)
wget -c --progress=dot:giga \
  -O $ROOT/models/vae/qwen_image_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"

echo "--- done ---"
find $ROOT/models -name '*.safetensors' -printf '%p  %s bytes\n'
```

## Verify the sizes afterwards

A truncated download fails later as a confusing safetensors header error at model-load time, so
check now:

```bash
%%bash
cd /workspace/models
sha() { printf "%-42s %14s  %s\n" "$(basename $1)" "$(stat -c%s $1)" "$2"; }
echo "file                                            actual        expected"
sha unet/Qwen-Rapid-AIO-SFW-v23.safetensors     28431840023
sha clip/qwen_2.5_vl_7b_fp8_scaled.safetensors   9384670680
sha vae/qwen_image_vae.safetensors                253806246
```

Every "actual" must equal "expected". If one doesn't, delete that file and re-run the download
cell — `wget -c` resumes rather than restarting.

## Faster alternative: `hf` CLI

HuggingFace's own client parallelises chunks and is usually noticeably faster than `wget` for the
26 GB file:

```bash
%%bash
pip install -q -U "huggingface_hub[cli]"
hf download Phr00t/Qwen-Image-Edit-Rapid-AIO v23/Qwen-Rapid-AIO-SFW-v23.safetensors \
    --local-dir /tmp/dl
mv /tmp/dl/v23/Qwen-Rapid-AIO-SFW-v23.safetensors /workspace/models/unet/
```

Note it preserves the repo's folder structure under `--local-dir`, hence the `mv`.

---

## Why these three, and only these three

Derived by scanning **every** workflow JSON in the project — not from memory:

| Model | Loader | Goes in | Used by |
|---|---|---|---|
| `Qwen-Rapid-AIO-SFW-v23.safetensors` | `UNETLoader` | `models/unet/` | all 7 workflow files |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `CLIPLoader` | `models/clip/` | all 7 workflow files |
| `qwen_image_vae.safetensors` | `VAELoader` | `models/vae/` | all 7 workflow files |

**Deliberately excluded:** `Qwen-Image-Edit-F2P一致性.safetensors`, a LoRA referenced *only* by the
superseded `reference_edit_workflow_*` files. It was removed from production after an A/B test
showed the AIO checkpoint already has the edit behaviour built in. No current workflow loads it.

**Directory names matter.** `unet` / `vae` / `clip` are what the workflow loaders resolve against
via `extra_model_paths.iron-vale.yaml`. Note the text encoder lives under `split_files/text_encoders/`
in its HuggingFace repo but belongs in `models/clip/` on the volume — that mismatch is expected.
