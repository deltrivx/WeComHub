# 关于 WeComHub

WeComHub 是面向 Unraid 的**企业微信中枢插件**，把原本散落在系统各处的两套脚本统一为一个标准插件：

1. **通知出**：`/boot/config/plugins/dynamix/notifications/agents/WeCom.sh` + `.wecom.env`
2. **指令入**：`/boot/config/unraid-cmd/unraid_cmd.py`（监听 8181）+ user.scripts 常驻服务

目标是接入官方通知代理体系，不再散落脚本、不再改 `/boot/config/go` 兜底。

## 项目定位

- 不是企业微信机器人框架，而是 Unraid 侧的**收发中枢**。
- 通知通过官方「设置 → 通知 → 通知代理」入口配置，与内置代理同一套变量表单与测试按钮。
- 不实现企微协议直连：企业微信要求调用方 IP 在「企业可信 IP」白名单内，因此统一经**中转服务**代发。
- 不在仓库、文档、日志或 Release 中保存任何真实凭据。
- 指令侧只执行白名单命令，不拼接任意 shell。

## 设计原则

1. **设置是唯一真相来源**：所有行为由 `设置 → 通知` 页面写入的 cfg 决定。
2. **凭据不进入浏览器**：令牌字段只显示「已设置/未设置」，不回显明文。
4. **不依赖 `/boot/config/go`**：由阵列启动事件钩子调起 `/etc/rc.d/rc.WeComHub`，随插件安装/移除。
4. **失败不影响系统**：通知发送异常静默退出，不阻塞 Unraid 其他流程。
5. **云端构建唯一可信**：所有 `plg` / `txz` 由 GitHub Actions 产出，本地 `dist/` 仅自测且已 gitignore。
6. **最小权限**：`restart` 指令受容器名前缀白名单约束，默认关闭。

## 架构

```text
WeComHub.page（设置 → 通知）
        │
        ├── wecom-hub-save.php ──→ /boot/config/plugins/WeComHub/wecom.hub.cfg
        │
        ├── scripts/notify-agent.sh（部署到 dynamix/notifications/agents/）
        │        └── wecom-hub-notify-agent.sh ──→ 中转服务 /notify ──→ 企业微信
        │
        └── scripts/rc.WeComHub（部署到 /etc/rc.d/rc.WeComHub）
                 └── wecom-hub-cmd.py（监听 LOCAL_CMD_PORT）
                          企业微信 ──→ 中转服务 ──→ 白名单命令 ──→ 文本回传
```

## 发布模型

- `versions/index.json` 是可安装版本索引。
- `versions/<版本>/` 保存该版本的运行文件快照与 plg。
- GitHub Release 提供 `wecom.hub.plg` 与 `WeComHub-<版本>.txz`。
- 打 `v*` tag 触发 `.github/workflows/build-release.yml` 云端构建。

## 项目关系

WeComHub 与 Lime Technology, Inc.（Unraid）、腾讯企业微信均无官方隶属或背书关系，详见 [NOTICE](NOTICE)。
