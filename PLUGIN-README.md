# WeComHub

适用于 Unraid 6.9+ 的企业微信中枢插件：把 Unraid 系统通知推送到企业微信，并支持企业微信指令反向交互。

## 核心能力

- 接入官方通知代理：安装后出现在 **设置 → 通知 → 通知代理**，与内置代理同一入口，可填写并测试
- 系统通知（阵列/磁盘/容器/uptime 等）经中转转发到企业微信应用
- 企业微信指令反向交互：只读查询（阵列/容器/负载/磁盘）与受限容器重启
- 最低通知级别过滤：`normal` / `warning` / `alert`
- 开机自启：阵列启动事件钩子调起 `/etc/rc.d/rc.WeComHub`，不依赖启动脚本兜底
- 所有归档由 GitHub Actions 云端构建并发布

## 入口

安装后前往：**设置 → 通知 → 通知代理**，找到 **WeComHub**，填写后点击 Apply。

填写中转地址、中转端口、推送令牌与最低通知级别。页面上的 Test 按钮可直接验证推送链路。

## 为何需要中转

Unraid 所在网络的出口 IP 可能不固定或动态变化，而企业微信要求调用方 IP 落在「企业可信 IP」白名单内。直连会因 IP 不在白名单被拒。

WeComHub 只把通知交给一台公网 IP 固定的中转服务代发，本地不直连企业微信。

## 数据与安全

- 通知侧变量（中转地址/端口/令牌）保存在 agent 脚本的变量块中，由官方通知代理页管理
- 指令侧配置保存在 `/boot/config/plugins/WeComHub/wecom.hub.cfg`，权限 `0600`
- 指令服务仅执行白名单命令；`restart` 受 `RESTART_ALLOW_PREFIX` 限制并校验容器名字符集
- 令牌比较使用常量时间比较，避免时序侧信道

仓库与文档中一律使用占位符：`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。

项目主页、完整说明、更新日志和支持信息：
https://github.com/deltrivx/WeComHub
