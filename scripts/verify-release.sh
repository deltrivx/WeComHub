#!/bin/bash
# WeComHub 发布产物校验
# 用法: ./scripts/verify-release.sh <version>
set -uo pipefail

VER="${1:?usage: verify-release.sh <version>}"
NAME="WeComHub"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
rc=0

say() { printf '%-8s %s\n' "$1" "$2"; }

# 1) 产物存在
for f in "$DIST/$NAME-$VER.txz" "$DIST/wecom.hub.plg"; do
  [ -s "$f" ] && say OK "存在: $(basename "$f")" \
             || { say FAIL "缺失或为空: $(basename "$f")"; rc=1; }
done

# 2) plg 无未替换占位符
if [ -f "$DIST/wecom.hub.plg" ]; then
  if grep -qE '\{(VERSION|MD5_[A-Z0-9_]+)\}' "$DIST/wecom.hub.plg"; then
    say FAIL "plg 仍有未替换占位符"
    grep -oE '\{(VERSION|MD5_[A-Z0-9_]+)\}' "$DIST/wecom.hub.plg" | sort -u
    rc=1
  else
    say OK "plg 占位符已全部替换"
  fi
fi

# 3) plg XML 合法
if command -v python3 >/dev/null 2>&1 && [ -f "$DIST/wecom.hub.plg" ]; then
  if python3 -c "import sys,xml.etree.ElementTree as ET; ET.parse('$DIST/wecom.hub.plg')" 2>/dev/null; then
    say OK "plg XML 合法"
  else
    say FAIL "plg XML 非法"; rc=1
  fi
fi

# 4) txz 内目录结构正确
# 注意：不要写成 `tar -tJf ... | grep -q`。grep -q 命中后立即退出会让 tar 收到
# SIGPIPE（141），在 `set -o pipefail` 下整条管道被判为失败，导致误报「缺少插件目录」。
# 4) txz 内容校验
# ⚠️ 这是离线安装方案的核心：txz 必须自包含**所有**运行时文件。
# /usr 是内存 overlay，重启即失。txz 里缺任何一个，开机后对应功能就消失：
#   - rc.$NAME            -> 无法 start/stop 服务（不能群发谎报成功，见 DEVELOPMENT.md）
#   - agents/$NAME.xml    -> 通知代理页面没有 WeComHub 入口
#   - icons/wecomhub.png  -> 代理图标缺失
#   - event/started/zz-*  -> 开机不自启
#   - scripts/agent-config-template.sh -> 新装机无法生成 agent 配置
# 同时反向校验：用户配置文件**不得**被打包，否则解包会覆盖用户的令牌。
if [ -f "$DIST/$NAME-$VER.txz" ]; then
  TXZ_LIST="$(tar -tJf "$DIST/$NAME-$VER.txz" 2>/dev/null || true)"
  missing=0
  for want in \
      "usr/local/emhttp/plugins/$NAME" \
      "usr/local/emhttp/plugins/$NAME/$NAME.page" \
      "usr/local/emhttp/plugins/$NAME/wecom-hub-cmd.py" \
      "usr/local/emhttp/plugins/$NAME/wecom-hub-notify-agent.sh" \
      "usr/local/emhttp/plugins/$NAME/scripts/agent-config-template.sh" \
      "usr/local/emhttp/plugins/$NAME/scripts/event-started.sh" \
      "usr/local/emhttp/plugins/$NAME/scripts/rc.$NAME" \
      "usr/local/emhttp/plugins/dynamix/agents/$NAME.xml" \
      "usr/local/emhttp/plugins/dynamix/icons/wecomhub.png" \
      "usr/local/emhttp/plugins/dynamix/event/started/zz-wecomhub" \
      "etc/rc.d/rc.$NAME"; do
    if printf '%s\n' "$TXZ_LIST" | grep -qF "$want"; then
      say OK "txz 包含 $want"
    else
      say FAIL "txz 缺少 $want"; rc=1; missing=1
    fi
  done
  [ "$missing" = "0" ] && say OK "txz 自包含完整"

  if printf '%s\n' "$TXZ_LIST" | grep -qE "notifications/agents"; then
    say FAIL "txz 打包了用户配置文件（会覆盖用户令牌）"; rc=1
  else
    say OK "txz 未打包用户配置"
  fi
fi

# 4b) plg 必须只有一个网络 FILE（txz 本体），否则开机又要逐个下载
if [ -f "$DIST/wecom.hub.plg" ]; then
  # ⚠️ 不能用 grep -c '<URL>' 统计：XML 注释里若出现该字面量会被误计入
  # （实测踩过：故障说明注释里的 "<URL>" 让计数变成 2）。
  # 必须按 XML 语义解析，只统计真正带 URL 子元素的 FILE 条目。
  NET=$(python3 - "$DIST/wecom.hub.plg" <<'PYNET'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
print(sum(1 for f in root.findall("FILE") if f.find("URL") is not None))
PYNET
)
  if [ "$NET" = "1" ]; then
    say OK "plg 仅 1 个联网条目（txz）"
  else
    say FAIL "plg 有 $NET 个联网条目，开机仍依赖网络"; rc=1
  fi
  if grep -q "upgradepkg --install-new --reinstall" "$DIST/wecom.hub.plg"; then
    say OK "plg 使用 txz 本地解包（含 --reinstall，避免已登记时跳过解包）"
  else
    say FAIL "plg 缺少 upgradepkg --install-new --reinstall"; rc=1
  fi
fi

# 5) 无真实凭据泄漏
if grep -rIqE "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,})" "$DIST" 2>/dev/null; then
  say FAIL "产物含疑似真实凭据"; rc=1
else
  say OK "产物无真实凭据"
fi

exit $rc
