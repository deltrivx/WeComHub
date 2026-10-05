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
# 通知代理定义：dynamix 扫描 agents/*.xml 后渲染到 设置 → 通知 → 通知代理
[ -d "$ROOT/agents" ] && cp -a "$ROOT/agents" "$STAGE/agents"
# 通知代理图标：48x48 PNG，页面按 <小写名>.png 查找
[ -f "$ROOT/assets/icon-wecomhub.png" ] && cp "$ROOT/assets/icon-wecomhub.png" "$STAGE/" && \
  mv "$STAGE/icon-wecomhub.png" "$STAGE/wecomhub.png"

# 插件页描述：Unraid 插件管理器读取 plugins/<name>/README.md 作为「描述」列
[ -f "$ROOT/README.plugin.md" ] && cp "$ROOT/README.plugin.md" "$STAGE/README.md"
# 脚本目录（开机钩子、rc 脚本等，供 plg 安装钩子调用）
mkdir -p "$STAGE/scripts"
for f in "event-started.sh" "rc.$NAME" "notify-agent.sh" "agent-config-template.sh"; do
  [ -f "$ROOT/scripts/$f" ] && cp "$ROOT/scripts/$f" "$STAGE/scripts/"
done

# 2) 生成 txz
#
# 关键：txz 由 plg 下载到**闪存**（/boot/config/plugins/$NAME/）后由 upgradepkg 本地解包。
# /usr 是内存 overlay，重启即失；因此所有运行时文件都必须进 txz，才能在每次开机时
# 由已在闪存上的包重新还原，**不再依赖开机瞬间的网络**。
# 设计要点（见 DEVELOPMENT.md 第 11 条）：
#   - plugin-manager 对已存在的 FILE 打印 skipping 后**仍会执行 Run**，
#     所以“跳过下载”不等于“跳过解包”。
#   - 用户配置（notifications/agents/$NAME.sh）刻意**不打包**，避免被解包覆盖。
PAYLOAD="$WORK/payload"
PLUGDIR="$PAYLOAD/usr/local/emhttp/plugins/$NAME"
mkdir -p "$PLUGDIR"
cp -a "$STAGE/." "$PLUGDIR/"

# 不在 $STAGE 内、但运行时必需的文件
for sub in "usr/local/emhttp/plugins/dynamix/agents" \
           "usr/local/emhttp/plugins/dynamix/icons" \
           "usr/local/emhttp/plugins/dynamix/event/started" \
           "etc/rc.d"; do
  mkdir -p "$PAYLOAD/$sub"
done

[ -f "$ROOT/agents/$NAME.xml" ] && cp "$ROOT/agents/$NAME.xml" "$PAYLOAD/usr/local/emhttp/plugins/dynamix/agents/$NAME.xml"
[ -f "$ROOT/assets/icon-wecomhub.png" ] && cp "$ROOT/assets/icon-wecomhub.png" "$PAYLOAD/usr/local/emhttp/plugins/dynamix/icons/wecomhub.png"
[ -f "$ROOT/scripts/event-started.sh" ] && cp "$ROOT/scripts/event-started.sh" "$PAYLOAD/usr/local/emhttp/plugins/dynamix/event/started/zz-wecomhub"
[ -f "$ROOT/scripts/rc.$NAME" ] && cp "$ROOT/scripts/rc.$NAME" "$PAYLOAD/etc/rc.d/rc.$NAME"

