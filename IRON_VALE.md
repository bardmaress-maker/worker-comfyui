# Iron Vale / Adrian Valen custom build

A custom serverless worker for the Iron Vale manhwa recap panel-generation pipeline, living inside
this fork of `runpod-workers/worker-comfyui`. Everything here is **additive** — upstream's own
`Dockerfile`, `docker-bake.hcl`, `dev.yml` and `release.yml` are untouched, so
`git fetch upstream && git merge upstream/main` stays low-conflict.

| Path | What |
|---|---|
| `Dockerfile.iron-vale` | The image: custom nodes + reference crops on `runpod/worker-comfyui:5.8.6-base`. |
| `extra_model_paths.iron-vale.yaml` | Model path resolution — fixes a real `unet`/`diffusion_models` naming gap. |
| `snapshots/` | Verbatim ComfyUI Manager export from the working pod (provenance). |
| `scripts/iron-vale/install-models.sh` | Populates the RunPod Network Volume; verified URLs, size-checked. |
| `scripts/iron-vale/api_to_ui.py` | API→UI workflow converter, for editing/re-exporting in ComfyUI. |
| `workflows/` | The production workflow (API + UI) and legacy ones. See `workflows/README.md`. |
| `input/` | Character + location reference PNGs baked into the image. |
| `docs/iron-vale/` | Model list, custom-node decisions, workflow notes. |
| `.github/workflows/iron-vale-build.yml` | Builds/pushes `Dockerfile.iron-vale` to Docker Hub. |

## Setup

1. **Models** → `docs/iron-vale/models.md`. Run `scripts/iron-vale/install-models.sh` on a
   temporary Pod with the network volume attached (~36 GB, resumable, size-verified).
2. **CI secrets** → `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` as repository secrets. Pushes build
   `<user>/iron-vale-comfyui-worker:latest` and `:<sha>`.
3. **Endpoint** → create a Serverless Endpoint on the pushed image, attaching the volume under
   **Advanced → Select Network Volume**.

Request shape is upstream's: `{"input": {"images": [...], "workflow": {...}}}` — see
`test_input.json`.

## Design decisions worth knowing

- **Models live on the volume, not in the image.** ~36 GB would never fit a standard GitHub runner
  (~14 GB disk), and the volume is shared across workers and persists across restarts.
- **The snapshot is committed but not `restore-snapshot`-ed.** Most of its pinned commits no longer
  exist upstream, so restoring hard-fails; the reasoning and the full hash-verification table are
  in `docs/iron-vale/custom-nodes.md`.
- **Only one custom node is actually required** (`ComfyUI-Easy-Use`, for `easy cleanGpuUsed`).
  Everything else in the production workflow was verified to be core ComfyUI.

Two upstream findings that are **documented but not applied** — both would alter tuned generation
behavior — are written up at the end of `docs/iron-vale/models.md`: the checkpoint being an
all-in-one (the separate 8.7 GB CLIP may be redundant), and a patched text-encode node that raises
the reference-image limit from 3 to 4 and targets the same aspect-ratio/cropping bug class this
project already hit.

## Syncing from upstream

```bash
git fetch upstream && git merge upstream/main
```
