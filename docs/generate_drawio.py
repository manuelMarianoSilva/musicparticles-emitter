#!/usr/bin/env python3
"""
generate_drawio.py  —  Generic, language-agnostic draw.io diagram generator.

Usage:
    python3 generate_drawio.py <config.json> [output.drawio]

If output path is omitted, writes <config-basename>.drawio next to the config.

Config JSON format
──────────────────
{
  "title": "My App Architecture",          // optional

  "layers": [
    {
      "id":    "LayerName",                // required; used as column header
      "label": "Layer Display Name",       // optional (defaults to id)
      "theme": {                           // optional; auto-assigned from palette
        "fill":   "dae8fc",               // node fill  (hex, no #)
        "stroke": "6c8ebf",               // node border
        "font":   "1a3a5c",               // node text
        "group":  "EBF5FB"               // column background
      },
      "nodes": [
        {
          "id":    "ClassName",            // required; must be unique across all layers
          "label": "ClassName\\n(detail)" // optional (defaults to id); \\n = line break
        },
        ...
      ]
    },
    ...
  ],

  "edges": [
    {
      "from":    "SourceNodeId",           // required
      "to":      "TargetNodeId",           // required
      "label":   "relationship",           // optional
      "routing": "auto"                    // optional; see below
    },
    ...
  ]
}

Routing values (edge-level override):
  "auto"     — no forced ports; draw.io picks the path (good default)
  "right"    — exit right / enter left  (forward across columns)
  "down"     — exit bottom / enter top  (adjacent downward, same column)
  "skip_r"   — skip downward on right side of column
  "up_l"     — upward on left side of column
  "below"    — backward edge routed below both nodes (U-bend)

Omitting "routing" enables smart auto-detection (recommended).
"""

import json
import re as _re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Default colour palette (cycles if more layers than entries) ───────────────
# Each tuple: (fill, stroke, font, group_bg)  — all hex without #
PALETTE = [
    ("dae8fc", "6c8ebf", "1a3a5c", "EBF5FB"),
    ("e1d5e7", "9673a6", "3d1a54", "F3EEF8"),
    ("d5e8d4", "82b366", "1a3d1a", "EBF7EB"),
    ("ffe6cc", "d6b656", "5c3a00", "FEF5E7"),
    ("f8cecc", "b85450", "6b1a17", "FDEDEC"),
    ("fff2cc", "a0a000", "3d3d00", "FEFDE7"),
    ("f5f5f5", "888888", "333333", "FAFAFA"),
    ("d0e8ff", "4a90d9", "0d3a6b", "E8F4FF"),
    ("e8f5e9", "388e3c", "1b5e20", "F1FAF1"),
    ("fce4ec", "e91e63", "880e4f", "FFF0F5"),
    ("fff3e0", "e65100", "5c3700", "FFF8F0"),
    ("e8eaf6", "3949ab", "1a237e", "F0F1FA"),
]

# ── Layout constants ──────────────────────────────────────────────────────────
NW               = 180  # node width
NH               = 75   # node height
V_GAP            = 55   # vertical gap between nodes — room for edge labels
MARGIN_X         = 50
MARGIN_Y         = 50
SWIMLANE_HEADER  = 30   # height of swimlane header (where the layer name shows)
NODE_PAD         = 18   # padding between swimlane border and the nodes inside

# Edge label font used in BASE_EDGE_STYLE — kept in sync manually.
_EDGE_FONT_SIZE  = 9    # pt / draw.io font-size units
_CHAR_WIDTH_PX   = 5.8  # empirical: avg px per character at font-size 9
_GAP_PADDING     = 40   # minimum clear space on each side of a label in the gap
_GAP_MIN         = 120  # floor gap width so very short labels don't collapse layout

