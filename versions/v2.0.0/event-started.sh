#!/bin/bash
# WeComHub 开机自启钩子（array started 事件）
#
# 部署位置：/usr/local/emhttp/plugins/dynamix/event/started/zz-wecomhub
#
# 为何需要它：Unraid 的 rc.M 只显式逐个启动已知的 rc 脚本，并不会遍历
# /etc/rc.d/rc.*，因此「只安装 /etc/rc.d/rc.WeComHub」在开机时不会被拉起。
# 由 dynamix 在阵列启动完成后执行本钩子，再转调 rc 脚本，实现零轮询开机自启。
#
# 不依赖 /boot/config/go，不需要 user.scripts 定时轮询。
set -u

RC="/etc/rc.d/rc.WeComHub"
[ -x "$RC" ] || exit 0

"$RC" start >/dev/null 2>&1
exit 0
