"""sjfig: SJ (SPMDL) house style for scientific figures in matplotlib.

Design principle: draw every figure at its FINAL printed size, so that the
point sizes in the code are the point sizes the reader sees.

Usage
-----
    import sjfig
    fig, axes = sjfig.figure("paper", width="double", aspect=0.38, ncols=3)
    ... plot ...
    sjfig.label_panels(fig, axes)          # a, b, c (bold, lowercase)
    sjfig.audit(fig)                       # prints size / font / overlap report
    sjfig.save(fig, "fig2_jv", "paper")    # PDF (vector) + PNG preview
"""
from __future__ import annotations

from pathlib import Path
import string
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from cycler import cycler

MM = 1 / 25.4  # inches per mm

# ---------------------------------------------------------------- widths (mm)
# Verified against publisher pages (Nov 2026). For any other journal, read its
# author guide, or for LaTeX templates print \the\columnwidth and convert.
WIDTHS_MM = {
    "nature":   {"single": 89, "onehalf": 120, "double": 183, "maxheight": 247},
    "elsevier": {"single": 90, "onehalf": 140, "double": 190},
    "acs":      {"single": 84.6, "double": 177.8},           # 240 pt / 504 pt
    "patent":   {"single": 170, "double": 170, "maxheight": 262},  # A4 sight 17.0 x 26.2 cm
    "blog":     {"single": 203, "double": 203},              # 8 in; 1600 px @ 200 dpi
    "slide":    {"single": 160, "double": 320},              # half / full 16:9 slide
}

# ---------------------------------------------------------------- font sizes (pt)
# "As large as legibility and balance allow", capped by each venue's rule.
SIZES = {
    #            text  tick  legend panel  line  axes
    "nature":   (7.0,  7.0,  6.5,   8.0,  1.0,  0.6),   # Nature caps text at 7 pt, labels 8 pt bold
    "paper":    (8.5,  8.0,  7.5,  10.0,  1.2,  0.7),   # Elsevier/ACS/APS/Wiley: generous default
    "note":     (9.0,  8.5,  8.0,  11.0,  1.3,  0.8),   # research notebook, lab meeting
    "patent":   (14.0, 14.0, 14.0, 16.0,  1.0,  1.0),   # digit height 0.69 em; >= 0.32 cm -> >= 13.2 pt
    "blog":     (15.0, 13.5, 13.0, 18.0,  2.2,  1.2),
    "slide":    (18.0, 16.0, 15.0, 22.0,  2.5,  1.4),
}

# ---------------------------------------------------------------- color
# Colour-vision-deficiency safe (Okabe-Ito based) with a deep blue anchor.
PALETTE = {
    "key":       "#0F4D92",  # proposed method / main result
    "contrast":  "#D55E00",  # main comparison (vermillion, not red-vs-green)
    "green":     "#009E73",
    "orange":    "#E69F00",
    "sky":       "#56B4E9",
    "purple":    "#CC79A7",
    "baseline":  "#7F7F7F",  # reference / baseline / guide lines
    "light":     "#D9D9D9",  # background categories
    "ink":       "#1A1A1A",
}
CYCLE = [PALETTE[k] for k in ("key", "contrast", "green", "orange", "sky", "purple", "baseline")]
SEQUENTIAL = "viridis"   # or "cividis" for strict CVD safety; never "jet"
DIVERGING = "RdBu_r"     # centre the colour norm on the physical zero

PATENT_LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1, 1, 1))]
PATENT_MARKERS = ["o", "s", "^", "D", "v"]
PATENT_HATCHES = ["", "///", "\\\\\\", "xxx", "...", "---"]

# ---------------------------------------------------------------- fonts
_FONT_CHAIN = [
    "Arial Narrow",            # SJ's choice
    "Liberation Sans Narrow",  # metric-compatible stand-in (same widths)
    "Noto Sans CJK KR", "Malgun Gothic", "Apple SD Gothic Neo", "NanumGothic",  # Hangul fallback
    "DejaVu Sans",
]


def available_fonts() -> list[str]:
    names = {f.name for f in fm.fontManager.ttflist}
    return [f for f in _FONT_CHAIN if f in names]


def _primary_font() -> str:
    chain = available_fonts()
    if not chain or chain[0] not in ("Arial Narrow", "Liberation Sans Narrow"):
        warnings.warn("Arial Narrow / Liberation Sans Narrow not found: install one "
                      "(see SKILL.md, 'Font setup') before producing final figures.")
    return chain[0] if chain else "DejaVu Sans"


