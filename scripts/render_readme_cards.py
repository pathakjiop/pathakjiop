"""Draw every README card as an animated SVG from data/*.json.

  python scripts/render_readme_cards.py                  # animated adaptive cards
  STATIC=1 python scripts/render_readme_cards.py         # final frame only (for screenshots)
  python scripts/render_readme_cards.py --theme paper    # force classic paper & ink
  python scripts/render_readme_cards.py --theme dark     # force dark obsidian theme
  python scripts/render_readme_cards.py --theme adaptive # auto-switch on GitHub dark/light (default)

SVGs shown through <img> on GitHub cannot run JavaScript or fetch external stylesheets,
but self-contained <style> with CSS keyframes, @media (prefers-color-scheme), and SMIL run natively.
Fonts are embedded directly as base64 WOFF.
"""
from __future__ import annotations

import argparse, base64, datetime as dt, html, io, json, math, os, sys, time, urllib.request
from collections import OrderedDict
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cards"
OUT.mkdir(exist_ok=True)

# Parse command line flags
parser = argparse.ArgumentParser(description="Render animated GitHub profile README SVG cards.")
parser.add_argument("--static", action="store_true", help="Render static final frame only (no animations)")
parser.add_argument("--theme", choices=["adaptive", "paper", "dark"], default=None,
                    help="Theme mode: adaptive (default), paper, or dark")
args, _ = parser.parse_known_args()

STATIC = args.static or (os.environ.get("STATIC") == "1")

# Load configuration and cached GitHub data
cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
data_contrib = json.loads((ROOT / "data/contributions.json").read_text(encoding="utf-8")) if (ROOT / "data/contributions.json").exists() else {"days": []}
days = data_contrib.get("days", [])
prof = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8")) if (ROOT / "data/profile.json").exists() else {}

THEME = args.theme or cfg.get("theme", "adaptive")

# ---- Colour Palettes ---------------------------------------------------------------------
# Primary accents
BLUE, RED, YELLOW = "#2563eb", "#e5484d", "#f5b301"
SERIF, SANS, MONO = "Instrument Serif", "Geist", "Geist Mono"

# Heatmap ramp - Light (Paper warm blues) and Dark (Vibrant electric blues)
BLUES_LIGHT = ["#e6dfd0", "#c7d7fb", "#8aaaf5", "#4c7cee", "#1d4ed8"]
BLUES_DARK  = ["#1c222b", "#1e3a8a", "#2563eb", "#60a5fa", "#93c5fd"]

# Expanded Language Palette (25+ modern languages)
LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Go": "#00ADD8", "Rust": "#dea584",
    "C++": "#f34b7d", "C": "#555555", "C#": "#178600", "Swift": "#F05138",
    "PHP": "#4F5D95", "Ruby": "#701516", "Dart": "#00B4AB", "HTML": "#e34c26",
    "CSS": "#563d7c", "SCSS": "#c6538c", "Shell": "#89e051", "Bash": "#4eaa25",
    "Vue": "#41b883", "Svelte": "#ff3e00", "Solidity": "#AA6746", "Lua": "#000080",
    "R": "#198CE7", "Scala": "#c22d40", "Elixir": "#6e4a7e", "Haskell": "#5e5086",
    "Zig": "#ec915c", "Nix": "#7e7eff", "Markdown": "#083fa1", "Docker": "#384d54"
}

