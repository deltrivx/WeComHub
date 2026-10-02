# 配置说明

所有配置在 **设置 → 通知** 页面填写，保存到 `/boot/config/plugins/WeComHub/wecom.hub.cfg`。

> 以下取值均为**占位符示例**，请替换为你自己的实际值。仓库与文档不含任何真实凭据。

## 配置项

| 键 | 占位符示例 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `ENABLE_NOTIFY` | `yes` | `yes` | 是否启用通知推送 |
| `ENABLE_CMD` | `yes` | `yes` | 是否启用指令交互 |
| `RELAY_HOST` | `RELAY_HOST` | 空 | 中转服务地址（公网可达） |
| `RELAY_PORT` | `RELAY_PORT` | `8181` | 中转服务端口 |
| `RELAY_PUSH_TOKEN` | `RELAY_PUSH_TOKEN` | 空 | 与中转服务共享的令牌 |
| `LOCAL_CMD_PORT` | `LOCAL_CMD_PORT` | `8181` | 本地指令服务监听端口 |
| `MIN_IMPORTANCE` | `normal` | `normal` | 最低通知级别：`normal`/`warning`/`alert` |

## 为何需要中转

Unraid 所在网络的出口 IP 可能不固定或动态变化，而企业微信要求调用方 IP 在
「企业可信 IP」白名单内。直连会因 IP 不在白名单被拒。

解决方式：由一台公网 IP 固定的中转服务代发，Unraid 只把通知交给中转。

```
企业微信  ←→  中转服务（公网固定 IP）  ←→  WeComHub（Unraid）
```

## 指令交互

企业微信发送指令 → 中转 → 本地 `LOCAL_CMD_PORT` → 执行白名单命令 → 回传文本。

内置指令：

| 指令 | 说明 |
| --- | --- |
| `help` | 列出可用指令 |
| `status` | 阵列/磁盘概览 |
| `docker` | 容器列表 |
| `uptime` | 系统运行时间 |
| `disk` | 磁盘使用 |

`restart <容器>` 仅在配置 `RESTART_ALLOW_PREFIX` 且容器名匹配前缀时允许，
用于避免任意容器被操作。