def _estimate_label_px(text: str) -> int:
    """Pixel-width estimate for a label string at _EDGE_FONT_SIZE.
    Multi-line labels: use the longest line."""
    if not text:
        return 0
    longest = max(len(line) for line in text.replace("\\n", "\n").split("\n"))
    return int(longest * _CHAR_WIDTH_PX)

def _compute_col_stride(cfg: dict) -> int:
    """Return COL_STRIDE sized so that the widest edge label fits inside the
    inter-column gap without overlapping adjacent swimlanes.

    Only same-column skip-row edges place their label in the gap; cross-column
    edges use the top corridor (y=25) above all content, so their labels never
    consume gap space.  We scan *all* edge labels as a safe upper bound.
    """
    max_px = max(
        (_estimate_label_px(e.get("label", "")) for e in cfg.get("edges", [])),
        default=0,
    )
    sl_w = NW + NODE_PAD * 2                          # swimlane width (216 px)
    gap  = max(max_px + _GAP_PADDING * 2, _GAP_MIN)  # label + breathing room
    return sl_w + gap

# COL_STRIDE is set dynamically per config in build_xml(); this module-level
# variable is overwritten there and used by _gap_mid / _left_gap_mid.
COL_STRIDE: int = NW + NODE_PAD * 2 + _GAP_MIN  # sensible default until overwritten

# ── Helpers — all take the ABSOLUTE position dict ────────────────────────────

def _cx(pos, node):  return pos[node][0] + NW // 2
def _cy(pos, node):  return pos[node][1] + NH // 2
def _top(pos, node): return pos[node][1]
def _bot(pos, node): return pos[node][1] + NH
def _lft(pos, node): return pos[node][0]
def _rgt(pos, node): return pos[node][0] + NW

def _gap_mid(col_idx: int) -> int:
    """X-midpoint of the gap between column col_idx and col_idx+1.
    Vertical edge segments placed here are safely between swimlanes."""
    sl_w       = NW + NODE_PAD * 2
    right_edge = MARGIN_X + col_idx * COL_STRIDE + sl_w
    left_next  = MARGIN_X + (col_idx + 1) * COL_STRIDE
    return (right_edge + left_next) // 2

def _left_gap_mid(col_idx: int) -> int:
    """X-midpoint of the gap to the LEFT of column col_idx.
    For col 0 uses the left margin corridor."""
    if col_idx == 0:
        return MARGIN_X // 2
    return _gap_mid(col_idx - 1)

# ── Config loading ─────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)

    if "layers" not in cfg:
        raise ValueError("Config must have a 'layers' key.")
    if "edges" not in cfg:
        raise ValueError("Config must have an 'edges' key.")

    # Normalise: fill in defaults
    all_node_ids = set()
    for i, layer in enumerate(cfg["layers"]):
        if "id" not in layer:
            raise ValueError(f"Layer at index {i} is missing 'id'.")
        layer.setdefault("label", layer["id"])

        # Assign palette colour if no theme provided
        if "theme" not in layer:
            fill, stroke, font, group = PALETTE[i % len(PALETTE)]
            layer["theme"] = {
                "fill": fill, "stroke": stroke,
                "font": font, "group": group,
            }
        else:
            t = layer["theme"]
            fill, stroke, font, group = PALETTE[i % len(PALETTE)]
            t.setdefault("fill",   fill)
            t.setdefault("stroke", stroke)
            t.setdefault("font",   font)
            t.setdefault("group",  group)

        for j, node in enumerate(layer.get("nodes", [])):
            if "id" not in node:
                raise ValueError(
                    f"Node at index {j} in layer '{layer['id']}' is missing 'id'."
                )
            if node["id"] in all_node_ids:
                raise ValueError(f"Duplicate node id: '{node['id']}'.")
            all_node_ids.add(node["id"])
            # \\n in JSON label → actual newline encoded for draw.io HTML
            node.setdefault("label", node["id"])

    for k, edge in enumerate(cfg["edges"]):
        if "from" not in edge or "to" not in edge:
            raise ValueError(f"Edge at index {k} is missing 'from' or 'to'.")
        if edge["from"] not in all_node_ids:
            raise ValueError(f"Edge {k}: unknown source node '{edge['from']}'.")
        if edge["to"] not in all_node_ids:
            raise ValueError(f"Edge {k}: unknown target node '{edge['to']}'.")
        edge.setdefault("label", "")

    return cfg


