"""
Generates docs/architecture.drawio

Fixes vs previous version:
  - No swim lanes (they caused nodes/backgrounds to render at wrong absolute coords)
  - 7 true columns: one group per column, zero same-column overlap
  - Edge exit/entry points matched to actual direction (down, right, left-loop)
  - Backward edge (TouchInputManager → ParticleSurfaceView) routed via explicit
    waypoints below the two nodes so it never crosses other edges
  - No labelBackgroundColor set on edges → draw.io uses transparent default,
    which is readable in both light and dark mode
  - Skip-edges within the Particle column routed on the right-hand side so they
    don't pile on top of the straight adjacency arrows
"""

import xml.etree.ElementTree as ET

# ── Geometry constants ────────────────────────────────────────────────────────
NW, NH      = 180, 75    # node width / height
V_GAP       = 20         # vertical gap between nodes in same group
COL_STRIDE  = 260        # column width + inter-column gap
MARGIN_X    = 50
MARGIN_Y    = 50
GROUP_PAD   = 18         # padding around group bounding box

# ── Layers & node order ───────────────────────────────────────────────────────
# Each layer is one column (left → right, col index 0..6)
LAYER_ORDER = ["Entry", "UI/GL", "Input", "Particle", "Network", "Data", "External"]

LAYERS = {
    "Entry":    ["AndroidManifest", "MainActivity"],
    "UI/GL":    ["ParticleSurfaceView", "ParticleRenderer", "ShaderProgram"],
    "Input":    ["TouchInputManager", "VelocityTracker"],
    "Particle": ["ParticleSystem", "ParticleEmitter", "ParticlePool", "NoiseField", "Particle"],
    "Network":  ["BroadcastServer", "TouchEventSerializer"],
    "Data":     ["TouchEvent", "TouchEventType"],
    "External": ["ExtListeners"],
}

NODE_LABELS = {
    "AndroidManifest":      "AndroidManifest&#xa;(INTERNET, WIFI,&#xa;OpenGL ES 2.0)",
    "MainActivity":         "MainActivity&#xa;(AppCompatActivity)",
    "ParticleSurfaceView":  "ParticleSurfaceView&#xa;(GLSurfaceView)",
    "ParticleRenderer":     "ParticleRenderer&#xa;(GLSurfaceView.Renderer)",
    "ShaderProgram":        "ShaderProgram&#xa;(GLSL vert + frag)",
    "TouchInputManager":    "TouchInputManager",
    "VelocityTracker":      "VelocityTracker&#xa;(Android SDK)",
    "ParticleSystem":       "ParticleSystem&#xa;(cap 20 000)",
    "ParticleEmitter":      "ParticleEmitter",
    "ParticlePool":         "ParticlePool&#xa;(pre-alloc 20 000)",
    "NoiseField":           "NoiseField&#xa;(Perlin noise)",
    "Particle":             "Particle&#xa;(pos, vel, life, hue)",
    "BroadcastServer":      "BroadcastServer&#xa;(UDP :9876 →&#xa;255.255.255.255)",
    "TouchEventSerializer": "TouchEventSerializer&#xa;&#x26;&#xa;⚠ fromJson() unused",
    "TouchEvent":           "TouchEvent&#xa;(data class)",
    "TouchEventType":       "TouchEventType&#xa;(enum: DOWN/MOVE&#xa;/UP/BURST)",
    "ExtListeners":         "External Listeners&#xa;(LAN :9876)",
}

# fillColor, strokeColor, fontColor, groupBgColor
LAYER_THEME = {
    "Entry":    ("dae8fc", "6c8ebf", "1a3a5c", "EBF5FB"),
    "UI/GL":    ("e1d5e7", "9673a6", "3d1a54", "F3EEF8"),
    "Input":    ("d5e8d4", "82b366", "1a3d1a", "EBF7EB"),
    "Particle": ("ffe6cc", "d6b656", "5c3a00", "FEF5E7"),
    "Network":  ("f8cecc", "b85450", "6b1a17", "FDEDEC"),
    "Data":     ("fff2cc", "d6b656", "5c4a00", "FEFDE7"),
    "External": ("f5f5f5", "888888", "333333", "FAFAFA"),
}

