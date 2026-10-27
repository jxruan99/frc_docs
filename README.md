# 家长 Mentor 学习计划

写给想加入孩子高中 FRC 机器人队的家长的学习资料，以网站形式发布在 GitHub Pages：
https://jxruan99.github.io/frc_docs/

## 添加文档

把 HTML 文件放进 `docs/` 就行，子目录可以有任意层级。push 到 `main` 后，网站会自动更新，新文档出现在首页和左侧导航里。

- **排序**：在文件名或目录名前加数字前缀，例如 `02-怎么当mentor.html`、`03-技术方向/01-编程.html`。显示时会自动去掉前缀。
- **导航名称**：默认用文档的 `<title>`。标题太长时，可以在文档里加一个短名：
  ```html
  <meta name="nav-title" content="认识 FRC">
  ```
- **简介**：首页列表会显示 `<meta name="description" content="...">` 的内容。
- **不发布**：以 `_` 或 `.` 开头的文件和目录会被忽略，适合放草稿，例如 `_drafts/`。
- 文档之间可以用普通的相对链接互相跳转，比如 `<a href="../01-understanding-frc.html">`。

## 本地预览

```sh
python3 scripts/build_manifest.py
python3 -m http.server -d docs 8000
```

然后在浏览器里打开 http://localhost:8000/。

## 测试

```sh
python3 -m unittest discover -s tests -v
node --test "tests/*.test.js"
```

## 一次性设置

在 GitHub 仓库的 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。

## 目录结构

| 路径 | 作用 |
| --- | --- |
| `docs/` | 网站根目录，所有文档都放在这里 |
| `docs/index.html` | 首页框架 |
| `docs/_site/` | 框架的样式和脚本；`manifest.js` 是自动生成的，不提交 |
| `scripts/build_manifest.py` | 扫描 `docs/`，生成文档清单 |
| `.github/workflows/pages.yml` | 自动测试、生成清单并部署 |
| `design/` | 设计文档和实现计划，不发布 |
