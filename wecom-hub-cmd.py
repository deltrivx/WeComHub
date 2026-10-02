#!/usr/bin/env python3
"""WeComHub 本地指令服务。

监听 0.0.0.0:<LOCAL_CMD_PORT>，接收中转服务转来的企业微信指令，
执行只读查询 / 容器重启，返回文本结果。

鉴权：共享令牌（RELAY_PUSH_TOKEN），与通知同源。
配置：/boot/config/plugins/WeComHub/wecom.hub.cfg

安全约定：
- 只执行白名单命令，绝不拼接任意 shell。
- 令牌比较使用常量时间比较，避免时序侧信道。
"""
import json
import os
import subprocess
import time

from http.server import BaseHTTPRequestHandler, HTTPServer

CFG = "/boot/config/plugins/WeComHub/wecom.hub.cfg"
PORT = int(os.environ.get("LOCAL_CMD_PORT", "8181"))
TOKEN = os.environ.get("RELAY_PUSH_TOKEN", "")

# 命令白名单：指令名 -> (说明, 命令模板)
COMMANDS = {
    "status": ("阵列/磁盘/容器概览", "mdcmd status | grep -E '^mdState|^mdNumDisks|^mdNumMissing'"),
    "docker": ("容器列表", "docker ps --format 'table {{.Names}}\\t{{.Status}}'"),
    "uptime": ("系统运行时间", "uptime"),
    "disk": ("磁盘使用", "df -h /mnt/user | tail -2"),
}

# 允许重启的容器名前缀（避免任意容器被操作）
RESTART_ALLOW_PREFIX = os.environ.get("RESTART_ALLOW_PREFIX", "")


def constant_time_eq(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    r = 0
    for x, y in zip(a, b):
        r |= ord(x) ^ ord(y)
    return r == 0


def sh(cmd: str, timeout: int = 15) -> str:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return (p.stdout or "").strip() or (p.stderr or "").strip() or "(无输出)"
    except Exception as e:  # noqa: BLE001
        return "执行失败: %s" % e


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 静音默认访问日志
        pass

    def _send(self, code: int, text: str):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            data = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            self._send(400, "bad request")
            return

        if not constant_time_eq(str(data.get("token", "")), TOKEN):
            self._send(403, "forbidden")
            return

        cmd = str(data.get("cmd", "")).strip().lower()
        arg = str(data.get("arg", "")).strip()

        if cmd == "help" or cmd == "":
            lines = ["可用指令："]
            for k, (desc, _) in COMMANDS.items():
                lines.append("  %-8s %s" % (k, desc))
            if RESTART_ALLOW_PREFIX:
                lines.append("  restart  重启容器（仅限前缀 %s*）" % RESTART_ALLOW_PREFIX)
            self._send(200, "\n".join(lines))
            return

        if cmd == "restart":
            if not RESTART_ALLOW_PREFIX or not arg.startswith(RESTART_ALLOW_PREFIX):
                self._send(403, "restart 不被允许：%s" % (arg or "(空)"))
                return
            if not arg.isalnum() and not all(c.isalnum() or c in "-_" for c in arg):
                self._send(400, "非法容器名")
                return
            self._send(200, sh("docker restart %s" % arg, timeout=60))
            return

        if cmd in COMMANDS:
            self._send(200, sh(COMMANDS[cmd][1]))
            return

        self._send(404, "未知指令: %s（发送 help 查看）" % cmd)


def main():
    global PORT
    if os.path.exists(CFG):
        for line in open(CFG, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k == "LOCAL_CMD_PORT" and v.isdigit():
                    PORT = int(v)
                if k == "RELAY_PUSH_TOKEN":
                    globals()["TOKEN"] = v

    print("[%s] WeComHub cmd service on :%d" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), PORT), flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