# ── Compute node positions ────────────────────────────────────────────────────
node_to_layer = {n: l for l, ns in LAYERS.items() for n in ns}
col_of = {layer: idx for idx, layer in enumerate(LAYER_ORDER)}

def col_x(layer):
    return MARGIN_X + col_of[layer] * COL_STRIDE

def node_y(layer, idx):
    # Offset group label header (20px) then stack nodes
    return MARGIN_Y + 30 + idx * (NH + V_GAP)

positions = {}   # node → (x, y)
for layer, nodes in LAYERS.items():
    x = col_x(layer)
    for i, n in enumerate(nodes):
        positions[n] = (x, node_y(layer, i))

def cx(node):   # centre-x of node
    return positions[node][0] + NW // 2

def cy(node):   # centre-y of node
    return positions[node][1] + NH // 2

def bottom(node):
    return positions[node][1] + NH

def top(node):
    return positions[node][1]

def right(node):
    return positions[node][0] + NW

def left(node):
    return positions[node][0]

# ── Build XML ─────────────────────────────────────────────────────────────────
root = ET.Element("mxGraphModel",
    dx="1422", dy="762", grid="1", gridSize="10",
    guides="1", tooltips="1", connect="1", arrows="1",
    fold="1", page="0", pageScale="1",
    pageWidth="1920", pageHeight="1080",
    math="0", shadow="0")

rc = ET.SubElement(root, "root")
ET.SubElement(rc, "mxCell", id="0")
ET.SubElement(rc, "mxCell", id="1", parent="0")

# ── Group background rectangles (rendered first = behind nodes) ───────────────
for gid, layer in enumerate(LAYER_ORDER, start=50):
    nodes = LAYERS[layer]
    xs = [positions[n][0] for n in nodes]
    ys = [positions[n][1] for n in nodes]
    gx = min(xs) - GROUP_PAD
    gy = min(ys) - GROUP_PAD - 20    # extra room for the group label above nodes
    gw = NW + GROUP_PAD * 2
    gh = (max(ys) + NH) - min(ys) + GROUP_PAD * 2 + 20
    _, stroke, _, bg = LAYER_THEME[layer]
    style = (
        f"rounded=1;arcSize=4;"
        f"fillColor=#{bg};strokeColor=#{stroke};strokeWidth=2;"
        f"fontSize=11;fontStyle=1;align=center;verticalAlign=top;"
        f"spacingTop=4;fontColor=#{stroke};"
    )
    cell = ET.SubElement(rc, "mxCell",
        id=str(gid), value=layer, style=style, vertex="1", parent="1")
    ET.SubElement(cell, "mxGeometry",
        x=str(gx), y=str(gy), width=str(gw), height=str(gh),
        **{"as": "geometry"})

# ── Node cells ────────────────────────────────────────────────────────────────
node_id = {}   # node name → xml id string
nid = 200
for layer in LAYER_ORDER:
    for node in LAYERS[layer]:
        fill, stroke, font, _ = LAYER_THEME[layer]
        style = (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=12;"
            f"fillColor=#{fill};strokeColor=#{stroke};fontColor=#{font};"
            f"fontSize=10;fontStyle=1;align=center;verticalAlign=middle;"
        )
        x, y = positions[node]
        cell = ET.SubElement(rc, "mxCell",
            id=str(nid), value=NODE_LABELS[node],
            style=style, vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry",
            x=str(x), y=str(y), width=str(NW), height=str(NH),
            **{"as": "geometry"})
        node_id[node] = str(nid)
        nid += 1

# ── Edge helpers ──────────────────────────────────────────────────────────────
eid = 900

BASE_EDGE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
    "jettySize=auto;fontSize=9;fontStyle=0;"
    # No labelBackgroundColor → transparent in both light and dark mode
)

def add_edge(src, dst, label, extra_style="", waypoints=None):
    global eid
    style = BASE_EDGE + extra_style
    cell = ET.SubElement(rc, "mxCell",
        id=str(eid), value=label, style=style,
        edge="1", source=node_id[src], target=node_id[dst], parent="1")
    geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
    if waypoints:
        arr = ET.SubElement(geo, "Array", **{"as": "points"})
        for wx, wy in waypoints:
            ET.SubElement(arr, "mxPoint", x=str(wx), y=str(wy))
    eid += 1

