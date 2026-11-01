import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import inject_sdk as inj  # noqa: E402

SERVER = "https://comments.example.org"
TAG = f'<script src="{SERVER}/sdk.js" data-server="{SERVER}"></script>'


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read(root, rel):
    return (Path(root) / rel).read_text(encoding="utf-8")


class InjectTagTest(unittest.TestCase):
    def test_inserts_before_the_last_closing_body(self):
        html = "<html><body><p>a</p><pre>&lt;/body&gt;</pre></body></html>"
        self.assertEqual(inj.inject(html, TAG), f"<html><body><p>a</p><pre>&lt;/body&gt;</pre>{TAG}\n</body></html>")

    def test_closing_body_is_case_insensitive(self):
        self.assertEqual(inj.inject("<p>a</p></BODY>", TAG), f"<p>a</p>{TAG}\n</BODY>")

    def test_appends_when_there_is_no_closing_body(self):
        self.assertEqual(inj.inject("<p>a</p>", TAG), f"<p>a</p>\n{TAG}\n")

    def test_already_injected_page_is_left_alone(self):
        once = inj.inject("<body><p>a</p></body>", TAG)
        self.assertEqual(inj.inject(once, TAG), once)


class ServerUrlTest(unittest.TestCase):
    def test_accepts_http_and_https_and_drops_trailing_slash(self):
        self.assertEqual(inj.server_url("https://c.example.org/"), "https://c.example.org")
        self.assertEqual(inj.server_url("http://localhost:3001"), "http://localhost:3001")

    def test_rejects_other_schemes_and_markup(self):
        for bad in ["c.example.org", "javascript:alert(1)", 'https://x.org/"><script>', "https://x.org/a b"]:
            with self.assertRaises(ValueError, msg=bad):
                inj.server_url(bad)


class InjectTreeTest(unittest.TestCase):
    def test_injects_doc_pages_but_not_the_shell_or_site_assets(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "index.html", "<body>shell</body>")
            write(root, "01-understanding-frc.html", "<body>doc</body>")
            write(root, "02-怎么当Mentor/01-概览.html", "<body>中文</body>")
            write(root, "_site/demo.html", "<body>asset</body>")
            write(root, "_site/shell.js", "x")
            changed = inj.inject_tree(Path(root), SERVER)
            self.assertEqual(sorted(changed), ["01-understanding-frc.html", "02-怎么当Mentor/01-概览.html"])
            self.assertIn(TAG, read(root, "01-understanding-frc.html"))
            self.assertIn(TAG, read(root, "02-怎么当Mentor/01-概览.html"))
            self.assertEqual(read(root, "index.html"), "<body>shell</body>")
            self.assertEqual(read(root, "_site/demo.html"), "<body>asset</body>")


if __name__ == "__main__":
    unittest.main()