# ---------------------------------------------------------------- style
def apply_style(target: str = "paper") -> dict:
    text, tick, legend, panel, lw, axw = SIZES[target]
    main = _primary_font()
    mono = target == "patent"
    rc = {
        "font.family": available_fonts() or ["DejaVu Sans"],
        "font.size": text,
        "axes.labelsize": text,
        "axes.titlesize": panel,
        "xtick.labelsize": tick,
        "ytick.labelsize": tick,
        "legend.fontsize": legend,
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "legend.borderaxespad": 0.3,
        "axes.linewidth": axw,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": True,
        "axes.prop_cycle": (cycler(color=["black"] * 5) + cycler(linestyle=PATENT_LINESTYLES))
                           if mono else cycler(color=CYCLE),
        "axes.edgecolor": "black" if mono else PALETTE["ink"],
        "axes.labelcolor": "black" if mono else PALETTE["ink"],
        "text.color": "black" if mono else PALETTE["ink"],
        "xtick.color": "black" if mono else PALETTE["ink"],
        "ytick.color": "black" if mono else PALETTE["ink"],
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.width": axw, "ytick.major.width": axw,
        "xtick.minor.width": axw * 0.7, "ytick.minor.width": axw * 0.7,
        "xtick.major.size": 3.0 if target in ("nature", "paper", "note") else 5.0,
        "ytick.major.size": 3.0 if target in ("nature", "paper", "note") else 5.0,
        "xtick.minor.size": 1.6, "ytick.minor.size": 1.6,
        "lines.linewidth": lw,
        "lines.markersize": 3.5 if target in ("nature", "paper", "note") else 6,
        "errorbar.capsize": 2,
        "image.cmap": SEQUENTIAL,
        "mathtext.fontset": "custom",
        "mathtext.rm": main, "mathtext.it": f"{main}:italic", "mathtext.bf": f"{main}:bold",
        "mathtext.sf": main, "mathtext.cal": main, "mathtext.tt": "DejaVu Sans Mono",
        "mathtext.default": "regular",
        "pdf.fonttype": 42, "ps.fonttype": 42,  # embed TrueType: editable in Illustrator
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "figure.dpi": 150,
    }
    mpl.rcParams.update(rc)
    return rc


def figure(target="paper", width="single", aspect=0.75, nrows=1, ncols=1,
           journal=None, height_mm=None, **subplot_kw):
    """Create a figure at final print size.

    width   : "single" | "onehalf" | "double" | number in mm
    aspect  : height / width (ignored if height_mm given)
    journal : key of WIDTHS_MM; defaults to "nature" for target "nature",
              "elsevier" for other paper targets, otherwise the target itself.
    """
    apply_style(target)
    if journal is None:
        journal = {"nature": "nature", "paper": "elsevier", "note": "elsevier"}.get(target, target)
    w_mm = width if isinstance(width, (int, float)) else WIDTHS_MM[journal][width]
    h_mm = height_mm if height_mm else w_mm * aspect
    maxh = WIDTHS_MM[journal].get("maxheight")
    if maxh and h_mm > maxh:
        warnings.warn(f"height {h_mm:.0f} mm exceeds {journal} max {maxh} mm")
    fig, axes = plt.subplots(nrows, ncols, figsize=(w_mm * MM, h_mm * MM),
                             layout="constrained", squeeze=False, **subplot_kw)
    fig.get_layout_engine().set(w_pad=2 * MM, h_pad=2 * MM, wspace=0.04, hspace=0.04)
    fig._sj_target = target
    axes = axes.ravel()
    # Reserve a title-height strip above each axes for the panel label
    # (SJ uses panel labels only, never panel titles).
    for ax in axes:
        ax.set_title(" ", fontsize=SIZES[target][3], pad=1)
    return fig, (axes if len(axes) > 1 else axes[0])


def label_panels(fig, axes, labels=None, upper=False, start=0):
    """Bold lowercase a, b, c at the top-left of each panel's full extent
    (including tick and axis labels). Call after all plotting, before save."""
    axes = list(axes) if hasattr(axes, "__iter__") else [axes]
    target = getattr(fig, "_sj_target", "paper")
    size = SIZES[target][3]
    if labels is None:
        letters = string.ascii_uppercase if upper else string.ascii_lowercase
        labels = letters[start:start + len(axes)]
    fig.canvas.draw()                      # let constrained layout settle
    fig.set_layout_engine("none")          # freeze positions
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    for ax, lab in zip(axes, labels):
        bb = ax.get_tightbbox(r)
        x0, _ = inv.transform((bb.x0, bb.y1))
        _, y_top = inv.transform((0, ax.get_window_extent(r).y1))
        fig.text(max(x0, 0.002), y_top, lab, fontsize=size, fontweight="bold",
                 ha="left", va="bottom")
    return fig


def patent_label(fig, number, korean=False, suffix=""):
    """Patent drawings: 'FIG. 1' (US) or '도 1' (KR) centred under the drawing,
    larger than reference numerals. One drawing per figure; no a/b/c labels."""
    text = f"도 {number}{suffix}" if korean else f"FIG. {number}{suffix}"
    fig.canvas.draw()
    fig.set_layout_engine("none")
    fig.text(0.5, 0.005, text, ha="center", va="bottom",
             fontsize=SIZES["patent"][3] + 2, fontweight="bold")


