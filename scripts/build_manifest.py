#!/usr/bin/env python3
"""Scan docs/ for HTML documents and write docs/_site/manifest.js for the site shell."""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PREFIX_RE = re.compile(r"^\d+[-_. ]+")
READ_LIMIT = 64 * 1024


def strip_prefix(name: str) -> str:
    """Drop a leading ordering prefix such as "01-"; keep the name if nothing would remain."""
    stripped = PREFIX_RE.sub("", name)
    return stripped or name


def natural_key(name: str) -> list:
    """Sort key that compares digit runs numerically and other text case-insensitively."""
    return [(0, int(part)) if part.isdigit() else (1, part.lower())
            for part in re.split(r"(\d+)", name) if part]


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {"title": "", "nav_title": "", "description": ""}
        self._in_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "title" and not self.meta["title"]:
            self._in_title = True
        elif tag == "meta":
            attrs = {k.lower(): (v or "") for k, v in attrs}
            name = attrs.get("name", "").lower()
            key = {"nav-title": "nav_title", "description": "description"}.get(name)
            if key and not self.meta[key]:
                self.meta[key] = attrs.get("content", "").strip()

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.meta["title"] = "".join(self._title_parts).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)


def extract_meta(html: str) -> dict:
    """Return the <title>, nav-title and description meta values ("" when missing)."""
    parser = _MetaParser()
    parser.feed(html)
    parser.close()
    return parser.meta


def _excluded(path: Path, root: Path) -> bool:
    if path.name.startswith(("_", ".")):
        return True
    return path.parent == root and path.name == "index.html"


def _doc_node(path: Path, root: Path) -> dict:
    with path.open("rb") as f:
        html = f.read(READ_LIMIT).decode("utf-8", errors="replace")
    meta = extract_meta(html)
    title = meta["nav_title"] or meta["title"] or strip_prefix(path.stem)
    return {"type": "doc", "name": path.name, "path": path.relative_to(root).as_posix(),
            "title": title, "description": meta["description"]}


def _children(directory: Path, root: Path) -> list:
    docs, dirs = [], []
    for path in directory.iterdir():
        if _excluded(path, root):
            continue
        if path.is_dir():
            kids = _children(path, root)
            if kids:
                dirs.append({"type": "dir", "name": path.name,
                             "title": strip_prefix(path.name), "children": kids})
        elif path.suffix.lower() == ".html":
            docs.append(_doc_node(path, root))
    by_name = lambda node: natural_key(node["name"])  # noqa: E731
    return sorted(docs, key=by_name) + sorted(dirs, key=by_name)


def build_tree(root: Path) -> dict:
    """Return the manifest tree for every non-excluded HTML file under root."""
    root = Path(root)
    return {"title": "", "children": _children(root, root)}


def render_manifest(tree: dict) -> str:
    return "window.SITE_MANIFEST = " + json.dumps(tree, ensure_ascii=False, indent=1) + ";\n"


def _count_docs(node: dict) -> int:
    return sum(1 if c["type"] == "doc" else _count_docs(c) for c in node["children"])


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(REPO_ROOT / "docs"), help="docs directory to scan")
    parser.add_argument("--out", help="output file (default: <root>/_site/manifest.js)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    out = Path(args.out) if args.out else root / "_site" / "manifest.js"
    tree = build_tree(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_manifest(tree), encoding="utf-8")
    print(f"Found {_count_docs(tree)} documents -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
