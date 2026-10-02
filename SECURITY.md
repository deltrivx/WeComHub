# 安全说明

## 支持范围

安全修复优先覆盖最新正式版。旧版本仅保留回滚能力，不保证单独发布安全补丁。

## 报告安全问题

请不要在公开 Issue 中提交令牌、中转地址、完整配置、日志中的会话信息或可直接利用的漏洞细节。

推荐通过 GitHub 仓库的 **Security → Report a vulnerability** 私密报告功能联系维护者。报告中请包含：

- 受影响的 WeComHub 版本和 Unraid 版本；
- 启用的是通知出、指令入还是两者；
- 可重复的最小步骤；
- 影响范围及你已采取的临时缓解措施；
- 已脱敏的日志或截图。

## 凭据处理

- 推送令牌保存在 `/boot/config/plugins/WeComHub/wecom.hub.cfg`，由设置页写入。
- 页面不回显令牌明文，只提示「已设置/未设置」。
- 仓库、文档、Release 产物中一律使用占位符：`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。
- `verify.yml` 会扫描 `sk-` / `ghp_` / `gho_` 前缀的真实 token，命中即失败。

## 指令服务安全

- 只执行内建白名单命令（`help` / `status` / `docker` / `uptime` / `disk`），不拼接任意 shell。
- `restart <容器>` 默认禁用；仅当配置 `RESTART_ALLOW_PREFIX` 且容器名匹配前缀时允许。
- 令牌比较使用常量时间比较，避免时序侧信道。
- 服务监听 `LOCAL_CMD_PORT`，仅应通过中转访问；不要把该端口直接暴露到公网。

## 网络边界

- 中转服务需要公网可达且 IP 已加入企业微信「企业可信 IP」。
- 建议为远程访问使用可信 VPN/组网方案，并保持 Unraid 与浏览器处于受支持版本。

## 免责声明

本项目按现状提供，不承诺适用于任何特定用途。许可证中的责任限制仍然适用。
