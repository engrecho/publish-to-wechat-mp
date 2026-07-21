# Server Setup for Remote API Publishing

This guide covers the one-time server-side setup required when using `default_publish_method: remote-api`. All WeChat API HTTPS calls will egress from the configured server's IP, so WeChat's IP allowlist must include that IP.

The default server assumed by this skill is `62.234.16.218` (Tencent Cloud, root user). Replace with your own server if needed.

## WeChat IP Allowlist

WeChat's Official Account API rejects calls from IPs not on its allowlist with `errcode 40164`. Add the server's egress IP before using `remote-api`:

1. Log in to https://mp.weixin.qq.com
2. Go to 设置与开发 → 基本配置 (Basic Configuration)
3. Find "IP 白名单" (IP Allowlist)
4. Add `62.234.16.218` (or your server's egress IP)
5. Save

To verify the server's egress IP (in case it differs from the public IP):
```bash
ssh root@62.234.16.218 'curl -s https://ifconfig.me'
```

## Verify SSH Reachability

The local machine must be able to SSH into the server non-interactively (for password auth, `sshpass` handles the prompt; for key auth, the key must be in `ssh-agent` or unencrypted).

Quick check:
```bash
ssh root@62.234.16.218 'echo ok'
```

If this hangs or fails, fix SSH connectivity before proceeding.

## Install sshpass (if using password auth)

`remote-api` mode supports two SSH auth methods:

- **SSH key** (recommended for production): set `remote_publish_identity_file` in EXTEND.md. No extra tools needed.
- **Password** (acceptable for trusted private servers): set `remote_publish_password` in EXTEND.md. Requires `sshpass` installed locally.

### macOS

`sshpass` is not in the default Homebrew tap due to security concerns. Install via third-party tap:

```bash
brew install hudochenkov/sshpass/sshpass
```

Verify:
```bash
sshpass -V
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y sshpass
sshpass -V
```

### Other Linux

Most distributions package `sshpass`. Use your package manager (`yum`, `dnf`, `pacman`, etc.).

## Configure EXTEND.md

After completing the steps above, edit `.post-to-wechat/EXTEND.md` (project) or `~/.post-to-wechat/EXTEND.md` (user):

### Password auth (quick start)

```md
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_password: your_ssh_password
```

### SSH key auth (recommended for production)

First, set up key-based SSH access:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_tencent -N ''
ssh-copy-id -i ~/.ssh/id_tencent.pub root@62.234.16.218
```

Then configure:
```md
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_identity_file: ~/.ssh/id_tencent
remote_publish_strict_host_key_checking: accept-new
```

If both `remote_publish_password` and `remote_publish_identity_file` are set, the identity file takes precedence and the password is ignored.

## Security Notes

- **Password auth is acceptable only for trusted private servers.** The password is stored in plaintext in EXTEND.md — never commit it to git. Prefer the user-level config (`~/.post-to-wechat/EXTEND.md`) outside the repo, or use SSH keys.
- **SSH keys are recommended for production.** Generate a dedicated key per server, use `ssh-keygen` with a passphrase (and `ssh-agent`), and rotate periodically.
- **The SSH tunnel forwards raw TCP only.** TLS verification for `api.weixin.qq.com` is still performed end-to-end by the local process; the server cannot intercept or decrypt WeChat API traffic.
- **AppSecret never leaves the local process.** The server only sees encrypted TLS bytes destined for `api.weixin.qq.com`.
- **Add `.post-to-wechat/` to `.gitignore`** if using project-level config with passwords:
  ```
  .post-to-wechat/
  ```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `errcode 40164` (invalid IP) | The server's egress IP is not on WeChat's allowlist. Add it in 公众号设置 → 基本配置 → IP 白名单. Verify egress IP with `ssh root@62.234.16.218 'curl -s https://ifconfig.me'`. |
| `Permission denied (password)` | Wrong password, or password auth disabled on server. Verify with `ssh root@62.234.16.218`. Check `/etc/ssh/sshd_config` for `PasswordAuthentication yes`. |
| `sshpass: command not found` | Install sshpass: `brew install hudochenkov/sshpass/sshpass` (macOS) / `apt install sshpass` (Debian/Ubuntu). Or switch to `remote_publish_identity_file`. |
| `SOCKS proxy on 127.0.0.1:... not ready` | SSH could not establish the tunnel. Check host reachability, credentials, and `StrictHostKeyChecking`. Raise `remote_publish_connect_timeout` if the link is slow. |
| `Remote publish requires either remote_publish_password or remote_publish_identity_file` | Neither auth method is configured. Set one of them in EXTEND.md or via `--remote-password` / `--remote-identity-file` CLI flags. |