# ---- Vector Icons (Clean 16x16 / 14x14 SVG Paths) ---------------------------------------
ICONS = {
    "star": '<path d="M8 1.5l1.8 3.7 4.1.6-3 2.9.7 4.1L8 10.9 4.4 12.8l.7-4.1-3-2.9 4.1-.6L8 1.5z" fill="currentColor"/>',
    "fork": '<path d="M4 1a2 2 0 00-2 2c0 1.3 1.1 2.4 2.4 2.5a3.5 3.5 0 001.6 2.3v.4a3.5 3.5 0 001.6-2.3C6.4 5.4 5.3 4.3 4 3V3a2 2 0 00-2-2zm8 0a2 2 0 100 4c1.3 0 2.4-1.1 2.4-2.5A3.5 3.5 0 0012.8 1zm0 2a1 1 0 110-2 1 1 0 010 2zM4 3a1 1 0 110-2 1 1 0 010 2zm4 7a2 2 0 100 4 2 2 0 000-4zm0 1a1 1 0 110 2 1 1 0 010-2z" fill="currentColor"/>',
    "portfolio": '<circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.3"/><ellipse cx="8" cy="8" rx="3" ry="6.5" fill="none" stroke="currentColor" stroke-width="1.3"/><line x1="1.5" y1="8" x2="14.5" y2="8" stroke="currentColor" stroke-width="1.3"/>',
    "github": '<path fill-rule="evenodd" clip-rule="evenodd" d="M8 1.5C4.4 1.5 1.5 4.4 1.5 8c0 2.9 1.9 5.3 4.5 6.2.3.1.4-.1.4-.3v-1.2c-1.8.4-2.2-.8-2.2-.8-.3-.8-.7-1-.7-1-.6-.4 0-.4 0-.4.7 0 1 .7 1 .7.6 1 1.5.7 1.9.5.1-.4.2-.7.4-.9-1.4-.2-3-.7-3-3.1 0-.7.2-1.3.7-1.7 0-.2-.3-.8.1-1.7 0 0 .5-.2 1.8.7.5-.1 1.1-.2 1.6-.2s1.1.1 1.6.2c1.3-.9 1.8-.7 1.8-.7.4.9.1 1.5.1 1.7.4.5.7 1.1.7 1.7 0 2.4-1.5 3-3 3.1.3.2.5.7.5 1.4v2.1c0 .2.2.4.5.3 2.6-.9 4.5-3.3 4.5-6.2 0-3.6-2.9-6.5-6.5-6.5z" fill="currentColor"/>',
    "linkedin": '<path d="M2.5 3.5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zM1 5h3v9H1V5zm5 0h2.8v1.3h.1c.4-.7 1.4-1.5 2.8-1.5 3 0 3.6 2 3.6 4.5V14h-3v-4.2c0-1-.1-2.3-1.4-2.3s-1.6 1.1-1.6 2.2V14H6V5z" fill="currentColor"/>',
    "x": '<path d="M12.6 1.5h2.2l-4.8 5.5 5.7 7.5H11.2l-3.5-4.6-4 4.6H1.5l5.1-5.9L1.1 1.5h4.6l3.2 4.2 3.7-4.2zm-.8 11.7h1.2L4.7 2.7H3.4l8.4 10.5z" fill="currentColor"/>',
    "instagram": '<rect x="2" y="2" width="12" height="12" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2.8" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="11.4" cy="4.6" r=".8" fill="currentColor"/>',
    "hackerrank": '<path d="M1 1.5h4.2v4.2H1V1.5zm9.8 0H15v4.2h-4.2V1.5zM1 10.3h4.2v4.2H1v-4.2zm9.8 0H15v4.2h-4.2v-4.2zM5.2 6.5h5.6v3H5.2v-3z" fill="currentColor"/>',
    "leetcode": '<path d="M9.8 2.6l-5.6 5.6a2.5 2.5 0 000 3.5l3.2 3.2a2.5 2.5 0 003.5 0l2-2-1.2-1.2-2 2a.8.8 0 01-1.1 0L5.4 10.5a.8.8 0 010-1.1l5.6-5.6-1.2-1.2zm-2.4 5.9h5.6v1.7H7.4V8.5z" fill="currentColor"/>',
    "youtube": '<path d="M14.6 4.6c-.2-.6-.7-1.1-1.3-1.3C12.1 3 8 3 8 3s-4.1 0-5.3.3c-.6.2-1.1.7-1.3 1.3C1.1 5.8 1.1 8 1.1 8s0 2.2.3 3.4c.2.6.7 1.1 1.3 1.3 1.2.3 5.3.3 5.3.3s4.1 0 5.3-.3c.6-.2 1.1-.7 1.3-1.3.3-1.2.3-3.4.3-3.4s0-2.2-.3-3.4zM6.5 10.1V5.9L10.3 8l-3.8 2.1z" fill="currentColor"/>',
    "discord": '<path d="M13.2 3.5A11.7 11.7 0 0010.3 2.6c-.1.2-.3.6-.4.9a11.1 11.1 0 00-3.8 0 6 6 0 00-.4-.9 11.8 11.8 0 00-2.9.9C1 6.2.5 10.4.7 12.8a11.8 11.8 0 003.6 1.8c.3-.4.6-.9.8-1.4-.6-.2-1.1-.5-1.6-.9.1-.1.3-.2.4-.3a8.3 8.3 0 018.2 0c.1.1.3.2.4.3-.5.4-1 .7-1.6.9.2.5.5 1 .8 1.4a11.8 11.8 0 003.6-1.8c.3-2.8-.5-7-2.1-9.3zM5.5 10.5c-.8 0-1.4-.7-1.4-1.6s.6-1.6 1.4-1.6c.8 0 1.4.7 1.4 1.6 0 .9-.6 1.6-1.4 1.6zm5 0c-.8 0-1.4-.7-1.4-1.6s.6-1.6 1.4-1.6c.8 0 1.4.7 1.4 1.6 0 .9-.6 1.6-1.4 1.6z" fill="currentColor"/>',
    "email": '<path d="M1.5 3.5A1.5 1.5 0 013 2h10a1.5 1.5 0 011.5 1.5v9a1.5 1.5 0 01-1.5 1.5H3A1.5 1.5 0 011.5 12.5v-9zm1.7.3l4.8 3.5 4.8-3.5H3.2zm9.6 1.4l-4.5 3.3a.5.5 0 01-.6 0L3.2 5.2v7.1a.3.3 0 00.3.3h9a.3.3 0 00.3-.3V5.2z" fill="currentColor"/>',
    "globe": '<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.3"/><ellipse cx="8" cy="8" rx="2.5" ry="6" fill="none" stroke="currentColor" stroke-width="1.3"/><line x1="2" y1="8" x2="14" y2="8" stroke="currentColor" stroke-width="1.3"/>'
}

