# 文档网站 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `docs/index.html` 成为网站首页框架，自动发现 `docs/` 下任意层级的 HTML 文档，用树形导航和 iframe 把它们组成一个网站，并通过 GitHub Pages 自动部署。

**Architecture:** Python 脚本扫描 `docs/`，生成 `docs/_site/manifest.js`（`window.SITE_MANIFEST`）。首页框架读取这份清单，渲染导航树、首页列表，并用 hash 路由在 iframe 里显示文档。路径换算逻辑放在独立的纯函数文件 `paths.js` 里，方便用 Node 测试。GitHub Actions 在 push 时运行测试、生成清单，然后部署 `docs/`。

**Tech Stack:** Python 3.9+ 标准库（`html.parser`、`unittest`）；原生 HTML/CSS/JS；`node --test`（仅用于测试，不引入依赖）；GitHub Actions + Pages。

**Spec:** `design/2026-10-26-docs-site-design.md`

## Global Constraints

- Python 代码必须兼容 3.9（本机是 3.9.6）：不能用 `match`，类型注解不能用 `X | Y`。
- 不引入任何第三方依赖（Python 和 JS 都一样）。
- 被排除的路径：根目录的 `index.html`；任何以 `_` 或 `.` 开头的文件或目录。
- 数字前缀正则：`^\d+[-_. ]+`；去掉前缀后为空时保留原名。
- 每个文件只读前 64 KB，按 UTF-8 解码，`errors="replace"`。
- 清单输出：`docs/_site/manifest.js`，内容是 `window.SITE_MANIFEST = <json>;`，json 用 `ensure_ascii=False`。
- 节点格式：根节点 `{"title": "", "children": [...]}`；文档节点 `{"type":"doc","name","path","title","description"}`；目录节点 `{"type":"dir","name","title","children"}`。
- 网站名："家长 Mentor 学习计划"；文档页标题格式："文档标题 · 家长 Mentor 学习计划"。
- 宽度 ≤ 860px 时，导航变成抽屉。
- 颜色变量沿用 `docs/01-understanding-frc.html` 的 `:root` 定义（亮色和暗色两套），字体也一样。

## Review Focus

1. **GitHub Pages 项目站点挂在子路径下**（`https://jxruan99.github.io/frc_docs/`）：iframe 的 pathname 是 `/frc_docs/a/b.html`，必须相对首页所在目录来换算，不能相对 `/`。→ Task 2 `relativeToBase` 测试
2. **中文文件名和目录名**：iframe 的 pathname 和用户复制的 hash 都是百分号编码的，比较前要先解码；生成 `src` 时要按路径段分别编码。→ Task 2 `parseHash` / `docHref` 测试
3. **文件名含空格、`#`、`?`**：`docHref` 必须逐段使用 `encodeURIComponent`，否则 `#` 会截断地址。→ Task 2 测试
4. **不规范的 HTML**：大写标签 `<TITLE>`、`content` 写在 `name` 前面、没有 `<title>`、`<title>` 里带实体（`&amp;`）。→ Task 1 测试
5. **畸形的 hash**（例如 `#/%E0%A4%A`，不是合法的 URL 编码）：`decodeURIComponent` 会抛异常，此时应当显示"文档不存在"视图，而不是让整个页面崩溃。→ Task 2 测试

---

### Task 1: 清单生成脚本

**Files:**
- Create: `scripts/build_manifest.py`
- Create: `tests/test_build_manifest.py`
- Create: `.gitignore`（一行：`docs/_site/manifest.js`）

**Interfaces:**
- Produces（Python，`scripts/build_manifest.py`）:
  - `strip_prefix(name: str) -> str`
  - `natural_key(name: str) -> list`：数字段转成 `int`，其余部分转小写；为避免 int 和 str 直接比较报错，每段用 `(0, int)` 或 `(1, str)` 的元组表示
  - `extract_meta(html: str) -> dict`：返回 `{"title": str, "nav_title": str, "description": str}`，缺失的字段为 `""`。用 `html.parser.HTMLParser` 子类实现，标签名和属性名不区分大小写，实体自动解码，文本两端去空白
  - `build_tree(root: Path) -> dict`：返回根节点
  - `render_manifest(tree: dict) -> str`
  - `main(argv: Optional[list] = None) -> int`：参数 `--root`（默认为 `<repo>/docs`）和 `--out`（默认为 `<root>/_site/manifest.js`），会自动创建父目录，打印 `Found N documents -> <out>`，返回 0
