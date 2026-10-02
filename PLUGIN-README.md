# WeComHub

适用于 Unraid 6.9+ 的企业微信中枢插件：把 Unraid 系统通知推送到企业微信，并支持企业微信指令反向交互。

## 核心能力

- 设置 → 通知 页面可视化配置，不写 env 文件、不修改 `/boot/config/go`
- 系统通知（阵列/磁盘/容器/uptime 等）经中转转发到企业微信应用
- 企业微信指令反向交互：只读查询（阵列/容器/负载/磁盘）与受限容器重启
- 最低通知级别过滤：`normal` / `warning` / `alert`
- 开机自启：`/etc/rc.d/rc.WeComHub`，不依赖启动脚本兜底
- 所有归档由 GitHub Actions 云端构建、经 SHA/MD5 校验后发布

## 入口

安装后前往：**设置 → 通知**

填写中转地址、中转端口、推送令牌与本地指令端口。页面不回显已保存的令牌，只提示「已设置，留空保持不变」。

## 为何需要中转

Unraid 所在网络的出口 IP 可能不固定或动态变化，而企业微信要求调用方 IP 落在「企业可信 IP」白名单内。直连会因 IP 不在白名单被拒。

WeComHub 只把通知交给一台公网 IP 固定的中转服务代发，本地不直连企业微信。

## 数据与安全

- 配置保存于 `/boot/config/plugins/WeComHub/wecom.hub.cfg`，权限 `0600`
- 推送令牌不在页面回显，不写入日志
- 指令服务仅执行白名单命令；`restart` 受 `RESTART_ALLOW_PREFIX` 前缀限制并校验容器名字符集
- 令牌比较使用常量时间比较，避免时序侧信道

仓库与文档中一律使用占位符：`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。

项目主页、完整说明、更新日志和支持信息：
https://github.com/deltrivx/WeComHub
