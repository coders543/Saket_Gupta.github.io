"""Fetch public GitHub repos and write projects.json for the portfolio site."""
import json
import os
import re
import urllib.request
from pathlib import Path

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "coders543")
THIS_REPO = os.environ.get("GITHUB_REPOSITORY", "").split("/")[-1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Only repos with this topic show up on the site. Set to None to show every repo.
REQUIRE_TOPIC = "portfolio"

OUT_FILE = Path(__file__).resolve().parent.parent / "projects.json"


def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "portfolio-updater"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        return json.load(resp)


def pretty_name(name):
    name = name.strip("-_")
    name = re.sub(r"-{2,}", "\x00", name)
    name = re.sub(r"[-_]+", " ", name)
    name = name.replace("\x00", " - ")
    return re.sub(r"\s+", " ", name).strip()


def build_projects(repos):
    projects = []
    for r in repos:
        if r.get("fork") or r.get("archived") or r["name"] == THIS_REPO:
            continue
        topics = r.get("topics") or []
        if REQUIRE_TOPIC and REQUIRE_TOPIC not in topics:
            continue
        tech = ([r["language"]] if r.get("language") else []) + [t for t in topics if t != REQUIRE_TOPIC]
        desc = (r.get("description") or "").strip() or "No description yet."
        links = [["GitHub repo", r["html_url"]]]
        if r.get("homepage"):
            links.append(["Live demo", r["homepage"]])
        projects.append({
            "t": pretty_name(r["name"]),
            "tech": tech,
            "d": desc,
            "long": desc,
            "built": [],
            "learned": "",
            "links": links,
            "img": "SCREENSHOT: " + pretty_name(r["name"]).upper(),
        })
    return projects


def main():
    repos = get("https://api.github.com/users/%s/repos?per_page=100&sort=updated" % OWNER)
    projects = build_projects(repos)
    OUT_FILE.write_text(json.dumps(projects, indent=2) + "\n", encoding="utf-8")
    print("Wrote %d projects to %s" % (len(projects), OUT_FILE))


if __name__ == "__main__":
    main()