- Produces（文件）：`docs/_site/manifest.js`，供 Task 2 读取

- [ ] **Step 1: 写失败的测试** `tests/test_build_manifest.py`（`unittest`；用 `sys.path.insert` 引入 `scripts/`；`build_tree` 的测试在 `tempfile.TemporaryDirectory` 里造文件）：
  - `test_strip_prefix`：`"01-intro"→"intro"`，`"3_技术方向"→"技术方向"`，`"10. 编程"→"编程"`，`"2026"→"2026"`，`"01-"→"01-"`
  - `test_natural_sort`：`sorted(["10-a","2-b","1-c","B","a"], key=natural_key) == ["1-c","2-b","10-a","a","B"]`
  - `test_extract_title_and_description`：`<title> A &amp; B </title><meta name="description" content="说明">` → title `"A & B"`，description `"说明"`
  - `test_extract_case_and_attr_order`：`<TITLE>X</TITLE><META CONTENT="短" NAME="nav-title">` → title `"X"`，nav_title `"短"`
  - `test_extract_missing`：`"<p>hi</p>"` → 三个字段都是 `""`
  - `test_tree_nesting_and_exclusions`：创建 `index.html`、`01-a.html`、`_drafts/x.html`、`.hidden/y.html`、`_z.html`、`02-sec/index.html`、`02-sec/03-deep/9-b.html`、`02-sec/03-deep/10-c.html`、`empty/readme.txt`。断言：根的 children 的 name 依次为 `["01-a.html","02-sec"]`；`02-sec` 的 children 依次为 `index.html`、`03-deep`；`03-deep` 的 children 的 path 依次为 `["02-sec/03-deep/9-b.html","02-sec/03-deep/10-c.html"]`；目录 title 为 `"sec"`、`"deep"`；`empty` 不出现
  - `test_title_fallback_order`：只有 `<title>T</title>` → `"T"`；`nav-title` 和 `<title>` 都有时用 nav-title；两者都没有时，`05-my-page.html` → `"my-page"`
  - `test_render_manifest`：输出以 `window.SITE_MANIFEST = ` 开头、以 `;\n` 结尾，中文原样保留（没有转成 `\u` 转义），中间部分能被 `json.loads` 解析
  - `test_main_writes_file`：`main(["--root", tmp, "--out", tmp + "/_site/manifest.js"])` 返回 0，文件存在

- [ ] **Step 2: 运行，确认失败**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: 报 `ModuleNotFoundError: build_manifest` 或 ERROR

- [ ] **Step 3: 在 `scripts/build_manifest.py` 实现上述接口**
  `build_tree` 用 `sorted(path.iterdir())` 递归遍历，跳过排除项；同一层先列文档、再列目录，各自按 `natural_key(name)` 排序；子目录如果没有任何文档就丢弃。`path` 用 `relative_to(root).as_posix()`。

- [ ] **Step 4: 运行，确认通过**
  Run: `python3 -m unittest discover -s tests -v`
  Expected: 全部 OK

- [ ] **Step 5: 对真实目录跑一次**
  Run: `python3 scripts/build_manifest.py`
  Expected: `Found 1 documents -> .../docs/_site/manifest.js`，文件内容里包含 `01-understanding-frc.html`

- [ ] **Step 6: Commit**
  ```bash
  git add scripts/build_manifest.py tests/test_build_manifest.py .gitignore
  git commit -m "Add manifest builder for docs site"
  ```

### Task 2: 首页框架

**Files:**
- Create: `docs/_site/paths.js`（纯函数，没有 DOM 依赖）
- Create: `docs/_site/shell.js`
- Create: `docs/_site/shell.css`
- Create: `tests/paths.test.js`
- Modify: `docs/index.html`（整体替换成框架页面）
- Modify: `docs/01-understanding-frc.html`（前面已经加了 charset/viewport，这里一并提交；再加上 `<meta name="nav-title" content="认识 FRC">` 和 `<meta name="description">`，description 内容和 Artifact 的描述保持一致）

