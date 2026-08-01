"""Shared look-and-feel for every generated SVG.

Everything visual lives here: the palette, the terminal window chrome, the font
stack and the escaping helpers. The four generator scripts import from this
module and never hand-roll their own colours or frame — that is the whole point.
Four images that are supposed to read as one terminal will drift apart the first
time one of them is edited in isolation.

Two constraints shape the choices below:

1. The SVGs are loaded through <img> in a README, so they cannot reach the
   network. No webfonts, no external stylesheets. Only fonts already installed
   on the reader's machine are available, hence the generic monospace stack.

2. A README renders on the *visitor's* theme, light or dark. Every document
   therefore paints its own opaque background instead of relying on the page.
"""

# --- palette -----------------------------------------------------------------
# GitHub's own dark-theme values, so the cards sit naturally on a dark profile
# and remain legible on a light one.
BG      = "#0d1117"   # window body
CHROME  = "#161b22"   # title bar
BORDER  = "#30363d"
TEXT    = "#c9d1d9"   # body copy
MUTED   = "#8b949e"   # labels, secondary detail
KEY     = "#58a6ff"   # neofetch keys
PROMPT  = "#39d353"   # shell prompt / accents
ASCII   = "#adbac7"   # portrait glyphs — one colour, deliberately

# Traffic lights.
DOTS = ("#ff5f56", "#ffbd2e", "#27c93f")

# Contribution ramp, empty → busiest. Level 5 is a brighter top end than
# GitHub's own, so the densest days still read after the SVG is downscaled.
HEAT = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0")

# --- type --------------------------------------------------------------------
# Ordered by likelihood: Apple, Windows, then the common Linux families.
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono','DejaVu Sans Mono',monospace")

TITLE_BAR = 34   # height of the chrome strip
PAD       = 18   # inner padding of the content area


def esc(s):
    """Escape text for XML content and attribute values.

    Applied to every dynamic string without exception. Content here comes from
    a local JSON file rather than the open web, but the cost of escaping is
    nil and the cost of forgetting once is a silently corrupt document — an
    unescaped & alone is enough to make the whole SVG fail to parse, and a
    broken SVG in a README renders as nothing at all.
    """
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def window(w, h, title):
    """Terminal window chrome: rounded body, title bar, traffic lights.

    Returns the SVG fragment. Content should be placed inside the rectangle
    described by content_box().
    """
    dots = "".join(
        f'<circle cx="{18 + i * 18}" cy="{TITLE_BAR / 2}" r="5.5" fill="{c}"/>'
        for i, c in enumerate(DOTS)
    )
    return f"""  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="9"
        fill="{BG}" stroke="{BORDER}"/>
  <path d="M0.5 9.5a9 9 0 0 1 9-9h{w - 19}a9 9 0 0 1 9 9v{TITLE_BAR - 9}H0.5z"
        fill="{CHROME}"/>
  <line x1="0.5" y1="{TITLE_BAR}" x2="{w - 0.5}" y2="{TITLE_BAR}" stroke="{BORDER}"/>
  {dots}
  <text x="{w / 2}" y="{TITLE_BAR / 2 + 4}" text-anchor="middle"
        font-family="{MONO}" font-size="11.5" fill="{MUTED}">{esc(title)}</text>"""


def content_box(w, h):
    """Origin and size of the usable area inside the chrome."""
    return PAD, TITLE_BAR + PAD, w - 2 * PAD, h - TITLE_BAR - 2 * PAD


def document(w, h, body, label, css=""):
    """Wrap a fragment in a complete, standalone SVG document.

    `label` becomes the <title>, which screen readers announce and which
    GitHub surfaces on hover.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"
     viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
  <title>{esc(label)}</title>
  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
{css}
  </style>
{body}
</svg>
"""


# Reveal animations.
#
# Each is written to run exactly once and hold its final state: iteration-count
# 1 plus fill-mode forwards. A looping README animation is a distraction that
# never stops moving in the reader's peripheral vision.
#
# `clip-path: inset()` drives the portrait wipe rather than an animated
# <clipPath>, which would need one <clipPath> definition per row — 53 extra
# nodes to express one idea. Per-row timing comes from an inline
# `animation-delay`, so the keyframes are declared once and shared.
REVEAL_CSS = f"""    @keyframes wipe {{
      from {{ clip-path: inset(0 100% 0 0); }}
      to   {{ clip-path: inset(0 0 0 0); }}
    }}
    @keyframes fade {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pop {{
      from {{ opacity: 0; transform: translateY(-3px) scale(0.72); }}
      to   {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    .wipe {{ animation: wipe .22s steps(24) both 1; }}
    .fade {{ animation: fade .34s ease-out both 1; }}
    /* transform-box: fill-box is load-bearing. Without it a percentage
       transform-origin on an SVG shape resolves against the SVG root's origin,
       so `scale` throws the cell across the canvas instead of growing it in
       place. */
    .pop  {{ animation: pop .3s ease-out both 1;
             transform-box: fill-box; transform-origin: center; }}

    /* Readers who ask for reduced motion get the finished frame immediately. */
    @media (prefers-reduced-motion: reduce) {{
      .wipe, .fade, .pop {{ animation-duration: 1ms !important;
                            animation-delay: 0ms !important; }}
    }}"""
