"""Fetch contribution calendar + profile + repo data into data/*.json.
Uses the public contributions page (no token needed). The GitHub API is used
for profile/repo info and picks up GITHUB_TOKEN automatically when present."""
import json, os, re, sys, urllib.request, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())
USER = cfg["username"]
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

def get(url, api=False):
    h = {"User-Agent": "readme-cards"}
    if api:
        h["Accept"] = "application/vnd.github+json"
        if TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode()

def calendar():
    page = get(f"https://github.com/users/{USER}/contributions")
    cells = re.findall(r'<td[^>]*data-date="([\d-]+)"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', page)
    tips = dict(re.findall(r'for="(contribution-day-component[^"]+)"[^>]*>\s*([^<]+?)\s*<', page))
    days = []
    for date, cid, level in cells:
        m = re.match(r"(\d+|No)\s+contribution", html.unescape(tips.get(cid, "")))
        count = 0 if (not m or m.group(1) == "No") else int(m.group(1))
        days.append({"date": date, "count": count, "level": int(level)})
    days.sort(key=lambda d: d["date"])
    return days

def main():
    days = calendar()
    if not days:
        sys.exit("no contribution data parsed; keeping previous files")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data/contributions.json").write_text(json.dumps({"days": days}))
    try:
        prof = json.loads(get(f"https://api.github.com/users/{USER}", api=True))
        repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed", api=True))
    except Exception as e:  # rate-limited / offline: keep the previous profile.json if there is one
        print("profile API unavailable:", e)
        if (ROOT / "data/profile.json").exists():
            return
        prof, repos = {"followers": 13, "public_repos": 26}, []
    info = {
        "followers": prof.get("followers", 0), "repos": prof.get("public_repos", 0),
        "repo_list": [{"name": r["name"], "description": r.get("description") or "",
                       "language": r.get("language") or "", "stars": r["stargazers_count"],
                       "forks": r["forks_count"], "url": r["html_url"]} for r in repos],
    }
    (ROOT / "data/profile.json").write_text(json.dumps(info))
    print(f"{len(days)} days, {sum(d['count'] for d in days)} contributions")

if __name__ == "__main__":
    main()
