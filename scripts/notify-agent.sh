#!/bin/bash
# WeComHub 通知 agent（部署副本）
#
# 插件安装时部署到 /boot/config/plugins/dynamix/notifications/agents/WeComHub.sh，
# 由 Unraid notify 逐个执行。实际逻辑与 wecom-hub-notify-agent.sh 一致，
# 此处仅做转发，便于单一维护点。

AGENT="/usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh"
[ -x "$AGENT" ] && exec "$AGENT"
exit 0
