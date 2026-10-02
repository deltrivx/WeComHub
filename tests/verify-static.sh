#!/bin/bash
# WeComHub 本地静态自检
#
# 覆盖与 .github/workflows/verify.yml 相同的检查项，便于提交前本地跑一遍。
# 用法: ./tests/verify-static.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
ok()   { echo "OK   $*"; }
bad()  { echo "FAIL $*"; fail=1; }

echo "==> Shell 语法"
while IFS= read -r f; do
  bash -n "$f" && ok "$f" || bad "$f"
done < <(find . -name '*.sh' -not -path './.git/*')

echo "==> Python 语法"
while IFS= read -r f; do
  python3 -m py_compile "$f" && ok "$f" || bad "$f"
done < <(find . -name '*.py' -not -path './.git/*')

echo "==> XML / PLG 合法性"
python3 - <<'PY'
import glob, sys, xml.etree.ElementTree as ET
bad = 0
for f in sorted(glob.glob('**/*.xml', recursive=True) + glob.glob('**/*.plg', recursive=True)):
    if '/.git/' in f:
        continue
    try:
        ET.parse(f)
        print('OK   %s' % f)
    except Exception as e:
        print('FAIL %s %s' % (f, e))
        bad = 1
sys.exit(bad)
PY
[ $? -eq 0 ] || fail=1

echo "==> JSON 合法性"
while IFS= read -r f; do
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" && ok "$f" || bad "$f"
done < <(find . -name '*.json' -not -path './.git/*')

echo "==> PHP 语法"
if command -v php >/dev/null 2>&1; then
  while IFS= read -r f; do
    php -l "$f" >/dev/null && ok "$f" || bad "$f"
  done < <(find . -name '*.php' -not -path './.git/*')
else
  echo "SKIP php 未安装"
fi

echo "==> 真实凭据扫描"
# 仓库不得包含真实凭据；只允许出现占位符 RELAY_HOST / RELAY_PORT / RELAY_PUSH_TOKEN / LOCAL_CMD_PORT
if grep -rInE "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,})" \
     --exclude-dir=.git . ; then
  bad "发现疑似真实凭据"
else
  ok "无 sk-/ghp_/gho_ 前缀真实 token"
fi

echo "==> PLG 占位符完整性"
# 仓库内的 wecom.hub.plg 是模板，构建时替换；这里只检查占位符成对出现
python3 - <<'PY'
import re, sys
src = open('wecom.hub.plg', encoding='utf-8').read()
keys = set(re.findall(r'\{(MD5_[A-Z0-9_]+)\}', src))
print('OK   发现 %d 个 MD5 占位符' % len(keys)) if keys else print('FAIL 未发现 MD5 占位符')
sys.exit(0 if keys else 1)
PY
[ $? -eq 0 ] || fail=1

echo
if [ "$fail" -eq 0 ]; then
  echo "==> 全部通过"
else
  echo "==> 存在失败项"
fi
exit "$fail"
