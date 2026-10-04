#!/bin/bash
# WeComHub notification agent (program body).
#
# This is the implementation half. It is deployed by the plugin into the plugin
# directory and updated on every plugin upgrade.
#
# The matching half is the agent file at
#   /boot/config/plugins/dynamix/notifications/agents/WeComHub.sh
# which holds ONLY the user's variables and then execs this script. Keeping the
# two halves separate means:
#   - upgrading the plugin updates this logic
#   - user configuration in the agent file is never overwritten
#
# Unraid's notify subsystem injects these variables:
#   EVENT, SUBJECT, DESCRIPTION, IMPORTANCE, CONTENT, LINK, HOSTNAME, TIMESTAMP
#
# Manual test:
#   EVENT="My Event" SUBJECT="My Subject" DESCRIPTION="My Description" \
#   RELAY_HOST=your-relay RELAY_PUSH_TOKEN=your-token \
#   bash /usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh
#
# If a notification does not arrive, check /var/log/notify_WeComHub.
############

SCRIPTNAME=$(basename "$0")
LOG="/var/log/notify_WeComHub"

# Fill in the environment when run for a quick manual test.
# Do NOT invent placeholder text for SUBJECT / DESCRIPTION.
# Old versions filled "Notification" / "No description" here, and those
# resolved fallbacks then got persisted into the snapshot and restored as if
# they were real configuration -- so every notification showed fake template
# text instead of the real content.
EVENT="${EVENT:-Unraid Status}"
SUBJECT="${SUBJECT:-}"
DESCRIPTION="${DESCRIPTION:-}"
IMPORTANCE="${IMPORTANCE:-normal}"
CONTENT="${CONTENT:-}"
LINK="${LINK:-}"
HOSTNAME="${HOSTNAME:-$(hostname)}"

# 保存用户原始配置值（未经过任何兜底解析），仅供快照持久化使用。
# 只有原始值才写进快照；空值表示“跟随 subject/description”，还原后仍动态解析。
RAW_TITLE="${TITLE:-}"
RAW_MESSAGE="${MESSAGE:-}"

# 迁移：旧版曾把兜底文案 "Notification" / "No description" 写进配置与快照。
# 这些不是用户填的真实值，必须视为“未设置”，否则每条通知都显示假标题/假详情。
if [[ "${RAW_TITLE}" == "Notification" ]]; then
  RAW_TITLE=""
fi
if [[ "${RAW_MESSAGE}" == "No description" ]]; then
  RAW_MESSAGE=""
fi

