# GZH Pipeline — 公众号内容生产流水线

从原文到公众号草稿的端到端流水线：**解析内容 → 原创化改写 → 图片处理 → 排版 → 发布**。

由 1 个总编排 skill + 5 个阶段 skill 组成，每个阶段独立可用，也可整链串行。

## 目录结构

```
├── SKILL.md                  # 0_ 总编排：阶段调度、产物验收、失败回退
├── 1_content-parser/         # ① 解析内容：URL/文件/文本 → source.md
├── 2_content-rewriter/       # ② 原创化改写：四层改写 + 原创自检 + 标题/简介生成
│   └── scripts/              #    originality-check.ts 原创性自检
├── 3_image-processor/        # ③ 图片处理：感知哈希去重 + 头图生成（900×383）
├── 4_theme-formator/         # ④ 排版：Markdown → 微信友好 HTML
│   ├── vendor/gzh-design/    #    上游 gzh-design-skill 镜像（GitHub Action 每日自动同步）
│   └── themes-local/         #    本地自建主题（同步不覆盖）
├── 5_article-publisher/      # ⑤ 发布：remote-api / api / browser → 公众号草稿箱
│   ├── scripts/              #    wechat-api.ts 等发布脚本与测试
│   └── references/           #    发布配置与服务器设置参考文档
├── server/                   # 微信发布中转服务（部署脚本 + 说明）
└── work/<slug>/              # 单篇文章工作目录（中间产物，不入库）
```

> 阶段目录按 `N_` 数字前缀排序，序号即执行顺序：`1_` 解析 → `2_` 改写 → `3_` 图片 → `4_` 排版 → `5_` 发布。

## 快速开始

### 1. 环境准备

```bash
# 安装 Bun
brew install oven-sh/bun/bun   # 或 npm install -g bun

# 发布配置（项目级或用户级）
mkdir -p .post-to-wechat && cat > .post-to-wechat/EXTEND.md <<'EOF'
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_identity_file: ~/.ssh/id_tencent
remote_publish_strict_host_key_checking: accept-new
EOF
```

remote-api 方式需先完成服务器侧配置（微信 IP 白名单等），见 `5_article-publisher/references/server-setup.md`。

### 2. 全流程

把原文（URL / 文件 / 纯文本）交给总编排 skill（根 SKILL.md），按流水线产出：

| 中间产物 | 说明 |
|---------|------|
| `work/<slug>/source.md` | 解析后的规范化原文 |
| `work/<slug>/rewritten.md` | 改写稿（含 title/summary/cover frontmatter） |
| `work/<slug>/images/` | 去重后正文图 + cover.jpg 头图 |
| `work/<slug>/final.html` | 微信格式 HTML（另有 final_预览.html） |
| 公众号草稿 | 发布结果（media_id + 后台链接） |

### 3. 单独使用某阶段

每个子目录都是独立 skill，单独触发即可，例如只要改写：

```
用户提供原文 → 2_content-rewriter → 改写稿 + 原创自检报告 + 标题 + 简介
```

## 原创性检测说明

微信没有公开的原创检测查询 API（检测发生在发布/声明原创时，由平台自动比对全网已声明原创内容）。本项目采用四层防护：

1. **预防**：2_content-rewriter 的四层改写（观点层为主，杜绝纯同义词替换式洗稿）
2. **本地自检**：`2_content-rewriter/scripts/originality-check.ts`（发布前代理指标）

   ```bash
   bun 2_content-rewriter/scripts/originality-check.ts work/<slug>/source.md work/<slug>/rewritten.md
   ```

   通过标准：≥13 字连续重复片段 0 个、最长公共子串 < 13 字、8-gram 重合率 < 20%

3. **发布后验证**：后台尝试声明原创，提示相似则回改写阶段加强
4. **降级方案**：多次不过则不声明原创按转载发布（保留原文链接）

## 发布方式

| 方式 | 说明 |
|------|------|
| remote-api（默认） | API 调用经 SSH SOCKS5 隧道从白名单服务器出口 |
| api | 本机 IP 在白名单时直连 |
| browser | Chrome 会话模拟（贴图发布） |

详见 `5_article-publisher/SKILL.md`。

## 服务器与部署

- 部署面板：https://deploy.bajiaolu.cn（部署详情见 deploy-system skill）
- GitHub Webhook 推送 main 分支自动部署（deploy-system 原生支持，无需额外配置）
- server 中转服务部署：见 `server/README.md`

## 更多文档

- 各阶段用法：对应子目录的 SKILL.md
- API 凭据：`5_article-publisher/references/api-setup.md`
- 服务器设置：`5_article-publisher/references/server-setup.md`
- 多账号：`5_article-publisher/references/multi-account.md`
