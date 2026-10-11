"""Fetch public GitHub repos and write projects.json for the portfolio site."""
import json
import os
import re
from urllib.parse import quote
import urllib.request
from pathlib import Path

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "coders543")
THIS_REPO = os.environ.get("GITHUB_REPOSITORY", "").split("/")[-1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Repos owned by other people (or forks) you still want on the site, as "owner/repo".
EXTRA_REPOS = []  # e.g. ["someone/their-project"]

# Only repos with this topic show up on the site. Set to None to show every repo.
REQUIRE_TOPIC = "portfolio"

MAX_README = 12000     # characters of README to keep
MAX_FILES = 6          # code files per project
MAX_FILE_SIZE = 40000  # bytes per file
MAX_TOTAL = 120000     # characters of code per project
CODE_EXT = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs",
            ".sh", ".ps1", ".html", ".css", ".sql", ".rb", ".php", ".kt", ".swift"}
SKIP_DIRS = {"node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".github", "vendor"}

OUT_FILE = Path(__file__).resolve().parent.parent / "projects.json"


def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "portfolio-updater"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        return json.load(resp)


def get_raw(url):
    headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "portfolio-updater"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        return resp.read().decode("utf-8")


def fetch_readme(owner, name):
    try:
        return get_raw("https://api.github.com/repos/%s/%s/readme" % (owner, name))[:MAX_README].strip()
    except Exception:
        return ""


def fetch_files(r):
    files, total = [], 0
    try:
        owner = r.get("owner", {}).get("login", OWNER)
        branch = r.get("default_branch") or "main"
        tree = get("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1" % (owner, r["name"], quote(branch)))
        cands = [
            t for t in tree.get("tree", [])
            if t["type"] == "blob"
            and os.path.splitext(t["path"])[1].lower() in CODE_EXT
            and t.get("size", 0) <= MAX_FILE_SIZE
            and not (set(t["path"].split("/")[:-1]) & SKIP_DIRS)
        ]
        cands.sort(key=lambda t: (t["path"].count("/"), len(t["path"])))
        for t in cands[:MAX_FILES]:
            try:
                code = get_raw("https://api.github.com/repos/%s/%s/contents/%s?ref=%s"
                               % (owner, r["name"], quote(t["path"]), quote(branch)))
            except Exception:
                continue
            if total + len(code) > MAX_TOTAL:
                break
            total += len(code)
            files.append({"path": t["path"], "code": code})
    except Exception:
        pass
    return files


def pretty_name(name):
    name = name.strip("-_")
    name = re.sub(r"-{2,}", "\x00", name)
    name = re.sub(r"[-_]+", " ", name)
    name = name.replace("\x00", " - ")
    return re.sub(r"\s+", " ", name).strip()


def build_projects(repos):
    projects = []
    for r in repos:
        if (r.get("fork") and not r.get("_extra")) or r.get("archived") or r["name"] == THIS_REPO:
            continue
        topics = r.get("topics") or []
        if REQUIRE_TOPIC and not r.get("_extra") and REQUIRE_TOPIC not in topics:
            continue
        tech = ([r["language"]] if r.get("language") else []) + [t for t in topics if t != REQUIRE_TOPIC]
        desc = (r.get("description") or "").strip() or "No description yet."
        links = [["GitHub repo", r["html_url"]]]
        if r.get("homepage"):
            links.append(["Live demo", r["homepage"]])
        readme = fetch_readme(r.get("owner", {}).get("login", OWNER), r["name"])
        h1 = re.match(r"\s*#\s+(.+)", readme)
        title = h1.group(1).strip() if h1 else pretty_name(r["name"])
        if h1:
            readme = readme[h1.end():].lstrip()  # title is shown separately
        projects.append({
            "t": title,
            "tech": tech,
            "d": desc,
            "long": desc,
            "built": [],
            "learned": "",
            "readme": readme,
            "files": fetch_files(r),
            "links": links,
        })
    return projects


def main():
    repos = get("https://api.github.com/users/%s/repos?per_page=100&sort=updated" % OWNER)
    for full in EXTRA_REPOS:
        try:
            repos.append(dict(get("https://api.github.com/repos/" + full), _extra=True))
        except Exception:
            print("Could not load", full)
    projects = build_projects(repos)
    OUT_FILE.write_text(json.dumps(projects, indent=2) + "\n", encoding="utf-8")
    print("Wrote %d projects to %s" % (len(projects), OUT_FILE))


if __name__ == "__main__":
    main()