# Turn literal \n sequences into real line breaks.
if [[ -n "${DESCRIPTION}" ]]; then
  DESCRIPTION=${DESCRIPTION//\\r\\n/$'\n'}
  DESCRIPTION=${DESCRIPTION//\\n/$'\n'}
  DESCRIPTION=${DESCRIPTION//\\r/$'\n'}
fi
if [[ -n "${CONTENT}" ]]; then
  CONTENT=${CONTENT//\\r\\n/$'\n'}
  CONTENT=${CONTENT//\\n/$'\n'}
  CONTENT=${CONTENT//\\r/$'\n'}
fi

RELAY_HOST="${RELAY_HOST:-}"
# 默认 8484 = VPS 上的 wecom-api-proxy（防火墙对所有来源开放，免疫出口 IP 漂移）。
# 仅当通知代理页未填写该值时兜底；用户一旦在 UI 填写，以 UI 值为准。
RELAY_PORT="${RELAY_PORT:-8484}"
RELAY_PUSH_TOKEN="${RELAY_PUSH_TOKEN:-}"
MIN_IMPORTANCE="${MIN_IMPORTANCE:-normal}"

# Silently exit when not configured so other notification paths keep running.
# The placeholder values count as "not configured".
if [[ -z "${RELAY_HOST}" || "${RELAY_HOST}" == "RELAY_HOST" \
   || -z "${RELAY_PUSH_TOKEN}" || "${RELAY_PUSH_TOKEN}" == "RELAY_PUSH_TOKEN" ]]; then
  echo "$(date) not configured (Relay Host / Push Token), skipping" >>"$LOG"
  exit 0
fi

# 配置持久化：仅在配置有效时，把当前变量镜像到持久化快照。
# agent 配置文件（用户在通知代理页填写处）可能被 Delete 删除或丢失；
# 快照让重装/升级后能自动还原配置，而不是退回占位默认值。
# 注意：本文件在 plg 的 <FILE> 清单内，每次升级都会更新，因此该逻辑能覆盖存量用户。

case "${MIN_IMPORTANCE}" in
  alert)   [[ "${IMPORTANCE}" == "alert" ]] || exit 0 ;;
  warning) [[ "${IMPORTANCE}" == "alert" || "${IMPORTANCE}" == "warning" ]] || exit 0 ;;
esac

# Drop any global proxy so the request is not routed through a LAN proxy.
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

# Fall back to the most informative field available; never fabricate text.
# Title falls back to EVENT (meaningful), message falls back to CONTENT.
TITLE="${TITLE:-${SUBJECT:-${EVENT}}}"
MESSAGE="${MESSAGE:-${DESCRIPTION:-${CONTENT}}}"

# 配置持久化：仅在配置有效时，把当前变量镜像到持久化快照。
# agent 配置文件（用户在通知代理页填写处）可能被 Delete 删除或丢失；
# 快照让重装/升级后能自动还原配置，而不是退回占位默认值。
# 位置必须在 TITLE/MESSAGE 解析之后，否则快照会存到空值。
# 本文件在 plg 的 <FILE> 清单内，每次升级都会更新，因此该逻辑能覆盖存量用户。
SNAP="/boot/config/plugins/WeComHub/agent-vars.conf"
mkdir -p "/boot/config/plugins/WeComHub" 2>/dev/null
{
  printf 'RELAY_HOST=%s\n' "${RELAY_HOST}"
  printf 'RELAY_PORT=%s\n' "${RELAY_PORT}"
  printf 'RELAY_PUSH_TOKEN=%s\n' "${RELAY_PUSH_TOKEN}"
  printf 'MIN_IMPORTANCE=%s\n' "${MIN_IMPORTANCE}"
  # Persist only the user's raw values. Empty means "follow subject/description",
  # so restoring never bakes fallback text into the configuration.
  printf 'TITLE=%s\n' "${RAW_TITLE}"
  printf 'MESSAGE=%s\n' "${RAW_MESSAGE}"
} > "$SNAP" 2>/dev/null
chmod 0600 "$SNAP" 2>/dev/null

export WH_EVENT="${EVENT}"
export WH_IMPORTANCE="${IMPORTANCE}"
export WH_CONTENT="${CONTENT}"
export WH_LINK="${LINK}"
export WH_HOSTNAME="${HOSTNAME}"
export WH_TITLE="${TITLE}"
export WH_MESSAGE="${MESSAGE}"
export WH_HOST="${RELAY_HOST}"
export WH_PORT="${RELAY_PORT}"
export WH_TOKEN="${RELAY_PUSH_TOKEN}"
export WH_LOG="${LOG}"

python3 - <<'PYEOF'
import json, os, time, urllib.request

host = os.environ.get("WH_HOST", "")
port = os.environ.get("WH_PORT", "8181")
token = os.environ.get("WH_TOKEN", "")

event = os.environ.get("WH_EVENT", "")
imp = os.environ.get("WH_IMPORTANCE", "normal")
content = os.environ.get("WH_CONTENT", "")
link = os.environ.get("WH_LINK", "")
hostname = os.environ.get("WH_HOSTNAME", "")
title = os.environ.get("WH_TITLE", "")
message = os.environ.get("WH_MESSAGE", "")

# Keep the payload contract compatible with the relay: token + text is the core
# pair (text is the rendered markdown body). The remaining fields are optional
# extensions the relay may ignore.
text = "【%s 通知】\n> 事件：%s\n> 重要性：%s\n\n**标题：** %s" % (
    hostname or "Unraid", event, imp, title)
if message:
    text += "\n\n**详情：**\n" + message
if content and content != message:
    text += "\n\n" + content
if link:
    text += "\n\n[查看详情](%s)" % link

payload = {
    "token": token,
    "text": text,
    "event": event,
    "importance": imp,
    "content": content,
    "link": link,
}
url = "http://%s:%s/notify" % (host, port)
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(req, timeout=10).read()
except Exception as e:
    # A failed notification must not affect other Unraid notification paths.
    with open(os.environ.get("WH_LOG", "/var/log/notify_WeComHub"), "a") as fh:
        fh.write("%s FAIL %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), str(e)[:200]))
PYEOF
