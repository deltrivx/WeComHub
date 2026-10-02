# 开发约定

## 构建与发布

- **禁止本地构建后上传**。所有 `plg` / `txz` 由 `.github/workflows/build-release.yml` 在云端生成并挂到 Release。
- 本地 `scripts/build-release.sh` 仅用于自测；产物在 `dist/`，已加入 `.gitignore`。
- 发布流程：更新 `RELEASES.md` → 提交 → 打 `v*` tag → Actions 自动构建。

## 配置安全

- 仓库与文档中**不得出现真实凭据**。地址/端口/令牌一律用占位符：
  `RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。
- `verify.yml` 会扫描疑似真实 token（`sk-` / `ghp_` / `gho_` 前缀），命中即失败。
- 页面不回显已保存令牌；仅提示"已设置"。

## 命令执行安全

- `wecom-hub-cmd.py` 只执行白名单命令，不拼接任意 shell。
- `restart` 受 `RESTART_ALLOW_PREFIX` 前缀限制，且校验容器名字符集。
- 令牌比较使用常量时间比较。

## 文件布局

| 路径 | 作用 |
| --- | --- |
| `agents/WeComHub.xml` | 通知代理定义（渲染到 设置 → 通知 → 通知代理） |
| `WeComHub.page` | 插件自身配置页 |
| `wecom-hub-save.php` | 保存配置 |
| `wecom-hub-notify-agent.sh` | 通知转发 |
| `wecom-hub-cmd.py` | 本地指令服务 |
| `scripts/event-started.sh` | 阵列启动事件钩子（开机自启） |
| `scripts/rc.WeComHub` | 服务启停（不依赖 `/boot/config/go`） |
| `wecom.hub.cfg` | 配置模板（占位值） |
| `wecom.hub.plg` | 插件描述（构建时替换版本/MD5） |
| `scripts/build-release.sh` | 构建（云端调用） |
| `scripts/verify-release.sh` | 产物校验 |


## 版本号规则（重要）

Unraid 插件安装器用 `strcmp()` 比较版本字符串，**不是**语义化版本比较：

```php
// dynamix.plugin.manager/scripts/plugin:730
if (strcmp($version, $installed_version) < 0) {
    write("plugin: not installing older version\n");
```

因此 `1.0.10` 会被判定为比 `1.0.8` **旧**（第 5 位 `1` < `8`），升级被拒绝。

**规则**：补丁号达到两位数时，必须提升次版本号：

| 当前版本 | 错误（被拒） | 正确（可升级） |
| --- | --- | --- |
| `1.0.8` | `1.0.10` | `1.1.0` |
| `1.0.9` | — | `1.1.0` |

发版前务必确认新版本号 `strcmp` 大于所有已发布版本。