# ── Edges ─────────────────────────────────────────────────────────────────────

# ── Same-column, adjacent downward (straight vertical arrow) ──────────────────
STRAIGHT_DOWN = "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
add_edge("AndroidManifest",     "MainActivity",         "launches",       STRAIGHT_DOWN)
add_edge("ParticleSurfaceView", "ParticleRenderer",     "sets renderer",  STRAIGHT_DOWN)
add_edge("ParticleRenderer",    "ShaderProgram",        "compiles & uses",STRAIGHT_DOWN)
add_edge("TouchInputManager",   "VelocityTracker",      "uses",           STRAIGHT_DOWN)
add_edge("BroadcastServer",     "TouchEventSerializer", "serializes via", STRAIGHT_DOWN)
add_edge("TouchEvent",          "TouchEventType",       "has",            STRAIGHT_DOWN)
add_edge("NoiseField",          "Particle",             "steers",         STRAIGHT_DOWN)

# ── Same-column skip-downward edges: route on RIGHT side of Particle column ───
# exitX=1 (right of source), entryX=1 (right of target) → orthogonal routes
# along the right edge of the column, avoiding the nodes in between.
SKIP_RIGHT = "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
add_edge("ParticleSystem", "ParticlePool", "manages", SKIP_RIGHT)
add_edge("ParticlePool",   "Particle",    "pools",   SKIP_RIGHT)

# NoiseField samples is a skip (PS→NF skips PE and PP): use further right offset
# add explicit waypoint 30px right of the column so it doesn't overlap 'manages'
NF_X = right("ParticleSystem") + 35
add_edge("ParticleSystem", "NoiseField", "samples",
         "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;",
         waypoints=[(NF_X, cy("ParticleSystem")), (NF_X, cy("NoiseField"))])

# ── ParticleEmitter → ParticleSystem: upward within same column ───────────────
# Route on LEFT side to avoid clashing with the downward skip-right routes
PE_LEFT_X = left("ParticleEmitter") - 30
add_edge("ParticleEmitter", "ParticleSystem", "spawn()",
         "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
         waypoints=[(PE_LEFT_X, cy("ParticleEmitter")), (PE_LEFT_X, cy("ParticleSystem"))])

# ── Cross-column rightward edges ──────────────────────────────────────────────
RIGHT = "exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;"

add_edge("MainActivity",        "ParticleSurfaceView", "creates",             RIGHT)
add_edge("MainActivity",        "TouchInputManager",   "creates",             RIGHT)
add_edge("MainActivity",        "BroadcastServer",     "creates",             RIGHT)
add_edge("ParticleSurfaceView", "TouchInputManager",   "forwards MotionEvent",RIGHT)
add_edge("ParticleSurfaceView", "ParticleEmitter",     "queueEvent → emit",   RIGHT)
add_edge("ParticleRenderer",    "ParticleSystem",      "reads liveParticles", RIGHT)
add_edge("TouchInputManager",   "BroadcastServer",     "emits TouchEvent",    RIGHT)
add_edge("BroadcastServer",     "TouchEvent",          "enqueues",            RIGHT)
add_edge("BroadcastServer",     "ExtListeners",        "UDP broadcast",       RIGHT)

# ── Backward edge: TouchInputManager → ParticleSurfaceView ────────────────────
# Routed BELOW both nodes via explicit waypoints so it never crosses other edges
LOOP_Y = max(bottom("TouchInputManager"), bottom("ParticleSurfaceView")) + 55
add_edge("TouchInputManager", "ParticleSurfaceView", "onBurst →\nqueueEvent",
         "exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;curved=1;",
         waypoints=[(cx("TouchInputManager"), LOOP_Y),
                    (cx("ParticleSurfaceView"), LOOP_Y)])

# ── Write output ──────────────────────────────────────────────────────────────
tree = ET.ElementTree(root)
ET.indent(tree, space="  ")
out = "/Users/manuelmarianosilva/Documents/particle-system/docs/architecture.drawio"
tree.write(out, encoding="utf-8", xml_declaration=True)
print(f"Saved: {out}")
print("Open at: https://app.diagrams.net  (File → Open from → Device)")
print("Or install the draw.io VS Code extension and open the file directly.")
