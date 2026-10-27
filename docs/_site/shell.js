// Site shell: builds the nav tree and home list from window.SITE_MANIFEST and shows
// the document named in the URL hash (#/path/to/doc.html) in the iframe.
(function () {
  "use strict";

  const SITE_NAME = "家长 Mentor 学习计划";
  const OPEN_KEY = "frcdocs.open";
  const P = window.SitePaths;
  const tree = window.SITE_MANIFEST;
  const $ = (id) => document.getElementById(id);
  const views = ["home", "notfound", "missing-manifest", "doc"];

  function show(id) {
    views.forEach((v) => { $(v).hidden = v !== id; });
  }

  if (!tree) {
    show("missing-manifest");
    return;
  }

  const docs = P.flattenDocs(tree);
  const byPath = new Map(docs.map((d) => [d.path, d]));
  const base = P.baseDir(location.pathname);
  const frame = $("doc");
  const nav = $("nav");
  const toggle = $("nav-toggle");
  const scrim = $("scrim");

  // ---- folder open state (per viewer convenience only) ----
  function loadOpen() {
    try {
      const saved = JSON.parse(localStorage.getItem(OPEN_KEY) || "[]");
      return new Set(Array.isArray(saved) ? saved : []);
    } catch (e) {
      return new Set();
    }
  }
  const open = loadOpen();
  function saveOpen() {
    try { localStorage.setItem(OPEN_KEY, JSON.stringify([...open])); } catch (e) { /* storage unavailable */ }
  }

  // ---- nav tree ----
  const dirButtons = new Map();
  const docLinks = new Map();

  function el(tag, attrs, text) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text != null) node.textContent = text;
    return node;
  }

  function renderDir(node, key) {
    const ul = el("ul");
    node.children.forEach((child) => {
      const li = el("li");
      if (child.type === "doc") {
        const a = el("a", { class: "doc-link", href: P.hashFor(child.path) }, child.title);
        docLinks.set(child.path, a);
        li.append(a);
      } else {
        const dirKey = key + child.name + "/";
        const btn = el("button", { class: "dir-toggle", type: "button", "aria-expanded": String(open.has(dirKey)) }, child.title);
        btn.addEventListener("click", () => setOpen(dirKey, btn.getAttribute("aria-expanded") !== "true"));
        dirButtons.set(dirKey, btn);
        li.append(btn, renderDir(child, dirKey));
      }
      ul.append(li);
    });
    return ul;
  }

  function setOpen(dirKey, isOpen) {
    const btn = dirButtons.get(dirKey);
    if (!btn) return;
    btn.setAttribute("aria-expanded", String(isOpen));
    if (isOpen) open.add(dirKey); else open.delete(dirKey);
    saveOpen();
  }

  function revealAncestors(path) {
    const parts = path.split("/").slice(0, -1);
    let key = "";
    parts.forEach((part) => {
      key += part + "/";
      setOpen(key, true);
    });
  }

  $("nav-tree").append(renderDir(tree, ""));

  // ---- home list, grouped by top-level folder ----
  function renderHome() {
    const groups = new Map();
    docs.forEach((d) => {
      const name = d.trail[0] || "";
      if (!groups.has(name)) groups.set(name, []);
      groups.get(name).push(d);
    });
    const root = $("home-list");
    groups.forEach((items, name) => {
      const section = el("section", { class: "group" });
      section.append(el("h2", {}, name || "文档"));
      const ul = el("ul", { class: "doc-list" });
      items.forEach((d) => {
        const a = el("a", { href: P.hashFor(d.path) });
        a.append(el("span", { class: "t" }, d.title));
        if (d.description) a.append(el("span", { class: "d" }, d.description));
        const sub = d.trail.slice(1);
        if (sub.length) a.append(el("span", { class: "where" }, "位于：" + sub.join(" › ")));
        const li = el("li");
        li.append(a);
        ul.append(li);
      });
      section.append(ul);
      root.append(section);
    });
  }
  renderHome();

  // ---- drawer (narrow screens) ----
  function setDrawer(isOpen) {
    if (isOpen) nav.setAttribute("data-open", ""); else nav.removeAttribute("data-open");
    scrim.hidden = !isOpen;
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "关闭目录" : "打开目录");
  }
  toggle.addEventListener("click", () => setDrawer(!nav.hasAttribute("data-open")));
  scrim.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setDrawer(false); });

  // ---- routing ----
  function highlight(path) {
    docLinks.forEach((a, p) => {
      if (p === path) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    const home = nav.querySelector(".nav-home");
    if (path === null) home.setAttribute("aria-current", "page"); else home.removeAttribute("aria-current");
  }

  function route() {
    const path = P.parseHash(location.hash);
    if (path === null) {
      show("home");
      highlight(null);
      document.title = SITE_NAME;
    } else if (path === undefined || !byPath.has(path)) {
      show("notfound");
      highlight("");
      document.title = "找不到文档 · " + SITE_NAME;
    } else {
      if (frame.dataset.path !== path) {
        frame.dataset.path = path;
        frame.src = P.docHref(path);
      }
      show("doc");
      highlight(path);
      revealAncestors(path);
      document.title = byPath.get(path).title + " · " + SITE_NAME;
    }
    setDrawer(false);
  }

  // Keep the hash in sync when a link inside the document navigates the iframe.
  frame.addEventListener("load", () => {
    let pathname;
    try {
      pathname = frame.contentWindow.location.pathname;
    } catch (e) {
      return; // cross-origin (e.g. opened from file://)
    }
    const path = P.relativeToBase(pathname, base);
    if (!path || !byPath.has(path)) return;
    frame.dataset.path = path;
    if (P.parseHash(location.hash) !== path) {
      history.replaceState(null, "", P.hashFor(path));
      route();
    }
  });

  window.addEventListener("hashchange", route);
  route();
})();
