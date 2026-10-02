#!/bin/bash
# WeComHub 通知 agent：把 Unraid 系统通知经中转转发到企业微信。
#
# 部署位置：/boot/config/plugins/dynamix/notifications/agents/WeComHub.sh
# 由 Unraid notify 逐个执行，注入环境变量：
#   EVENT / SUBJECT / DESCRIPTION / IMPORTANCE / CONTENT / LINK
#
# 为何经中转：Unraid 家宽为双出口 IP 且会漂移，无法固定加入企业微信
# 「企业可信 IP」，直连企微会被拒；中转服务公网 IP 已在可信 IP 内，
# 故本地只把通知 POST 给中转代发。

CFG="/boot/config/plugins/WeComHub/wecom.hub.cfg"
[ -f "$CFG" ] && . "$CFG" 2>/dev/null || true

RELAY_HOST="${RELAY_HOST:-}"
RELAY_PORT="${RELAY_PORT:-8181}"
RELAY_PUSH_TOKEN="${RELAY_PUSH_TOKEN:-}"
ENABLE_NOTIFY="${ENABLE_NOTIFY:-yes}"
MIN_IMPORTANCE="${MIN_IMPORTANCE:-normal}"

# 未配置或不启用则静默退出
[ "$ENABLE_NOTIFY" = "yes" ] || exit 0
[ -n "$RELAY_HOST" ] || exit 0
[ -n "$RELAY_PUSH_TOKEN" ] || exit 0

# 重要级别过滤
cur="${IMPORTANCE:-normal}"
case "$MIN_IMPORTANCE" in
  alert)   [ "$cur" = "alert" ] || exit 0 ;;
  warning) [ "$cur" = "alert" ] || [ "$cur" = "warning" ] || exit 0 ;;
  *)       ;;
esac

# 清理全局代理，避免请求被导入 LAN 代理
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

export WH_EVENT="${EVENT:-unknown}"
export WH_SUBJECT="${SUBJECT:-Unraid Notification}"
export WH_DESC="${DESCRIPTION:-}"
export WH_IMPORTANCE="${IMPORTANCE:-normal}"
export WH_CONTENT="${CONTENT:-}"
export WH_LINK="${LINK:-}"
export WH_HOST="$RELAY_HOST"
export WH_PORT="$RELAY_PORT"
export WH_TOKEN="$RELAY_PUSH_TOKEN"

python3 - <<'PYEOF'
import json, os, urllib.request

host = os.environ.get("WH_HOST", "")
port = os.environ.get("WH_PORT", "8181")
token = os.environ.get("WH_TOKEN", "")

event = os.environ.get("WH_EVENT", "")
subject = os.environ.get("WH_SUBJECT", "")
desc = os.environ.get("WH_DESC", "")
imp = os.environ.get("WH_IMPORTANCE", "normal")
content = os.environ.get("WH_CONTENT", "")
link = os.environ.get("WH_LINK", "")

# payload 契约必须与既有中转侧保持一致：
# 核心字段为 token + text（已渲染的 markdown 正文），中转只读这两个字段即可工作；
# 其余结构化字段为可选扩展，便于中转侧做分级/路由，多余字段应被忽略。
body = desc
if content:
    body = (body + "\n" + content).strip()

text = "【Unraid 通知】\n> 事件: %s\n> 重要性: %s\n\n**标题:** %s" % (event, imp, subject)
if body:
    text += "\n\n**详情:**\n" + body
if link:
    text += "\n\n[查看详情](%s)" % link

payload = {
    "token": token,
    "text": text,
    "event": event,
    "subject": subject,
    "description": desc,
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
except Exception:
    # 通知失败不应影响 Unraid 其他流程
    pass
PYEOF
