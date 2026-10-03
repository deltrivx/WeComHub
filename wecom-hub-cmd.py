#!/usr/bin/env python3
"""WeComHub 本地指令服务。

监听 0.0.0.0:<LOCAL_CMD_PORT>，接收中转服务转来的企业微信指令，
执行只读查询 / 容器重启，返回文本结果。

鉴权：共享令牌（RELAY_PUSH_TOKEN），与通知同源。
配置：/boot/config/plugins/WeComHub/wecom.hub.cfg

对外契约（与既有中转侧保持一致，勿随意变更）：
- POST /exec {"token":..., "cmd":...} -> 200 {"ok": true, "result": "<文本>"}
- 鉴权失败 -> 403 {"ok": false, "err": "forbidden"}
- 非法 JSON -> 400 {"ok": false, "err": "bad json"}
- 未知路径 -> 404 {"ok": false, "err": "not found"}

安全约定：
- 只执行白名单命令，绝不拼接任意 shell。
- 令牌比较使用常量时间比较，避免时序侧信道。
- 未配置令牌时拒绝全部指令（fail closed），避免出现无鉴权的命令端点。
- `restart` 受 RESTART_ALLOW_PREFIX 前缀白名单约束，默认不允许。
"""
import json
import os
import re
import subprocess
import time

from http.server import BaseHTTPRequestHandler, HTTPServer

CFG = "/boot/config/plugins/WeComHub/wecom.hub.cfg"
# 通知代理配置文件：用户在「设置 → 通知 → 通知代理 → WeComHub」填写的值存在这里的变量块，
# 是全插件凭据的唯一来源。指令侧也从这里取令牌，避免两处各填一份。
AGENT_CONF = "/boot/config/plugins/dynamix/notifications/agents/WeComHub.sh"
PORT = int(os.environ.get("LOCAL_CMD_PORT", "8181"))
TOKEN = os.environ.get("RELAY_PUSH_TOKEN", "")

# 命令白名单：指令名 -> (说明, 命令模板)
COMMANDS = {
    "status": ("阵列与系统状态", "mdcmd status | grep -E '^mdState|^mdNumDisks|^mdNumMissing'"),
    "array": ("阵列健康与校验", "mdcmd status | grep -E '^mdState|^mdResync|^mdNumInvalid|^sbNumDisks|^mdNumDisabled'"),
    "disk": ("磁盘使用", "df -h /mnt/user | tail -2"),
    "temp": ("CPU/核心温度", "sensors 2>/dev/null | head -20"),
    "docker": ("运行中容器列表", "docker ps --format 'table {{.Names}}\\t{{.Status}}'"),
    "uptime": ("系统运行时间与负载", "uptime"),
}

# 指令别名：中文菜单与英文指令都可用（既有企微菜单为中文，必须保持兼容）
ALIASES = {
    "status": "status", "状态": "status",
    "array": "array", "阵列": "array",
    "disk": "disk", "磁盘": "disk",
    "temp": "temp", "温度": "temp",
    "docker": "docker", "container": "docker", "containers": "docker", "容器": "docker",
    "uptime": "uptime", "运行时长": "uptime", "负载": "uptime",
    "help": "help", "帮助": "help", "?": "help", "menu": "help",
}

# 允许重启的容器名范围：空串=禁用；"*"=允许任意容器；其他值=前缀匹配
# 详见 wecom-hub-cmd.py 的 restart_container()
RESTART_ALLOW_PREFIX = os.environ.get("RESTART_ALLOW_PREFIX", "")

# 通配值：配置为该值时允许重启任意容器（显式选择，不是默认值）
RESTART_ALLOW_ALL = "*"


def is_placeholder(v: str) -> bool:
    """占位默认值视为未配置。"""
    return v.strip() in ("", "RELAY_PUSH_TOKEN", "RELAY_HOST")


