# Models -- what goes where

## Split: image vs. network volume

| | What | Why |
|---|---|---|
| **Baked into the image** | Custom nodes, reference PNGs (`input/`, ~23 MB), workflow JSON | Small, static, and needed on every request. Baking them in means no upload round-trip. |
| **RunPod Network Volume** | All three model files (~36 GB) | Far too large for a Docker image built on a standard GitHub runner (~14 GB disk). The volume persists across worker restarts and is shared by every worker, so it's downloaded once, not per-image-build. |

## Storage layout

The base image auto-detects a network volume and resolves models through
`extra_model_paths.yaml`. **Serverless workers** mount it at `/runpod-volume`; **Pods** mount the
same volume at `/workspace`. Required structure:

```
<volume root>/
└── models/
    ├── unet/
    │   └── Qwen-Rapid-AIO-SFW-v23.safetensors
    ├── vae/
    │   └── qwen_image_vae.safetensors
    └── clip/
        └── qwen_2.5_vl_7b_fp8_scaled.safetensors
```

### A path gotcha this repo fixes

The stock `src/extra_model_paths.yaml` declares only the legacy `unet:` and `clip:` keys. Current
ComfyUI registers those folders internally as **`diffusion_models`** (dirs: `models/unet` +
`models/diffusion_models`) and **`text_encoders`** (dirs: `models/text_encoders` + `models/clip`).
An `extra_model_paths` key only takes effect when it matches a *registered* folder name, so with
the stock file a `UNETLoader`/`CLIPLoader` can fail to find models that are sitting in exactly the
documented place.

`extra_model_paths.iron-vale.yaml` in this repo declares **both spellings** and replaces the stock
file at build time, so it resolves either way. If models still aren't found, that's the first thing
to check.

## The three files

All URLs and byte sizes below were **verified live** (HTTP 200 + `Content-Length` read directly)
on 2026-08-19 — not copied out of documentation.

| File | Dir | Bytes | Source |
|---|---|---|---|
| `Qwen-Rapid-AIO-SFW-v23.safetensors` | `models/unet/` | 28,431,840,023 (~26.5 GB) | `huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO` → `v23/` |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `models/clip/` | 9,384,670,680 (~8.7 GB) | `huggingface.co/Comfy-Org/Qwen-Image_ComfyUI` → `split_files/text_encoders/` |
| `qwen_image_vae.safetensors` | `models/vae/` | 253,806,246 (~242 MB) | `huggingface.co/Comfy-Org/Qwen-Image_ComfyUI` → `split_files/vae/` |

The checkpoint is the HuggingFace original behind the CivitAI "Qwen-Rapid-AIO-SFW" listing —
using HF directly avoids CivitAI's API-token-gated downloads entirely.

## Installing

Run on a **temporary Pod with the volume attached** (not on the serverless worker):

```bash
bash scripts/iron-vale/install-models.sh
```

It auto-detects `/runpod-volume` vs `/workspace`, creates the directories, resumes partial
downloads (`wget -c`), and **verifies each file's byte size** after download — a truncated model
otherwise fails much later and far more confusingly, as a safetensors header error at load time.

Then attach the volume to the endpoint (**Advanced → Select Network Volume**). To confirm the
worker sees the models, set `NETWORK_VOLUME_DEBUG=true` and send any request; the worker logs a
full report of what it found.

## Not needed

`Qwen-Image-Edit-F2P一致性.safetensors` (a LoRA) appears in an **older** workflow
(`Workflows/reference_edit_workflow_API.json` in the main project) but was deliberately removed
from production after an A/B test showed the base checkpoint already has the edit behavior. Don't
upload it.

---

## Two findings worth knowing about

These came out of reading the checkpoint author's documentation while verifying the download URLs.
**Neither is applied** — both would change generation behavior you've already tuned, so they're
recommendations, not changes.

### 1. The checkpoint is an all-in-one; the separate CLIP may be redundant

Phr00t describes it as a *"merge of accelerators, VAE and CLIP"* and says to load it with a **Load
Checkpoint** node. Our workflow instead uses `UNETLoader` + separate `VAELoader`/`CLIPLoader` —
which demonstrably works, but means we're storing a 8.7 GB text encoder and a 242 MB VAE that may
already be inside the 26.5 GB checkpoint.

Switching to `CheckpointLoaderSimple` could cut the volume from ~36 GB to ~26.5 GB. Worth testing
if volume cost matters; not worth breaking a working pipeline over otherwise.

### 2. There's a patched text-encode node that targets bugs we already hit

The same repo ships `fixed-textencode-node/nodes_qwen.v2.py`, a drop-in replacement for ComfyUI's
core `comfy_extras/nodes_qwen.py`. Per its README it:

- **raises the image inputs from 3 to 4** — directly relieves the 3-slot budget in
  `resolve_reference_images()`, where a location reference plus three characters currently forces
  the location image to be dropped;
- **"addresses unexpected zoom / cropping problems"** and an issue where "the image would get cut
  off and mirror itself";
- **takes a latent input to size the reference scaling from** — the core node hardcodes reference
  images to ~1024×1024 total pixels regardless of your actual output dimensions (verified by
  reading the core source), which is the same class of aspect-ratio bug this project already
  root-caused and hand-fixed by rewiring `latent_image` to node 49.

Also noted while reading: the author recommends **`euler_ancestral` / `beta`** for v23; our
workflow currently runs `euler` / `simple` at 6 steps, cfg 1. That's a deliberate, tested setting
here, so it stays — but the discrepancy is worth knowing if output quality is ever revisited.
