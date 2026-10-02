# WeComHub

Unraid 企业微信中枢插件：**设置 → 通知** 可视化配置，把 Unraid 系统通知推送到企业微信，并支持企业微信指令反向交互。

## 功能

1. **通知出**：Unraid 系统通知（阵列/磁盘/容器/uptime 等）经中转转发到企业微信应用。
2. **指令入**：企业微信发指令，插件内本地服务接收并执行只读查询 / 容器重启，回传文本。
3. **接入方式**：在 `设置 → 通知 → 通知代理` 中启用并配置 WeComHub，与官方通知代理同一入口。
4. **云端构建**：所有 `plg` / `txz` 由 GitHub Actions 构建，禁止本地打包后上传。

## 架构

```
企业微信  ←→  中转服务（你的公网/VPS）  ←→  WeComHub 插件（Unraid）
                                              ├─ notify agent（通知 → 中转）
                                              └─ 本地指令服务（中转 → 执行命令）
```

## 安装

1. Unraid → 插件 → 安装插件 → 填本仓库 `wecom.hub.plg` 地址。
2. 打开 **设置 → 通知 → 通知代理**，找到 **WeComHub**，按提示填写后点击 Apply。

| 配置项 | 示例（占位符，非真实值） | 说明 |
| --- | --- | --- |
| Relay Host | `RELAY_HOST` | 你的 VPS 域名或 IP |
| Relay Port | `RELAY_PORT` | 默认 `8181` |
| Push Token | `RELAY_PUSH_TOKEN` | 与中转服务共享，用于鉴权 |
| Minimum Importance | `normal` | 接收的最低通知级别 |

> 以上均为通配占位符。请使用你自己的值；仓库与文档中不含任何真实凭据。

指令侧的本地端口与「允许重启的容器名前缀」保存在 `/boot/config/plugins/WeComHub/wecom.hub.cfg`，可按需调整。

## 开发

```bash
./scripts/build-release.sh 1.0.0     # 本地仅用于自测，产物不得上传
./scripts/verify-release.sh 1.0.0
```

正式发布：推送 `v*` tag，由 `.github/workflows/build-release.yml` 云端构建并挂到 Release。

## 文档

**使用与排障**

- [docs/configuration.md](docs/configuration.md) — 配置项详解
- [docs/troubleshooting.md](docs/troubleshooting.md) — 排障
- [SUPPORT.md](SUPPORT.md) — 支持与常见症状
- [SECURITY.md](SECURITY.md) — 凭据与指令服务安全边界

**项目与开发**

- [ABOUT.md](ABOUT.md) — 项目定位、设计原则与架构
- [DEVELOPMENT.md](DEVELOPMENT.md) — 开发约定
- [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献指南
- [CHANGELOG.md](CHANGELOG.md) — 更新日志
- [RELEASES.md](RELEASES.md) — 版本记录
- [PLUGIN-README.md](PLUGIN-README.md) — 插件页说明
- [README.en.md](README.en.md) — English

## 许可

代码见 [LICENSE](LICENSE)（MIT）。原创文档与视觉资产见 [LICENSE-ASSETS.md](LICENSE-ASSETS.md)（CC BY-NC-SA 4.0）。
第三方商标与关系声明见 [NOTICE](NOTICE)。
