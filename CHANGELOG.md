# 更新日志

本文件记录 WeComHub 的版本变更。格式参考 Keep a Changelog，语言与仓库中文文档保持一致。

## [1.0.3] - 2026-10-02

修复

- **插件页描述为空**：Unraid 插件管理器的「描述」列读的是 `plugins/<name>/README.md`，不是 plg 里的 `<CHANGES>`。之前没有这个文件，页面上只显示插件名。已新增并在构建时部署。
- **`rc.WeComHub` 日志时间戳空白**：`date +%F %T` 在 Unraid 的 busybox `date` 下会报 `extra operand`。改为 `+%Y-%m-%d %H:%M:%S`。
- **启动时抢 8181 端口**：旧实例尚未退出时会 `Address already in use`。启动前先回收旧进程并等待其退出。

新增

- **`restart` 支持 `*` 通配**：`RESTART_ALLOW_PREFIX` 设为 `*` 时允许重启任意容器，无需逐个配置。授权规则现为：空=禁用，`*`=任意，其他=前缀匹配。

## [1.0.2] - 2026-10-02

新增

- **通知代理定义**（`agents/WeComHub.xml`）：安装后出现在 `设置 → 通知 → 通知代理`，与内置代理同一入口，可填写变量并使用 Test 按钮。

修复

- 修复 `verify-release.sh` 的占位符正则不识别含数字的键名（如 `MD5_AGENTXML`）。
- 修复 txz 目录校验因 `grep -q` 提前退出触发 SIGPIPE（141）导致的误报。

## [1.0.1] - 2026-10-02

修复

- **指令服务契约**：固定 `POST /exec`（根路径 `/` 保留兼容）并统一返回 JSON `{"ok", "result"}`。
- **指令词汇**：增加中文别名表，中文与英文指令都可用。
- **restart 前缀白名单**：原先硬编码在环境变量里、UI 无法配置，迁移后会静默失效或不受控。现在可以在设置页配置「允许重启的容器名前缀」，留空即完全禁用（fail closed）。
- **容器名校验**：`str.isalnum()` 对中文返回 True，会放过非 ASCII 字符。现在显式限定 ASCII + `. _ -`。
- **fail closed**：未配置 `RELAY_PUSH_TOKEN` 时，指令服务拒绝全部请求，避免产生无鉴权的命令端点。
- **版本索引**：`versions/index.json` 原先只有 `latest_version`，而 `wecom-hub-update.php` 读的是 `latest`，导致检查更新恒失败。现两者都写，并让 updater 兼容两种写法。

新增

- 白名单指令：`status`、`array`、`disk`、`temp`、`docker`、`uptime`、`help` 及其中文别名。
- `tests/cmd-service-contract.py`：路径契约、鉴权、中文别名、restart 前缀约束、非法字符与响应码的契约测试（39 项）。
- `scripts/event-started.sh`：阵列启动事件钩子，保证开机自启（`rc.M` 不会遍历 `/etc/rc.d/rc.*`）。
- 卸载清理块：移除 rc 脚本、通知代理与事件钩子，保留用户配置。

## [1.0.0] - 2026-10-02

首个正式版本。把原本散落在 Unraid 上的两套企业微信脚本合并为标准插件，接入官方通知代理体系。

新增

- **通知代理定义**（`agents/WeComHub.xml`）：安装后出现在 `设置 → 通知 → 通知代理`，与内置代理同一入口，可填写变量并使用页面上的 Test 按钮。
- `WeComHub.page`：插件自身的配置页（中转地址、端口、推送令牌、本地指令端口、最低通知级别）。
- `wecom-hub-notify-agent.sh`：把 Unraid 系统通知经中转服务转发到企业微信，支持 `IMPORTANCE` 分级过滤，发送失败静默退出。
- `wecom-hub-cmd.py`：本地指令服务，监听 `LOCAL_CMD_PORT`，执行白名单只读查询，令牌使用常量时间比较。
- `scripts/rc.WeComHub`：常驻服务的启停脚本，**不依赖 `/boot/config/go`**。
- `scripts/notify-agent.sh`：dynamix notification agent 的转发副本，便于单一维护点。
- `scripts/build-release.sh` / `scripts/verify-release.sh`：构建与产物校验。
- `.github/workflows/verify.yml`：Shell 语法、PHP lint、XML 合法性、真实凭据扫描。
- `.github/workflows/build-release.yml`：打 `v*` tag 时云端构建 `wecom.hub.plg` 与 `WeComHub-<版本>.txz` 并挂到 Release。
- 文档：README、README.en、PLUGIN-README、DEVELOPMENT、RELEASES、ABOUT、SECURITY、SUPPORT、CONTRIBUTING、CHANGELOG、docs/configuration.md、docs/troubleshooting.md。

变更

- 迁移自旧方案 `/boot/config/plugins/dynamix/notifications/agents/WeCom.sh` + `.wecom.env`：配置从散落 env 文件改为统一 cfg + UI。
- 迁移自旧方案 `/boot/config/unraid-cmd/unraid_cmd.py` + user.scripts 常驻服务：由 `/etc/rc.d/rc.WeComHub` 接管启停。

安全

- 页面不回显已保存令牌，只提示「已设置/未设置」。
- 仓库与文档中所有敏感值一律占位符：`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。
- `verify.yml` 扫描 `sk-` / `ghp_` / `gho_` 前缀真实 token，命中即失败。
- 代码与归档不经本地构建上传，一律由 GitHub Actions 云端产出。

[1.0.3]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.3
[1.0.2]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.2
[1.0.1]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.1
[1.0.0]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.0