# ---- Fonts Engine ------------------------------------------------------------------------
FONTFILES = {SERIF: "serif.woff", SANS: "sans.woff", MONO: "mono.woff"}
_fonts: dict[str, TTFont] = {}
for k, v in FONTFILES.items():
    p = ROOT / "assets/fonts" / v
    if p.is_file():
        try: _fonts[k] = TTFont(p)
        except Exception: pass

_width_cache: dict[tuple[str, int, str], float] = {}

def tw(text: str, size: float, font: str = SANS) -> float:
    """Measure exact rendered pixel width with zero-crash fallback for special chars/emojis."""
    cache_key = (text, int(size * 10), font)
    if cache_key in _width_cache:
        return _width_cache[cache_key]
    
    if font in _fonts:
        try:
            f = _fonts[font]
            cmap = f.getBestCmap()
            hm = f["hmtx"]
            upm = f["head"].unitsPerEm
            space_gid = cmap.get(32, 0)
            total_w = 0.0
            for ch in text:
                gid = cmap.get(ord(ch))
                if gid is None or gid not in hm:
                    gid = space_gid
                total_w += hm[gid][0] if gid in hm else upm * 0.5
            w = total_w * size / upm
            _width_cache[cache_key] = w
            return w
        except Exception:
            pass
    # Resilient fallback: monospace vs proportional estimation
    ratio = 0.60 if font == MONO else 0.54
    w = sum(ratio if ord(c) < 128 else 1.0 for c in text) * size
    _width_cache[cache_key] = w
    return w

def font_css() -> str:
    out = ""
    for fam, fn in FONTFILES.items():
        p = ROOT / "assets/fonts" / fn
        if p.is_file():
            b64 = base64.b64encode(p.read_bytes()).decode()
            out += f"@font-face{{font-family:'{fam}';src:url(data:font/woff;base64,{b64}) format('woff');font-display:swap;}}"
    return out

FONT_CSS = font_css()
esc = html.escape

# ---- Theme CSS Variables -----------------------------------------------------------------
def theme_css() -> str:
    """Generate adaptive or static color variables for Paper and Dark modes."""
    paper_vars = """
      --paper: #f4efe6;
      --card: #fbf8f2;
      --ink: #16130f;
      --mute: #7a7367;
      --line: rgba(22, 19, 15, 0.12);
      --border: rgba(22, 19, 15, 0.14);
      --track: #e9e3d7;
      --hl0: #e6dfd0; --hl1: #c7d7fb; --hl2: #8aaaf5; --hl3: #4c7cee; --hl4: #1d4ed8;
      --bar-idle: #d9d1c0;
      --sh-ink: #16130f;
    """
    dark_vars = """
      --paper: #0d1117;
      --card: #161b22;
      --ink: #e6edf3;
      --mute: #8b949e;
      --line: rgba(230, 237, 243, 0.12);
      --border: rgba(230, 237, 243, 0.15);
      --track: #21262d;
      --hl0: #161b22; --hl1: #0e4429; --hl2: #006d32; --hl3: #26a641; --hl4: #39d353;
      --bar-idle: #262c36;
      --sh-ink: #e6edf3;
    """
    if THEME == "paper":
        return f":root {{{paper_vars}}}"
    elif THEME == "dark":
        return f":root {{{dark_vars}}}"
    else:  # adaptive (switches automatically on GitHub)
        return f":root {{{paper_vars}}} @media (prefers-color-scheme: dark) {{ :root {{{dark_vars}}} }}"

# ---- Shared Keyframes & Reduced Motion --------------------------------------------------
BASE_CSS = f"""
text{{font-family:'{SANS}',system-ui,-apple-system,sans-serif;fill:var(--ink)}}
.serif{{font-family:'{SERIF}',Georgia,serif}}
.mono{{font-family:'{MONO}',ui-monospace,SFMono-Regular,monospace}}
.rise{{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}}
.fade{{animation:fade .8s ease-out both}}
.pop{{animation:pop .5s cubic-bezier(.3,1.6,.5,1) both;transform-box:fill-box;transform-origin:center}}
.grow{{animation:grow .8s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:bottom}}
.pulse{{animation:pulse 2.2s ease-out infinite;transform-box:fill-box;transform-origin:center}}
.nudge{{animation:nudge 2.4s ease-in-out infinite}}
.st{{animation:fade .01s linear both}}
.fr{{display:inline}}
@keyframes rise{{from{{opacity:0;transform:translateY(24px)}}to{{opacity:1;transform:none}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes pop{{0%{{opacity:0;transform:scale(0)}}100%{{opacity:1;transform:scale(1)}}}}
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes pulse{{0%{{opacity:.7;transform:scale(1)}}100%{{opacity:0;transform:scale(3.2)}}}}
@keyframes nudge{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(3px,-3px)}}}}
@keyframes swing{{0%{{opacity:0;transform:translateY(50px) rotate(-6deg)}}60%{{opacity:1;transform:translateY(-5px) rotate(1.2deg)}}80%{{transform:translateY(2px) rotate(-.3deg)}}100%{{transform:none}}}}
@keyframes sheen{{0%,55%{{transform:translateX(-160px) skewX(-18deg)}}100%{{transform:translateX(440px) skewX(-18deg)}}}}
"""
REDUCED = ".rise,.fade,.pop,.grow,.pulse,.nudge,.st,.tile,.sheen{animation:none!important}.fr{display:none}"

