---
name: first-time-setup
description: post-to-wechat 偏好设置的首次设置流程
---

# 首次设置

## 概述

当找不到 EXTEND.md 时，引导用户完成偏好设置。

**阻塞性操作**：此设置必须在其他任何工作流步骤之前完成。不得：
- 询问要发布的内容或文件
- 询问主题或发布方式
- 继续执行内容转换或发布

仅提问本设置流程中的问题，保存 EXTEND.md，然后继续。

## 设置流程

```
未找到 EXTEND.md
        |
        v
+---------------------+
| AskUserQuestion     |
| （所有问题）         |
+---------------------+
        |
        v
+---------------------+
| 创建 EXTEND.md      |
+---------------------+
        |
        v
    继续到步骤 1
```

## 问题

**语言**：使用用户的输入语言或已保存的语言偏好。

在一次调用中使用 AskUserQuestion 提出所有问题：

### 问题 1：默认主题

```yaml
header: "主题"
question: "文章转换的默认主题？"
options:
  - label: "default（推荐）"
    description: "经典布局 — 居中标题带边框，彩色背景上的白色 H2（默认：蓝色）"
  - label: "grace"
    description: "优雅风格 — 文字阴影、圆体卡片、精致引用（默认：紫色）"
  - label: "simple"
    description: "极简现代 — 不对称圆角、清爽留白（默认：绿色）"
  - label: "modern"
    description: "大圆角、胶囊式标题、宽敞布局（默认：橙色）"
```

### 问题 2：默认颜色

```yaml
header: "颜色"
question: "默认颜色预设？（未设置时使用主题默认值）"
options:
  - label: "主题默认（推荐）"
    description: "使用主题内置的默认颜色"
  - label: "blue"
    description: "#0F4C81 经典蓝"
  - label: "red"
    description: "#A93226 中国红"
  - label: "green"
    description: "#009874 翡翠绿"
```

注意：用户可选择"其他"输入任意预设名称（vermilion、yellow、purple、sky、rose、olive、black、gray、pink、orange）或十六进制值。

### 问题 3：默认发布方式

```yaml
header: "发布方式"
question: "默认发布方式？"
options:
  - label: "remote-api（推荐）"
    description: "快速，通过 SSH 将微信 API 调用隧道传输到 IP 在白名单上的服务器。默认服务器：62.234.16.218（root），可在 EXTEND.md 中编辑"
  - label: "api"
    description: "快速，需要 API 凭据（AppID + AppSecret）。注意：本机 IP 必须在微信白名单上"
  - label: "browser"
    description: "慢速，需要 Chrome 和登录会话"
```

如果用户选择了 `remote-api`，则提示输入 `remote_publish_host`（默认：`62.234.16.218`）、`remote_publish_user`（默认：`root`），以及 `remote_publish_password`（密码认证，通过 sshpass）或 `remote_publish_identity_file`（SSH 密钥认证，推荐）。这些也可以稍后在 EXTEND.md 中填写。引导用户查看 `./server-setup.md` 了解 IP 白名单和 sshpass 安装步骤。

### 问题 4：默认作者

```yaml
header: "作者"
question: "文章的默认作者名？"
options:
  - label: "无默认值"
    description: "留空，每篇文章单独指定"
```

注意：用户可能选择"其他"输入自己的作者名。

### 问题 5：开放评论

```yaml
header: "评论"
question: "默认开启文章评论？"
options:
  - label: "是（推荐）"
    description: "允许读者对文章进行评论"
  - label: "否"
    description: "默认关闭评论"
```

### 问题 6：仅粉丝可评论

```yaml
header: "仅粉丝"
question: "将评论限制为仅粉丝可评？"
options:
  - label: "否（推荐）"
    description: "所有读者都可以评论"
  - label: "是"
    description: "仅粉丝可以评论"
```

### 问题 7：保存位置

```yaml
header: "保存"
question: "偏好设置保存位置？"
options:
  - label: "项目级（推荐）"
    description: ".post-to-wechat/（仅当前项目）"
  - label: "用户级"
    description: "~/.post-to-wechat/（所有项目）"
```

## 保存位置

| 选择 | 路径 | 作用域 |
|--------|------|-------|
| 项目级 | `.post-to-wechat/EXTEND.md` | 当前项目 |
| 用户级 | `~/.post-to-wechat/EXTEND.md` | 所有项目 |

## 设置完成后

1. 如需要则创建目录
2. 写入 EXTEND.md
3. 确认："偏好设置已保存到 [path]"
4. 继续到步骤 0（加载已保存的偏好设置）
5. 如果选择了 `remote-api`，提醒："请参阅 ./server-setup.md 完成服务器侧配置（IP 白名单、SSH 可达性、sshpass 安装）"

## EXTEND.md 模板

### 单账号（默认）

```md
default_theme: [default/grace/simple/modern]
default_color: [预设名、十六进制值或留空使用主题默认]
default_publish_method: [remote-api/api/browser]
default_author: [作者名或留空]
need_open_comment: [1/0]
only_fans_can_comment: [1/0]
chrome_profile_path:

# 远程 API 发布 — 仅当 default_publish_method 为 remote-api
# 或计划通过 CLI --remote 时才需要填写。
# 默认服务器：62.234.16.218（root）。如有需要可替换。
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_port: 22
remote_publish_password:
remote_publish_identity_file:
remote_publish_known_hosts_file:
remote_publish_strict_host_key_checking:
remote_publish_connect_timeout:
remote_publish_proxy_jump:
```

明确不支持原始的 `ssh` / `scp` 选项；仅识别上述带类型的键。认证同时支持 SSH 密钥（`remote_publish_identity_file`，生产环境推荐）和密码（`remote_publish_password`，通过 sshpass，受信任的私有服务器可用）。如果同时设置，身份文件优先。

### 多账号

```md
default_theme: [default/grace/simple/modern]
default_color: [预设名、十六进制值或留空使用主题默认]

accounts:
  - name: [显示名称]
    alias: [短键，如 "main"]
    default: true
    default_publish_method: [remote-api/api/browser]
    default_author: [作者名]
    need_open_comment: [1/0]
    only_fans_can_comment: [1/0]
    app_id: [微信 App ID，可选]
    app_secret: [微信 App Secret，可选]
    # 远程 API 发布（可选，账号级覆盖全局设置）
    remote_publish_host:
    remote_publish_user:
    remote_publish_password:
    remote_publish_identity_file:
  - name: [第二个账号名称]
    alias: [短键，如 "ai-tools"]
    default_publish_method: [remote-api/api/browser]
    default_author: [作者名]
    need_open_comment: [1/0]
    only_fans_can_comment: [1/0]
```

## 后续添加更多账号

初次设置后，用户可通过编辑 EXTEND.md 添加账号：

1. 添加包含列表项的 `accounts:` 块
2. 将账号级设置（作者、发布方式、评论）移入各账号条目
3. 将全局设置（主题、颜色）保留在顶层
4. 每个账号需要唯一的 `alias`（用于 CLI `--account` 参数和 Chrome 配置文件命名）
5. 在主账号上设置 `default: true`

## 后续修改偏好设置

用户可直接编辑 EXTEND.md，或删除它以再次触发设置流程。
