const test = require("node:test");
const assert = require("node:assert/strict");
const P = require("../docs/_site/paths.js");

test("parseHash returns null for the home page", () => {
  assert.equal(P.parseHash(""), null);
  assert.equal(P.parseHash("#"), null);
  assert.equal(P.parseHash("#/"), null);
});

test("parseHash returns the decoded document path", () => {
  assert.equal(P.parseHash("#/02-sec/x.html"), "02-sec/x.html");
  assert.equal(P.parseHash("#/%E6%8A%80%E6%9C%AF/a%20b.html"), "技术/a b.html");
});

test("parseHash returns undefined for malformed encoding", () => {
  assert.equal(P.parseHash("#/%E0%A4%A"), undefined);
});

test("docHref encodes each path segment", () => {
  assert.equal(P.docHref("技术/a b#1.html"), "%E6%8A%80%E6%9C%AF/a%20b%231.html");
});

test("hashFor builds a route hash", () => {
  assert.equal(P.hashFor("a/b.html"), "#/a/b.html");
});

test("baseDir returns the directory of the shell page", () => {
  assert.equal(P.baseDir("/frc_docs/index.html"), "/frc_docs/");
  assert.equal(P.baseDir("/frc_docs/"), "/frc_docs/");
  assert.equal(P.baseDir("/index.html"), "/");
});

test("relativeToBase maps an iframe pathname to a document path", () => {
  assert.equal(P.relativeToBase("/frc_docs/%E6%8A%80%E6%9C%AF/a.html", "/frc_docs/"), "技术/a.html");
  assert.equal(P.relativeToBase("/other/a.html", "/frc_docs/"), null);
  assert.equal(P.relativeToBase("/frc_docs/%E0%A4%A.html", "/frc_docs/"), null);
});

test("flattenDocs lists documents in tree order with their folder trail", () => {
  const tree = {
    title: "",
    children: [
      { type: "doc", name: "a.html", path: "a.html", title: "A", description: "d" },
      {
        type: "dir", name: "1-sec", title: "sec", children: [
          { type: "dir", name: "deep", title: "deep", children: [
            { type: "doc", name: "b.html", path: "1-sec/deep/b.html", title: "B", description: "" },
          ] },
        ],
      },
    ],
  };
  assert.deepEqual(P.flattenDocs(tree), [
    { path: "a.html", title: "A", description: "d", trail: [] },
    { path: "1-sec/deep/b.html", title: "B", description: "", trail: ["sec", "deep"] },
  ]);
});
