# Workflow to use

`workflows/panel_reference_edit_workflow.json` is the **only** workflow currently in production
for this pipeline (copied from the main project's `panel_reference_edit_workflow.json`, which
`Workflows/generate_panel.py` builds every real panel from). It's already in API format, and
supports up to 3 reference images (`image1`/`image2`/`image3` on the `TextEncodeQwenImageEditPlus`
node) -- a location reference plus up to two characters, or up to three characters, decided
per-panel by the generation code. There's no second "future" workflow to add on top of it: the
3-image support already covers what location-reference generation needed.

It's already API format, so you don't strictly need to round-trip it through the ComfyUI UI at
all -- `worker-comfyui` takes API-format JSON directly in each request's `input.workflow` field
(see `test_input.json` in the upstream repo for the exact request shape: `{"input": {"images": [...],
"workflow": {...}}}`). If you do want to load it into the UI first (to sanity-check node wiring
visually, or tweak something), ComfyUI accepts API-format JSON via drag-and-drop same as UI-format
-- then use **Workflow → Export (API)** to get a fresh copy back out after any edit.

## Do NOT use these (still in the main project, kept for history only)

- `Workflows/reference_edit_workflow_UI.json` / `_API.json` -- an **older** version, from before
  the LoRA was removed and before the aspect-ratio/`latent_image` bug was fixed. Using this would
  silently reintroduce both.
- `Workflows/experimental_stitched_multiref_UI.json` / `_API.json` -- an abandoned experiment
  (image-stitching instead of native `image1`/`image2`/`image3` sockets), superseded once the
  native multi-image approach was confirmed working. Not used by any current code.

## One thing this changes about how panels get generated

The current pipeline (`Workflows/generate_panel.py` + `upload_references.py`) uploads reference
images to the ComfyUI pod's input folder as a separate step before generating, because that pod
persists between calls. A serverless worker doesn't guarantee that -- each request should be
self-contained.

This repo's `input/` folder bakes in the current character + location reference crops directly (see
the Dockerfile), so `LoadImage` nodes can find them by filename with no upload step at all, the same
way they already work today. If a new character or location reference gets added later, it needs to
be dropped into this repo's `input/` folder and rebuilt -- or sent per-request as base64 in the
request's `images` array instead (`worker-comfyui` supports both; see its `test_input.json`).
`generate_panel.py`/`generate_batch.py` will need a small update to target this worker's HTTP API
shape instead of the current pod's direct ComfyUI API -- that's a follow-up, not done in this pass.