def ref_numeral(ax, num, xy, xytext, **kw):
    """Patent reference numeral with a thin leader line (data coordinates)."""
    ax.annotate(str(num), xy=xy, xytext=xytext, ha="center", va="center",
                fontsize=SIZES["patent"][0],
                arrowprops=dict(arrowstyle="-", lw=0.8, color="black",
                                shrinkA=2, shrinkB=0, connectionstyle="arc3,rad=0.15"),
                **kw)


# ---------------------------------------------------------------- QA
def audit(fig, min_pt=None, verbose=True) -> dict:
    """Report final size, smallest font, thinnest line, text overlap and
    text running off the canvas. Returns the report as a dict."""
    target = getattr(fig, "_sj_target", "paper")
    if min_pt is None:
        min_pt = {"nature": 5.0, "patent": 13.2}.get(target, 6.0)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.get_size_inches()
    fb = fig.bbox
    # Tick labels exist for ticks outside the view limits and on hidden axes;
    # keep only the ones that are actually drawn.
    all_tick_texts, drawn_tick_texts = set(), set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                all_tick_texts.update({id(tk.label1), id(tk.label2)})
            if ax.axison and axis.get_visible():
                for tk in axis._update_ticks():
                    for lab in (tk.label1, tk.label2):
                        if lab.get_visible():
                            drawn_tick_texts.add(id(lab))
    texts = [t for t in fig.findobj(mpl.text.Text)
             if t.get_visible() and t.get_text().strip()
             and (id(t) not in all_tick_texts or id(t) in drawn_tick_texts)]
    sizes = [t.get_fontsize() for t in texts]
    small = sorted({round(s, 1) for s in sizes if s < min_pt})
    bbs = [(t, t.get_window_extent(r)) for t in texts]
    off = [t.get_text() for t, b in bbs
           if b.x0 < fb.x0 - 1 or b.x1 > fb.x1 + 1 or b.y0 < fb.y0 - 1 or b.y1 > fb.y1 + 1]
    overlaps = []
    for i in range(len(bbs)):
        for j in range(i + 1, len(bbs)):
            a, b = bbs[i][1], bbs[j][1]
            if a.overlaps(b) and a.width * a.height > 0 and b.width * b.height > 0:
                inter = (min(a.x1, b.x1) - max(a.x0, b.x0)) * (min(a.y1, b.y1) - max(a.y0, b.y0))
                if inter > 0.15 * min(a.width * a.height, b.width * b.height):
                    overlaps.append((bbs[i][0].get_text(), bbs[j][0].get_text()))
    lws = [l.get_linewidth() for l in fig.findobj(mpl.lines.Line2D) if l.get_visible()]
    rep = {
        "size_mm": (round(W / MM, 1), round(H / MM, 1)),
        "font_pt_range": (min(sizes), max(sizes)) if sizes else None,
        "below_min_font": small,
        "thinnest_line_pt": min(lws) if lws else None,
        "text_off_canvas": off,
        "text_overlaps": overlaps,
        "fonts_used": sorted({fm.FontProperties(family=t.get_fontfamily()).get_family()[0]
                              for t in texts}),
    }
    if verbose:
        print(f"[audit:{target}] size {rep['size_mm'][0]} x {rep['size_mm'][1]} mm | "
              f"font {rep['font_pt_range']} pt | thinnest line {rep['thinnest_line_pt']} pt")
        if small:
            print(f"  ! fonts below {min_pt} pt: {small}")
        if rep["thinnest_line_pt"] is not None and rep["thinnest_line_pt"] < 0.25:
            print("  ! line thinner than 0.25 pt may not print")
        if off:
            print(f"  ! text off canvas: {off}")
        if overlaps:
            print(f"  ! overlapping text: {overlaps[:8]}")
        if not (small or off or overlaps):
            print("  OK: no small fonts, no clipping, no overlaps")
    return rep


# ---------------------------------------------------------------- export
_DEFAULT_FORMATS = {
    "nature": ("pdf", "png"), "paper": ("pdf", "png"), "note": ("pdf", "png"),
    "patent": ("pdf", "png"), "blog": ("png", "svg"), "slide": ("png", "svg"),
}
_PNG_DPI = {"nature": 600, "paper": 600, "note": 300, "patent": 600, "blog": 200, "slide": 200}


def save(fig, stem, target=None, outdir="figures", formats=None, source=None):
    """Save at exact size (no bbox_inches='tight', which would change the width).
    `source` (script or data file) is written into the PDF metadata."""
    target = target or getattr(fig, "_sj_target", "paper")
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in formats or _DEFAULT_FORMATS[target]:
        p = out / f"{stem}.{ext}"
        kw = {}
        if ext == "pdf":
            kw["metadata"] = {"Author": "Seok Joon Kwon (SPMDL, SKKU)",
                              "Subject": source or ""}
        if ext in ("png", "tif", "tiff", "jpg"):
            kw["dpi"] = _PNG_DPI[target]
        fig.savefig(p, **kw)
        paths.append(p)
    return paths
