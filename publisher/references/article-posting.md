# 文章发布（文章发表）

将 Markdown 文章发布到微信公众号，支持完整的格式。

## 用法

```bash
# 发布 Markdown 文章
${BUN_X} ./publisher/scripts/wechat-article.ts --markdown article.md

# 指定主题
${BUN_X} ./publisher/scripts/wechat-article.ts --markdown article.md --theme grace

# 禁用将普通外部链接转换为底部引用的功能
${BUN_X} ./publisher/scripts/wechat-article.ts --markdown article.md --no-cite

# 显式指定选项
${BUN_X} ./publisher/scripts/wechat-article.ts --markdown article.md --author "作者名" --summary "摘要"
```

## 参数

| 参数 | 说明 |
|-----------|-------------|
| `--markdown <path>` | 要转换并发布的 Markdown 文件 |
| `--theme <name>` | 主题：default、grace、simple、modern |
| `--no-cite` | 保留普通外部链接为内联，不转换为底部引用 |
| `--title <text>` | 覆盖标题（自动从 Markdown 提取） |
| `--author <name>` | 作者名 |
| `--summary <text>` | 文章摘要 |
| `--html <path>` | 预渲染的 HTML 文件（Markdown 的替代选项） |
| `--profile <dir>` | Chrome 配置文件目录 |

## Markdown 格式

```markdown
---
title: 文章标题
author: 作者名
---

# 标题（将成为文章标题）

带 **粗体** 和 *斜体* 的常规段落。

## 章节标题

![图片描述](./image.png)

- 列表项 1
- 列表项 2

> 引用文本

[链接文本](https://example.com)
```

Markdown 模式下，默认会将普通外部链接转换为底部引用，以生成对微信友好的输出。使用 `--no-cite` 可禁用此行为。

## 图片处理流程

1. **解析**：Markdown 中的图片被替换为 `WECHATIMGPH_N`
2. **渲染**：生成带占位符的 HTML
3. **粘贴**：将 HTML 内容粘贴到微信编辑器
4. **替换**：对每个占位符：
   - 找到并选中占位符文本
   - 滚动到可见区域
   - 按 Backspace 删除占位符
   - 从剪贴板粘贴图片

## 脚本

| 脚本 | 用途 |
|--------|---------|
| `publisher/scripts/wechat-article.ts` | 主文章发布脚本（浏览器） |
| `typography/scripts/md-to-wechat.ts` | Markdown 转 HTML（带占位符） |

## 示例会话

```
用户：/post-to-wechat --markdown ./article.md

Claude：
1. 解析 Markdown，发现 5 张图片
2. 生成带占位符的 HTML
3. 打开 Chrome，导航到微信编辑器
4. 粘贴 HTML 内容
5. 对每张图片：
   - 选中 WECHATIMGPH_1
   - 滚动到可见区域
   - 按 Backspace 删除
   - 粘贴图片
6. 报告："文章已组成，包含 5 张图片。"
```
