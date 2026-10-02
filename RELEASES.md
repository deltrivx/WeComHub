# Releases

## v1.0.5（配置分离与全英文脚本）

- **修复 agent 脚本中文注释导致的报错**：Test 按钮执行时中文注释被 shell 当成命令（`command not found`）。Script 段与 Variables 全部改为英文，与官方 14 个 agent 一致（官方 agent 的 Variables 零中文）。
- **配置来源分离**，各自只有一个入口：
  - 通知（出）→ 设置 → 通知 → **通知代理** → WeComHub，存 agent 脚本变量块
  - 指令（入）→ 设置 → 通知 → **WeComHub**，存 `wecom.hub.cfg`
- **不再预置任何值**：变量块只留占位符，任何设备/用户安装后自行填写即可，不依赖任何手工补丁。
- 通知侧键（`RELAY_*` / `MIN_IMPORTANCE` / `ENABLE_NOTIFY`）从 cfg 与插件页移除。

## v1.0.4（通知代理配置页修复）

- 修复「设置 → 通知 → 通知代理 → WeComHub」读不到任何配置项的问题。原因：页面从所编辑的 `.sh` 文件里的 `####...####` 变量块读取变量，而插件部署的是不含变量块的转发壳。现改为部署带 `{0}` 占位与完整实现的脚本，与官方 agent 结构一致。
- `agents/WeComHub.xml` 与 `scripts/notify-agent.sh` 的脚本体保持单一真相源，避免两处漂移。

## v1.0.3（插件页描述、restart 通配、rc 修复）

- 新增 `plugins/WeComHub/README.md`，修复 Unraid 插件页「描述」列空白（该列读 README.md，不读 plg 内的 CHANGES）
- `RESTART_ALLOW_PREFIX` 支持 `*` 通配，允许重启任意容器，无需逐个配置
- 修复 `rc.WeComHub` 在 busybox `date` 下日志时间戳空白
- 修复 `rc.WeComHub` 启动时与旧实例抢 8181 端口

## v1.0.2（通知代理接入）

- 新增通知代理定义 `agents/WeComHub.xml`，安装后出现在 **设置 → 通知 → 通知代理**，与内置代理同一入口
- 修复 `verify-release.sh` 占位符正则不识别含数字的键名
- 修复 txz 目录校验因 `grep -q` 触发 SIGPIPE 导致的误报

## v1.0.1（契约对齐）

- 指令服务固定 `POST /exec`，统一返回 JSON `{"ok", "result"}`
- 指令支持中文别名（状态/磁盘/温度/阵列/重启 X）
- 新增阵列启动事件钩子，保证开机自启（`rc.M` 不遍历 `/etc/rc.d/rc.*`）
- 补全卸载清理；未配置令牌时指令服务 fail closed
- 修复版本索引与更新检查的字段名不一致

## v1.0.0（初始版本）

- 把两套散落脚本合并为标准插件
- 系统通知经中转转发至企业微信
- 内置本地指令服务，接收企微反向调用
- 所有归档由 GitHub Actions 云端构建
