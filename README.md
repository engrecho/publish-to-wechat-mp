# GZH Pipeline — 公众号内容生产流水线

从原文到公众号草稿的端到端流水线：**解析内容 → 原创化改写 → 图片处理 → 排版 → 发布**。

由 1 个总编排 skill + 5 个阶段 skill 组成，每个阶段独立可用，也可整链串行。

## 目录结构

```
├── SKILL.md                  # 0_ 总编排：阶段调度、产物验收、失败回退
├── 1_content-parser/         # ① 解析内容：URL/文件/文本 → source.md
│   └── vendor/               #    all-platform-video-extract 镜像（视频链接解析）
├── 2_content-rewriter/       # ② 原创化改写：四层改写 + 原创自检 + 标题/简介生成
│   └── scripts/              #    originality-check.ts 原创性自检
├── 3_image-processor/        # ③ 图片处理：感知哈希去重 + 头图生成（900×383）
├── 4_theme-formator/         # ④ 排版：Markdown → 微信友好 HTML
│   ├── vendor/gzh-design/    #    上游 gzh-design-skill 镜像（GitHub Action 每日自动同步）
│   ├── themes-local/         #    本地自建主题（同步不覆盖）
│   └── scripts/              #    inject-local-themes.py 本地主题注入
├── 5_article-publisher/      # ⑤ 发布：remote-api / api / browser → 公众号草稿箱
│   ├── scripts/              #    wechat-api.ts 等发布脚本与测试
│   └── references/           #    发布配置与服务器设置参考文档
├── .github/workflows/        #    sync-upstream-skills.yml 上游技能每日自动同步
├── server/                   # 微信发布中转服务（部署脚本 + 说明）
└── work/<slug>/              # 单篇文章工作目录（中间产物，不入库）
```

> 阶段目录按 `N_` 数字前缀排序，序号即执行顺序：`1_` 解析 → `2_` 改写 → `3_` 图片 → `4_` 排版 → `5_` 发布。

## 各环节工作原理

每篇文章一个独立工作目录 `work/<slug>/`，阶段间通过文件交付物衔接：上一阶段的输出就是下一阶段的输入，总编排负责验收每个检查点。

### ① 1_content-parser — 解析内容

**输入**：网页 URL / Markdown / HTML / 纯文本 / 视频平台分享链接。**输出**：`work/<slug>/source.md`。

工作过程：

1. **识别来源类型**：视频平台链接（抖音/快手/B站/YouTube/TikTok/小红书/微博等）委托 `vendor/all-platform-video-extract` 的解析脚本（`video_extract.cjs`）提取标题、封面、简介；普通网页则抓取正文并剥离导航、广告、评论等噪音。
2. **提取元数据**：title、author、source_url、source_platform、publish_date 写入 frontmatter，缺失标 `unknown`。
3. **规范化 Markdown**：正文标题统一从 H2 开始（H1 留给最终标题），保留段落/列表/表格/代码块/引用结构，图片以 `![](url)` 保留原位。
4. **登记图片清单**：文末附加机器可读的 `<!-- images: ... -->` 注释清单，供阶段③消费。

本阶段只解析不改写，原文事实与数据保持原样。

### ② 2_content-rewriter — 原创化改写

**输入**：`source.md`。**输出**：`work/<slug>/rewritten.md`（frontmatter 含 title / summary / cover）。

工作过程（固定顺序，不可跳步）：

1. **理解原文核心**：核心观点、论证逻辑、目标读者、情绪基调。
2. **四层深度改写**：观点层（加入独有评论/案例/结论，决定性）→ 结构层（重组段落顺序、重拟小标题）→ 句式层（拆并句、换视角）→ 词汇层（同义替换，仅辅助）。
3. **原创性自检**：`bun 2_content-rewriter/scripts/originality-check.ts` 比对 source 与 rewritten——≥13 字连续重复片段 0 个、最长公共子串 < 13 字、8-gram 重合率 < 20%。不过关回第 2 步重改（最多 3 轮，仍不过走降级方案按转载发布）。
4. **标题生成**：10 个候选标题，五维度评分选出 1 个最佳。
5. **简介生成**：写入 frontmatter。