# ── Layout ────────────────────────────────────────────────────────────────────

def compute_layout(cfg: dict):
    """
    Returns:
      abs_pos       : {node_id: (abs_x, abs_y)}  — absolute canvas positions
                      used by routing helpers and waypoint calculations
      rel_pos       : {node_id: (rel_x, rel_y)}  — positions relative to the
                      swimlane content area; used for mxGeometry of node cells
      swimlane_geom : {layer_id: (sl_x, sl_y, sl_w, sl_h)}
      node_to_layer : {node_id: layer_id}
      col_of        : {layer_id: col_index}
      layer_nodes   : {layer_id: [node_ids in order]}
    """
    abs_pos       = {}
    rel_pos       = {}
    swimlane_geom = {}
    node_to_layer = {}
    col_of        = {}
    layer_nodes   = {}

    for col_idx, layer in enumerate(cfg["layers"]):
        lid   = layer["id"]
        nodes = layer.get("nodes", [])
        n     = len(nodes)

        col_of[lid]      = col_idx
        layer_nodes[lid] = [nd["id"] for nd in nodes]

        sl_x = MARGIN_X + col_idx * COL_STRIDE
        sl_y = MARGIN_Y
        sl_w = NW + NODE_PAD * 2
        sl_h = (SWIMLANE_HEADER + NODE_PAD
                + n * NH + max(0, n - 1) * V_GAP
                + NODE_PAD)

        swimlane_geom[lid] = (sl_x, sl_y, sl_w, sl_h)

        for row_idx, node in enumerate(nodes):
            nid = node["id"]
            # relative to swimlane content area (below the header)
            rel_pos[nid] = (NODE_PAD,
                            SWIMLANE_HEADER + NODE_PAD + row_idx * (NH + V_GAP))
            # absolute canvas position for routing
            abs_pos[nid] = (sl_x + NODE_PAD,
                            sl_y + SWIMLANE_HEADER + NODE_PAD + row_idx * (NH + V_GAP))
            node_to_layer[nid] = lid

    return abs_pos, rel_pos, swimlane_geom, node_to_layer, col_of, layer_nodes


# ── Smart edge routing ────────────────────────────────────────────────────────

