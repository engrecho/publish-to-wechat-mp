---
name: typography
description: 公众号排版。将改写稿 Markdown 渲染为微信友好 HTML：主题与颜色配置、外部链接转底部引用、代码块/表格/图片适配微信显示。当用户要求"排版/渲染 HTML/预览样式/选主题"时触发；在 gzh-pipeline 流程中作为第四阶段。
---

# 公众号排版器

## 概述

将 content-rewriter 输出的 rewritten.md（含图片处理后的图片引用）渲染为可直接发布到微信公众号的 HTML，严格按以下顺序执行：

1. 读取排版输入（rewritten.md + images/）
2. 确定主题与颜色
3. 渲染为微信格式 HTML
4. 输出 final.html 与预览

## 排版输入约定

| 输入 | 来源 | 必需 |
|------|------|------|
| rewritten.md | content-rewriter 输出（frontmatter 已含 title / summary / cover） | 是 |
| images/ 目录 | image-processor 输出（含去重后正文图 + cover.jpg） | 是 |

## 排版流程

### 1. 校验输入

- rewritten.md 存在且 frontmatter 完整（title / summary / author / cover）
- frontmatter 中引用的封面文件存在
- 正文引用的图片均在 images/ 目录中，无失效引用

### 2. 确定主题与颜色

优先级：CLI 参数 → frontmatter → EXTEND.md → 默认值（确定后不要反复询问）。

**主题**（4 选 1）：

| 主题 | 风格 |
|------|------|
| default | 默认微信风 |
| grace | 优雅 |
| simple | 极简 |
| modern | 现代 |

**颜色预设**：blue、green、vermilion、yellow、purple、sky、rose、olive、black、gray、pink、red、orange（或十六进制值）。

### 3. 渲染 HTML

使用仓库根目录的渲染脚本（不要手工拼 HTML）：

```bash
bun ./scripts/md-to-wechat.ts <rewritten.md> [--theme <theme>] [--color <color>]
```

**Markdown 引用默认行为**：普通外部链接自动转换为底部引用（对微信友好）；用户明确要求保留内联链接时加 `--no-cite`。

**渲染规则**：

- 标题层级映射为微信样式（H2 → 小节标题，H3 → 小节内标题）
- 代码块等宽字体渲染，长代码横向滚动
- 表格转为微信兼容样式
- 图片转 `<img>` 标签（发布阶段会上传微信素材库替换为微信图床地址）

### 4. 输出与预览

- 输出 `work/<slug>/final.html`
- 同时生成 `final_预览.html`（浏览器可直接打开预览，不发布也能看效果）
- 输出排版报告：主题/颜色、字数、图片数、引用数

## 输出检查

- [ ] final.html 在 820px 宽度下（微信正文宽度）无横向溢出
- [ ] 代码块、表格、引用块显示正常
- [ ] 外部链接已转底部引用（除非用户要求保留）
- [ ] 图片全部有占位/引用，无死链
- [ ] 标题、摘要、封面与 rewritten.md frontmatter 一致

## 注意事项

- 只做排版，不改动文字内容——发现错别字等问题时报告给调用方，由 content-rewriter 阶段修复
- 切勿把 Markdown 预转成 HTML 再喂给渲染脚本（发布阶段对图片的处理逻辑会冲突）
- 微信不支持外链 CSS/JS，HTML 必须内联样式
