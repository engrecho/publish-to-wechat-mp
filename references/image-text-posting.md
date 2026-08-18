# 贴图发表（贴图发表，原名图文）

向微信公众号发布带多张图片的贴图内容。

> **注意**：微信已将公众号菜单中的"图文"重命名为"贴图"（截至 2026 年）。

## 用法

```bash
# 使用 Markdown 文件和图片目录发布（标题/内容自动提取）
${BUN_X} ./scripts/wechat-browser.ts --markdown source.md --images ./images/

# 显式指定标题和内容
${BUN_X} ./scripts/wechat-browser.ts --title "标题" --content "内容" --image img1.png --image img2.png

# 保存为草稿
${BUN_X} ./scripts/wechat-browser.ts --markdown source.md --images ./images/ --submit
```

## 参数

| 参数 | 说明 |
|--------|-------------|
| `--markdown <path>` | Markdown 文件，用于提取标题/内容 |
| `--images <dir>` | 包含图片的目录（按文件名排序） |
| `--title <text>` | 文章标题（最多 20 字，超长自动压缩） |
| `--content <text>` | 文章内容（最多 1000 字，超长自动压缩） |
| `--image <path>` | 单张图片文件（可重复使用） |
| `--submit` | 保存为草稿（默认：仅预览） |
| `--profile <dir>` | Chrome 配置文件目录 |

## 自动从 Markdown 提取标题/内容

使用 `--markdown` 时，脚本将：

1. **解析 frontmatter** 获取标题和作者：
   ```yaml
   ---
   title: 文章标题
   author: 作者名
   ---
   ```

2. **如果没有 frontmatter 标题则回退到 H1**：
   ```markdown
   # 这将成为标题
   ```

3. **标题过长时压缩至 20 字**：
   - 原文："如何在一天内彻底重塑你的人生"
   - 压缩后："一天重塑你的人生"

4. **提取前几段**作为内容（最多 1000 字）

## 图片目录模式

使用 `--images <dir>` 时：

- 目录中所有 PNG/JPG 文件都会被上传
- 文件按文件名字母顺序排序
- 命名规范：`01-cover.png`、`02-content.png` 等

## 限制

| 字段 | 最大长度 | 说明 |
|-------|------------|-------|
| 标题 | 20 字 | 过长时自动压缩 |
| 内容 | 1000 字 | 过长时自动压缩 |
| 图片 | 最多 9 张 | 微信限制 |

## 示例会话

```
用户：/post-to-wechat --markdown ./article.md --images ./xhs-images/

Claude：
1. 解析 Markdown 元数据：
   - 标题："如何在一天内彻底重塑你的人生" → "一天内重塑你的人生"
   - 作者：从 frontmatter 或默认值获取
2. 提取前几段作为内容
3. 在 xhs-images/ 中发现 7 张图片
4. 打开 Chrome，导航到微信"贴图"编辑器
5. 上传所有图片
6. 填写标题和内容
7. 报告："贴图已发布，包含 7 张图片。"
```

## 脚本

| 脚本 | 用途 |
|--------|---------|
| `wechat-browser.ts` | 主贴图发布脚本 |
| `cdp.ts` | Chrome DevTools Protocol 工具 |
| `copy-to-clipboard.ts` | 剪贴板操作 |
