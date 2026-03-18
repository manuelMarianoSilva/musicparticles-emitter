#!/usr/bin/env python3
"""
export_pdf.py  —  architecture.drawio → architecture.pdf

Parses the draw.io XML directly and renders a faithful, single-page PDF
whose dimensions match the diagram's native coordinate space.

draw.io coordinate units map to PDF points at the standard 72/96 ratio
(draw.io uses screen pixels at 96 dpi; PDF uses 72 dpi points).
"""

import re
import sys
import html
import math
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.colors import HexColor, black, white, Color
except ImportError:
    print("Missing dependency: pip install reportlab", file=sys.stderr)
    sys.exit(1)

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
DRAWIO_FILE = SCRIPT_DIR / "architecture.drawio"
PDF_OUT     = SCRIPT_DIR / "architecture.pdf"

# ── constants ─────────────────────────────────────────────────────────────────
DX_TO_PT   = 0.75   # 1 draw.io px → 0.75 PDF pt  (96 dpi → 72 dpi)
MARGIN     = 36     # pt — border around content on all sides
ARROW_SIZE = 5      # pt — arrowhead size
LABEL_PAD  = 3      # pt — label background padding

# ── helpers ───────────────────────────────────────────────────────────────────

def _sc(v: float) -> float:
    """Scale a draw.io coordinate value to PDF points."""
    return v * DX_TO_PT


def _parse_style(s: str) -> dict:
    """Parse a semicolon-separated draw.io style string into a dict."""
    d: dict = {}
    for part in (s or "").split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            d[k.strip()] = v.strip()
        elif part:
            d[part] = "1"
    return d


def _color(val: str | None, fallback: str | None = None) -> Color | None:
    """Convert a draw.io colour string to a ReportLab Color, or None."""
    if not val or val in ("none", "default", "inherit", ""):
        return HexColor(fallback) if fallback else None
    if val.startswith("#"):
        return HexColor(val)
    # draw.io may use named colours in some edge cases
    named = {"white": "#ffffff", "black": "#000000"}
    return HexColor(named.get(val.lower(), fallback or "#000000"))


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities; return plain text with \\n for breaks."""
    if not text:
        return ""
    text = text.replace("&#xa;", "\n").replace("&#xA;", "\n")
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _has_unused_badge(raw_value: str) -> bool:
    """Return True if the cell value contains the UNUSED HTML badge."""
    return "UNUSED" in raw_value and 'background-color:#FF0000' in raw_value


def _draw_arrow(c: Canvas, p1: tuple, p2: tuple, color: Color) -> None:
    """Draw a solid filled arrowhead at p2 pointing from p1."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length       # unit vector along edge
    nx, ny = -uy, ux                        # perpendicular unit vector
    sz = ARROW_SIZE
    tip   = p2
    base1 = (p2[0] - ux * sz + nx * sz * 0.45, p2[1] - uy * sz + ny * sz * 0.45)
    base2 = (p2[0] - ux * sz - nx * sz * 0.45, p2[1] - uy * sz - ny * sz * 0.45)
    c.setFillColor(color)
    path = c.beginPath()
    path.moveTo(*tip)
    path.lineTo(*base1)
    path.lineTo(*base2)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def _draw_centered_text(
    c: Canvas,
    lines: list[str],
    cx: float,
    cy_center: float,
    font_name: str,
    font_size: float,
    fill_color: Color,
    max_width: float | None = None,
) -> None:
    """Draw multi-line text centred around cy_center."""
    if not lines:
        return
    line_h = font_size * 1.3
    total_h = len(lines) * line_h
    top_y = cy_center + total_h / 2 - font_size * 0.85   # baseline of first line

    c.setFont(font_name, font_size)
    c.setFillColor(fill_color)
    y = top_y
    for line in lines:
        line = line.strip()
        if not line:
            y -= line_h
            continue
        # Truncate if too wide
        if max_width:
            while line and c.stringWidth(line, font_name, font_size) > max_width:
                line = line[:-1]
            if not line:
                y -= line_h
                continue
        c.drawCentredString(cx, y, line)
        y -= line_h


# ── main rendering ────────────────────────────────────────────────────────────

