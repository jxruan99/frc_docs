import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_manifest as bm  # noqa: E402


def write(root, rel, text="<title>x</title>"):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class StripPrefixTest(unittest.TestCase):
    def test_strip_prefix(self):
        self.assertEqual(bm.strip_prefix("01-intro"), "intro")
        self.assertEqual(bm.strip_prefix("3_技术方向"), "技术方向")
        self.assertEqual(bm.strip_prefix("10. 编程"), "编程")
        self.assertEqual(bm.strip_prefix("2026"), "2026")
        self.assertEqual(bm.strip_prefix("01-"), "01-")


class NaturalSortTest(unittest.TestCase):
    def test_natural_sort(self):
        names = ["10-a", "2-b", "1-c", "B", "a"]
        self.assertEqual(sorted(names, key=bm.natural_key), ["1-c", "2-b", "10-a", "a", "B"])


class ExtractMetaTest(unittest.TestCase):
    def test_extract_title_and_description(self):
        meta = bm.extract_meta('<title> A &amp; B </title><meta name="description" content="说明">')
        self.assertEqual(meta["title"], "A & B")
        self.assertEqual(meta["description"], "说明")

    def test_extract_case_and_attr_order(self):
        meta = bm.extract_meta('<TITLE>X</TITLE><META CONTENT="短" NAME="nav-title">')
        self.assertEqual(meta["title"], "X")
        self.assertEqual(meta["nav_title"], "短")

    def test_extract_missing(self):
        self.assertEqual(bm.extract_meta("<p>hi</p>"), {"title": "", "nav_title": "", "description": ""})


class BuildTreeTest(unittest.TestCase):
    def test_tree_nesting_and_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in [
                "index.html", "01-a.html", "_drafts/x.html", ".hidden/y.html", "_z.html",
                "02-sec/index.html", "02-sec/03-deep/9-b.html", "02-sec/03-deep/10-c.html",
            ]:
                write(tmp, rel)
            write(tmp, "empty/readme.txt", "hi")

            tree = bm.build_tree(Path(tmp))

            self.assertEqual([c["name"] for c in tree["children"]], ["01-a.html", "02-sec"])
            sec = tree["children"][1]
            self.assertEqual(sec["type"], "dir")
            self.assertEqual(sec["title"], "sec")
            self.assertEqual([c["name"] for c in sec["children"]], ["index.html", "03-deep"])
            deep = sec["children"][1]
            self.assertEqual(deep["title"], "deep")
            self.assertEqual([c["path"] for c in deep["children"]],
                             ["02-sec/03-deep/9-b.html", "02-sec/03-deep/10-c.html"])

    def test_title_fallback_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "1-t.html", "<title>T</title>")
            write(tmp, "2-n.html", '<title>T</title><meta name="nav-title" content="N">')
            write(tmp, "05-my-page.html", "<p>no title</p>")

            titles = [c["title"] for c in bm.build_tree(Path(tmp))["children"]]

            self.assertEqual(titles, ["T", "N", "my-page"])

    def test_doc_node_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html", '<title>A</title><meta name="description" content="D">')

            doc = bm.build_tree(Path(tmp))["children"][0]

            self.assertEqual(doc, {"type": "doc", "name": "a.html", "path": "a.html",
                                   "title": "A", "description": "D"})


class OutputTest(unittest.TestCase):
    def test_render_manifest(self):
        tree = {"title": "", "children": [{"type": "doc", "name": "a.html", "path": "a.html",
                                           "title": "认识", "description": ""}]}
        out = bm.render_manifest(tree)

        self.assertTrue(out.startswith("window.SITE_MANIFEST = "))
        self.assertTrue(out.endswith(";\n"))
        self.assertIn("认识", out)
        body = out[len("window.SITE_MANIFEST = "):-2]
        self.assertEqual(json.loads(body), tree)

    def test_main_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.html")
            out = os.path.join(tmp, "_site", "manifest.js")

            self.assertEqual(bm.main(["--root", tmp, "--out", out]), 0)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