**Interfaces:**
- Consumes: `window.SITE_MANIFEST`（Task 1 定义的格式）
- Produces（`paths.js`，在浏览器里挂到 `window.SitePaths`，在 Node 里通过 `module.exports` 导出）:
  - `parseHash(hash: string) -> string | null | undefined`：`""`、`"#"`、`"#/"` 返回 `null`（表示首页）；`"#/a/b.html"` 返回 `"a/b.html"`（先解码，再去掉开头的 `/`）；解码失败返回 `undefined`（表示不存在）
  - `docHref(path: string) -> string`：按 `/` 拆分，逐段 `encodeURIComponent`
  - `hashFor(path: string) -> string`：`"#/" + docHref(path)`
  - `baseDir(pathname: string) -> string`：返回首页 pathname 所在的目录，比如 `"/frc_docs/index.html"→"/frc_docs/"`，`"/frc_docs/"→"/frc_docs/"`
  - `relativeToBase(pathname: string, base: string) -> string | null`：不以 base 开头，或者解码失败时返回 `null`；否则返回解码后的剩余部分
  - `flattenDocs(tree) -> Array<{path, title, description, trail: string[]}>`：trail 是从根往下的目录 title 列表

- [ ] **Step 1: 写失败的测试** `tests/paths.test.js`（`node:test` 和 `node:assert/strict`，`require("../docs/_site/paths.js")`）:
  - `parseHash`：`""`、`"#"`、`"#/"` → `null`；`"#/02-sec/x.html"` → `"02-sec/x.html"`；`"#/%E6%8A%80%E6%9C%AF/a%20b.html"` → `"技术/a b.html"`；`"#/%E0%A4%A"` → `undefined`
  - `docHref`：`"技术/a b#1.html"` → `"%E6%8A%80%E6%9C%AF/a%20b%231.html"`
  - `hashFor`：`"a/b.html"` → `"#/a/b.html"`
  - `baseDir`：`"/frc_docs/index.html"`→`"/frc_docs/"`；`"/frc_docs/"`→`"/frc_docs/"`；`"/index.html"`→`"/"`
  - `relativeToBase`：(`"/frc_docs/%E6%8A%80%E6%9C%AF/a.html"`, `"/frc_docs/"`) → `"技术/a.html"`；(`"/other/a.html"`, `"/frc_docs/"`) → `null`
  - `flattenDocs`：输入一棵两层的树，输出顺序和树一致，深层文档的 `trail` 等于 `["sec","deep"]`

- [ ] **Step 2: 运行，确认失败**
  Run: `node --test tests/`
  Expected: FAIL（找不到模块）

- [ ] **Step 3: 实现 `docs/_site/paths.js`**，外面用 IIFE 包一层，同时兼容 `window` 和 `module`。

- [ ] **Step 4: 运行，确认通过**
  Run: `node --test tests/`
  Expected: 全部 pass

- [ ] **Step 5: 实现框架页面**
  - `docs/index.html`：带完整的 `<!doctype html>`、`lang="zh-CN"`、charset 和 viewport；`<title>家长 Mentor 学习计划</title>`；Google Fonts 字体链接和第一部分一致；依次加载 `_site/shell.css`、`_site/manifest.js`、`_site/paths.js`、`_site/shell.js`；body 里只放静态骨架：顶栏（网站名链接到 `#/`，再加一个 `id="nav-toggle"` 的抽屉按钮，带 `aria-controls`/`aria-expanded`）、`<nav id="nav">`、`<main>`，`<main>` 里有 `id="home"`、`id="notfound"`、`id="missing-manifest"` 三个视图，以及 `<iframe id="doc" title="文档">`。
  - 首页视图里的文案：介绍段落沿用现有 `index.html` 的 lede；下面按顶层分组列出所有文档，每项显示标题、简介，以及 trail 拼成的"所在目录"小字。
  - 清单缺失视图的文案：`目录清单尚未生成。请在仓库根目录运行 python3 scripts/build_manifest.py 后刷新页面。`
  - 不存在视图的文案：`找不到这篇文档，它可能已被移动或删除。` 再加一个返回首页的链接。
  - `shell.js`：
    - `renderNav(tree)`：生成嵌套的 `<ul>`。目录用 `<button aria-expanded>` 控制折叠，展开状态存进 `localStorage` 的 `frcdocs.open`（一个路径数组），读写都包在 try/catch 中；文档项是 `<a href=hashFor(path)>`。
    - `route()`：监听 `hashchange` 事件，页面加载时也调用一次。
      - 首页：显示首页视图，`document.title` 设为网站名。
      - 找不到文档：显示不存在视图。
      - 找到文档：如果 iframe 当前不是这篇，就设置 `iframe.src = docHref(path)`；高亮对应的导航项（加 `aria-current="page"`）；展开它的所有祖先目录；把 `document.title` 设为"标题 · 网站名"；手机上关闭抽屉。
    - `iframe` 的 `load` 事件：用 try 读取 `contentWindow.location.pathname`，算出 `relativeToBase(…, baseDir(location.pathname))`。如果结果在清单中，且和当前 hash 不同，就用 `history.replaceState(null, "", hashFor(p))` 更新地址，再调用 `route()`。
  - `shell.css`：颜色变量用两套暗色定义（`prefers-color-scheme` 和 `[data-theme]`），`body` 设置背景色；顶栏高 56px；用 grid 布局，左侧导航 280px，右侧主区域；iframe 宽高 100%、无边框，主区域高度 `calc(100dvh - 56px)`；宽度 ≤ 860px 时，导航改为 fixed 抽屉，用 `[data-open]` 控制显示；可聚焦元素都有 `:focus-visible` 样式；尊重 `prefers-reduced-motion`。

