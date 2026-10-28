# codex-account

一个只有 Python 标准库依赖的本机 Codex 账号切换工具。保存多个账号，按名字切换，并在切换时停止旧后台服务，避免重新打开 CLI 后仍显示上一个账号。

A small local account switcher for Codex CLI. Save accounts under names, switch explicitly or cycle through them, and stop the shared daemon before replacing credentials.

## 安装 / Install

需要 **Python 3.11+**、Codex CLI，以及 Linux、macOS 或 WSL。暂不支持原生 Windows Python；Windows 用户请在 WSL 中运行。

```bash
git clone https://github.com/huangsiyuan924/codex-account.git
cd codex-account
./install.sh
```

安装到 `~/.local/bin/codex-account`。如果终端找不到命令，把该目录加入 `PATH`：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Requires Python 3.11+, Codex CLI and Linux/macOS/WSL. Run `./install.sh` and ensure `~/.local/bin` is on your `PATH`. No pip packages are required.

## 开始使用 / Quick start

已登录 Codex 的用户，先保存当前账号：

```bash
codex-account save personal
codex-account add work
codex-account work
codex
```

`add work` 会调用 `codex login`，在浏览器登录新账号并保存；添加成功后再运行 `codex-account work` 切换。尚未登录过 Codex 的用户可以直接从 `add personal` 开始。

Save your existing login with `save personal`, then use `add work` to sign in to another account. Adding an account leaves the active `auth.json` unchanged. Switch with `codex-account work`, then start Codex again.

## 命令 / Commands

| 命令 | 功能 |
| --- | --- |
| `codex-account save NAME` | 保存当前 `auth.json` 为指定名字 / Save the current login |
| `codex-account add NAME` | 浏览器登录并保存新账号 / Sign in and save a new account |
| `codex-account import NAME FILE` | 从本机认证 JSON 文件导入 / Import an existing local auth file |
| `codex-account NAME` | 切换账号 / Switch accounts |
| `codex-account` 或 `codex-account toggle` | 按列表顺序轮换 / Cycle through accounts |
| `codex-account list` | 列出账号，`*` 表示当前认证文件匹配的账号 / List saved accounts |
| `codex-account status` | 查看当前认证文件匹配的账号 / Show the configured account |
| `codex-account login NAME` | 重新登录该账号并切换 / Renew a saved login and activate it |
| `codex-account --help` | 查看帮助 / Show help |

名字以英文字母开头，可包含数字、下划线和连字符，最长 32 位。命令名不能作为账号名。再次添加同名账号或重复的账号会报错，避免覆盖。

导入示例（文件路径，请勿把令牌直接写在命令行）：

```bash
codex-account import other /path/to/auth.json
```

## 凭据和后台服务 / Credentials and daemon

- 默认使用 `~/.codex`；设置 `CODEX_HOME` 可指定其他目录。
- 账号保存在 `$CODEX_HOME/accounts/NAME.json`，新目录权限为 `700`，认证文件为 `600`。通过临时文件和原子替换写入，并对本工具的并发操作加锁。
- 切换前保存当前账号的凭据，包括正常使用时更新的令牌。程序也会重新检查后台停止时写回的凭据，以免把它们归到错误的账号。
- 切换调用 `codex app-server daemon stop`。**请先结束其他终端里的 Codex 任务**，因为它会停止共享后台服务。已启动的独立进程也需要退出后重新运行。
- `status` 和列表星号反映磁盘文件，不检查正在运行的进程或在线验证登录有效性。过期且无法刷新的账号用 `login NAME` 重新登录。
- 只支持文件认证。若配置了其他存储方式，请先在 `config.toml` 中设置 `cli_auth_credentials_store = "file"`。环境变量提供的认证或管理员强制配置可能覆盖文件，应由用户在启动 Codex 前处理。
- 原双账号脚本的 `auth_main.json`、`auth_l.json` 仍可作为 `huang`、`li` 读取；新安装没有这些文件也能正常使用。

Credentials stay in local files and must be treated like passwords. Never commit or share them. This repository contains no working credentials. `add` and `login` delegate authentication to Codex; the tool does not implement its own OAuth flow. Native keyring and ephemeral authentication are not supported.

The shared daemon is stopped during a switch, so finish work in other Codex terminals first. Processes started independently must also be restarted. `status` reports the configured file, not a live server account. Expired or revoked credentials require `login NAME`.

See the [official OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth) for credential storage and login behavior. This is an independent community tool, not an official OpenAI project.

## 开发 / Development

```bash
python3 -m unittest discover -s tests -v
```

Tests use temporary directories and a fake `codex` executable. They do not read real logins, connect to OpenAI or stop an actual daemon. GitHub Actions runs the suite on Linux and macOS.

## 许可证 / License

[MIT](LICENSE)
