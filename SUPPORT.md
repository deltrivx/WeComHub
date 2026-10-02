# 支持与故障排查

## 先做这些检查

1. 打开 **设置 → 通知 → 通知代理**，找到 **WeComHub**，确认已启用并填写了中转地址与令牌。
2. 在该页面点击 **Test**，确认企业微信能收到测试通知。
3. 强制刷新 WebGUI（`Ctrl+F5`），避免浏览器继续使用旧 JS/CSS。
4. 检查本地指令服务是否在运行：
   ```bash
   /etc/rc.d/rc.WeComHub status
   ```
5. 查看日志 `/var/log/notify_WeComHub`，确认链路是否报错。
5. 手动触发一次系统通知（`设置 → 通知 → 通知代理 → WeComHub → Test`），确认企业微信是否收到。
6. 查看日志 `/var/log/notify_WeComHub` 与 `/var/log/wecom-hub.log`。

## 常见位置

```text
/boot/config/plugins/WeComHub/wecom.hub.cfg
/boot/config/plugins/dynamix/notifications/agents/WeComHub.sh
/etc/rc.d/rc.WeComHub
/usr/local/emhttp/plugins/WeComHub/version
/var/log/wecom-hub.log
```

## 常见症状

| 症状 | 可能原因 | 处理 |
| --- | --- | --- |
| 收不到任何通知 | 中转地址/端口不通，或令牌与中转不一致 | 先在 Unraid 上 `curl -v http://<RELAY_HOST>:<RELAY_PORT>/` 确认可达，再核对令牌 |
| 只有部分通知到达 | `MIN_IMPORTANCE` 过滤 | 改为 `normal` 接收全部 |
| 通知被代理吞掉 | 全局代理把请求导入 LAN 代理 | agent 已内置 `unset http_proxy https_proxy`；若仍异常检查 `/etc/profile` |
| 指令服务起不来 | 端口被占用或 cfg 缺失 | `/etc/rc.d/rc.WeComHub restart` 后看 `/var/log/wecom-hub.log` |
| 指令返回 403 | 令牌不匹配 | 核对 cfg 与中转侧令牌 |
| `restart` 被拒 | 未配置 `RESTART_ALLOW_PREFIX` 或名称不匹配 | 在 cfg 中配置允许的前缀 |

> 上表中的地址、端口、令牌均为占位符写法，请替换为你自己的值。

## 提交 Issue 时请附带

- WeComHub 与 Unraid 版本；
- 使用的是通知出、指令入还是两者；
- 中转服务的部署形态（不需要提供真实地址）；
- 操作步骤、预期行为和实际行为；
- 已脱敏的相关日志。

请勿提交令牌、Cookie、真实中转地址或完整配置。安全问题请按 [SECURITY.md](SECURITY.md) 私密报告。