- [ ] **Step 6: 浏览器验证**
  Run: `python3 scripts/build_manifest.py && python3 -m http.server -d docs 8765`（后台运行），然后为验证临时创建 `docs/zz-check/02-sec/03-深层/a b.html`（里面有指向 `../../../01-understanding-frc.html` 的链接；目录名不能以 `_` 开头，否则会被排除），重新生成清单；验证完删除这个目录，再重新生成一次清单。
  用 Playwright 依次检查：
  - 首页能列出两篇文档
  - 点开深层文档后，iframe 显示正常，导航展开到对应层级
  - 在 iframe 里点链接跳到第一篇后，网址栏 hash 变成 `#/01-understanding-frc.html`，导航高亮也跟着变
  - 打开 `#/nope.html` 显示不存在视图
  - 打开 `#/%E0%A4%A` 显示不存在视图，console 没有报错
  - 400px 宽度下抽屉能打开和关闭
  - 暗色模式截图一张
  Expected: 以上全部符合

- [ ] **Step 7: Commit**（先确认 `docs/zz-check` 已经删除）
  ```bash
  git add docs/index.html docs/_site/paths.js docs/_site/shell.js docs/_site/shell.css docs/01-understanding-frc.html tests/paths.test.js
  git commit -m "Add docs site shell with nav tree and iframe routing"
  ```

### Task 3: 部署流程和使用说明

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: `python3 scripts/build_manifest.py`、`python3 -m unittest discover -s tests`、`node --test tests/`

- [ ] **Step 1: 写 `.github/workflows/pages.yml`**
  - 触发条件：`push`（branches: `[main]`）和 `workflow_dispatch`
  - permissions：`contents: read`、`pages: write`、`id-token: write`
  - concurrency：group 设为 `pages`，`cancel-in-progress: false`
  - job `build`（ubuntu-latest）：`actions/checkout@v4` → `actions/setup-python@v5`（python-version 设为 `"3.12"`）→ `actions/setup-node@v4`（node-version 设为 `"22"`）→ 运行 `python3 -m unittest discover -s tests -v` → 运行 `node --test tests/` → 运行 `python3 scripts/build_manifest.py` → `actions/configure-pages@v5` → `actions/upload-pages-artifact@v3`（path 设为 `docs`）
  - job `deploy`：`needs: build`，environment 的 name 为 `github-pages`、url 为 `${{ steps.deployment.outputs.page_url }}`，使用 `actions/deploy-pages@v4`，`id: deployment`

- [ ] **Step 2: 验证 YAML 语法**
  Run: `ruby -ryaml -e 'p YAML.load_file(".github/workflows/pages.yml").keys'`
  Expected: 输出里包含 `"jobs"`（`on` 会被解析成 `true`，这是 YAML 的正常行为）

- [ ] **Step 3: 写 `README.md`**（中文，简短）：说明这个网站是什么；怎么添加文档（放进 `docs/` 任意层级；用数字前缀排序；可以加 `nav-title` 和 `description` 两个 meta；`_` 或 `.` 开头的会被排除）；本地预览命令；跑测试的命令；一次性的 Pages 设置（Settings → Pages → Source 选 GitHub Actions）

- [ ] **Step 4: Commit**
  ```bash
  git add .github/workflows/pages.yml README.md
  git commit -m "Add GitHub Pages workflow and README"
  ```
