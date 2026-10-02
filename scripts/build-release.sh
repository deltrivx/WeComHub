#!/bin/bash
# WeComHub 云端构建脚本
# 由 GitHub Actions 调用；禁止本地构建后上传产物。
# 用法: ./scripts/build-release.sh <version>    （version 不含前缀 v）
set -euo pipefail

VER="${1:?usage: build-release.sh <version>}"
NAME="WeComHub"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> 构建 $NAME v$VER"
mkdir -p "$DIST"

# 1) 组装插件目录
STAGE="$WORK/$NAME"
mkdir -p "$STAGE/assets"
echo "$VER" > "$STAGE/version"
for f in "$NAME.page" "wecom-hub-save.php" "wecom-hub-update.php" \
         "wecom-hub-notify-agent.sh" "wecom-hub-cmd.py"; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$STAGE/"
done
for f in "$NAME.css" "$NAME.js"; do
  [ -f "$ROOT/assets/$f" ] && cp "$ROOT/assets/$f" "$STAGE/assets/"
done

# 2) 生成 txz
PAYLOAD="$WORK/payload"
mkdir -p "$PAYLOAD/usr/local/emhttp/plugins/$NAME"
cp -a "$STAGE/." "$PAYLOAD/usr/local/emhttp/plugins/$NAME/"
( cd "$PAYLOAD" && tar -cJf "$DIST/$NAME-$VER.txz" . )
echo "    生成 $NAME-$VER.txz"

# 3) 生成 plg（替换版本与 MD5 占位符）
md5_of() { [ -f "$1" ] && md5sum "$1" | awk '{print $1}' || echo ''; }
OUT="$DIST/wecom.hub.plg"
cp "$ROOT/wecom.hub.plg" "$OUT"
sed -i "s/{VERSION}/$VER/g" "$OUT"
for k in MD5_PAGE MD5_CSS MD5_JS MD5_SAVE MD5_UPDATE MD5_AGENT MD5_CMD MD5_RC MD5_AGENTSH; do
  case "$k" in
    MD5_PAGE)    v="$(md5_of "$STAGE/$NAME.page")" ;;
    MD5_CSS)     v="$(md5_of "$STAGE/assets/$NAME.css")" ;;
    MD5_JS)      v="$(md5_of "$STAGE/assets/$NAME.js")" ;;
    MD5_SAVE)    v="$(md5_of "$STAGE/wecom-hub-save.php")" ;;
    MD5_UPDATE)  v="$(md5_of "$STAGE/wecom-hub-update.php")" ;;
    MD5_AGENT)   v="$(md5_of "$STAGE/wecom-hub-notify-agent.sh")" ;;
    MD5_CMD)     v="$(md5_of "$STAGE/wecom-hub-cmd.py")" ;;
    MD5_RC)      v="$(md5_of "$ROOT/scripts/rc.$NAME")" ;;
    MD5_AGENTSH) v="$(md5_of "$ROOT/scripts/notify-agent.sh")" ;;
  esac
  sed -i "s/{$k}/${v}/g" "$OUT"
done
echo "    生成 wecom.hub.plg"

# 4) 版本索引
mkdir -p "$ROOT/versions/v$VER"
cp -a "$STAGE/." "$ROOT/versions/v$VER/" 2>/dev/null || true
cp "$ROOT/scripts/rc.$NAME" "$ROOT/versions/v$VER/" 2>/dev/null || true
cp "$ROOT/scripts/notify-agent.sh" "$ROOT/versions/v$VER/" 2>/dev/null || true
cp "$OUT" "$ROOT/versions/v$VER/wecom.hub.plg" 2>/dev/null || true
cat > "$ROOT/versions/index.json" <<JSON
{
  "name": "$NAME",
  "latest": "$VER",
  "updatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "downloadUrl": "https://github.com/deltrivx/$NAME/releases/download/v$VER/$NAME-$VER.txz",
  "pluginUrl": "https://raw.githubusercontent.com/deltrivx/$NAME/main/wecom.hub.plg"
}
JSON

echo "==> 完成，产物在 $DIST"
ls -la "$DIST"
