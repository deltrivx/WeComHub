# 贡献指南

感谢你帮助改进 WeComHub。Issue、文档修正、兼容性反馈和代码贡献都欢迎使用中文提交。

## 提交前

1. 搜索现有 Issue 与 Release，确认问题尚未解决。
2. 隐去令牌、真实中转地址、Cookie、.container 凭据和私人日志内容。
3. 说明 WeComHub 与 Unraid 版本，以及使用的是通知出、指令入还是两者。
4. 给出最小、连续、可重复的步骤。

## 硬性约定

- **禁止本地构建后上传**：`plg` / `txz` 只能由 `.github/workflows/build-release.yml` 云端产出。本地 `dist/` 已 gitignore。
- **禁止提交真实凭据**：一律使用占位符 `RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。
- **不直接修改历史 `versions/<版本>/` 内容**，需要变更请发新版本。
- 涉及 Unraid 系统层（notification agents、`/etc/rc.d`、`/boot/config/go`）的改动必须在 PR 中显式说明影响与卸载/回滚路径。

## 开发约定

- 新增可执行文件需在 `wecom.hub.plg` 中登记 `<FILE>` 与 `<MD5>` 占位符，并在 `scripts/build-release.sh` 中补充对应 MD5 计算。
- 新增配置项需同步：`wecom.hub.cfg`、`WeComHub.page`、`wecom-hub-save.php`、`docs/configuration.md`。
- 通知失败必须静默退出，不能阻塞 Unraid 其他流程。
- 指令服务只扩展白名单命令，不得引入任意 shell 拼接。

## 验证

```bash
bash -n scripts/*.sh
python3 -m py_compile wecom-hub-cmd.py
php -l wecom-hub-save.php
./scripts/verify-release.sh <版本>
```

至少验证 Shell 语法、Python 语法、PHP 语法、XML 合法性和无真实凭据。

## Pull Request

PR 请写明：问题、根因、修改、用户影响、验证方式、是否涉及配置迁移或系统层改动。一个 PR 尽量只处理一个明确主题。
