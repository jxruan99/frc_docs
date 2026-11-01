#!/usr/bin/env python3
"""Add the html-comment SDK <script> to every document page under docs/ (run on the CI copy, never committed)."""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BODY_END_RE = re.compile(r"</body\s*>", re.IGNORECASE)
SERVER_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d+)?(/[A-Za-z0-9._~/-]*)?$")


def server_url(raw: str) -> str:
    """Validate the comment server URL (it goes into an attribute) and drop a trailing slash."""
    url = raw.strip().rstrip("/")
    if not SERVER_RE.match(url):
        raise ValueError(f"not an http(s) URL: {raw!r}")
    return url


def sdk_tag(server: str) -> str:
    return f'<script src="{server}/sdk.js" data-server="{server}"></script>'


def inject(html: str, tag: str) -> str:
    """Insert the tag before the last </body>, or append it; a page that already has it is unchanged."""
    if tag in html:
        return html
    ends = list(BODY_END_RE.finditer(html))
    if not ends:
        return html.rstrip("\n") + "\n" + tag + "\n"
    at = ends[-1].start()
    return html[:at] + tag + "\n" + html[at:]


def _excluded(path: Path, root: Path) -> bool:
    # same rule as build_manifest: the shell index.html and _site/ assets are not documents
    rel = path.relative_to(root)
    if any(part.startswith(("_", ".")) for part in rel.parts):
        return True
    return path.parent == root and path.name == "index.html"


def inject_tree(root: Path, server: str) -> list:
    """Inject into every document page under root; returns the changed paths, relative to root."""
    tag = sdk_tag(server_url(server))
    changed = []
    for path in sorted(root.rglob("*.html")):
        if _excluded(path, root):
            continue
        html = path.read_text(encoding="utf-8")
        out = inject(html, tag)
        if out != html:
            path.write_text(out, encoding="utf-8")
            changed.append(path.relative_to(root).as_posix())
    return changed


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", help="comment server URL, e.g. https://comments.example.org")
    parser.add_argument("--root", default=str(REPO_ROOT / "docs"), help="docs directory to process")
    args = parser.parse_args(argv)

    try:
        changed = inject_tree(Path(args.root), args.server)
    except ValueError as e:
        print(f"inject_sdk: {e}", file=sys.stderr)
        return 2
    print(f"Injected the comment SDK into {len(changed)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
