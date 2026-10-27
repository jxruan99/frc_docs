// Pure path helpers for the docs site shell. No DOM access, so they run under Node tests too.
(function (global) {
  "use strict";

  function safeDecode(text) {
    try {
      return decodeURIComponent(text);
    } catch (e) {
      return undefined;
    }
  }

  // "" | "#" | "#/" -> null (home); "#/a/b.html" -> "a/b.html"; bad encoding -> undefined.
  function parseHash(hash) {
    var raw = String(hash || "").replace(/^#/, "").replace(/^\/+/, "");
    if (!raw) return null;
    var decoded = safeDecode(raw);
    return decoded === undefined ? undefined : decoded.replace(/^\/+/, "");
  }

  function docHref(path) {
    return path.split("/").map(encodeURIComponent).join("/");
  }

  function hashFor(path) {
    return "#/" + docHref(path);
  }

  function baseDir(pathname) {
    return pathname.slice(0, pathname.lastIndexOf("/") + 1);
  }

  // Iframe pathname -> document path relative to the shell's directory, or null.
  function relativeToBase(pathname, base) {
    if (pathname.indexOf(base) !== 0) return null;
    var rest = safeDecode(pathname.slice(base.length));
    return rest === undefined ? null : rest;
  }

  // True when a document path points back at the shell itself (the site home).
  function isShellPath(path) {
    return path === "" || path === "index.html";
  }

  function flattenDocs(tree) {
    var out = [];
    (function walk(node, trail) {
      node.children.forEach(function (child) {
        if (child.type === "doc") {
          out.push({ path: child.path, title: child.title, description: child.description, trail: trail });
        } else {
          walk(child, trail.concat(child.title));
        }
      });
    })(tree, []);
    return out;
  }

  var api = {
    parseHash: parseHash,
    docHref: docHref,
    hashFor: hashFor,
    baseDir: baseDir,
    relativeToBase: relativeToBase,
    isShellPath: isShellPath,
    flattenDocs: flattenDocs,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else global.SitePaths = api;
})(this);