### ③ 3_image-processor — 图片处理

**输入**：`source.md` 的图片清单。**输出**：`work/<slug>/images/`（去重正文图 + cover.jpg）。

工作过程：

1. **下载全部图片**：按正文出现顺序命名 `img01.jpg`…，下载失败记录跳过，SVG 等微信不支持的格式转 PNG 或剔除。
2. **感知哈希去重**：aHash 粗筛 + pHash 主判 + dHash 辅助，汉明距离 ≤ 5 判重只留一张；URL/MD5 相同直接判重。同步删除改写稿中指向被剔除图片的引用。
3. **选图排序**：按主题相关度、横向构图、分辨率 ≥ 900×383、主体居中评估封面素材适配度。
4. **头图生成**：产出 900×383（2.35:1）的 `cover.jpg`。

### ④ 4_theme-formator — 排版

**输入**：`rewritten.md` + `images/`。**输出**：`work/<slug>/final.html`（+ 可直接浏览器打开的 `final_预览.html`）。

工作过程（调度层声明见 `4_theme-formator/SKILL.md`，核心流程以 `vendor/gzh-design/SKILL.md` 为权威）：

1. **输入校验**：frontmatter 完整、封面存在、正文图片引用无失效。
2. **非 Markdown 输入先归一**（docx/PDF/纯文本按 format-normalize 规则转 Markdown）。
3. **主题选择**：读 `vendor/gzh-design/references/theme-index.md`（已含上游 6 套主题 + themes-local 注入的本地主题），按题材推荐并让用户确认。
4. **组件化渲染**：从对应主题组件库取引言卡、章节标题、正文标记、签名区等 HTML 组件（不凭记忆手写），代码块/图片/小标签标题走通用增量库。
5. **关键词下划线标记**：每段主动标 1–3 个核心短语（该 skill 的核心特色）。
6. **输出校验**：微信 820px 正文宽度无横向溢出、无死链、内联样式（微信不支持外链 CSS/JS）。

### ⑤ 5_article-publisher — 发布

**输入**：`final.html` + `images/`。**输出**：公众号草稿箱草稿（media_id + 后台链接）。

三种发布方式：

| 方式 | 原理 |
|------|------|
| remote-api（默认） | API 调用经 SSH SOCKS5 隧道从白名单服务器（62.234.16.218）出口，绕开本机 IP 不在白名单的限制 |
| api | 本机 IP 已在白名单时直连微信 API |
| browser | Chrome 会话模拟，粘贴富文本与图片发布 |

发布只存草稿不直接群发，原创声明在后台人工验证——若提示与已有文章相似，回到阶段②加强改写后重走④⑤。

## 上游技能自动同步

两个阶段引入了外部 skill 作为 vendor 镜像，`.github/workflows/sync-upstream-skills.yml` 每天（北京时间 11:00）自动同步：

| vendor | 上游 | 本地扩展 |
|--------|------|---------|
| `1_content-parser/vendor/all-platform-video-extract/` | [engrecho/all-platform-video-extract](https://github.com/engrecho/all-platform-video-extract)（视频链接解析） | 无（纯镜像） |
| `4_theme-formator/vendor/gzh-design/` | [isjiamu/gzh-design-skill](https://github.com/isjiamu/gzh-design-skill)（排版主题组件库） | `themes-local/` 本地主题，同步后由 `inject-local-themes.py` 幂等注入 |

同步机制：拉上游 → `rsync --delete` 覆盖 vendor → 注入本地主题（仅阶段④）→ 有变化才 commit + push → 触发服务器自动部署。**vendor 目录禁止手工修改**（会被下次同步覆盖），本地定制一律走 `themes-local/`。

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
