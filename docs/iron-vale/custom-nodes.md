# Custom nodes

Source: ComfyUI Manager snapshot exported 2026-08-19 (`2026-08-19_20-39-45_snapshot.json`, not
committed here -- it's a point-in-time export of a whole interactive pod environment, most of which
doesn't belong in a headless worker; see "Not included" below for what got left out and why).

## Installed (`Dockerfile`)

| Node | How | Why |
|---|---|---|
| `comfyui-easy-use` | Comfy Registry | Provides `easy cleanGpuUsed`, used directly in the production workflow. |
| `comfyui-kjnodes` | Comfy Registry | General-purpose node pack present in the snapshot. |
| `comfyui-multigpu` | Comfy Registry | Present in the snapshot. |
| `comfyui_essentials` | Comfy Registry | Present in the snapshot. |
| `comfyui-custom-scripts` | Comfy Registry | Present in the snapshot. |
| `rgthree-comfy` | Comfy Registry | Present in the snapshot. |
| `sigmas_tools_and_the_golden_scheduler` | Comfy Registry | Present in the snapshot. |
| `ComfyUI-RunpodDirect` | git, pinned to `67999ba4a64462641213bc3e90a2f5eba52c22ae` | RunPod-specific node, not on the registry -- pinned to the exact commit from the source snapshot. |

Registry (CNR) nodes install via `comfy-node-install`, which always takes the latest release of
each package -- there's no simple pinned-version install path the way there is for a git commit.
If a specific version ever needs pinning, switch that one entry to the same
git-clone-then-`git checkout <hash>` pattern used for ComfyUI-RunpodDirect.

## Not included

- **ComfyUI-Manager** -- already present in the base image; `comfy-cli` installs it as part of a
  standard ComfyUI setup, and the base image's `start.sh` already assumes it's there (it calls
  `comfy-manager-set-mode offline` unconditionally at container start). Reinstalling it would be
  redundant.
- **Civicomfy** (`MoonGoblinDev/Civicomfy`) -- a CivitAI browse/download UI helper. Nothing in the
  production workflow calls it, and it's an interactive-only tool with no purpose on a headless
  serverless worker -- pure dead weight (extra image size, extra `requirements.txt` deps at build
  time) for zero runtime benefit. Add it back with the same git-clone pattern as
  ComfyUI-RunpodDirect if that assumption turns out wrong.

## Python packages

The snapshot's `pips` block lists ~260 pinned packages, but that's the **whole interactive pod
environment** -- it includes `jupyterlab`, `notebook`, `ipykernel`, `debugpy`, `matplotlib`, and
similar dev/notebook tooling that has nothing to do with running this workflow headlessly. Blindly
restoring all of it (e.g. via `comfy node restore-snapshot`) would meaningfully bloat the image and
slow every build for no runtime benefit.

Instead, each custom node installed above pulls in only its own `requirements.txt` -- the same
targeted approach the upstream base image itself uses for its own bundled nodes. If a specific pip
version pin from the snapshot turns out to matter (a node breaking on a newer transitive
dependency), pin it explicitly in the Dockerfile rather than restoring the full list.
