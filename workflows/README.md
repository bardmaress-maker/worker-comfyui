# Workflows

## Use this one

**`panel_reference_edit_workflow.json`** — API format, the only workflow in production. This is
what `Workflows/generate_panel.py` in the main project builds every real panel from, and what you
send to the worker in `input.workflow`.

**`panel_reference_edit_workflow_UI.json`** — the same graph in UI format, for loading into the
ComfyUI editor.

### Round-tripping through ComfyUI to export API format

The production workflow only ever existed in API format (it was hand-edited and converted), so
there was no UI twin to open in the editor. `scripts/iron-vale/api_to_ui.py` generates one:

```bash
python scripts/iron-vale/api_to_ui.py \
    workflows/panel_reference_edit_workflow.json \
    workflows/panel_reference_edit_workflow_UI.json \
    --comfy-url https://<your-pod>-8188.proxy.runpod.net   # optional but recommended
```

Then: drag the `_UI.json` into ComfyUI → edit → **Workflow → Export (API)** → drop the result back
over `panel_reference_edit_workflow.json`.

`--comfy-url` is optional. With it, widget ordering is resolved from the live server's
`/object_info`, which is what guarantees the editor reads values in the right slots. Without it the
script falls back to the order keys appear in the API JSON — usually correct, but check the graph
in the editor before trusting it. The generated file was verified to preserve all 19 nodes, all 20
links, and correct KSampler widget order (`seed, steps, cfg, sampler_name, scheduler, denoise` →
`6 steps, cfg 1, euler/simple`).

The reverse direction (UI → API, without going through the browser) already exists as
`Workflows/ui_to_api.py` in the main project.

> [!NOTE]
> You don't strictly need this round trip at all — `worker-comfyui` accepts API-format JSON
> directly in each request. It's only needed when you want to *edit* the graph visually.

## Do NOT use these

Kept for history only, prefixed `_legacy_`:

- **`_legacy_reference_edit_workflow_UI.json`** — predates two fixes: the LoRA removal, and the
  `latent_image` aspect-ratio bug (KSampler was wired to image1's `VAEEncode` instead of the
  correctly-sized empty latent, which was the real cause of the "deformed and pixelated faces"
  symptom). Using it silently reintroduces both.
- **`_legacy_experimental_stitched_multiref_UI.json`** — abandoned experiment that stitched
  reference images into one canvas instead of using the native `image1`/`image2`/`image3` sockets.
  Superseded once native multi-image was confirmed working.
