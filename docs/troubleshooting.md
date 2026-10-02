# 排障

排查 WeComHub 时，建议按「配置 → 链路 → 服务 → 日志」的顺序缩小范围。

> 文中地址、端口、令牌均为**占位符示例**，请替换为你自己的值。

## 1. 配置层

```bash
cat /boot/config/plugins/WeComHub/wecom.hub.cfg
```

确认：`ENABLE_NOTIFY` / `ENABLE_CMD` 为 `yes`，`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN` 均已填写。

令牌不会明文显示在设置页，只会提示「已设置」。如果忘记是否配置过，以 cfg 中是否有非空值为准。

## 2. 链路层

在中转服务所在的机器上确认服务可达：

```bash
curl -v http://<RELAY_HOST>:<RELAY_PORT>/
```

在 Unraid 上确认出口没有被代理劫持。agent 已内置清理：

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
```

若你的环境通过 `/etc/profile` 或 network 层注入代理，需要额外排除中转地址。

## 3. 服务层

```bash
/etc/rc.d/rc.WeComHub status
/etc/rc.d/rc.WeComHub restart
```

端口被占用时的定位办法：

```bash
ss -ltnp | grep 8181        # 把 8181 换成你的 LOCAL_CMD_PORT
```

## 4. 通知层

手动触发一次 Unraid 测试通知（`设置 → 通知`）并观察是否到达企业微信。

常见拦截点：

- `MIN_IMPORTANCE` 设为 `warning` / `alert`，导致普通级别通知被过滤；
- 令牌与中转侧不一致；
- 中转服务的出口 IP 未加入企业微信「企业可信 IP」；
- 企业微信应用未把接收人加入可见范围。

通知失败是**静默**的（设计如此，避免阻塞 Unraid 其他流程），因此收不到时请先看第 2 步的链路连通性。

## 5. 指令层

本地自测：

```bash
curl -s -X POST http://127.0.0.1:8181/ \
  -H 'Content-Type: application/json' \
  -d '{"token":"<RELAY_PUSH_TOKEN>","cmd":"help"}'
```

把 `8181` 换成你的 `LOCAL_CMD_PORT`。端口不要直接暴露到公网，只能由中转访问。

返回码含义：

| 返回 | 含义 |
| --- | --- |
| `403 forbidden` | 令牌不匹配 |
| `404 未知指令` | 指令不在白名单，发 `help` 看列表 |
| `400 bad request` | body 不是合法 JSON |
| `400 非法容器名` | `restart` 参数字符集不合法 |
| `403 restart 不被允许` | 未配置 `RELAY_PUSH_TOKEN` 对应前缀或名字不匹配 |

## 6. 日志

```bash
tail -n 100 /var/log/wecom-hub.log
```

日志可能包含容器名、主机名等信息，提交到公开渠道前请先脱敏。

## 仍未解决

请带上 WeComHub 与 Unraid 版本、使用方向（通知出 / 指令入）和已脱敏日志，
到仓库提 Issue。安全问题请按 [SECURITY.md](../SECURITY.md) 私密报告。
