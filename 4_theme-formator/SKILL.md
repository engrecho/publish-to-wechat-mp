---
name: theme-formator
description: 公众号排版。将改写稿 Markdown 渲染为微信友好 HTML。排版核心流程与主题组件库以 vendor/gzh-design（gzh-design-skill）为权威来源，本地自建主题经 themes-local/ 注入合并。当用户要求"排版/渲染 HTML/预览样式/选主题"时触发；在 gzh-pipeline 流程中作为第四阶段。
---

# 公众号排版器（调度层）

## 概述

本 SKILL 是**调度入口**，不是排版实现。排版的核心流程、主题组件库、渲染规范一律以 vendor 镜像为准：

> **优先执行 [vendor/gzh-design/SKILL.md](vendor/gzh-design/SKILL.md)**（上游 gzh-design-skill 的完整排版工作流）。

本目录在此基础上叠加一层**本地主题机制**：`themes-local/` 存放自建主题，经注入脚本与 vendor 合并后，vendor 的 theme-index 即包含全部主题（上游 + 本地），排版时无差别选用。

## 目录结构

| 路径 | 作用 |
|------|------|
| `vendor/gzh-design/` | 上游 [gzh-design-skill](https://github.com/isjiamu/gzh-design-skill) 镜像，由 GitHub Action 每日自动同步，**禁止手工修改**（会被下次同步覆盖） |
| `themes-local/` | 本地自建主题（组件库文件 + 登记行），同步永不动它 |
| `themes-local/theme-index.rows.md` | 本地主题在 theme-index 中的登记行（格式说明见文件内注释） |
| `scripts/inject-local-themes.py` | 本地主题注入脚本：把 themes-local 的主题文件与登记行幂等合入 vendor 镜像 |

## 排版流程

1. **读 [vendor/gzh-design/SKILL.md](vendor/gzh-design/SKILL.md) 并严格按其流程执行**——输入校验、格式归一、主题选择、组件取用、下划线标记、输出校验，全部以它为准。
2. **主题选择时**：读 `vendor/gzh-design/references/theme-index.md`。该表已包含 `themes-local/` 注入的本地主题（表中可能同时存在上游主题与本地主题），按 SKILL.md 的推荐规则统一选择，本地主题没有特殊地位。
3. **用户要求新风格时**：走 `vendor/gzh-design/references/theme-generator.md` 的自定义主题生成流程，但产物落点改为：
   - 组件库文件 → `themes-local/theme-{英文标识}.md`（**不是** vendor 的 references/）
   - 登记行 → 追加到 `themes-local/theme-index.rows.md`
4. **登记后本地验证**：跑 `python3 4_theme-formator/scripts/inject-local-themes.py`（任意目录执行均可），确认本地主题出现在 vendor 的 references/ 和 theme-index 中（该操作幂等，可重复执行），再跑 `python3 4_theme-formator/vendor/gzh-design/scripts/component_lint.py 4_theme-formator/vendor/gzh-design` 确认 0 ERROR。

## 上游同步机制

- `.github/workflows/sync-upstream-skills.yml` 每日自动：拉上游 → `rsync --delete` 覆盖 vendor → 跑注入脚本合并本地主题 → 有变化才 commit + push（随后触发服务器自动部署）。该 workflow 同时负责 1_content-parser 的 vendor 同步。
- 因此 vendor 里**永远** = 上游最新版 + 本地主题，本地改动零丢失。

## 硬性约束

- **不要修改 vendor/ 下任何文件**——同步会覆盖。想改上游某套主题，复制为 `themes-local/theme-{标识}-local.md` 换新标识登记自己的版本。
- 排版产出与检查清单以 vendor SKILL.md 为准，本文件不重复维护。
- 微信不支持外链 CSS/JS，HTML 必须内联样式（同 vendor 约定）。
