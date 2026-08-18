# 远程 API 发布的服务器设置

本指南涵盖使用 `default_publish_method: remote-api` 时所需的服务器侧一次性设置。所有微信 API 的 HTTPS 调用将从配置的服务器的 IP 出口发出，因此微信的 IP 白名单必须包含该 IP。

此技能默认使用的服务器是 `62.234.16.218`（腾讯云，root 用户）。如有需要可替换为你自己的服务器。

## 微信 IP 白名单

微信公众号 API 会拒绝来自不在白名单上的 IP 的请求，返回 `errcode 40164`。在使用 `remote-api` 之前，请添加服务器的出口 IP：

1. 登录 https://mp.weixin.qq.com
2. 进入 设置与开发 → 基本配置
3. 找到"IP 白名单"
4. 添加 `62.234.16.218`（或你服务器的出口 IP）
5. 保存

如需验证服务器的出口 IP（以防与公网 IP 不同）：
```bash
ssh root@62.234.16.218 'curl -s https://ifconfig.me'
```

## 验证 SSH 可达性

本机必须能以非交互方式 SSH 到服务器（密码认证方式下，`sshpass` 处理交互提示；密钥认证方式下，密钥必须在 `ssh-agent` 中或未加密）。

快速检查：
```bash
ssh root@62.234.16.218 'echo ok'
```

如果挂起或失败，请先修复 SSH 连接问题再继续。

## 安装 sshpass（如使用密码认证）

`remote-api` 模式支持两种 SSH 认证方式：

- **SSH 密钥**（生产环境推荐）：在 EXTEND.md 中设置 `remote_publish_identity_file`。无需额外工具。
- **密码**（受信任的私有服务器可用）：在 EXTEND.md 中设置 `remote_publish_password`。需要本机安装 `sshpass`。

### macOS

由于安全考虑，`sshpass` 不在默认的 Homebrew tap 中。请通过第三方 tap 安装：

```bash
brew install hudochenkov/sshpass/sshpass
```

验证：
```bash
sshpass -V
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y sshpass
sshpass -V
```

### 其他 Linux 发行版

大多数发行版都有 `sshpass` 包。使用你系统的包管理器（`yum`、`dnf`、`pacman` 等）。

## 配置 EXTEND.md

完成上述步骤后，编辑 `.post-to-wechat/EXTEND.md`（项目级）或 `~/.post-to-wechat/EXTEND.md`（用户级）：

### 密码认证（快速开始）

```md
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_password: your_ssh_password
```

### SSH 密钥认证（生产环境推荐）

首先，配置基于密钥的 SSH 访问：
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_tencent -N ''
ssh-copy-id -i ~/.ssh/id_tencent.pub root@62.234.16.218
```

然后配置：
```md
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_identity_file: ~/.ssh/id_tencent
remote_publish_strict_host_key_checking: accept-new
```

如果同时设置了 `remote_publish_password` 和 `remote_publish_identity_file`，身份文件优先，密码被忽略。

## 安全注意事项

- **密码认证仅适用于受信任的私有服务器。** 密码以明文形式存储在 EXTEND.md 中 — 切勿提交到 git。推荐使用仓库外的用户级配置（`~/.post-to-wechat/EXTEND.md`），或使用 SSH 密钥。
- **生产环境推荐使用 SSH 密钥。** 每个服务器生成专用密钥，使用带密码的 `ssh-keygen`（和 `ssh-agent`），并定期轮换。
- **SSH 隧道仅转发原始 TCP。** 对 `api.weixin.qq.com` 的 TLS 验证仍由本地进程端到端执行；服务器无法拦截或解密微信 API 流量。
- **AppSecret 不会离开本地进程。** 服务器只看到发往 `api.weixin.qq.com` 的加密 TLS 字节。
- **如使用含密码的项目级配置，请将 `.post-to-wechat/` 添加到 `.gitignore`**：
  ```
  .post-to-wechat/
  ```

## 故障排除

| 问题 | 修复方法 |
|-------|-----|
| `errcode 40164`（IP 无效） | 服务器的出口 IP 不在微信白名单上。在公众号设置 → 基本配置 → IP 白名单 中添加。用 `ssh root@62.234.16.218 'curl -s https://ifconfig.me'` 验证出口 IP。 |
| `Permission denied (password)` | 密码错误，或服务器禁用了密码认证。用 `ssh root@62.234.16.218` 验证。检查 `/etc/ssh/sshd_config` 中的 `PasswordAuthentication yes`。 |
| `sshpass: command not found` | 安装 sshpass：`brew install hudochenkov/sshpass/sshpass`（macOS）/ `apt install sshpass`（Debian/Ubuntu）。或改用 `remote_publish_identity_file`。 |
| `SOCKS proxy on 127.0.0.1:... not ready` | SSH 无法建立隧道。检查主机可达性、凭据和 `StrictHostKeyChecking`。如果链路较慢，提高 `remote_publish_connect_timeout`。 |
| `Remote publish requires either remote_publish_password or remote_publish_identity_file` | 两种认证方式都未配置。在 EXTEND.md 中设置其中之一，或通过 `--remote-password` / `--remote-identity-file` CLI 标志传入。 |
