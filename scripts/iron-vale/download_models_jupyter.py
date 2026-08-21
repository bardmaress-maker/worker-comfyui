"""Download every model the Iron Vale workflows need onto a RunPod Network Volume.

Written for JupyterLab on a RunPod **Pod** with the network volume attached.
Paste into a notebook cell and run, or from a terminal: `python download_models_jupyter.py`

WHERE FILES GO
--------------
RunPod mounts the same network volume at different paths depending on what's
using it (per RunPod's own network-volume docs):

    Pod (this script runs here)  ->  /workspace
    Serverless worker (reads it) ->  /runpod-volume

So you download to /workspace/models/... here, and the serverless worker sees
the identical files at /runpod-volume/models/... later. Nothing to re-copy.

The subdirectory names (unet / vae / clip) are what our workflows' loaders
resolve against -- see extra_model_paths.iron-vale.yaml. Don't rename them.

WHAT IT DOWNLOADS  (~35.5 GB total)
-----------------------------------
Derived by scanning every workflow JSON in the project, not from memory. All
three are used by all 7 workflow files, and every URL below was verified live
(HTTP 200 + Content-Length) on 2026-08-21.

Safe to re-run: finished files are skipped after a size check, partial files
resume.
"""
import os
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Where the volume is
# ---------------------------------------------------------------------------
# Auto-detects so the same script works on a Pod or (if ever needed) inside a
# serverless container. Override with VOLUME_ROOT if your setup differs.
if os.environ.get("VOLUME_ROOT"):
    ROOT = os.environ["VOLUME_ROOT"]
elif os.path.isdir("/workspace"):
    ROOT = "/workspace"            # Pod -- the normal case for this script
elif os.path.isdir("/runpod-volume"):
    ROOT = "/runpod-volume"        # serverless worker
else:
    sys.exit("No volume found at /workspace or /runpod-volume. "
             "Attach the network volume, or set VOLUME_ROOT.")

# (url, subdirectory, filename, exact expected size in bytes)
MODELS = [
    # Diffusion model -- UNETLoader. Phr00t's Qwen-Image-Edit-Rapid-AIO SFW v23.
    # This HuggingFace repo is the upstream source behind the CivitAI listing of
    # the same name; using HF avoids CivitAI's API-token-gated downloads.
    ("https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO/resolve/main/v23/Qwen-Rapid-AIO-SFW-v23.safetensors",
     "unet", "Qwen-Rapid-AIO-SFW-v23.safetensors", 28431840023),

    # Text encoder -- CLIPLoader. Note it lives in the HF repo's
    # split_files/text_encoders/ but goes in the volume's models/clip/.
    ("https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
     "clip", "qwen_2.5_vl_7b_fp8_scaled.safetensors", 9384670680),

    # VAE -- VAELoader.
    ("https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
     "vae", "qwen_image_vae.safetensors", 253806246),
]

# NOT downloaded: Qwen-Image-Edit-F2P<...>.safetensors, a LoRA that appears only
# in the superseded reference_edit_workflow_* files. It was deliberately removed
# from production after an A/B test showed the AIO checkpoint already has the
# edit behaviour built in. No current workflow references it.


def human(n):
    return f"{n / 1024**3:.2f} GB"


def free_space(path):
    return shutil.disk_usage(path).free


def download(url, subdir, filename, expected):
    target_dir = os.path.join(ROOT, "models", subdir)
    os.makedirs(target_dir, exist_ok=True)
    dest = os.path.join(target_dir, filename)

    if os.path.exists(dest):
        have = os.path.getsize(dest)
        if have == expected:
            print(f"  SKIP  {filename} -- already complete ({human(have)})")
            return True
        print(f"  RESUME {filename} -- have {human(have)}, want {human(expected)}")

    # -c resumes; a dropped connection on a 26 GB file is common enough that
    # restarting from zero is not acceptable.
    cmd = ["wget", "-c", "--progress=dot:giga", "-O", dest, url]
    print(f"  GET   {filename}  ({human(expected)})")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  ERROR wget exited {result.returncode} for {filename}")
        return False

    # Verify size. A truncated model otherwise fails much later and far more
    # confusingly -- as a safetensors header error at ComfyUI load time.
    got = os.path.getsize(dest)
    if got != expected:
        print(f"  ERROR {filename} is {got} bytes, expected {expected}. "
              f"Delete it and re-run.")
        return False
    print(f"  OK    {filename} ({human(got)})")
    return True


def main():
    total = sum(m[3] for m in MODELS)
    print(f"Volume root : {ROOT}")
    print(f"Free space  : {human(free_space(ROOT))}")
    print(f"To download : {human(total)} across {len(MODELS)} files\n")

    if free_space(ROOT) < total:
        print("WARNING: free space looks smaller than the download size. "
              "Files already present are skipped, so this may still be fine.\n")

    ok = True
    for url, subdir, filename, expected in MODELS:
        ok &= download(url, subdir, filename, expected)

    print("\n--- final layout ---")
    for root, _, files in os.walk(os.path.join(ROOT, "models")):
        for f in sorted(files):
            if f.endswith((".safetensors", ".ckpt")):
                p = os.path.join(root, f)
                print(f"  {p}  ({human(os.path.getsize(p))})")

    if ok:
        print("\nAll models present and size-verified.")
        print("Next: attach this volume to the serverless endpoint "
              "(Advanced -> Select Network Volume).")
        print("To confirm the worker sees them, set NETWORK_VOLUME_DEBUG=true "
              "and send any request.")
    else:
        print("\nSome downloads failed -- see errors above. Re-run to retry; "
              "completed files are skipped.")
        sys.exit(1)


if __name__ == "__main__":
    main()