# ⚠️ 权限与属主必须在打包前显式修正（2026-10-05 实测踩坑）：
# 改为 txz 后，原先每个 <FILE Mode="0755"> 施加的权限**不再生效**，
# tar 会把构建机的文件模式与 uid 原样带进包里。真机解包后：
#   rc.WeComHub 变成 -rw------- 且属主 UNKNOWN:UNKNOWN -> Permission denied，服务根本起不来。
# 因此这里统一 chmod，并用 --owner/--group=0 强制归 root。
chmod 0755 "$PAYLOAD/etc/rc.d/rc.$NAME"
chmod 0755 "$PAYLOAD/usr/local/emhttp/plugins/dynamix/event/started/zz-wecomhub"
chmod 0644 "$PAYLOAD/usr/local/emhttp/plugins/dynamix/agents/$NAME.xml"
chmod 0644 "$PAYLOAD/usr/local/emhttp/plugins/dynamix/icons/wecomhub.png"
find "$PLUGDIR" -type f -name "*.sh" -exec chmod 0755 {} +
find "$PLUGDIR" -type f -name "*.py" -exec chmod 0755 {} +
find "$PLUGDIR" -type f -name "*.php" -exec chmod 0755 {} +
find "$PLUGDIR" -type f -name "*.page" -exec chmod 0755 {} +
find "$PLUGDIR" -type f -name "*.css" -exec chmod 0644 {} +
find "$PLUGDIR" -type f -name "*.js"   -exec chmod 0644 {} +
find "$PLUGDIR" -type f -name "*.md"   -exec chmod 0644 {} +
chmod 0644 "$PLUGDIR/version" 2>/dev/null || true
# 按扩展名匹配会把这两个漏掉：scripts/rc.WeComHub 无扩展名、agents/*.xml 不在 find 列表里
chmod 0755 "$PLUGDIR/scripts/rc.$NAME" 2>/dev/null || true
chmod 0644 "$PLUGDIR/agents/$NAME.xml" 2>/dev/null || true
# 兜底：段内任何其他残留文件一律不再保留 0600（构建机 umask 077 会带进包）
find "$PAYLOAD" -type f ! -perm -0044 -exec chmod 0644 {} + 2>/dev/null || true

( cd "$PAYLOAD" && tar -cJf "$DIST/$NAME-$VER.txz" --owner=0 --group=0 . )
echo "    生成 $NAME-$VER.txz"

# 3) 生成 plg（替换版本与 MD5 占位符）
md5_of() { [ -f "$1" ] && md5sum "$1" | awk '{print $1}' || echo ''; }
OUT="$DIST/wecom.hub.plg"
cp "$ROOT/wecom.hub.plg" "$OUT"
sed -i "s/{VERSION}/$VER/g" "$OUT"
for k in MD5_TXZ MD5_PAGE MD5_CSS MD5_JS MD5_SAVE MD5_UPDATE MD5_AGENT MD5_CMD MD5_RC MD5_AGENTTMPL MD5_EVENT MD5_AGENTXML MD5_README MD5_ICON; do
  case "$k" in
    MD5_TXZ)     v="$(md5_of "$DIST/$NAME-$VER.txz")" ;;
    MD5_PAGE)    v="$(md5_of "$STAGE/$NAME.page")" ;;
    MD5_CSS)     v="$(md5_of "$STAGE/assets/$NAME.css")" ;;
    MD5_JS)      v="$(md5_of "$STAGE/assets/$NAME.js")" ;;
    MD5_SAVE)    v="$(md5_of "$STAGE/wecom-hub-save.php")" ;;
    MD5_UPDATE)  v="$(md5_of "$STAGE/wecom-hub-update.php")" ;;
    MD5_AGENT)   v="$(md5_of "$STAGE/wecom-hub-notify-agent.sh")" ;;
    MD5_CMD)     v="$(md5_of "$STAGE/wecom-hub-cmd.py")" ;;
    MD5_RC)      v="$(md5_of "$ROOT/scripts/rc.$NAME")" ;;
    MD5_AGENTTMPL) v="$(md5_of "$ROOT/scripts/agent-config-template.sh")" ;;
    MD5_EVENT)   v="$(md5_of "$ROOT/scripts/event-started.sh")" ;;
    MD5_AGENTXML) v="$(md5_of "$STAGE/agents/$NAME.xml")" ;;
    MD5_README)  v="$(md5_of "$STAGE/README.md")" ;;
    MD5_ICON)   v="$(md5_of "$STAGE/wecomhub.png")" ;;
  esac
  sed -i "s/{$k}/${v}/g" "$OUT"
done
echo "    生成 wecom.hub.plg"

# 4) 版本索引
mkdir -p "$ROOT/versions/v$VER"
cp -a "$STAGE/." "$ROOT/versions/v$VER/" 2>/dev/null || true
cp "$ROOT/scripts/rc.$NAME" "$ROOT/versions/v$VER/" 2>/dev/null || true
cp "$ROOT/scripts/event-started.sh" "$ROOT/versions/v$VER/" 2>/dev/null || true
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