def compute_routing(src, dst, positions, node_to_layer, col_of, layer_nodes,
                    backward_state, skip_r_state, up_l_state,
                    override=None, label=""):
    """
    Returns (extra_style: str, waypoints: list[(x,y)] | None).

    override can be one of: "auto", "right", "down", "skip_r", "up_l", "below"
    """
    sc = col_of[node_to_layer[src]]
    dc = col_of[node_to_layer[dst]]
    src_row = layer_nodes[node_to_layer[src]].index(src)
    dst_row = layer_nodes[node_to_layer[dst]].index(dst)

    # ── Explicit override ────────────────────────────────────────────────────
    if override == "auto":
        return ("", None)

    if override == "right":
        # Delegate to the same logic as auto-detected forward edges
        # by temporarily clearing override and falling through — handled below
        override = None

    if override == "down":
        return ("exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                "entryX=0.5;entryY=0;entryDx=0;entryDy=0;", None)

    if override == "skip_r":
        key  = f"skip_{sc}"
        step = _estimate_label_px(label) // 2 + 8
        offset = skip_r_state.get(key, 0)
        skip_r_state[key] = offset + step
        rx = _gap_mid(sc) + offset
        return ("exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                "entryX=1;entryY=0.5;entryDx=0;entryDy=0;",
                [(rx, _cy(positions, src)), (rx, _cy(positions, dst))])

    if override == "up_l":
        key  = f"up_{sc}"
        step = _estimate_label_px(label) // 2 + 8
        offset = up_l_state.get(key, 0)
        up_l_state[key] = offset + step
        lx = _left_gap_mid(sc) - offset
        return ("exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                "entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
                [(lx, _cy(positions, src)), (lx, _cy(positions, dst))])

    if override == "below":
        key = (sc, dc)
        offset = backward_state.get(key, 0)
        backward_state[key] = offset + 60
        loop_y = max(_bot(positions, src), _bot(positions, dst)) + 50 + offset
        return ("exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                "entryX=0.5;entryY=1;entryDx=0;entryDy=0;curved=1;",
                [(_cx(positions, src), loop_y), (_cx(positions, dst), loop_y)])

    # ── Auto-detect ──────────────────────────────────────────────────────────

    if sc < dc:
        sy    = _cy(positions, src)
        dy    = _cy(positions, dst)
        # Top corridor: above all swimlane headers (swimlanes start at MARGIN_Y=50)
        y_top = MARGIN_Y // 2   # = 25, safely above every swimlane

        if dc - sc == 1:
            # Adjacent columns — only one gap exists, no intermediate nodes.
            # Transition Y in that single gap; horizontal segments stay clear.
            if sy == dy:
                return ("exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;", None)
            gx = _gap_mid(sc)
            return ("exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                    "entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
                    [(gx, sy), (gx, dy)])

        # Multi-column span (dc - sc > 1):
        # Any horizontal segment at node-level Y would cut through intermediate
        # swimlane rows.  Route via top corridor above all content:
        #   source-right → gap-after-src (drop to top corridor)
        #   → top corridor horizontal → gap-before-dst (descend to dest Y)
        #   → destination-left
        g_src = _gap_mid(sc)        # gap right after source column
        g_dst = _gap_mid(dc - 1)    # gap right before destination column
        wps   = [(g_src, sy), (g_src, y_top)]
        if g_src != g_dst:
            wps.append((g_dst, y_top))
        wps.append((g_dst, dy))
        return ("exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                "entryX=0;entryY=0.5;entryDx=0;entryDy=0;", wps)

    if sc > dc:
        # Backward (cross-column, leftward) — route below both nodes
        key = (sc, dc)
        offset = backward_state.get(key, 0)
        backward_state[key] = offset + 60
        loop_y = max(_bot(positions, src), _bot(positions, dst)) + 50 + offset
        return ("exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                "entryX=0.5;entryY=1;entryDx=0;entryDy=0;curved=1;",
                [(_cx(positions, src), loop_y), (_cx(positions, dst), loop_y)])

    # Same column
    if src_row == dst_row:
        # Self-loop — let draw.io handle it
        return ("", None)

    if src_row < dst_row:
        # Downward same column
        if dst_row - src_row == 1:
            # Adjacent rows: straight vertical, no obstacles
            return ("exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                    "entryX=0.5;entryY=0;entryDx=0;entryDy=0;", None)
        else:
            # Skip rows: bypass through the centre of the right-hand gap so the
            # label stays in the clear space between swimlanes, not over nodes.
            # Stagger step = half the label's pixel width + 8px clear margin so
            # the next line always starts beyond this label's right edge.
            key  = f"skip_{sc}"
            step = _estimate_label_px(label) // 2 + 8
            offset = skip_r_state.get(key, 0)
            skip_r_state[key] = offset + step
            rx = _gap_mid(sc) + offset
            return ("exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                    "entryX=1;entryY=0.5;entryDx=0;entryDy=0;",
                    [(rx, _cy(positions, src)), (rx, _cy(positions, dst))])
    else:
        # Upward same column: bypass through the centre of the left-hand gap.
        # Same dynamic stagger logic, mirrored to the left.
        key  = f"up_{sc}"
        step = _estimate_label_px(label) // 2 + 8
        offset = up_l_state.get(key, 0)
        up_l_state[key] = offset + step
        lx = _left_gap_mid(sc) - offset
        return ("exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
                "entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
                [(lx, _cy(positions, src)), (lx, _cy(positions, dst))])


# ── XML builder ───────────────────────────────────────────────────────────────

BASE_EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
    "jettySize=auto;fontSize=9;fontStyle=0;html=1;"
    # Light pill background — readable in both light and dark mode,
    # clearly distinct from node fills, never blends into canvas.
    "labelBackgroundColor=#f5f5f5;labelBorderColor=#cccccc;fontColor=#333333;"
)

def build_xml(cfg: dict) -> ET.ElementTree:
    # Dynamically size COL_STRIDE to fit the widest edge label before layout.
    global COL_STRIDE
    COL_STRIDE = _compute_col_stride(cfg)

    abs_pos, rel_pos, swimlane_geom, node_to_layer, col_of, layer_nodes = \
        compute_layout(cfg)

    # ── Label & unused-node detection ────────────────────────────────────────
    # A node is "unused" if it has "unused": true OR its label contains any of
    # the dead-code markers below.
    _UNUSED_MARKERS = ("unused", "⚠", "dead code", "not used", "never called")

    def _is_unused(node: dict) -> bool:
        raw = node.get("label", "")
        return bool(node.get("unused")) or any(
            m in raw.lower() for m in _UNUSED_MARKERS
        )

    def _build_label(raw: str, is_unused_node: bool) -> str:
        """Return the draw.io cell value for a node.

        Normal nodes: plain text with &#xa; line breaks (html=1 renders them).
        Unused nodes: HTML with the clean node name + a red UNUSED badge.
          - Dead-code markers (⚠, "unused", …) are stripped from the main text.
          - An inline <span> with red background / white text provides the badge.
          - The rest of the box keeps its swimlane fill/font colours.
        """
        if not is_unused_node:
            return raw.replace("\\n", "&#xa;").replace("\n", "&#xa;")

        # Strip dead-code markers so the main text stays clean
        clean = raw
        for pat in (
            r"⚠\s*\w+\(\)\s*unused",   # e.g.  ⚠ fromJson() unused
            r"⚠\s*[^\n]*",             # any ⚠ annotation
            r"\bunused\b",
            r"\bdead\s*code\b",
            r"\bnot\s*used\b",
            r"\bnever\s*called\b",
        ):
            clean = _re.sub(pat, "", clean, flags=_re.IGNORECASE)

        # Split into lines, drop blanks, wrap each in <b>
        lines = [l.strip() for l in clean.replace("\\n", "\n").split("\n")]
        lines = [l for l in lines if l]
        body  = "<br>".join(f"<b>{l}</b>" for l in lines)

        # Red pill badge: white bold text, red background
        badge = (
            '<br><span style="background-color:#FF0000;color:#FFFFFF;'
            'font-weight:bold;border-radius:3px;padding:1px 6px;font-size:9px;">'
            "UNUSED</span>"
        )
        return body + badge

    node_label  = {}
    node_unused = {}

    for layer in cfg["layers"]:
        for node in layer.get("nodes", []):
            is_u = _is_unused(node)
            node_unused[node["id"]] = is_u
            node_label[node["id"]]  = _build_label(node["label"], is_u)

    # ── Root XML ─────────────────────────────────────────────────────────────
    root = ET.Element("mxGraphModel",
        dx="1422", dy="762", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1",
        fold="1", page="0", pageScale="1",
        pageWidth="1920", pageHeight="1080",
        math="0", shadow="0")
    rc = ET.SubElement(root, "root")
    ET.SubElement(rc, "mxCell", id="0")
    ET.SubElement(rc, "mxCell", id="1", parent="0")

    # ── Swimlane containers (one per layer) ───────────────────────────────────
    # Nodes are children of their swimlane so draw.io owns containment & z-order.
    swimlane_xml_id = {}   # layer_id → xml id string
    gid = 50
    for layer in cfg["layers"]:
        lid = layer["id"]
        t   = layer["theme"]
        sl_x, sl_y, sl_w, sl_h = swimlane_geom[lid]

        style = (
            f"swimlane;startSize={SWIMLANE_HEADER};"
            f"fillColor=#{t['group']};strokeColor=#{t['stroke']};strokeWidth=2;"
            f"fontColor=#{t['stroke']};fontSize=11;fontStyle=1;align=center;"
            f"rounded=1;arcSize=4;"
        )
        cell = ET.SubElement(rc, "mxCell",
            id=str(gid), value=layer["label"], style=style,
            vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry",
            x=str(sl_x), y=str(sl_y), width=str(sl_w), height=str(sl_h),
            **{"as": "geometry"})
        swimlane_xml_id[lid] = str(gid)
        gid += 1

    # ── Node cells (children of their swimlane) ───────────────────────────────
    # Unused nodes retain their swimlane fill/font colours so they blend into
    # their layer visually.  Only the border turns pure red (strokeWidth=3) and
    # the label contains a red UNUSED badge (see _build_label above).
    node_xml_id = {}
    nid = 200
    for layer in cfg["layers"]:
        lid = layer["id"]
        t   = layer["theme"]
        for node in layer.get("nodes", []):
            is_u   = node_unused[node["id"]]
            stroke = "FF0000" if is_u else t["stroke"]
            sw     = "3"      if is_u else "1"
            style  = (
                f"rounded=1;whiteSpace=wrap;html=1;arcSize=12;"
                f"fillColor=#{t['fill']};strokeColor=#{stroke};strokeWidth={sw};"
                f"fontColor=#{t['font']};fontSize=10;fontStyle=1;"
                f"align=center;verticalAlign=middle;"
            )
            rx, ry = rel_pos[node["id"]]
            cell = ET.SubElement(rc, "mxCell",
                id=str(nid), value=node_label[node["id"]],
                style=style, vertex="1",
                parent=swimlane_xml_id[lid])   # ← child of swimlane
            ET.SubElement(cell, "mxGeometry",
                x=str(rx), y=str(ry), width=str(NW), height=str(NH),
                **{"as": "geometry"})
            node_xml_id[node["id"]] = str(nid)
            nid += 1

    # ── Edge cells (always parent="1", use absolute waypoint coords) ──────────
    backward_state = {}
    skip_r_state   = {}
    up_l_state     = {}

    for eid, edge in enumerate(cfg["edges"], start=900):
        src, dst = edge["from"], edge["to"]
        override = edge.get("routing", None)

        raw_label = edge.get("label", "")
        extra_style, waypoints = compute_routing(
            src, dst, abs_pos, node_to_layer, col_of, layer_nodes,
            backward_state, skip_r_state, up_l_state, override,
            label=raw_label)

        style = BASE_EDGE_STYLE + extra_style
        label = raw_label.replace("\\n", "&#xa;").replace("\n", "&#xa;")

        cell = ET.SubElement(rc, "mxCell",
            id=str(eid), value=label, style=style,
            edge="1", source=node_xml_id[src], target=node_xml_id[dst],
            parent="1")
        geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

        if waypoints:
            arr = ET.SubElement(geo, "Array", **{"as": "points"})
            for wx, wy in waypoints:
                ET.SubElement(arr, "mxPoint", x=str(wx), y=str(wy))

    return ET.ElementTree(root)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    config_path = sys.argv[1]
    if len(sys.argv) >= 3:
        out_path = sys.argv[2]
    else:
        out_path = str(Path(config_path).with_suffix(".drawio"))

    cfg  = load_config(config_path)
    tree = build_xml(cfg)
    ET.indent(tree, space="  ")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
