#!/bin/bash
############
RELAY_HOST="RELAY_HOST"
RELAY_PORT="8181"
RELAY_PUSH_TOKEN="RELAY_PUSH_TOKEN"
MIN_IMPORTANCE="normal"
TITLE="$SUBJECT"
MESSAGE="$DESCRIPTION"
############

# 变量必须 export：本文件用 exec 调用程序本体，未导出的 shell 变量不会传递过去。
export RELAY_HOST RELAY_PORT RELAY_PUSH_TOKEN MIN_IMPORTANCE TITLE MESSAGE

############
# WeComHub notification agent (configuration half).
#
# This file holds ONLY your configuration. The implementation lives in
#   /usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh
# and is updated together with the plugin. Because this file is not managed by
# the plugin, your settings survive plugin upgrades.
#
# Edit the variables through:
#   Settings -> Notification -> Notification Agents -> WeComHub
# Do not edit the block above by hand; the page regenerates it on Apply.
############


SNAP="/boot/config/plugins/WeComHub/agent-vars.conf"
mkdir -p "/boot/config/plugins/WeComHub" 2>/dev/null
# Mirror the variables into a persistent snapshot BEFORE calling the plugin body
# (exec replaces this process, so nothing after it would run).
# This file can be deleted (Delete button, flash restore); the snapshot is what
# lets reinstallation recover your settings instead of falling back to placeholders.
if [[ "${RELAY_HOST}" != "RELAY_HOST" && -n "${RELAY_HOST}" && "${RELAY_PUSH_TOKEN}" != "RELAY_PUSH_TOKEN" && -n "${RELAY_PUSH_TOKEN}" ]]; then
  {
    printf 'RELAY_HOST=%s\n' "$RELAY_HOST"
    printf 'RELAY_PORT=%s\n' "$RELAY_PORT"
    printf 'RELAY_PUSH_TOKEN=%s\n' "$RELAY_PUSH_TOKEN"
    printf 'MIN_IMPORTANCE=%s\n' "$MIN_IMPORTANCE"
    printf 'TITLE=%s\n' "$TITLE"
    printf 'MESSAGE=%s\n' "$MESSAGE"
  } > "$SNAP"
  chmod 0600 "$SNAP" 2>/dev/null
fi

AGENT="/usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh"
if [[ -x "$AGENT" ]]; then
  exec "$AGENT"
fi

# Plugin body missing: record it instead of failing silently.
echo "$(date) plugin body not found: $AGENT" >>/var/log/notify_WeComHub
exit 0
