# WeComHub

Unraid 企业微信中枢插件：**设置 → 通知** 可视化配置，把 Unraid 系统通知推送到企业微信，并支持企业微信指令反向交互。

## 它解决什么

- Unraid 家宽出口 IP 会漂移，无法固定加入企业微信「企业可信 IP」，直连企微会失败 → 需要一个**中转**。
- 以前靠散落脚本 + 手改 `/boot/config/go` 兜底，难维护、难分享 → 现在是**标准插件**，UI 配置。
- 配置明文写在多个 env 文件里 → 现在统一存插件 cfg，UI 填写。

## 功能

1. **通知出**：Unraid 系统通知（阵列/磁盘/容器/uptime 等）经中转转发到企业微信应用。
2. **指令入**：企业微信发指令，插件内本地服务接收并执行只读查询 / 容器重启，回传文本。
3. **UI 配置**：入口在 `设置 → 通知`，不写 env、不碰 `/boot/config/go`。
4. **云端构建**：所有 `plg` / `txz` 由 GitHub Actions 构建，禁止本地打包后上传。

## 架构

```
企业微信  ←→  中转服务（你的公网/VPS）  ←→  WeComHub 插件（Unraid）
                                              ├─ notify agent（通知 → 中转）
                                              └─ 本地指令服务（中转 → 执行命令）
```

## 安装

1. Unraid → 插件 → 安装插件 → 填本仓库 `wecom.hub.plg` 地址；
   或在「设置 → 通知」页内直接配置。
2. 打开 **设置 → 通知**，填写：

| 配置项 | 示例（占位符，非真实值） | 说明 |
| --- | --- | --- |
| 中转地址 | `RELAY_HOST` | 例如你的 VPS 域名或 IP |
| 中转端口 | `RELAY_PORT` | 默认 `8181` |
| 推送令牌 | `RELAY_PUSH_TOKEN` | 与中转服务共享，用于鉴权 |
| 本地服务端口 | `LOCAL_CMD_PORT` | 默认 `8181`，接收反向指令 |

> 以上均为通配占位符。请使用你自己的值；仓库与文档中不含任何真实凭据。

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
