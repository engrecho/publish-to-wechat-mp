---
name: content-parser
description: 公众号内容流水线第一阶段：解析多来源内容为规范化中间产物。支持网页 URL、Markdown/HTML/纯文本文件，视频平台链接优先委托 vendor/all-platform-video-extract 解析，输出统一的 source.md。当用户提供原文链接或文件要求"解析内容/提取正文"时触发；在 gzh-pipeline 全流程中作为第一阶段。
---

# 内容解析器

## 概述

将任意来源的原始内容解析为统一的规范化 Markdown 中间产物（source.md），供后续改写、图片处理、排版阶段直接消费。

**视频平台链接（抖音/快手/B站/YouTube/TikTok/小红书/微博等）优先委托 [vendor/all-platform-video-extract/SKILL.md](vendor/all-platform-video-extract/SKILL.md) 解析**——它是上游 [all-platform-video-extract](https://github.com/engrecho/all-platform-video-extract) 的镜像，支持 1000+ 视频平台的标题、封面、下载直链提取，其解析/下载工作流以该 SKILL 为权威。

严格按以下顺序执行：

1. 识别来源类型并获取原始内容
2. 提取正文与元数据
3. 规范化为 Markdown
4. 提取并登记图片清单
5. 输出 source.md

## 目录结构

| 路径 | 作用 |
|------|------|
| `vendor/all-platform-video-extract/` | 上游 all-platform-video-extract 镜像，由 GitHub Action 每日自动同步，**禁止手工修改**（会被下次同步覆盖） |

## 支持的来源类型

| 来源类型 | 识别方式 | 获取方法 |
|---------|---------|---------|
| 视频平台链接 | 抖音/快手/B站/YouTube/TikTok/小红书/微博等分享文本或 URL | **走 [vendor/all-platform-video-extract/SKILL.md](vendor/all-platform-video-extract/SKILL.md) 流程**：`node vendor/all-platform-video-extract/scripts/video_extract.cjs "<分享文本或URL>"`，从结果提取标题、简介、封面登记进 source.md；用户要下载视频时用其 download_videos.cjs |
| 普通网页 URL | 以 http(s):// 开头 | 抓取页面，提取正文（剥离导航、广告、评论） |
| Markdown 文件 | 路径以 .md 结尾且存在 | 直接读取 |
| HTML 文件 | 路径以 .html 结尾且存在 | 读取后提取 body 正文 |
| 纯文本 | 非文件路径，或文件不存在 | 原样接收为文本 |

## 解析流程

### 1. 获取原始内容

- URL 抓取时保留正文中的图片地址（后续图片处理阶段需要）
- 公众号文章链接（mp.weixin.qq.com）注意提取正文内的图片、作者、发布信息
- 视频平台链接按上表委托 vendor 技能处理（分享文本需整段传入，不要只提取 URL）
- 拿不到正文时（反爬、需要登录），明确告知用户改用本地文件

### 2. 提取元数据

尽量从原文提取，缺失则留空：

| 字段 | 来源 |
|------|------|
| title | 原文标题 / 首个 H1 / 视频标题 |
| author | 原文作者 / 视频作者 |
| source_url | 原文链接（发布时可作为"阅读原文"） |
| source_platform | 微信公众号 / 博客 / 新闻站 / 视频平台等 |
| publish_date | 原文发布日期（如有） |

### 3. 规范化为 Markdown

- 统一标题层级：正文从 H2 开始（H1 留给最终标题）
- 去除原文中的订阅引导、广告、投票、推荐阅读等噪音内容
- 保留原文结构（段落、列表、表格、代码块、引用）
- 图片位置以 `![描述](url或本地路径)` 保留在原位

### 4. 提取图片清单

在 source.md 末尾附加机器可读的图片清单：

```markdown
<!-- images:
1. https://.../img01.jpg | 正文第2段后
2. https://.../img02.jpg | 正文第5段后
-->
```

### 5. 输出 source.md

写入工作目录（默认 `work/<slug>/source.md`），frontmatter 结构：

```markdown
---
title: 原文标题
author: 原文作者
source_url: https://...
source_platform: 微信公众号
parsed_at: YYYY-MM-DD
---

（规范化后的正文）
```

## 输出检查

输出 source.md 前自查：

- [ ] 正文完整，无导航/广告等噪音
- [ ] 标题层级规范（正文从 H2 开始）
- [ ] 图片全部登记在清单中
- [ ] frontmatter 元数据字段齐全（缺失的标 `unknown`）
- [ ] 纯文本输入已保存为文件而非仅存于内存
- [ ] 视频链接解析结果（标题/封面/简介）已进入 source.md 元数据

## 上游同步机制

- `.github/workflows/sync-upstream-skills.yml` 每日自动：拉上游 → `rsync --delete` 覆盖 vendor → 有变化才 commit + push（随后触发服务器自动部署）。
- vendor 是纯镜像，无本地注入层（区别于 4_theme-formator 的主题机制）。

## 注意事项

- 只做解析与规范化，不做任何改写或观点加工（那是 content-rewriter 的职责）
- 原文中的事实、数据、引用保持原样，不去核实也不修改
- 图片只登记不下载（下载与去重在 image-processor 阶段进行）
- vendor 技能的配置（下载目录、并行数等）按其 SKILL.md 的初始化流程走，与本阶段无关
