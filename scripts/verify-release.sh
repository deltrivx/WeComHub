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
if [ -f "$DIST/$NAME-$VER.txz" ]; then
  TXZ_LIST="$(tar -tJf "$DIST/$NAME-$VER.txz" 2>/dev/null || true)"
  if printf '%s\n' "$TXZ_LIST" | grep -qF "usr/local/emhttp/plugins/$NAME"; then
    say OK "txz 包含插件目录"
  else
    say FAIL "txz 缺少 usr/local/emhttp/plugins/$NAME"; rc=1
  fi
fi

# 5) 无真实凭据泄漏
if grep -rIqE "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,})" "$DIST" 2>/dev/null; then
  say FAIL "产物含疑似真实凭据"; rc=1
else
  say OK "产物无真实凭据"
fi

exit $rc
