# 更新日志

本文件记录 WeComHub 的版本变更。格式参考 Keep a Changelog，语言与仓库中文文档保持一致。

## [1.0.8] - 2026-10-02

修复

- **指令服务鉴权失败（403）**：v1.0.5 把令牌从 cfg 移除后，`wecom-hub-cmd.py` 仍只从 cfg 读令牌，而 cfg 里已没有令牌，导致所有指令返回 403。现在指令侧改为优先读取通知代理配置文件（用户实际填写处）的变量块，cfg 仅作兼容回退。
- **通知代理页面左上角图标缺失**：页面按 `plugins/dynamix/icons/<小写名>.png` 查找图标，插件未提供该文件。现新增 48x48 PNG 并随插件部署。

变更

- **通知正文与变量标签中文化**：推送到企业微信的正文改为中文（事件/重要性/标题/详情）；通知代理页面的变量名、说明文字改为中文。脚本内部注释仍保持英文，避免 shell 把中文当命令执行（v1.0.5 修复过的问题）。
- `RESTART_ALLOW_PREFIX` 等指令侧配置仍在插件页，与通知侧互不重叠。

## [1.0.7] - 2026-10-02

修复

- **从旧版升级上来的用户 Test 仍报 `{0}`**：v1.0.6 的安装钩子只在文件不存在时生成，但 v1.0.5 遗留的 agent 文件已存在且带字面 `{0}`，会被跳过。现增加兼容检测：`grep -q '^{0}$'` 命中则用模板重建（先备份为 `.bak-pre106`）。

变更

- 安装钩子改用插件内的 `agent-config-template.sh` 作为生成源，不再在 plg 里内嵌一份副本，彻底消除双份维护。

## [1.0.5] - 2026-10-02

修复

- **agent 脚本中文注释导致 Test 报错**：`scripts/notify-agent.sh` 的中文注释被 shell 当成命令执行（`command not found`）。Script 段与 Variables 全部改为英文，与官方 14 个 agent 一致（官方 agent 的 Variables 零中文）。

变更

- **配置来源分离**，各自只有一个入口，不再出现“改了一处另一处不生效”：
  - 通知（出）→ 设置 → 通知 → **通知代理** → WeComHub，存 agent 脚本变量块
  - 指令（入）→ 设置 → 通知 → **WeComHub**，存 `wecom.hub.cfg`
- **不再预置任何值**：变量块只留占位符，任何设备/用户安装后自行填写即可。
- 通知侧键（`RELAY_*` / `MIN_IMPORTANCE` / `ENABLE_NOTIFY`）从 cfg 模板与插件页移除。
- `wecom-hub-save.php` 保存时保留 cfg 中不属于本页的既有键，避免覆盖面。

## [1.0.4] - 2026-10-02

修复

- **通知代理页面空白**：「设置 → 通知 → 通知代理 → WeComHub」读不到任何配置项。根因是页面从所编辑的 `.sh` 文件里的 `####...####` 变量块读取变量（`NotificationAgents.page`），而插件部署的是不含变量块的转发壳。现改为部署带 `{0}` 占位与完整实现的脚本，与官方 agent 结构一致。
- `agents/WeComHub.xml` 与 `scripts/notify-agent.sh` 的脚本体保持单一真相源，避免两处漂移。

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

[1.0.8]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.8
[1.0.7]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.7
[1.0.6]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.6
[1.0.5]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.5
[1.0.4]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.4
[1.0.3]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.3
[1.0.2]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.2
[1.0.1]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.1
[1.0.0]: https://github.com/deltrivx/WeComHub/releases/tag/v1.0.0
