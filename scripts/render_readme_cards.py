"""Draw every README card as an animated SVG from data/*.json.

  python scripts/render_readme_cards.py          # animated cards
  STATIC=1 python scripts/render_readme_cards.py # final frame only (for screenshots)

SVGs shown through <img> on GitHub can't load scripts, fonts or images, but their own
<style> (CSS keyframes) and SMIL <animate>/<set> run. Fonts are embedded as base64.
"""
import base64, datetime as dt, html, io, json, os, urllib.request
from collections import OrderedDict
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cards"; OUT.mkdir(exist_ok=True)
STATIC = os.environ.get("STATIC") == "1"
cfg = json.loads((ROOT / "config.json").read_text())
days = json.loads((ROOT / "data/contributions.json").read_text())["days"]
prof = json.loads((ROOT / "data/profile.json").read_text())

# ---- palette (paper, ink, three colours) ------------------------------------------------
PAPER, CARD, INK, MUTE, LINE = "#f4efe6", "#fbf8f2", "#16130f", "#7a7367", "#16130f1f"
BLUE, RED, YELLOW = "#2563eb", "#e5484d", "#f5b301"
BLUES = ["#e6dfd0", "#c7d7fb", "#8aaaf5", "#4c7cee", "#1d4ed8"]
SERIF, SANS, MONO = "Instrument Serif", "Geist", "Geist Mono"

# ---- fonts ------------------------------------------------------------------------------
FONTFILES = {SERIF: "serif.woff", SANS: "sans.woff", MONO: "mono.woff"}
_fonts = {k: TTFont(ROOT / "assets/fonts" / v) for k, v in FONTFILES.items()}
def tw(text, size, font=SANS):
    f = _fonts[font]; cmap = f.getBestCmap(); hm = f["hmtx"]; upm = f["head"].unitsPerEm
    return sum(hm[cmap.get(ord(ch), cmap.get(32))][0] for ch in text) * size / upm
def font_css():
    out = ""
    for fam, fn in FONTFILES.items():
        b64 = base64.b64encode((ROOT / "assets/fonts" / fn).read_bytes()).decode()
        out += f"@font-face{{font-family:'{fam}';src:url(data:font/woff;base64,{b64}) format('woff')}}"
    return out
FONT_CSS = font_css()
esc = html.escape

# ---- shared css: one small set of keyframes, switched off for reduced motion ------------
BASE_CSS = f"""
text{{font-family:'{SANS}',system-ui,sans-serif}}
.serif{{font-family:'{SERIF}',Georgia,serif}} .mono{{font-family:'{MONO}',ui-monospace,monospace}}
.rise{{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}}
.fade{{animation:fade .8s ease-out both}}
.pop{{animation:pop .5s cubic-bezier(.3,1.6,.5,1) both;transform-box:fill-box;transform-origin:center}}
.grow{{animation:grow .8s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:bottom}}
.pulse{{animation:pulse 2.2s ease-out infinite;transform-box:fill-box;transform-origin:center}}
.nudge{{animation:nudge 2.4s ease-in-out infinite}}
.st{{animation:fade .01s linear both}} .fr{{display:inline}}
@keyframes rise{{from{{opacity:0;transform:translateY(26px)}}to{{opacity:1;transform:none}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes pop{{0%{{opacity:0;transform:scale(0)}}100%{{opacity:1;transform:scale(1)}}}}
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes pulse{{0%{{opacity:.7;transform:scale(1)}}100%{{opacity:0;transform:scale(3.2)}}}}
@keyframes nudge{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(3px,-3px)}}}}
@keyframes swing{{0%{{opacity:0;transform:translateY(60px) rotate(-7deg)}}60%{{opacity:1;transform:translateY(-6px) rotate(1.5deg)}}80%{{transform:translateY(2px) rotate(-.4deg)}}100%{{transform:none}}}}
@keyframes sheen{{0%,55%{{transform:translateX(-140px) skewX(-18deg)}}100%{{transform:translateX(420px) skewX(-18deg)}}}}
"""
REDUCED = ".rise,.fade,.pop,.grow,.pulse,.nudge,.st,.tile,.sheen{animation:none!important}.fr{display:none}"
def css(extra=""):
    r = REDUCED if STATIC else f"@media (prefers-reduced-motion:reduce){{{REDUCED}}}"
    return f"<style>{FONT_CSS}{BASE_CSS}{extra}{r}</style>"
