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
EVENT="${EVENT:-Unraid Status}"
SUBJECT="${SUBJECT:-Notification}"
DESCRIPTION="${DESCRIPTION:-No description}"
IMPORTANCE="${IMPORTANCE:-normal}"
CONTENT="${CONTENT:-}"
LINK="${LINK:-}"
HOSTNAME="${HOSTNAME:-$(hostname)}"

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
RELAY_PORT="${RELAY_PORT:-8181}"
RELAY_PUSH_TOKEN="${RELAY_PUSH_TOKEN:-}"
MIN_IMPORTANCE="${MIN_IMPORTANCE:-normal}"

# Silently exit when not configured so other notification paths keep running.
# The placeholder values count as "not configured".
if [[ -z "${RELAY_HOST}" || "${RELAY_HOST}" == "RELAY_HOST" \
   || -z "${RELAY_PUSH_TOKEN}" || "${RELAY_PUSH_TOKEN}" == "RELAY_PUSH_TOKEN" ]]; then
  echo "$(date) not configured (Relay Host / Push Token), skipping" >>"$LOG"
  exit 0
fi

case "${MIN_IMPORTANCE}" in
  alert)   [[ "${IMPORTANCE}" == "alert" ]] || exit 0 ;;
  warning) [[ "${IMPORTANCE}" == "alert" || "${IMPORTANCE}" == "warning" ]] || exit 0 ;;
esac

# Drop any global proxy so the request is not routed through a LAN proxy.
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

TITLE="${TITLE:-${SUBJECT}}"
MESSAGE="${MESSAGE:-${DESCRIPTION}}"

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
text = "[%s Notification]\n> Event: %s\n> Importance: %s\n\n**Subject:** %s" % (
    hostname or "Unraid", event, imp, title)
if message:
    text += "\n\n**Details:**\n" + message
if content and content != message:
    text += "\n\n" + content
if link:
    text += "\n\n[Details](%s)" % link

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
