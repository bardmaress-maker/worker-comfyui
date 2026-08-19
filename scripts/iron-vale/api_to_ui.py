"""Convert a ComfyUI API-format workflow (flat node_id -> {class_type, inputs})
back into a UI-format workflow (nodes[]/links[]) that ComfyUI's editor can
open normally.

WHY THIS EXISTS: this project's production workflow
(workflows/panel_reference_edit_workflow.json) only exists in API format --
it was hand-edited and converted, so there's no UI-format twin to load into
ComfyUI when you want to inspect the graph visually or re-export it via
Workflow -> Export (API). This script produces that twin. The reverse
direction already exists as Workflows/ui_to_api.py in the main project.

Round trip:
    python api_to_ui.py panel_reference_edit_workflow.json panel_ui.json
    # drag panel_ui.json into ComfyUI, edit, then Workflow -> Export (API)

Usage:
    python api_to_ui.py <api_workflow.json> <output_ui.json> [--comfy-url URL]

--comfy-url is optional. Given a reachable ComfyUI, widget values are ordered
using the live server's /object_info, which is what makes the result exactly
match what the editor expects. Without it, widget order falls back to the
order keys happen to appear in the API JSON -- usually right, but verify the
graph in the editor before trusting it.
"""
import argparse
import json
import sys
import urllib.request

# Laid out in a simple grid; ComfyUI has no auto-layout on import, so without
# explicit positions every node would stack at the origin and be unreadable.
COL_WIDTH = 400
ROW_HEIGHT = 180
NODES_PER_COL = 6
DEFAULT_SIZE = [340, 120]


def fetch_object_info(comfy_url: str) -> dict:
    # Same User-Agent workaround as ui_to_api.py -- the RunPod proxy in front
    # of ComfyUI 403s urllib's default UA.
    req = urllib.request.Request(
        f"{comfy_url.rstrip('/')}/object_info",
        headers={"User-Agent": "Mozilla/5.0 (compatible; api_to_ui.py)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_link(value) -> bool:
    """API-format inputs are either a literal widget value or a link, encoded
    as [source_node_id, output_slot]."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], int)
    )


def _widget_order(class_type: str, inputs: dict, object_info: dict):
    """Return widget input names in the order ComfyUI expects them in
    widgets_values. Falls back to API-JSON key order when /object_info isn't
    available."""
    literal_names = [k for k, v in inputs.items() if not _is_link(v)]
    info = (object_info or {}).get(class_type)
    if not info:
        return literal_names

    ordered = []
    input_def = info.get("input", {})
    for section in ("required", "optional"):
        for name in (input_def.get(section) or {}):
            if name in literal_names:
                ordered.append(name)
    # Anything present in the API JSON but not declared by the server (custom
    # node version drift) still needs to survive the conversion.
    ordered += [n for n in literal_names if n not in ordered]
    return ordered


def convert_api_to_ui(api: dict, object_info: dict) -> dict:
    node_ids = sorted(api.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)
    index_of = {nid: i for i, nid in enumerate(node_ids)}

    nodes = []
    links = []
    next_link_id = 1
    # (target_node_id, input_name) -> link id, built as we walk inputs
    outputs_needed = {}  # source_node_id -> max slot index referenced

    # First pass: discover how many output slots each node actually needs, so
    # a node feeding two different consumers still declares both slots.
    for nid, node in api.items():
        for value in (node.get("inputs") or {}).values():
            if _is_link(value):
                src, slot = str(value[0]), value[1]
                outputs_needed[src] = max(outputs_needed.get(src, 0), slot)

    for nid in node_ids:
        node = api[nid]
        class_type = node.get("class_type")
        inputs = node.get("inputs") or {}
        i = index_of[nid]
        pos = [(i // NODES_PER_COL) * COL_WIDTH, (i % NODES_PER_COL) * ROW_HEIGHT]

        ui_inputs = []
        for name, value in inputs.items():
            if not _is_link(value):
                continue
            src_id, src_slot = str(value[0]), value[1]
            link_id = next_link_id
            next_link_id += 1
            # UI link record: [id, origin_node, origin_slot, target_node,
            # target_slot, type]
            links.append([link_id, int(src_id), src_slot, int(nid), len(ui_inputs), "*"])
            ui_inputs.append({"name": name, "type": "*", "link": link_id})

        n_out = outputs_needed.get(nid, -1) + 1
        ui_outputs = []
        for slot in range(n_out):
            slot_links = [l[0] for l in links if l[1] == int(nid) and l[2] == slot]
            ui_outputs.append({"name": f"OUT{slot}", "type": "*", "links": slot_links, "slot_index": slot})

        widgets_values = [inputs[n] for n in _widget_order(class_type, inputs, object_info)]

        nodes.append({
            "id": int(nid),
            "type": class_type,
            "pos": pos,
            "size": DEFAULT_SIZE,
            "flags": {},
            "order": i,
            "mode": 0,
            "inputs": ui_inputs,
            "outputs": ui_outputs,
            "properties": {"Node name for S&R": class_type},
            "widgets_values": widgets_values,
        })

    return {
        "last_node_id": max((int(n) for n in node_ids if str(n).isdigit()), default=0),
        "last_link_id": next_link_id - 1,
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--comfy-url", default=None,
                   help="Live ComfyUI URL, for exact widget ordering via /object_info")
    args = p.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        api = json.load(f)

    if "nodes" in api and "links" in api:
        print("Input already looks like a UI-format workflow (has nodes[]/links[]).", file=sys.stderr)
        sys.exit(1)

    object_info = {}
    if args.comfy_url:
        try:
            object_info = fetch_object_info(args.comfy_url)
            print(f"Loaded /object_info ({len(object_info)} node types)")
        except Exception as exc:
            print(f"WARNING: could not reach {args.comfy_url} ({exc}).", file=sys.stderr)
            print("Falling back to API-JSON key order for widgets -- verify the graph "
                  "in the editor before exporting.", file=sys.stderr)

    ui = convert_api_to_ui(api, object_info)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(ui, f, indent=2)

    print(f"Wrote {args.output}: {len(ui['nodes'])} nodes, {len(ui['links'])} links")
    if not object_info:
        print("NOTE: converted without /object_info. Open it in ComfyUI and confirm "
              "each node's widget values look right before relying on it.")


if __name__ == "__main__":
    main()