def agent_var(key: str) -> str:
    """从通知代理配置文件的变量块读取一个值（页面 Apply 写入 ####...#### 之间）。"""
    try:
        with open(AGENT_CONF, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return ""
    m = re.search(r"[#]{6,100}(.*?)[#]{6,100}", text, re.S)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""


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
        return (p.stdout or "").strip() or (p.stderr or "").strip() or ""
    except Exception as e:  # noqa: BLE001
        return ""


def _kv(text: str) -> dict:
    """把 key=value 形式的命令输出解析成字典。"""
    d = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def fmt_status() -> str:
    d = _kv(sh("mdcmd status | grep -E '^mdState|^mdNumDisks|^mdNumMissing|^mdResync|^mdNumInvalid'"))
    if not d:
        return "无法读取阵列状态（mdcmd 无输出）。"
    state_map = {"STARTED": "已启动", "STOPPED": "已停止",
                 "NEW_ARRAY": "新阵列", "DISABLED": "已禁用"}
    lines = ["【阵列与系统状态】"]
    st = d.get("mdState", "未知")
    lines.append("阵列状态：%s" % state_map.get(st, st))
    if "mdNumDisks" in d:
        lines.append("已安装磁盘：%s 块" % d["mdNumDisks"])
    if "mdNumMissing" in d:
        lines.append("缺失磁盘：%s 块" % d["mdNumMissing"])
    if d.get("mdResync") not in (None, "", "0"):
        lines.append("正在进行校验/重建：%s" % d["mdResync"])
    if d.get("mdNumInvalid") not in (None, "", "0"):
        lines.append("无效磁盘：%s 块" % d["mdNumInvalid"])
    return "\n".join(lines)


def fmt_array() -> str:
    d = _kv(sh("mdcmd status | grep -E '^mdState|^mdResync|^mdNumInvalid|^sbNumDisks|^mdNumDisabled'"))
    if not d:
        return "无法读取阵列健康信息（mdcmd 无输出）。"
    lines = ["【阵列健康与校验】"]
    st = d.get("mdState", "未知")
    state_map = {"STARTED": "已启动", "STOPPED": "已停止",
                 "NEW_ARRAY": "新阵列", "DISABLED": "已禁用"}
    lines.append("阵列状态：%s" % state_map.get(st, st))
    resync = d.get("mdResync", "0")
    if resync in (None, "", "0"):
        lines.append("校验状态：未在校验")
    else:
        lines.append("校验状态：进行中（%s）" % resync)
    if "sbNumDisks" in d:
        lines.append("缓存池磁盘：%s" % d["sbNumDisks"])
    if "mdNumDisabled" in d:
        lines.append("禁用磁盘：%s" % d["mdNumDisabled"])
    if d.get("mdNumInvalid") not in (None, "", "0"):
        lines.append("无效磁盘：%s" % d["mdNumInvalid"])
    return "\n".join(lines)


def fmt_disk() -> str:
    out = sh("df -h /mnt/user 2>/dev/null | tail -1")
    parts = out.split()
    if len(parts) >= 5:
        return ("【磁盘使用】\n"
                "用户共享总容量：%s\n"
                "已用：%s\n"
                "可用：%s\n"
                "使用率：%s" % (parts[1], parts[2], parts[3], parts[4]))
    return "无法读取磁盘使用情况。"


def fmt_temp() -> str:
    out = sh("sensors 2>/dev/null | head -20")
    if not out:
        return "未检测到温度数据（可能未安装 lm_sensors）。"
    lines = ["【CPU / 核心温度】"]
    for line in out.splitlines():
        if "°C" in line:
            lines.append(line.strip())
    if len(lines) == 1:
        lines.append(out.splitlines()[0].strip())
    return "\n".join(lines[:12])


def fmt_docker() -> str:
    out = sh("docker ps --format '{{.Names}}\t{{.Status}}'")
    if not out:
        return "当前没有正在运行的容器。"
    lines = ["【运行中容器列表】"]
    for row in out.splitlines():
        cols = row.split("\t")
        name = cols[0].strip()
        status = cols[1].strip() if len(cols) > 1 else ""
        # 把常见状态译为中文，其余原样保留（避免丢失信息）
        status_zh = status
        if status.startswith("Up"):
            status_zh = "运行中 " + status[2:].strip()
            if "healthy" in status:
                status_zh = "运行中（健康）"
            elif "unhealthy" in status:
                status_zh = "运行中（不健康）"
        elif status.startswith("Exited"):
            status_zh = "已退出 " + status[6:].strip()
        elif status.startswith("Restarting"):
            status_zh = "重启中"
        lines.append("%s：%s" % (name, status_zh))
    return "\n".join(lines)


def fmt_uptime() -> str:
    out = sh("uptime")
    if not out:
        return "无法读取系统运行时间。"
    text = out
    if " up " in text:
        text = text.split(" up ", 1)[1]
        if "," in text and "load average" in text:
            up_part, load_part = text.split(",", 1)
            load_part = load_part.replace("load average:", "平均负载：").strip()
            return ("【系统运行时间与负载】\n"
                    "运行时长：%s\n"
                    "%s" % (up_part.strip(), load_part))
    return "【系统运行时间与负载】\n" + out


# 指令名 -> 中文格式化函数
FORMATTERS = {
    "status": fmt_status,
    "array": fmt_array,
    "disk": fmt_disk,
    "temp": fmt_temp,
    "docker": fmt_docker,
    "uptime": fmt_uptime,
}


def fmt_help() -> str:
    lines = ["【Unraid 指令】"]
    order = ["status", "array", "disk", "temp", "docker", "uptime"]
    zh = {
        "status": "状态", "array": "阵列", "disk": "磁盘",
        "temp": "温度", "docker": "容器", "uptime": "运行时长",
    }
    for k in order:
        desc = COMMANDS.get(k, ("", ""))[0]
        lines.append("%s / %s - %s" % (zh.get(k, k), k, desc))
    if RESTART_ALLOW_PREFIX == RESTART_ALLOW_ALL:
        lines.append("重启 <容器名> / restart <容器名> - 重启任意容器")
    elif RESTART_ALLOW_PREFIX:
        lines.append("重启 <容器名> / restart <容器名> - 重启指定容器（仅限前缀 %s*）" % RESTART_ALLOW_PREFIX)
    else:
        lines.append("重启 <容器名> - 未启用（未配置 RESTART_ALLOW_PREFIX）")
    lines.append("帮助 / help - 本菜单")
    return "\n".join(lines)


def restart_container(name: str) -> str:
    """重启容器。返回给用户的文本（不抛异常，拒绝原因也以文本回传）。

    授权规则（RESTART_ALLOW_PREFIX）：
      "*"   -> 允许任意容器
      "xxx" -> 仅允许 xxx 前缀的容器
      ""    -> 完全禁用

    无论哪种模式，容器名都必须先通过严格字符集校验，且必须真实存在（走 docker 参数
    而非拼接 shell），因此通配模式不会引入命令注入面。
    """
    name = (name or "").strip()
    if not name:
        return "用法: 重启 <容器名>"

    # 授权：空=禁用；* = 任意；其他 = 前缀匹配
    if not RESTART_ALLOW_PREFIX:
        return "重启已被禁用：请在「设置 → 通知 → 通知代理 → WeComHub」把「允许重启的容器名前缀」设为 * 以允许任意容器"
    if RESTART_ALLOW_PREFIX != RESTART_ALLOW_ALL and not name.startswith(RESTART_ALLOW_PREFIX):
        return "重启不被允许：%s（仅允许前缀 %s*）" % (name, RESTART_ALLOW_PREFIX)

    # 字符集校验：仅 ASCII 字母数字与 . _ -（isalnum() 对中文返回 True，必须显式限定 ASCII）
    if not name.isascii() or not all(c.isalnum() or c in "._-" for c in name):
        return "容器名非法"

    exists = sh("docker ps -a --format '{{.Names}}' | grep -Fx %s" % json.dumps(name))
    if not exists or exists == "(无输出)":
        return "未找到容器: %s" % name
    sh("docker restart %s" % name, timeout=60)
    time.sleep(2)
    st = sh("docker ps --filter name=^/%s$ --format '{{.Status}}'" % name)
    return "【重启】%s → %s" % (name, st if st and st != "(无输出)" else "已执行")


def dispatch(cmd: str) -> str:
    """把指令文本解析并执行，返回结果文本。未知指令返回菜单。"""
    raw = (cmd or "").strip()
    if not raw:
        return fmt_help()

    low = raw.lower()

    # 重启：<前缀> <容器名>，支持中英文
    if low.startswith("重启") or low.startswith("restart"):
        parts = raw.split(None, 1)
        if len(parts) < 2:
            return "用法: 重启 <容器名>"
        return restart_container(parts[1])

    # 白名单查询：中文别名优先按原文匹配，英文按小写匹配
    key = ALIASES.get(raw) or ALIASES.get(low)
    if key == "help":
        return fmt_help()
    if key in COMMANDS:
        # 优先走中文格式化，让回复与中文菜单保持一致；
        # 若某个指令没有对应格式化函数，退回原始 shell 输出（不丢信息）。
        fmt = FORMATTERS.get(key)
        if fmt is not None:
            out = fmt()
            if out:
                return out
        return sh(COMMANDS[key][1]) or "（无输出）"
    return "未知指令: %s\n\n%s" % (raw, fmt_help())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 静音默认访问日志
        pass

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        # 路径契约：中转侧固定调用 /exec；根路径保留以兼容旧调用方
        path = (self.path or "/").rstrip("/") or "/"
        if path not in ("/exec", "/"):
            self._send_json(404, {"ok": False, "err": "not found"})
            return

        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:  # noqa: BLE001
            self._send_json(400, {"ok": False, "err": "bad json"})
            return

        # fail closed：未配置令牌时拒绝全部指令
        if not TOKEN or not constant_time_eq(str(data.get("token", "")), TOKEN):
            self._send_json(403, {"ok": False, "err": "forbidden"})
            return

        self._send_json(200, {"ok": True, "result": dispatch(data.get("cmd", ""))})


def main():
    global PORT, TOKEN, RESTART_ALLOW_PREFIX
    cfg_token = ""
    if os.path.exists(CFG):
        for line in open(CFG, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k == "LOCAL_CMD_PORT" and v.isdigit():
                    PORT = int(v)
                elif k == "RELAY_PUSH_TOKEN":
                    cfg_token = v
                elif k == "RESTART_ALLOW_PREFIX":
                    RESTART_ALLOW_PREFIX = v

    # 令牌优先取通知代理配置文件（用户填写处），cfg 里的旧值作为兼容回退
    agent_token = agent_var("RELAY_PUSH_TOKEN")
    if not is_placeholder(agent_token):
        TOKEN = agent_token
    elif not is_placeholder(cfg_token):
        TOKEN = cfg_token
    else:
        TOKEN = ""

    if not TOKEN:
        print("[%s] WARN 未配置推送令牌，指令服务将拒绝全部请求。"
              "请在「设置 → 通知 → 通知代理 → WeComHub」填写 Push Token 后 Apply。" % (
                  time.strftime("%Y-%m-%d %H:%M:%S")), flush=True)

    print("[%s] WeComHub cmd service on :%d" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), PORT), flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