def main() -> None:
    tree = ET.parse(str(DRAWIO_FILE))
    xml_root = tree.getroot()
    # Support both <mxfile><diagram><mxGraphModel><root> and bare <mxGraphModel><root>
    cells_elem = (
        xml_root.find(".//root")          # works for any nesting depth
    )
    if cells_elem is None:
        print("ERROR: cannot find <root> in drawio file.", file=sys.stderr)
        sys.exit(1)

    by_id: dict = {}
    for cell in cells_elem.findall("mxCell"):
        cid = cell.get("id")
        if cid:
            by_id[cid] = cell

    # ── compute absolute positions for every vertex ───────────────────────────
    abs_geom: dict = {}   # cell_id → (abs_x, abs_y, w, h)
    for cell in cells_elem.findall("mxCell"):
        if cell.get("vertex") != "1":
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue
        x = float(geom.get("x", 0))
        y = float(geom.get("y", 0))
        w = float(geom.get("width",  0))
        h = float(geom.get("height", 0))
        parent = cell.get("parent", "1")
        if parent not in ("0", "1"):
            p_cell = by_id.get(parent)
            if p_cell is not None:
                pg = p_cell.find("mxGeometry")
                if pg is not None:
                    x += float(pg.get("x", 0))
                    y += float(pg.get("y", 0))
        abs_geom[cell.get("id")] = (x, y, w, h)

    # ── bounding box of all vertices ──────────────────────────────────────────
    all_x = [g[0] for g in abs_geom.values()] + [g[0] + g[2] for g in abs_geom.values()]
    all_y = [g[1] for g in abs_geom.values()] + [g[1] + g[3] for g in abs_geom.values()]
    min_x, min_y = min(all_x), min(all_y)
    max_x, max_y = max(all_x), max(all_y)

    page_w = _sc(max_x - min_x) + 2 * MARGIN
    page_h = _sc(max_y - min_y) + 2 * MARGIN

    c = Canvas(str(PDF_OUT), pagesize=(page_w, page_h))

    def to_pdf(dx: float, dy: float) -> tuple:
        """Convert draw.io absolute coords to PDF points (y-axis flipped)."""
        return (
            MARGIN + _sc(dx - min_x),
            page_h - MARGIN - _sc(dy - min_y),
        )

    def rect_blwh(dx: float, dy: float, dw: float, dh: float) -> tuple:
        """Return (x_bl, y_bl, w, h) in PDF points for a draw.io rect."""
        x_bl = MARGIN + _sc(dx - min_x)
        y_top = page_h - MARGIN - _sc(dy - min_y)
        w = _sc(dw)
        h = _sc(dh)
        return x_bl, y_top - h, w, h   # bottom-left, width, height

    # ── pass 1 — swimlane containers ─────────────────────────────────────────
    for cell in cells_elem.findall("mxCell"):
        if cell.get("vertex") != "1":
            continue
        style_str = cell.get("style", "")
        if "swimlane" not in style_str:
            continue
        cid = cell.get("id")
        if cid not in abs_geom:
            continue

        st = _parse_style(style_str)
        ax, ay, dw, dh = abs_geom[cid]
        rx, ry, rw, rh = rect_blwh(ax, ay, dw, dh)

        fill_c   = _color(st.get("fillColor"), "#f5f5f5")
        stroke_c = _color(st.get("strokeColor"), "#000000")
        sw       = _sc(float(st.get("strokeWidth", 1)))
        arc_pct  = float(st.get("arcSize", 4)) / 100
        radius   = min(rw, rh) * arc_pct
        start_h  = _sc(float(st.get("startSize", 30)))

        # Body (white fill)
        c.setFillColor(white)
        c.setStrokeColor(stroke_c or black)
        c.setLineWidth(sw)
        c.roundRect(rx, ry, rw, rh, radius=radius, fill=1, stroke=1)

        # Header overlay with swimlane colour
        c.setFillColor(fill_c or white)
        c.setStrokeColor(stroke_c or black)
        c.setLineWidth(sw)
        # Clip the top header area to the rounded shape — approximate by drawing
        # a rounded rect that bleeds below the header line, then mask out lower part.
        # Simpler: draw a rect for header + redraw rounded corners only on top.
        header_y = ry + rh - start_h
        c.roundRect(rx, header_y, rw, start_h, radius=radius, fill=1, stroke=0)
        # Separator line
        c.setStrokeColor(stroke_c or black)
        c.setLineWidth(sw * 0.6)
        c.line(rx, header_y, rx + rw, header_y)

        # Redraw full border on top so corners look clean
        c.setFillColor(Color(0, 0, 0, alpha=0))
        c.setStrokeColor(stroke_c or black)
        c.setLineWidth(sw)
        c.roundRect(rx, ry, rw, rh, radius=radius, fill=0, stroke=1)

        # Header label
        label_raw = cell.get("value", "")
        label     = _clean_html(label_raw)
        font_size = _sc(float(st.get("fontSize", 11)))
        font_c    = _color(st.get("fontColor"), "#000000")
        _draw_centered_text(
            c, [label],
            cx=rx + rw / 2,
            cy_center=header_y + start_h / 2,
            font_name="Helvetica-Bold",
            font_size=max(5.0, font_size),
            fill_color=font_c or black,
            max_width=rw - 8,
        )

    # ── pass 2 — node cells ───────────────────────────────────────────────────
    for cell in cells_elem.findall("mxCell"):
        if cell.get("vertex") != "1":
            continue
        style_str = cell.get("style", "")
        if "swimlane" in style_str:
            continue
        cid = cell.get("id")
        if cid in ("0", "1") or cid not in abs_geom:
            continue
        st = _parse_style(style_str)
        if not st:
            continue

        ax, ay, dw, dh = abs_geom[cid]
        rx, ry, rw, rh = rect_blwh(ax, ay, dw, dh)

        fill_c   = _color(st.get("fillColor"),   "#ffffff")
        stroke_c = _color(st.get("strokeColor"),  "#000000")
        sw       = _sc(float(st.get("strokeWidth", 1)))
        arc_pct  = float(st.get("arcSize", 12)) / 100
        radius   = min(rw, rh) * arc_pct

        c.setFillColor(fill_c or white)
        c.setStrokeColor(stroke_c or black)
        c.setLineWidth(sw)
        c.roundRect(rx, ry, rw, rh, radius=radius, fill=1, stroke=1)

        label_raw = cell.get("value", "")
        font_size = _sc(float(st.get("fontSize", 10)))
        font_c    = _color(st.get("fontColor"), "#000000")
        fs        = max(5.0, font_size)

        if _has_unused_badge(label_raw):
            # Extract name (before the badge span)
            name_part = re.sub(r'<span[^>]*>.*?</span>', '', label_raw, flags=re.DOTALL)
            name      = _clean_html(name_part)
            name_lines = name.split("\n")

            # Lay out: name lines then badge
            line_h    = fs * 1.3
            badge_fs  = max(5.0, fs * 0.85)
            badge_txt = "UNUSED"
            c.setFont("Helvetica-Bold", badge_fs)
            badge_tw  = c.stringWidth(badge_txt, "Helvetica-Bold", badge_fs)
            badge_bw  = badge_tw + 8
            badge_bh  = badge_fs * 1.4

            total_lines = len(name_lines) + 1   # +1 for badge row
            total_h     = total_lines * line_h
            top_y = ry + rh / 2 + total_h / 2 - fs * 0.85

            # Name lines
            c.setFont("Helvetica-Bold", fs)
            c.setFillColor(font_c or black)
            y = top_y
            for line in name_lines:
                c.drawCentredString(rx + rw / 2, y, line.strip())
                y -= line_h

            # Badge
            bx = rx + (rw - badge_bw) / 2
            by = y - badge_bh + line_h * 0.3
            c.setFillColor(HexColor("#FF0000"))
            c.roundRect(bx, by, badge_bw, badge_bh, radius=2, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", badge_fs)
            c.drawCentredString(rx + rw / 2, by + (badge_bh - badge_fs) / 2 + 1, badge_txt)
        else:
            label = _clean_html(label_raw)
            lines = [l for l in label.split("\n") if l.strip()]
            _draw_centered_text(
                c, lines,
                cx=rx + rw / 2,
                cy_center=ry + rh / 2,
                font_name="Helvetica-Bold",
                font_size=fs,
                fill_color=font_c or black,
                max_width=rw - 6,
            )

    # ── pass 3 — edges ────────────────────────────────────────────────────────
    for cell in cells_elem.findall("mxCell"):
        if cell.get("edge") != "1":
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue

        src_id  = cell.get("source")
        dst_id  = cell.get("target")
        if not src_id or not dst_id:
            continue
        if src_id not in abs_geom or dst_id not in abs_geom:
            continue

        st = _parse_style(cell.get("style", ""))

        # ── compute exact exit / entry points ─────────────────────────────────
        sx, sy, sw_dx, sh_dx = abs_geom[src_id]
        dx_, dy_, dw_dx, dh_dx = abs_geom[dst_id]

        exit_x  = float(st.get("exitX",  0.5))
        exit_y  = float(st.get("exitY",  1.0))
        entry_x = float(st.get("entryX", 0.5))
        entry_y = float(st.get("entryY", 0.0))

        start_pt = (sx + exit_x  * sw_dx, sy + exit_y  * sh_dx)
        end_pt   = (dx_ + entry_x * dw_dx, dy_ + entry_y * dh_dx)

        # Intermediate waypoints
        waypoints: list[tuple] = []
        arr = geom.find("Array[@as='points']")
        if arr is not None:
            for pt in arr.findall("mxPoint"):
                waypoints.append((float(pt.get("x", 0)), float(pt.get("y", 0))))

        path_dx = [start_pt] + waypoints + [end_pt]
        path_pdf = [to_pdf(p[0], p[1]) for p in path_dx]

        edge_stroke = _color(st.get("strokeColor"), "#000000") or black
        c.setStrokeColor(edge_stroke)
        c.setLineWidth(0.75)
        c.setDash()   # solid line

        # Draw polyline
        poly = c.beginPath()
        poly.moveTo(*path_pdf[0])
        for pt in path_pdf[1:]:
            poly.lineTo(*pt)
        c.drawPath(poly, stroke=1, fill=0)

        # Arrowhead at destination end
        if len(path_pdf) >= 2:
            _draw_arrow(c, path_pdf[-2], path_pdf[-1], edge_stroke)

        # ── edge label ────────────────────────────────────────────────────────
        raw_label = cell.get("value", "")
        label     = _clean_html(raw_label)
        if not label:
            continue

        # Place label at the midpoint of the longest horizontal segment,
        # falling back to polyline midpoint.
        best_seg   = None
        best_len   = -1
        for i in range(len(path_pdf) - 1):
            p_a, p_b = path_pdf[i], path_pdf[i + 1]
            seg_len  = math.hypot(p_b[0] - p_a[0], p_b[1] - p_a[1])
            is_horiz = abs(p_b[1] - p_a[1]) < 4
            if is_horiz and seg_len > best_len:
                best_len = seg_len
                best_seg = i

        if best_seg is not None:
            pa, pb  = path_pdf[best_seg], path_pdf[best_seg + 1]
            lbl_cx  = (pa[0] + pb[0]) / 2
            lbl_cy  = pa[1]
        else:
            # Polyline midpoint by arc length
            segs = []
            total = 0.0
            for i in range(len(path_pdf) - 1):
                d = math.hypot(path_pdf[i+1][0] - path_pdf[i][0],
                               path_pdf[i+1][1] - path_pdf[i][1])
                segs.append(d)
                total += d
            accum   = 0.0
            half    = total / 2
            lbl_cx  = (path_pdf[0][0] + path_pdf[-1][0]) / 2
            lbl_cy  = (path_pdf[0][1] + path_pdf[-1][1]) / 2
            for i, seg_d in enumerate(segs):
                if accum + seg_d >= half:
                    t      = (half - accum) / seg_d if seg_d > 0 else 0.5
                    lbl_cx = path_pdf[i][0] + t * (path_pdf[i+1][0] - path_pdf[i][0])
                    lbl_cy = path_pdf[i][1] + t * (path_pdf[i+1][1] - path_pdf[i][1])
                    break
                accum += seg_d

        edge_fs   = max(5.0, _sc(float(st.get("fontSize", 9))))
        lbl_lines = label.split("\n")
        line_h    = edge_fs * 1.2
        total_lh  = len(lbl_lines) * line_h
        max_lw    = max(
            c.stringWidth(ln, "Helvetica", edge_fs) for ln in lbl_lines
        )

        # Draw label background pill
        pad  = LABEL_PAD
        bg_c = _color(st.get("labelBackgroundColor"), "#f5f5f5")
        if bg_c:
            c.setFillColor(bg_c)
            c.roundRect(
                lbl_cx - max_lw / 2 - pad,
                lbl_cy - total_lh - pad + edge_fs * 0.3,
                max_lw + 2 * pad,
                total_lh + 2 * pad,
                radius=2,
                fill=1,
                stroke=0,
            )

        # Draw label text (above the line so the line does not cut through)
        c.setFillColor(HexColor("#333333"))
        base_y = lbl_cy + (total_lh / 2) - edge_fs * 0.85
        for ln in lbl_lines:
            c.setFont("Helvetica", edge_fs)
            c.drawCentredString(lbl_cx, base_y, ln.strip())
            base_y -= line_h

    c.save()
    print(f"Saved → {PDF_OUT}  ({page_w:.0f} × {page_h:.0f} pt  /  "
          f"{page_w/72:.1f}\" × {page_h/72:.1f}\")")


if __name__ == "__main__":
    main()
