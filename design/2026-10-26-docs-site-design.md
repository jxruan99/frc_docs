# 文档网站：自动发现 `docs/` 下的 HTML 文档

日期：2026-10-26

## 目标

`docs/index.html` 是网站首页。`docs/` 下任意层级子目录中的 HTML 文档都会被自动发现，并在首页框架里组成一个统一的网站。作者只需要往 `docs/` 里放 HTML 文件，不需要改首页，也不需要往文档里加任何代码。

## 约束

- 浏览器无法列出静态服务器上的目录，因此由构建脚本生成目录清单。
- 托管方式：GitHub Pages，由 GitHub Actions 在每次 push 到 `main` 时生成清单并部署。
- 文档保持独立：单独打开能正常显示，放进框架后样式也互不干扰。
- 不引入第三方依赖：脚本只用 Python 3 标准库，前端只用原生 JS/CSS。

## 方案

首页框架加 iframe（方案 A）。另外两个备选方案没有采用：部署时往每篇文档注入导航（B），样式容易冲突，部署产物也和源文件不一致；改用静态网站生成器（C），需要改变文档的写法。

## 目录结构

```
docs/                         网站根目录
  index.html                  首页框架
  _site/shell.css             框架样式
  _site/shell.js              框架逻辑
  _site/manifest.js           生成的清单，加入 .gitignore
  **/*.html                   文档
scripts/build_manifest.py     扫描脚本
tests/test_build_manifest.py  单元测试（unittest）
.github/workflows/pages.yml   部署流程
design/                       设计文档，不发布
```

## 扫描规则（`scripts/build_manifest.py`）

- 递归扫描 `docs/` 下的 `*.html`。
- 排除：根目录的 `index.html`；名称以 `_` 或 `.` 开头的文件或目录（包括其下所有内容）。子目录里的 `index.html` 不排除，作为普通文档处理。
- 文档字段：
  - `path`：相对 `docs/` 的路径，用 `/` 分隔，不做 URL 编码
  - `title`：依次取 `<meta name="nav-title" content>`、`<title>` 文本、去掉数字前缀和扩展名的文件名，取第一个非空的
  - `description`：取 `<meta name="description" content>`，没有则为空字符串
  - 只读取每个文件的前 64 KB，并做 HTML 实体解码，按 UTF-8 读取，遇到无法解码的字节时替换处理
- 目录字段：`name`（原始目录名）、`title`（去掉数字前缀后的目录名）、`children`。
- 数字前缀：开头匹配 `^\d+[-_. ]+` 的部分，显示时去掉；如果去掉后为空，就保留原名。
- 排序：同一层级里先排文档、后排目录，各自按原始名称自然排序（数字段按数值比较，其余部分不区分大小写）。
- 没有文档的目录不输出。
- 输出 `docs/_site/manifest.js`，内容为 `window.SITE_MANIFEST = <json>;`，其中 json 是根节点 `{"title": "", "children": [...]}`；子节点是 `{"type": "doc", ...}` 或 `{"type": "dir", ...}`，JSON 保留非 ASCII 字符。
- 命令行：`python3 scripts/build_manifest.py [--root docs] [--out docs/_site/manifest.js]`，结束时打印找到的文档数量。

## 首页框架

- `index.html` 依次加载 `_site/shell.css`、`_site/manifest.js`、`_site/shell.js`。
- 清单加载失败（`window.SITE_MANIFEST` 不存在）时，显示一段提示，说明如何运行扫描脚本。
- 顶栏：网站名，以及手机上用来打开导航抽屉的按钮。
- 侧边导航：树形结构；目录可以折叠，默认展开当前文档所在的路径，其余展开状态可以保留在 `localStorage` 里（读写都包在 try/catch 中）。当前文档高亮。宽度不超过 860px 时，导航变成抽屉。
- 路由：`location.hash`
  - 为空或 `#/`：首页视图，包含介绍文字，以及按目录分组的文档列表（标题 + 简介）。
  - `#/<path>`：如果 `<path>` 在清单中，就把 iframe 的 `src` 设为该路径，侧栏高亮，`document.title` 设为"文档标题 · 网站名"；否则显示"文档不存在"视图。
- iframe 加载后，尝试读取 `contentWindow.location.pathname`（同源时可以读到），换算成相对网站根目录的路径。如果它和当前 hash 不一致且在清单中，就用 `history.replaceState` 更新 hash 和侧栏高亮。因为跨源（例如通过 `file://` 打开）读取会失败，这一步包在 try/catch 中。
- iframe 占满顶栏以下的全部区域，由文档自己负责滚动。
- 主题：沿用第一部分的颜色变量，支持 `prefers-color-scheme` 和 `data-theme` 两种方式。

## 部署

`.github/workflows/pages.yml`：在 push 到 `main` 或手动触发时运行，依次执行 checkout → setup-python → `python3 scripts/build_manifest.py` → `actions/upload-pages-artifact`（path: `docs`）→ `actions/deploy-pages`。需要的权限：`pages: write`、`id-token: write`。一次性设置：在仓库 Settings → Pages → Source 中选择 GitHub Actions。

## 测试

- 单元测试（`python3 -m unittest`）覆盖：多层嵌套；排除规则；标题回退顺序；description 提取；实体解码；自然排序；去掉数字前缀；空目录不输出；输出格式。
- 手动验证：本地运行 `python3 -m http.server -d docs`，检查首页列表、打开文档、子目录里的文档、文档内相对链接跳转后 hash 是否同步、不存在的路径、手机宽度、深色模式。

## 不做的事

计划中但尚不存在的文档占位、上一篇/下一篇导航、全文搜索、SEO 相关处理。
