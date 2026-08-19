# Iron Vale / Adrian Valen custom build

This fork adds a custom build for the Iron Vale / Adrian Valen manhwa recap panel-generation
pipeline, kept separate from everything upstream so `git fetch upstream && git merge upstream/main`
stays low-conflict:

- `Dockerfile.iron-vale` -- the actual image (custom nodes + baked-in reference crops on top of
  `runpod/worker-comfyui:5.8.6-base`). Upstream's own `Dockerfile` is untouched.
- `.github/workflows/iron-vale-build.yml` -- builds and pushes `Dockerfile.iron-vale` to Docker Hub.
  Independent of upstream's `dev.yml`/`release.yml` (which build the sdxl/sd3/flux*/z-image-turbo
  matrix via `docker-bake.hcl` and are tied to this repo's changesets release flow) -- untouched.
- `input/` -- the current character and location reference PNGs baked into the image.
- `workflows/panel_reference_edit_workflow.json` -- the one ComfyUI workflow this pipeline uses.
- `docs/iron-vale/` -- model list for the RunPod Network Volume, custom-node decisions, and
  workflow notes.

## CI secrets

`.github/workflows/iron-vale-build.yml` needs the same `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`
repository secrets documented in upstream's `docs/ci-cd.md`.

## Syncing from upstream

```
git fetch upstream
git merge upstream/main
```

Should almost never conflict with anything above, since none of it touches a file upstream also
modifies.
