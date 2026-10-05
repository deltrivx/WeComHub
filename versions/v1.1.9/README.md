# WeComHub

Unraid 企业微信中枢插件：把 Unraid 系统通知推送到企业微信，并支持企业微信指令反向交互。

- **通知代理**：安装后出现在 **设置 → 通知 → 通知代理**，与内置代理同一入口，可填写变量并使用 Test 按钮。
- **指令服务**：内置白名单只读查询与受限容器重启，本地监听可配置端口。
- **不依赖 `/boot/config/go`**：由阵列启动事件钩子调起服务。
- **云端构建**：所有 `plg` / `txz` 由 GitHub Actions 构建，禁止本地打包后上传。

配置项（通知代理页）：`RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`MIN_IMPORTANCE`。
指令侧配置（插件页）：`LOCAL_CMD_PORT`、`RESTART_ALLOW_PREFIX`。

项目主页、完整说明、更新日志与支持信息：
https://github.com/deltrivx/WeComHub
