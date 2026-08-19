# Models -- RunPod Network Volume

None of these are baked into the Docker image (see the Dockerfile's comment on why) -- they go on a
RunPod **Network Volume**, which the base `worker-comfyui` image auto-detects at `/runpod-volume`
via its built-in `extra_model_paths.yaml`. Create the volume in the same region as the endpoint,
then place files in exactly this structure:

```
/runpod-volume/
└── models/
    ├── unet/
    │   └── Qwen-Rapid-AIO-SFW-v23.safetensors
    ├── vae/
    │   └── qwen_image_vae.safetensors
    └── clip/
        └── qwen_2.5_vl_7b_fp8_scaled.safetensors
```

(Folder names must be `unet` / `vae` / `clip` exactly -- that's what our workflow's `UNETLoader` /
`VAELoader` / `CLIPLoader` nodes look for, per the base image's `extra_model_paths.yaml`.)

## The three files

| File | Goes in | Size | Source |
|---|---|---|---|
| `Qwen-Rapid-AIO-SFW-v23.safetensors` | `models/unet/` | ~26 GB (based on sibling versions) | **Not auto-downloadable by me -- see below.** |
| `qwen_image_vae.safetensors` | `models/vae/` | 254 MB | Confirmed: `https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors` |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `models/clip/` | 9.38 GB | Confirmed: `https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` |

The VAE and CLIP URLs are both live-verified (HTTP 200, real file sizes checked directly, not
guessed) and come from the same Comfy-Org HuggingFace repo -- the VAE one is also independently
confirmed by embedded metadata already sitting in this project's own
`Workflows/reference_edit_workflow_UI.json`.

### The checkpoint (`Qwen-Rapid-AIO-SFW-v23.safetensors`) needs your input

I can't confirm an exact download URL for this one, and I'm not going to guess -- getting a model
URL wrong is worse than not having one. What I did confirm: "Qwen-Rapid-AIO-SFW" is a real,
actively-updated checkpoint series on CivitAI (`civitai.com/models/2113348`, a merge of
accelerators + VAE + CLIP for fast Qwen Image Edit), currently indexed up to v9 there -- v23 is
newer than what search results show, consistent with it still being actively updated. CivitAI
downloads also commonly need an API token even for a direct `wget`/`curl`.

Two ways to close this out:
1. Open your own CivitAI download history / the model page, grab the exact v23 file, and either
   hand me the direct URL (I'll verify it before using it) or upload it straight to the network
   volume yourself (temporary Pod + drag-drop, or the S3-compatible API RunPod provides).
2. If it actually came from somewhere else (a local merge, a different host), just tell me and I'll
   adjust this doc.

## Not needed

`Qwen-Image-Edit-F2P一致性.safetensors` (a LoRA) shows up in an **older** workflow file in the main
project (`Workflows/reference_edit_workflow_API.json`) but was deliberately removed from the
current production workflow (`panel_reference_edit_workflow.json`) after an A/B test showed the
base checkpoint already has the edit behavior built in. Don't bother uploading it.

## Verifying it worked

Once the volume is attached to the endpoint (**Advanced → Select Network Volume**), set
`NETWORK_VOLUME_DEBUG=true` on the endpoint and send any request -- the worker logs a full report
of what it found under `/runpod-volume/models/...`. Turn it back off once confirmed (see the base
image's `docs/network-volumes.md` for the full diagnostic format).
