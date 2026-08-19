# Custom nodes

Source of truth: `snapshots/2026-08-19_20-39-45_snapshot.json` — the verbatim ComfyUI Manager
export from the working pod, committed unmodified.

## Why the snapshot isn't restored directly

The obvious move is `comfy node restore-snapshot <file>` (what upstream's own
`src/restore_snapshot.sh` does). It doesn't work here. Every commit hash in the snapshot was
checked against its public repo on 2026-08-19:

| Pinned in snapshot | Commit | Status |
|---|---|---|
| `yolain/ComfyUI-Easy-Use` | `54d080bf6a` | **exists** |
| `kijai/ComfyUI-KJNodes` | `d19ce9078f` | gone |
| `MadiatorLabs/ComfyUI-RunpodDirect` | `67999ba4a6` | gone |
| `ltdrdata/ComfyUI-Manager` | `b2a9dec9b1` | gone |
| ComfyUI core | `35903cbdfa` | gone — not in `comfyanonymous/ComfyUI` at all |

Most of these repos force-push or rebase, and the ComfyUI core hash isn't in the upstream repo at
all (the source pod ran a RunPod-modified ComfyUI fork). `restore-snapshot` hard-fails on a dead
hash — the first build of this image failed exactly that way, exit 128 on the RunpodDirect
checkout. So `Dockerfile.iron-vale` installs explicitly and pins only what verifies.

Restoring the core ComfyUI pin would be undesirable even if it resolved: it would fight the base
image's own known-good ComfyUI.

## What our workflow actually requires

Every node class in `workflows/panel_reference_edit_workflow.json` was checked against ComfyUI
core source. Confirmed **core** (no custom node needed): `CFGNorm`, `ModelSamplingAuraFlow`,
`FluxKontextMultiReferenceLatentMethod`, `TextEncodeQwenImageEditPlus`, `ImageScaleToTotalPixels`,
`EmptySD3LatentImage`, `KSampler`, `VAEEncode`, `VAEDecode`, `LoadImage`, `SaveImage`,
`VAELoader`, `CLIPLoader`, `UNETLoader`.

The **only** custom-node dependency is `easy cleanGpuUsed` (node 65) → **ComfyUI-Easy-Use**. That's
why it's the one package pinned to an exact commit; the rest are installed because they were in
your environment, not because the current workflow needs them.

## Installed

| Node | How | Notes |
|---|---|---|
| `comfyui-easy-use` | registry, then pinned to `54d080bf6a` | **Required** — provides `easy cleanGpuUsed`. |
| `comfyui-kjnodes` | registry, latest | Snapshot pin dead; not used by current workflow. |
| `comfyui-multigpu` | registry, latest | From snapshot. |
| `comfyui_essentials` | registry, latest | From snapshot. |
| `comfyui-custom-scripts` | registry, latest | From snapshot. |
| `rgthree-comfy` | registry, latest | From snapshot. |
| `sigmas_tools_and_the_golden_scheduler` | registry, latest | From snapshot. |

Registry installs always take the latest release — there's no exact-version install path — which is
fine since the snapshot pins these as version strings, not reproducible commits. To truly pin one,
use the `git fetch <sha> && git checkout <sha>` pattern the Dockerfile uses for Easy-Use.

Each installed node's own `requirements.txt` is installed explicitly afterward. A node missing its
Python deps fails at ComfyUI import time, which surfaces on a live worker as the misleading
"ComfyUI server not reachable" error rather than anything naming the real cause. A CPU boot smoke
test (`main.py --quick-test-for-ci --cpu`) then runs at build time to catch exactly that class of
failure in CI instead of on a live GPU worker.

## Not installed

- **ComfyUI-Manager** — already in the base image; `start.sh` there already assumes it exists
  (it calls `comfy-manager-set-mode offline` unconditionally at boot).
- **Civicomfy** — interactive CivitAI browser/downloader UI. Nothing in the workflow calls it and
  it has no purpose headless.
- **ComfyUI-RunpodDirect** — convenience node for the RunPod *pod* UI. Its pinned commit is gone,
  nothing references it, and it has no role on a serverless worker. This is what broke the first
  build.

## Python packages

The snapshot's `pips` block lists ~260 pinned packages, but that's the **whole interactive pod
environment** — `jupyterlab`, `notebook`, `ipykernel`, `debugpy`, `matplotlib` and similar dev
tooling with no bearing on headless generation. Restoring it wholesale would bloat the image and,
worse, risks overwriting the specific `torch`/`transformers` versions the base image pins on
purpose (upstream's Dockerfile has extended comments on why those pins matter — a wrong `torch`
build fails CUDA init at startup).

Per-node `requirements.txt` covers what's actually needed. If a specific pin from the snapshot ever
proves necessary, add it explicitly to the Dockerfile rather than restoring the whole list.