def css(extra: str = "") -> str:
    r = REDUCED if STATIC else f"@media (prefers-reduced-motion:reduce){{{REDUCED}}}"
    return f"<style>{FONT_CSS}{theme_css()}{BASE_CSS}{extra}{r}</style>"

def svg(w: int, h: int, body: str, extra_css: str = "", title: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{esc(title)}">{css(extra_css)}{body}</svg>')

def delay(s: float) -> str:
    return f"animation-delay:{s:.2f}s"

def frame(w: int, h: int, fill: str = "var(--paper)", r: int = 22) -> str:
    return (f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="{fill}" '
            f'stroke="var(--border)" stroke-width="1"/>')

def write(name: str, content: str) -> None:
    (OUT / name).write_text(content, encoding="utf-8")

# ---- Contribution Stats Derivations -----------------------------------------------------
total = sum(d.get("count", 0) for d in days)
active = sum(1 for d in days if d.get("count", 0) > 0)
busiest = max(days, key=lambda d: d.get("count", 0)) if days else {"count": 0, "date": dt.date.today().isoformat()}

def streaks():
    best = run = 0
    for d in days:
        run = run + 1 if d.get("count", 0) > 0 else 0
        if run > best: best = run
    cur, i = 0, len(days) - 1
    if i >= 0 and days[i].get("count", 0) == 0:
        i -= 1  # current day may be in progress
    while i >= 0 and days[i].get("count", 0) > 0:
        cur += 1; i -= 1
    return cur, best

cur_streak, best_streak = streaks()

# Group by month for the monthly activity chart
months = OrderedDict()
for d in days:
    k = d.get("date", "")[:7]
    if k:
        months.setdefault(k, 0)
        months[k] += d.get("count", 0)
months = list(months.items())[-12:]

def month_label(k: str) -> str:
    try:
        return dt.date(int(k[:4]), int(k[5:7]), 1).strftime("%b").upper()
    except Exception:
        return k[-2:]

def pretty_date(d_str: str) -> str:
    try:
        x = dt.date.fromisoformat(d_str)
        return f"{x.strftime('%b')} {x.day}"
    except Exception:
        return d_str

# ---- 1. Hero Card ------------------------------------------------------------------------
def sierpinski(n: int = 38) -> list[str]:
    """Mathematical fractal fallback art if no portrait photo is found."""
    rows = []
    for y in range(n):
        cells = "".join(("#" if (x & (y - x)) == 0 else " ") + " " for x in range(y + 1))
        rows.append((" " * (n - y - 1) + cells).rstrip())
    return rows

def ascii_portrait(cols: int = 78) -> list[str]:
    """Render a crisp, contrast-optimized ASCII portrait from photo or cached avatar."""
    from PIL import Image, ImageOps
    cache_file = ROOT / "assets/.avatar_cache.png"
    src = ROOT / cfg.get("portrait", "")
    img = None

    if src.is_file():
        try: img = Image.open(src)
        except Exception: pass
    elif cache_file.is_file():
        try: img = Image.open(cache_file)
        except Exception: pass

    if img is None:
        # Fast non-blocking avatar fetch with low timeout
        try:
            req = urllib.request.Request(
                f"https://github.com/{cfg['username']}.png?size=400",
                headers={"User-Agent": "readme-cards"}
            )
            data = urllib.request.urlopen(req, timeout=3).read()
            img = Image.open(io.BytesIO(data))
            try: cache_file.write_bytes(data)
            except Exception: pass
        except Exception:
            return sierpinski()

    # Crop square focused on face and enhance contrast for sharp terminal rendering
    img = img.convert("RGB")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, 0, (w - side) // 2 + side, side))
    rows = round(cols * 0.50)
    img = img.resize((cols, rows), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=2)

    # 10-step perceptual density ramp
    ramp = " .:-=+*#%@"
    px = img.load()
    lines = []
    for y in range(rows):
        lines.append("".join(ramp[int((255 - px[x, y]) / 256 * len(ramp))] for x in range(cols)).rstrip())
    return lines

def hero():
    W, H = 900, 360
    first, last = cfg.get("first_name", "Developer"), cfg.get("last_name", "")
    lines = ascii_portrait()
    has = bool(lines)
    b = frame(W, H, fill="var(--paper)")

    # Right side: ASCII Portrait
    if has:
        wide = max(len(l) for l in lines)
        fs = 5.0 if wide > 60 else 7.6
        lh = fs * 1.04
        cw = tw("M", fs, MONO)
        x0 = W - 44 - cw * wide
        y0 = (H - lh * len(lines)) / 2 + lh
        for i, ln in enumerate(lines):
            b += (f'<text class="mono fade" x="{x0:.1f}" y="{y0+i*lh:.1f}" font-size="{fs}" '
                  f'fill="var(--ink)" fill-opacity=".80" xml:space="preserve" '
                  f'style="{delay(.2+i*.018)}">{esc(ln)}</text>')

    # Left side: Typography & Identity
    nx = 48
    b += (f'<text class="mono fade" x="{nx}" y="56" font-size="12" letter-spacing="2" '
          f'fill="var(--mute)" style="{delay(.1)}">{esc(cfg.get("username", "DEV")).upper()} / GITHUB</text>')
    
    b += f'<text class="serif rise" x="{nx}" y="156" font-size="112" fill="var(--ink)" style="{delay(.25)}">{esc(first)}</text>'

    # Shimmer wave across last name
    name_len = tw(last, 112, SERIF)
    b += (f'<defs><linearGradient id="sh" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{name_len:.0f}" y2="0" '
          f'gradientTransform="translate(-{name_len*1.2:.0f} 0)">'
          f'<stop offset="0" stop-color="var(--ink)"/><stop offset=".40" stop-color="var(--ink)"/>'
          f'<stop offset=".50" stop-color="{BLUE}"/><stop offset=".60" stop-color="var(--ink)"/>'
          f'<stop offset="1" stop-color="var(--ink)"/>'
          f'<animateTransform attributeName="gradientTransform" type="translate" '
          f'values="-{name_len*1.2:.0f} 0;{name_len*2:.0f} 0;{name_len*2:.0f} 0" keyTimes="0;.4;1" dur="7s" begin="1.8s" repeatCount="indefinite"/>'
          f'</linearGradient></defs>')
    b += f'<text class="serif rise" x="{nx}" y="258" font-size="112" fill="url(#sh)" style="{delay(.45)}">{esc(last)}</text>'

    # Tagline
    tagline = cfg.get("tagline", "")
    if tagline:
        b += f'<text class="fade" x="{nx+2}" y="298" font-size="16.5" fill="var(--ink)" fill-opacity=".92" style="{delay(.9)}">{esc(tagline)}</text>'

    # Live pulse dot + Role description
    b += f'<circle class="pulse" cx="{nx+6}" cy="326" r="4" fill="{BLUE}" style="{delay(1.2)}"/><circle cx="{nx+6}" cy="326" r="4" fill="{BLUE}"/>'
    role = cfg.get("role", "Software Engineer")
    b += f'<text class="fade mono" x="{nx+20}" y="330" font-size="12.5" fill="var(--mute)" style="{delay(1.1)}">{esc(role)}</text>'

    write("hero.svg", svg(W, H, b, title=f"{first} {last}"))

# ---- 2. Contribution Heatmap -------------------------------------------------------------
def heatmap():
    W, H, cell, gap = 900, 196, 13, 3
    cols = (len(days) + 6) // 7
    x0 = (W - cols * (cell + gap) + gap) / 2
    y0 = 68

    b = frame(W, H, fill="var(--paper)")
    b += f'<text class="mono fade" x="28" y="36" font-size="12" letter-spacing="1.5" fill="var(--mute)">CONTRIBUTIONS · LAST 12 MONTHS</text>'
    b += f'<text class="serif fade" x="{W-28}" y="40" font-size="28" text-anchor="end" fill="{BLUE}" style="{delay(.4)}">{total:,}</text>'

    # Day-of-week labels on the left (Mon, Wed, Fri)
    day_labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    for lab, row in day_labels:
        b += (f'<text class="mono fade" x="{x0-10:.1f}" y="{y0+row*(cell+gap)+9.5:.1f}" font-size="9" '
              f'text-anchor="end" fill="var(--mute)" fill-opacity=".65">{lab}</text>')

    # Month header labels above calendar columns
    last_m = ""
    for i, d in enumerate(days):
        if i % 7 == 0:  # start of each week column
            m_str = d.get("date", "")[5:7]
            if m_str != last_m and i // 7 < cols - 2:
                last_m = m_str
                c = i // 7
                m_name = dt.date(2026, int(m_str), 1).strftime("%b")
                b += (f'<text class="mono fade" x="{x0+c*(cell+gap):.1f}" y="{y0-12}" font-size="10" '
                      f'fill="var(--mute)" fill-opacity=".80">{m_name}</text>')

    # Grid squares
    for i, d in enumerate(days):
        c, r = divmod(i, 7)
        lvl = min(max(d.get("level", 0), 0), 4)
        count = d.get("count", 0)
        date_str = d.get("date", "")
        # Uses CSS var(--hl0)..var(--hl4) for seamless dark/light adaptive colors
        b += (f'<rect class="pop" x="{x0+c*(cell+gap):.1f}" y="{y0+r*(cell+gap)}" width="{cell}" height="{cell}" rx="3" '
              f'fill="var(--hl{lvl})" style="{delay(.35+c*.018)}">'
              f'<title>{count} contributions on {date_str}</title></rect>')

    # Bottom legend: "Less [0][1][2][3][4] More"
    lx = W - 148
    ly = H - 18
    b += f'<text class="mono fade" x="{lx-12}" y="{ly+9}" font-size="9.5" text-anchor="end" fill="var(--mute)">Less</text>'
    for k in range(5):
        b += f'<rect x="{lx+k*14}" y="{ly}" width="10" height="10" rx="2" fill="var(--hl{k})"/>'
    b += f'<text class="mono fade" x="{lx+5*14+4}" y="{ly+9}" font-size="9.5" fill="var(--mute)">More</text>'

    write("heatmap.svg", svg(W, H, b, title="Contribution graph"))

# ---- 3. Monthly Activity Chart + Key Stats ----------------------------------------------
def activity():
    W, H = 900, 330
    b = frame(W, H, fill="var(--paper)")
    stats = [
        ("Contributions", f"{total:,}", "last 12 months"),
        ("Current streak", f"{cur_streak}", "days in a row"),
        ("Active days", f"{active}", f"of {len(days)}"),
        ("Busiest day", f"{busiest.get('count', 0)}", pretty_date(busiest.get("date", "")))
    ]

    for i, (lab, val, sub) in enumerate(stats):
        x = 36 + i * 212
        b += f'<text class="mono fade" x="{x}" y="42" font-size="11" letter-spacing="1.5" fill="var(--mute)" style="{delay(.2+i*.1)}">{lab.upper()}</text>'
        b += f'<text class="serif rise" x="{x}" y="92" font-size="52" fill="var(--ink)" style="{delay(.25+i*.1)}">{val}</text>'
        b += f'<text class="fade" x="{x}" y="112" font-size="12.5" fill="var(--mute)" style="{delay(.5+i*.1)}">{esc(sub)}</text>'
        if i < 3:
            b += f'<line x1="{x+180}" x2="{x+180}" y1="36" y2="114" stroke="var(--line)" stroke-dasharray="2 3"/>'

    b += f'<line x1="32" x2="{W-32}" y1="134" y2="134" stroke="var(--line)"/>'

    # 12-Month Bar Chart
    base, maxh, bw = 292, 120, 44
    gap = (W - 64 - 12 * bw) / 11
    mx = max((v for _, v in months), default=1) or 1
    best_idx = max(range(len(months)), key=lambda i: months[i][1]) if months else -1

    for i, (k, v) in enumerate(months):
        x = 32 + i * (bw + gap)
        h = max(4, (v / mx) * maxh)
        d = .7 + i * .07
        is_best = (i == best_idx)

        # Background track groove for modern depth
        b += f'<rect x="{x:.1f}" y="{base-maxh:.1f}" width="{bw}" height="{maxh:.1f}" rx="6" fill="var(--track)" fill-opacity=".35"/>'

        # Animated bar
        fill_col = BLUE if is_best else "var(--bar-idle)"
        b += (f'<rect class="grow" x="{x:.1f}" y="{base-h:.1f}" width="{bw}" height="{h:.1f}" rx="6" '
              f'fill="{fill_col}" style="{delay(d)}"><title>{v} contributions in {k}</title></rect>')
        
        # Month name label
        b += f'<text class="mono fade" x="{x+bw/2:.1f}" y="{base+20}" font-size="11" text-anchor="middle" fill="var(--mute)" style="{delay(d)}">{month_label(k)}</text>'

        # Number pop on peak month
        if is_best and v > 0:
            b += (f'<text class="serif pop" x="{x+bw/2:.1f}" y="{base-h-10:.1f}" font-size="26" '
                  f'text-anchor="middle" fill="{BLUE}" style="{delay(d+.5)}">{v}</text>')

    write("activity.svg", svg(W, H, b, title="Monthly contributions"))

# ---- 4. Three World Tiles ----------------------------------------------------------------
def lum(hexc: str) -> float:
    try:
        r, g, bl = (int(hexc[i:i+2], 16) for i in (1, 3, 5))
        return (0.299 * r + 0.587 * g + 0.114 * bl) / 255
    except Exception:
        return 0.0

def metric(name: str) -> int:
    total_stars = sum(r.get("stars", 0) for r in prof.get("repo_list", []))
    return {
        "repos": prof.get("repos", 0),
        "followers": prof.get("followers", 0),
        "following": prof.get("following", 0),
        "stars": total_stars,
        "contributions": total,
        "streak": best_streak,
        "active_days": active
    }.get(name, 0)

def tiles():
    W, H, N = 300, 214, 18
    for k, t in enumerate(cfg.get("tiles", [])):
        col = t.get("color", BLUE)
        fg = "#16130f" if lum(col) > .6 else "#ffffff"
        d = 2.6 + k * .22
        val = metric(t.get("metric", ""))
        cd = d + .55
        label = esc(t.get("label", "TILE"))
        caption = esc(t.get("caption", ""))

        b = (f'<defs><clipPath id="c{k}"><rect width="{W}" height="{H}" rx="22"/></clipPath></defs>'
             f'<g class="tile" style="transform-box:view-box;transform-origin:0 {H}px;animation:swing 1.1s cubic-bezier(.2,.8,.2,1) {d:.2f}s both">'
             f'<rect width="{W}" height="{H}" rx="22" fill="{col}"/>'
             # Shimmer light sheen sweep
             f'<g clip-path="url(#c{k})"><rect class="sheen" x="0" y="-20" width="70" height="{H+40}" fill="#fff" fill-opacity=".24" '
             f'style="transform:translateX(-200px);animation:sheen 6s ease-in-out {d+1.5:.2f}s infinite"/></g>'
             # Pulse target ring
             f'<circle class="pulse" cx="{W-34}" cy="34" r="6" fill="none" stroke="{fg}" stroke-width="1.5" style="{delay(d+1)}"/>'
             f'<circle cx="{W-34}" cy="34" r="3" fill="{fg}"/>'
             f'<text class="mono" x="26" y="40" font-size="12" letter-spacing="2" fill="{fg}">{label}</text>')

        # SMIL odometer count-up frames
        for i in range(N - 1):
            v = round(val * (i / (N - 1)) ** 2)
            b += (f'<text class="serif fr" x="24" y="152" font-size="104" fill="{fg}" visibility="hidden">{v:,}'
                  f'<set attributeName="visibility" to="visible" begin="{cd+i*.045:.3f}s" dur=".045s" fill="remove"/></text>')

        b += f'<text class="serif st" x="24" y="152" font-size="104" fill="{fg}" style="animation-delay:{cd+(N-1)*.045:.3f}s">{val:,}</text>'
        b += f'<text class="fade" x="26" y="184" font-size="14" fill="{fg}" fill-opacity=".88" style="{delay(d+.5)}">{caption}</text>'
        b += f'<g class="nudge" style="{delay(d)}"><text class="serif" x="{W-44}" y="{H-24}" font-size="30" fill="{fg}">↗</text></g></g>'

        write(f"tile{k+1}.svg", svg(W, H, b, title=f"{label}: {val:,} {caption}"))

# ---- 5. Repo Cards with Micro-Icons ------------------------------------------------------
def wrap(text: str, size: float, width: float, lines: int = 2) -> list[str]:
    words = text.split()
    out: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if tw(candidate, size) <= width:
            cur = candidate
        else:
            if cur: out.append(cur)
            cur = w
    if cur: out.append(cur)

    if len(out) > lines:
        out = out[:lines]
        while out and tw(out[-1] + "…", size) > width:
            if " " in out[-1]:
                out[-1] = out[-1].rsplit(" ", 1)[0]
            else:
                out[-1] = out[-1][:-1]
        if out: out[-1] += "…"
    return out

def repos():
    W, H = 440, 160
    live = {r["name"]: r for r in prof.get("repo_list", [])}
    
    for k, name in enumerate(cfg.get("featured_repos", [])):
        r = {**cfg.get("repo_fallback", {}).get(name, {}), **live.get(name, {})}
        d = 4.2 + k * .2
        b = f'<g class="rise" style="{delay(d)}">{frame(W, H, fill="var(--card)", r=20)}'
        b += f'<text class="mono" x="24" y="34" font-size="11" letter-spacing="1.5" fill="var(--mute)">FEATURED REPO</text>'

        # Name with smart sizing
        title_size = 28 if tw(name, 28, SERIF) < (W - 56) else 22
        b += f'<text class="serif" x="24" y="66" font-size="{title_size}" fill="var(--ink)">{esc(name)}</text>'

        # Description
        desc = r.get("description", "")
        for j, ln in enumerate(wrap(desc, 13, W - 48)):
            b += f'<text x="24" y="{92+j*18}" font-size="13" fill="var(--ink)" fill-opacity=".78">{esc(ln)}</text>'

        # Bottom row: Language indicator + Star and Fork counts with crisp vector icons
        lang = r.get("language", "")
        if lang:
            col = LANG_COLORS.get(lang, BLUE)
            b += (f'<circle cx="29" cy="{H-22}" r="5" fill="{col}"/>'
                  f'<text x="40" y="{H-18}" font-size="12" fill="var(--ink)">{esc(lang)}</text>')

        stars = r.get("stars", 0)
        forks = r.get("forks", 0)
        
        # Right aligned Star and Fork icons
        bx = W - 24
        fork_str = f"{forks}"
        fw = tw(fork_str, 12, MONO)
        bx -= fw
        b += f'<text class="mono" x="{bx}" y="{H-18}" font-size="12" fill="var(--mute)">{fork_str}</text>'
        bx -= 18
        b += f'<svg x="{bx}" y="{H-28}" width="14" height="14" viewBox="0 0 16 16" fill="var(--mute)">{ICONS["fork"]}</svg>'
        
        bx -= 16
        star_str = f"{stars}"
        sw = tw(star_str, 12, MONO)
        bx -= sw
        b += f'<text class="mono" x="{bx}" y="{H-18}" font-size="12" fill="var(--mute)">{star_str}</text>'
        bx -= 18
        b += f'<svg x="{bx}" y="{H-28}" width="14" height="14" viewBox="0 0 16 16" fill="var(--mute)">{ICONS["star"]}</svg>'

        b += '</g>'
        write(f"repo{k+1}.svg", svg(W, H, b, title=name))

# ---- 6. Link Pills with Crisp Vector Glyphs ----------------------------------------------
PILL_CONFIG = {
    "portfolio":  {"label": "Portfolio",  "icon": "portfolio"},
    "github":     {"label": "GitHub",     "icon": "github"},
    "linkedin":   {"label": "LinkedIn",   "icon": "linkedin"},
    "instagram":  {"label": "Instagram",  "icon": "instagram"},
    "x":          {"label": "X",          "icon": "x"},
    "twitter":    {"label": "Twitter",    "icon": "x"},
    "hackerrank": {"label": "HackerRank", "icon": "hackerrank"},
    "leetcode":   {"label": "LeetCode",   "icon": "leetcode"},
    "youtube":    {"label": "YouTube",    "icon": "youtube"},
    "discord":    {"label": "Discord",    "icon": "discord"},
    "email":      {"label": "Email",      "icon": "email"},
    "website":    {"label": "Website",    "icon": "globe"}
}

def pills():
    links = cfg.get("links", {})
    for key, url in links.items():
        meta = PILL_CONFIG.get(key.lower(), {"label": key.capitalize(), "icon": "globe"})
        label = meta["label"]
        icon_name = meta["icon"]
        icon_svg = ICONS.get(icon_name, ICONS["globe"])

        label_w = tw(label, 14, SANS)
        # pill width: 16 (pad) + 16 (icon) + 8 (gap) + label_w + 8 (gap) + 14 (arrow) + 16 (pad)
        w = int(16 + 16 + 8 + label_w + 8 + 14 + 16)
        h = 38

        b = (f'<g class="rise" style="{delay(4.8)}">'
             f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="19" fill="var(--card)" '
             f'stroke="var(--border)" stroke-width="1"/>'
             # Icon
             f'<svg x="16" y="11" width="16" height="16" viewBox="0 0 16 16" fill="var(--ink)">{icon_svg}</svg>'
             # Label
             f'<text x="40" y="24.5" font-size="14" fill="var(--ink)">{label}</text>'
             # Arrow ↗
             f'<text class="nudge" x="{40+label_w+8:.1f}" y="24" font-size="14" fill="{BLUE}" '
             f'style="{delay(5)}">↗</text></g>')

        write(f"link-{key}.svg", svg(w, h, b, title=label))

# ---- README.md Generator -----------------------------------------------------------------
def readme():
    L = cfg.get("links", {})
    tl = cfg.get("tiles", [])
    hero_href = cfg.get("hero_href") or L.get("portfolio") or f"https://github.com/{cfg['username']}"

    t = "\n".join(f'<a href="{x["href"]}"><img src="./cards/tile{i+1}.svg" width="32.5%" alt="{x.get("label","TILE")}" /></a>'
                  for i, x in enumerate(tl))
    rp = "\n".join(f'<a href="https://github.com/{cfg["username"]}/{n}"><img src="./cards/repo{i+1}.svg" width="49.5%" alt="{n}" /></a>'
                   for i, n in enumerate(cfg.get("featured_repos", [])))

    order = ("portfolio", "github", "linkedin", "instagram", "x", "twitter", "hackerrank", "leetcode", "youtube", "discord", "email")
    active_keys = [k for k in order if k in L] + [k for k in L if k not in order]
    pl = "\n".join(f'<a href="{L[k]}"><img src="./cards/link-{k}.svg" height="38" alt="{k}" /></a>' for k in active_keys)

    first, last = cfg.get("first_name", "Developer"), cfg.get("last_name", "")
    content = f"""<a href="{hero_href}"><img src="./cards/hero.svg" width="100%" alt="{first} {last}" /></a>

<img src="./cards/heatmap.svg" width="100%" alt="Contribution graph" />

<img src="./cards/activity.svg" width="100%" alt="Monthly contributions" />

{t}

{rp}

{pl}
"""
    (ROOT / "README.md").write_text(content, encoding="utf-8")

# ---- Main Execution ----------------------------------------------------------------------
def main():
    t0 = time.time()
    hero()
    heatmap()
    activity()
    tiles()
    repos()
    pills()
    readme()
    dt_ms = (time.time() - t0) * 1000
    card_files = sorted(p.name for p in OUT.glob("*.svg"))
    print(f"Rendered {len(card_files)} cards in {dt_ms:.1f}ms: {', '.join(card_files)}")

if __name__ == "__main__":
    main()