def svg(w, h, body, extra_css="", title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{esc(title)}">{css(extra_css)}{body}</svg>')
def delay(s): return f"animation-delay:{s:.2f}s"
def frame(w, h, fill=PAPER, r=22):
    return f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="{fill}" stroke="{INK}" stroke-opacity=".14"/>'
def write(name, content): (OUT / name).write_text(content, encoding="utf-8")

# ---- data derivations -------------------------------------------------------------------
total = sum(d["count"] for d in days)
active = sum(1 for d in days if d["count"] > 0)
busiest = max(days, key=lambda d: d["count"])
def streaks():
    best = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0; best = max(best, run)
    cur, i = 0, len(days) - 1
    if i >= 0 and days[i]["count"] == 0: i -= 1   # today may not have happened yet
    while i >= 0 and days[i]["count"]: cur += 1; i -= 1
    return cur, best
cur_streak, best_streak = streaks()
months = OrderedDict()
for d in days: months.setdefault(d["date"][:7], 0); months[d["date"][:7]] += d["count"]
months = list(months.items())[-12:]
def month_label(k): return dt.date(int(k[:4]), int(k[5:]), 1).strftime("%b").upper()
def pretty(d): x = dt.date.fromisoformat(d); return f"{x.strftime('%b')} {x.day}"

# ---- 1. hero ----------------------------------------------------------------------------
def sierpinski(n=38):
    """Fallback art when there is no portrait: recursion, drawn in ASCII."""
    rows = []
    for y in range(n):
        cells = "".join(("#" if (x & (y - x)) == 0 else " ") + " " for x in range(y + 1))
        rows.append((" " * (n - y - 1) + cells).rstrip().ljust(0))
    return rows

def ascii_portrait(cols=78):
    from PIL import Image, ImageOps
    src = ROOT / cfg.get("portrait", "")
    img = None
    if src.is_file(): img = Image.open(src)
    else:
        try:
            req = urllib.request.Request(f"https://github.com/{cfg['username']}.png?size=400", headers={"User-Agent": "readme-cards"})
            img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read()))
        except Exception: return sierpinski()
    img = ImageOps.autocontrast(ImageOps.grayscale(img.convert("RGB")), cutoff=2)
    w, h = img.size; side = min(w, h)
    img = img.crop(((w - side) // 2, 0, (w - side) // 2 + side, side))      # square, keep the top (face)
    rows = round(cols * 0.5)
    img = img.resize((cols, rows))
    ramp = " .:-=+*#%@"
    px = img.load(); lines = []
    for y in range(rows):
        lines.append("".join(ramp[int((255 - px[x, y]) / 256 * len(ramp))] for x in range(cols)).rstrip())
    return lines

def hero():
    W, H = 900, 360
    first, last = cfg["first_name"], cfg["last_name"]
    lines = ascii_portrait()
    has = bool(lines)
    b = frame(W, H)
    if has:
        wide = max(len(l) for l in lines)
        fs = 5.0 if wide > 60 else 7.6; lh = fs * 1.04; cw = tw("M", fs, MONO); x0 = W - 44 - cw * wide
        y0 = (H - lh * len(lines)) / 2 + lh
        for i, ln in enumerate(lines):
            b += (f'<text class="mono fade" x="{x0:.1f}" y="{y0+i*lh:.1f}" font-size="{fs}" fill="{INK}" fill-opacity=".82" '
                  f'xml:space="preserve" style="{delay(.2+i*.018)}">{esc(ln)}</text>')
    nx = 48
    b += f'<text class="mono fade" x="{nx}" y="58" font-size="12" letter-spacing="2" fill="{MUTE}" style="{delay(.1)}">{esc(cfg["username"]).upper()} / GITHUB</text>'
    b += f'<text class="serif rise" x="{nx}" y="158" font-size="112" fill="{INK}" style="{delay(.25)}">{esc(first)}</text>'
    b += (f'<defs><linearGradient id="sh" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="320" y2="0" gradientTransform="translate(-340 0)">'
          f'<stop offset="0" stop-color="{INK}"/><stop offset=".38" stop-color="{INK}"/><stop offset=".5" stop-color="{BLUE}"/>'
          f'<stop offset=".62" stop-color="{INK}"/><stop offset="1" stop-color="{INK}"/>'
          f'<animateTransform attributeName="gradientTransform" type="translate" values="-340 0;560 0;560 0" keyTimes="0;.4;1" dur="7s" begin="1.8s" repeatCount="indefinite"/>'
          f'</linearGradient></defs>')
    b += f'<text class="serif rise" x="{nx}" y="260" font-size="112" fill="url(#sh)" style="{delay(.45)}">{esc(last)}</text>'
    b += f'<text class="fade" x="{nx+2}" y="300" font-size="16.5" fill="{INK}" style="{delay(.9)}">{esc(cfg["tagline"])}</text>'
    b += f'<circle class="pulse" cx="{nx+6}" cy="326" r="4" fill="{BLUE}" style="{delay(1.2)}"/><circle cx="{nx+6}" cy="326" r="4" fill="{BLUE}"/>'
    b += f'<text class="fade mono" x="{nx+20}" y="330" font-size="12.5" fill="{MUTE}" style="{delay(1.1)}">{esc(cfg["role"])}</text>'
    write("hero.svg", svg(W, H, b, title=f"{first} {last}"))

# ---- 2. blue contribution graph ----------------------------------------------------------
def heatmap():
    W, H, cell, gap = 900, 178, 13, 3
    cols = (len(days) + 6) // 7
    x0 = (W - cols * (cell + gap) + gap) / 2; y0 = 56
    b = frame(W, H)
    b += f'<text class="mono fade" x="28" y="34" font-size="12" letter-spacing="1.5" fill="{MUTE}">CONTRIBUTIONS · LAST 12 MONTHS</text>'
    b += f'<text class="serif fade" x="{W-28}" y="38" font-size="26" text-anchor="end" fill="{BLUE}" style="{delay(.4)}">{total:,}</text>'
    for i, d in enumerate(days):
        c, r = divmod(i, 7)
        b += (f'<rect class="pop" x="{x0+c*(cell+gap):.1f}" y="{y0+r*(cell+gap)}" width="{cell}" height="{cell}" rx="3" '
              f'fill="{BLUES[d["level"]]}" style="{delay(.35+c*.022)}"><title>{d["count"]} on {d["date"]}</title></rect>')
    write("heatmap.svg", svg(W, H, b, title="Contribution graph"))

# ---- 3. monthly chart + stats ------------------------------------------------------------
def activity():
    W, H = 900, 330
    b = frame(W, H)
    stats = [("Contributions", f"{total:,}", "last 12 months"), ("Current streak", f"{cur_streak}", "days in a row"),
             ("Active days", f"{active}", f"of {len(days)}"), ("Busiest day", f"{busiest['count']}", pretty(busiest["date"]))]
    for i, (lab, val, sub) in enumerate(stats):
        x = 32 + i * 214
        b += f'<text class="mono fade" x="{x}" y="42" font-size="11" letter-spacing="1.5" fill="{MUTE}" style="{delay(.2+i*.1)}">{lab.upper()}</text>'
        b += f'<text class="serif rise" x="{x}" y="92" font-size="52" fill="{INK}" style="{delay(.25+i*.1)}">{val}</text>'
        b += f'<text class="fade" x="{x}" y="112" font-size="12.5" fill="{MUTE}" style="{delay(.5+i*.1)}">{esc(sub)}</text>'
    b += f'<line x1="32" x2="{W-32}" y1="134" y2="134" stroke="{INK}" stroke-opacity=".12"/>'
    base, maxh, bw = 292, 120, 44
    gap = (W - 64 - 12 * bw) / 11
    mx = max(v for _, v in months) or 1
    best = max(range(len(months)), key=lambda i: months[i][1])
    for i, (k, v) in enumerate(months):
        x = 32 + i * (bw + gap); h = max(3, v / mx * maxh); d = .7 + i * .07
        col = BLUE if i == best else "#d9d1c0"
        b += f'<rect class="grow" x="{x:.1f}" y="{base-h:.1f}" width="{bw}" height="{h:.1f}" rx="6" fill="{col}" style="{delay(d)}"><title>{v} in {k}</title></rect>'
        b += f'<text class="mono fade" x="{x+bw/2:.1f}" y="{base+20}" font-size="11" text-anchor="middle" fill="{MUTE}" style="{delay(d)}">{month_label(k)}</text>'
        if i == best:
            b += f'<text class="serif pop" x="{x+bw/2:.1f}" y="{base-h-10:.1f}" font-size="26" text-anchor="middle" fill="{BLUE}" style="{delay(d+.6)}">{v}</text>'
    write("activity.svg", svg(W, H, b, title="Monthly contributions"))

# ---- 4. three tiles (count-up via SMIL <set>, one text element per frame) -----------------
def lum(hexc):
    r, g, bl = (int(hexc[i:i+2], 16) for i in (1, 3, 5)); return (0.299*r + 0.587*g + 0.114*bl) / 255
def metric(name):
    return {"repos": prof.get("repos", 0), "followers": prof.get("followers", 0), "contributions": total,
            "streak": best_streak, "active_days": active}.get(name, 0)
def tiles():
    W, H, N = 300, 214, 18
    for k, t in enumerate(cfg["tiles"]):
        col = t["color"]; fg = INK if lum(col) > .6 else "#ffffff"; d = 2.6 + k * .22
        val = metric(t["metric"]); cd = d + .55
        b = (f'<defs><clipPath id="c{k}"><rect width="{W}" height="{H}" rx="22"/></clipPath></defs>'
             f'<g class="tile" style="transform-box:view-box;transform-origin:0 {H}px;animation:swing 1.1s cubic-bezier(.2,.8,.2,1) {d:.2f}s both">'
             f'<rect width="{W}" height="{H}" rx="22" fill="{col}"/>'
             f'<g clip-path="url(#c{k})"><rect class="sheen" x="0" y="-20" width="70" height="{H+40}" fill="#fff" fill-opacity=".22" '
             f'style="transform:translateX(-200px);animation:sheen 6s ease-in-out {d+1.5:.2f}s infinite"/></g>'
             f'<circle class="pulse" cx="{W-34}" cy="34" r="6" fill="none" stroke="{fg}" stroke-width="1.5" style="{delay(d+1)}"/>'
             f'<circle cx="{W-34}" cy="34" r="3" fill="{fg}"/>'
             f'<text class="mono" x="26" y="40" font-size="12" letter-spacing="2" fill="{fg}">{esc(t["label"])}</text>')
        # frames: each shown for 45ms, staggered; final value is a static element that fades in after
        for i in range(N - 1):
            v = round(val * (i / (N - 1)) ** 2)
            b += (f'<text class="serif fr" x="24" y="152" font-size="104" fill="{fg}" visibility="hidden">{v:,}'
                  f'<set attributeName="visibility" to="visible" begin="{cd+i*.045:.3f}s" dur=".045s" fill="remove"/></text>')
        b += f'<text class="serif st" x="24" y="152" font-size="104" fill="{fg}" style="animation-delay:{cd+(N-1)*.045:.3f}s">{val:,}</text>'
        b += f'<text class="fade" x="26" y="184" font-size="14" fill="{fg}" fill-opacity=".85" style="{delay(d+.5)}">{esc(t["caption"])}</text>'
        b += f'<g class="nudge" style="{delay(d)}"><text class="serif" x="{W-44}" y="{H-24}" font-size="30" fill="{fg}">↗</text></g></g>'
        write(f"tile{k+1}.svg", svg(W, H, b, title=f'{t["label"]}: {val:,} {t["caption"]}'))

# ---- 5. repo cards -----------------------------------------------------------------------
LANG = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Java": "#b07219", "Kotlin": "#A97BFF",
        "HTML": "#e34c26", "CSS": "#563d7c", "C++": "#f34b7d", "C": "#555555", "Go": "#00ADD8", "Shell": "#89e051"}
def wrap(text, size, width, lines=2):
    words, out, cur = text.split(), [], ""
    for w in words:
        if tw((cur + " " + w).strip(), size) <= width: cur = (cur + " " + w).strip()
        else: out.append(cur); cur = w
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        while tw(out[-1] + "…", size) > width: out[-1] = out[-1].rsplit(" ", 1)[0]
        out[-1] += "…"
    return out
def repos():
    W, H = 440, 160
    live = {r["name"]: r for r in prof.get("repo_list", [])}
    for k, name in enumerate(cfg["featured_repos"]):
        r = {**cfg.get("repo_fallback", {}).get(name, {}), **{kk: vv for kk, vv in live.get(name, {}).items() if vv not in ("", None)}}
        d = 4.2 + k * .2
        b = f'<g class="rise" style="{delay(d)}">{frame(W, H, CARD, 20)}'
        b += f'<text class="mono" x="24" y="34" font-size="11" letter-spacing="1.5" fill="{MUTE}">REPO</text>'
        b += f'<text class="serif" x="24" y="68" font-size="30" fill="{INK}">{esc(name if tw(name,30,SERIF)<350 else name[:22]+"…")}</text>'
        for j, ln in enumerate(wrap(r.get("description", ""), 13, W - 48)):
            b += f'<text x="24" y="{94+j*18}" font-size="13" fill="{INK}" fill-opacity=".75">{esc(ln)}</text>'
        lang = r.get("language", "")
        if lang:
            b += f'<circle cx="30" cy="{H-22}" r="5" fill="{LANG.get(lang, BLUE)}"/><text x="42" y="{H-18}" font-size="12.5" fill="{INK}">{esc(lang)}</text>'
        b += f'<text class="mono" x="{W-24}" y="{H-18}" font-size="12" text-anchor="end" fill="{MUTE}">{r.get("stars", 0)} stars   {r.get("forks", 0)} forks</text></g>'
        write(f"repo{k+1}.svg", svg(W, H, b, title=name))

# ---- 6. link pills -----------------------------------------------------------------------
def pills():
    labels = {
        "portfolio": "Portfolio",
        "github": "GitHub",
        "linkedin": "LinkedIn",
        "instagram": "Instagram",
        "x": "X",
        "hackerrank": "HackerRank"
    }
    for key, label in labels.items():
        if key not in cfg["links"]: continue
        w = int(tw(label, 14) + 56); h = 38
        b = (f'<g class="rise" style="{delay(4.8)}"><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="19" fill="{CARD}" stroke="{INK}" stroke-opacity=".2"/>'
             f'<text x="20" y="24.5" font-size="14" fill="{INK}">{label}</text>'
             f'<text class="nudge" x="{20+tw(label,14)+8:.1f}" y="24" font-size="14" fill="{BLUE}" style="{delay(5)}">↗</text></g>')
        write(f"link-{key}.svg", svg(w, h, b, title=label))

# ---- README ------------------------------------------------------------------------------
def readme():
    L = cfg["links"]; tl = cfg["tiles"]
    hero_href = cfg.get("hero_href") or L.get("portfolio") or f"https://github.com/{cfg['username']}"
    t = "\n".join(f'<a href="{x["href"]}"><img src="./cards/tile{i+1}.svg" width="32.5%" alt="{x["label"]}" /></a>' for i, x in enumerate(tl))
    rp = "\n".join(f'<a href="https://github.com/{cfg["username"]}/{n}"><img src="./cards/repo{i+1}.svg" width="49.5%" alt="{n}" /></a>'
                   for i, n in enumerate(cfg["featured_repos"]))
    order = ("portfolio", "github", "linkedin", "instagram", "x", "hackerrank")
    pl = "\n".join(f'<a href="{L[k]}"><img src="./cards/link-{k}.svg" height="38" alt="{k}" /></a>'
                   for k in order if k in L)
    (ROOT / "README.md").write_text(f"""<a href="{hero_href}"><img src="./cards/hero.svg" width="100%" alt="{cfg['first_name']} {cfg['last_name']}" /></a>

<img src="./cards/heatmap.svg" width="100%" alt="Contribution graph" />

<img src="./cards/activity.svg" width="100%" alt="Monthly contributions" />

{t}

{rp}

{pl}
""", encoding="utf-8")

if __name__ == "__main__":
    hero(); heatmap(); activity(); tiles(); repos(); pills(); readme()
    print("cards:", ", ".join(sorted(p.name for p in OUT.glob("*.svg"))))
