---
name: gzh-pipeline
description: 公众号内容生产全流程编排：解析内容 → 原创化改写（四层改写+原创性自检+标题/简介生成）→ 图片处理（去重+头图生成）→ 排版 → 发布。当用户要求端到端生产/发布一篇公众号文章，或提到"跑一遍完整流程/从原文到发布"时触发；单个阶段任务直接调用对应子技能。
version: 2.0.0
metadata:
  openclaw:
    requires:
      anyBins:
        - bun
        - npx
---

# 公众号内容生产流水线（总编排）

## 概述

本仓库是一条完整的公众号内容生产流水线，由 5 个阶段子技能 + 1 个总编排（本文件）组成。总编排负责**顺序调度、阶段间交付物验收、失败回退**；具体怎么做由各阶段子技能定义。

## 流水线总览

```
原文（URL / 文件 / 文本）
   │
   ▼
1_content-parser        ① 解析内容 → source.md（规范化 Markdown + 元数据 + 图片清单）
   │
   ▼
2_content-rewriter      ② 原创化改写 → rewritten.md（四层改写 + 原创自检 + 标题 + 简介）
   │
   ▼
3_image-processor       ③ 图片处理 → images/（去重后正文图 + cover.jpg 头图）
   │
   ▼
4_theme-formator       ④ 排版 → final.html（微信格式 HTML + 预览）
   │
   ▼
5_article-publisher    ⑤ 发布 → 公众号草稿箱（media_id + 后台链接）
```

> 目录统一按 `N_` 数字前缀排序：`1_`~`5_` 对应流水线 5 个阶段，序号即执行顺序，看目录名即可知道全流程。

## 目录结构

| 目录 | 职责 |
|------|------|
| `SKILL.md`（0_ 总编排） | 阶段调度、产物验收、失败回退 |
| `1_content-parser/` | 阶段①：解析内容 |
| `2_content-rewriter/` | 阶段②：原创化改写 + 原创检测 + 标题/简介生成（脚本在 `2_content-rewriter/scripts/`） |
| `3_image-processor/` | 阶段③：图片去重 + 头图生成 |
| `4_theme-formator/` | 阶段④：排版渲染（核心流程在 `4_theme-formator/vendor/gzh-design/SKILL.md`，本地主题在 `4_theme-formator/themes-local/`，注入脚本在 `4_theme-formator/scripts/`） |
| `5_article-publisher/` | 阶段⑤：发布（remote-api / api / browser，脚本在 `5_article-publisher/scripts/`，配置文档在 `5_article-publisher/references/`） |
| `server/` | 服务器端微信发布中转服务（含部署脚本 `server/deploy.sh` 与部署说明） |
| `work/<slug>/` | 单篇文章的工作目录（中间产物，不入库） |

## 编排规则

### 1. 工作目录

每篇文章一个独立工作目录 `work/<slug>/`（slug 取标题 2-4 个有意义词汇，中文翻译为英文，短横线连接）。所有中间产物写入该目录：

| 产物 | 产生阶段 | 消费阶段 |
|------|---------|---------|
| `source.md` | ① | ② |
| `rewritten.md` | ② | ③④⑤ |
| `images/`（含 cover.jpg） | ③ | ④⑤ |
| `final.html` + `final_预览.html` | ④ | ⑤ |

### 2. 阶段执行顺序

- **默认串行执行 ①→②→③→④→⑤**，前序产物验收通过才进入下一阶段
- 用户只要某一个阶段时，直接调用对应子技能（如"帮我改写"→ 2_content-rewriter），此时以用户提供的输入替代该阶段的常规上游产物
- 阶段②与③无数据依赖（改写不依赖图片处理结果），可并行；④⑤ 必须串行

### 3. 验收检查点（进入下一阶段前）

| 检查点 | 不过关的处理 |
|--------|-------------|
| ① source.md 无噪音、图片已登记 | 补充解析 |
| ② 原创自检三项指标达标（重复片段 0 / LCS<13 / 8-gram 重合率<20%） | 回②重改，最多 3 轮；仍不过走降级方案（见 2_content-rewriter） |
| ② 标题/简介已产出（10 候选评分选 1） | 必须产出才能进入③ |
| ③ 重复图已剔除、cover.jpg 已生成 | 回③补做 |
| ④ final.html 预览无溢出、无死链 | 回④修排版 |
| ⑤ 草稿保存成功（拿到 media_id） | 按 5_article-publisher 常见问题排查 |

### 4. 失败回退

- 任一阶段失败：优先在本阶段内修复重试（最多 3 次）
- 涉及上游产物的缺陷（如排版阶段发现文字错误）：回退到②修复 rewritten.md 后，**③④⑤ 中受影响的产物必须重新生成**
- 发布失败但草稿已创建：报告 media_id，不要重复发布（可能产生重复草稿）

### 5. 发布后动作（提醒用户）

- 草稿在公众号后台「内容管理 → 草稿箱」
- **原创声明验证**：后台尝试声明原创，若提示与已有文章相似，回到②针对相似文章加强改写后重新走 ④⑤
- 「阅读原文」链接指向原文 source_url（转载属性内容）

## 全流程调用示例

用户："把这篇 https://example.com/article 改写发布到公众号"

1. ① 1_content-parser：抓取 URL → `work/ai-job-impact/source.md`
2. ② 2_content-rewriter：四层改写 → 原创自检（`bun 2_content-rewriter/scripts/originality-check.ts`）→ 10 标题评分选 1 → 简介 → `work/ai-job-impact/rewritten.md`
3. ③ 3_image-processor：下载图片、pHash 去重、生成 900×383 封面 → `work/ai-job-impact/images/`
4. ④ 4_theme-formator：渲染 final.html + 预览
5. ⑤ 5_article-publisher：remote-api 方式存草稿，报告 media_id 与后台链接

## 环境要求

- Bun（`brew install oven-sh/bun/bun` 或 `npm install -g bun`）
- 发布配置 `.post-to-wechat/EXTEND.md`（详见 5_article-publisher/SKILL.md 与 5_article-publisher/references/）
- remote-api 方式需服务器 IP（62.234.16.218）已加入微信 IP 白名单

## 语言

使用用户的语言进行回复。技术标记（路径、标志、字段名）保持英文。
