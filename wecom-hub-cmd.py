#!/usr/bin/env python3
"""WeComHub 2.0 企业微信中枢本地服务

集成企业微信入站验签解密、指令白名单执行、出站消息推送与菜单同步。
零外部依赖（纯 Python 标准库），自闭环运行在 Unraid 宿主机。
"""
import base64
import hashlib
import json
import os
import re
import struct
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

CFG = "/boot/config/plugins/WeComHub/wecom.hub.cfg"
AGENT_CONF = "/boot/config/plugins/dynamix/notifications/agents/WeComHub.sh"
LOG = "/var/log/wecom-hub.log"
PORT = 8181
TOKEN = ""

def constant_time_eq(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    r = 0
    for x, y in zip(a, b):
        r |= ord(x) ^ ord(y)
    return r == 0


# ---------- 纯 Python AES-256-CBC 实现 (零依赖) ----------
s_box = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]
inv_s_box = [0] * 256
for _i, _v in enumerate(s_box):
    inv_s_box[_v] = _i
rcon = [0, 1, 2, 4, 8, 16, 32, 64, 128, 27, 54, 108, 216, 171, 77, 154]

def _sub_word(w):
    return ((s_box[(w >> 24) & 0xff] << 24) |
            (s_box[(w >> 16) & 0xff] << 16) |
            (s_box[(w >> 8) & 0xff] << 8) |
            s_box[w & 0xff])

def _rot_word(w):
    return ((w << 8) & 0xffffffff) | ((w >> 24) & 0xff)

def _expand_key(key):
    w = []
    for i in range(8):
        w.append((key[4*i] << 24) | (key[4*i+1] << 16) | (key[4*i+2] << 8) | key[4*i+3])
    for i in range(8, 60):
        temp = w[i-1]
        if i % 8 == 0:
            temp = _sub_word(_rot_word(temp)) ^ (rcon[i // 8] << 24)
        elif i % 8 == 4:
            temp = _sub_word(temp)
        w.append(w[i-8] ^ temp)
    round_keys = []
    for i in range(15):
        rk = []
        for j in range(4):
            word = w[4*i + j]
            rk.extend([(word >> 24) & 0xff, (word >> 16) & 0xff, (word >> 8) & 0xff, word & 0xff])
        round_keys.append(rk)
    return round_keys

def _xtime(a):
    return ((a << 1) ^ 0x1b) & 0xff if (a & 0x80) else (a << 1)

def _mul(a, b):
    res = 0
    while b:
        if b & 1: res ^= a
        a = _xtime(a)
        b >>= 1
    return res

def _inv_mix_columns(s):
    res = [0] * 16
    for c in range(4):
        i = 4 * c
        s0, s1, s2, s3 = s[i], s[i+1], s[i+2], s[i+3]
        res[i]   = _mul(s0, 0x0e) ^ _mul(s1, 0x0b) ^ _mul(s2, 0x0d) ^ _mul(s3, 0x09)
        res[i+1] = _mul(s0, 0x09) ^ _mul(s1, 0x0e) ^ _mul(s2, 0x0b) ^ _mul(s3, 0x0d)
        res[i+2] = _mul(s0, 0x0d) ^ _mul(s1, 0x09) ^ _mul(s2, 0x0e) ^ _mul(s3, 0x0b)
        res[i+3] = _mul(s0, 0x0b) ^ _mul(s1, 0x0d) ^ _mul(s2, 0x09) ^ _mul(s3, 0x0e)
    return res

def _decrypt_block(block, round_keys):
    state = list(block)
    state = [s ^ k for s, k in zip(state, round_keys[14])]
    for r in range(13, 0, -1):
        state = [
            state[0], state[13], state[10], state[7],
            state[4], state[1], state[14], state[11],
            state[8], state[5], state[2], state[15],
            state[12], state[9], state[6], state[3],
        ]
        state = [inv_s_box[b] for b in state]
        state = [s ^ k for s, k in zip(state, round_keys[r])]
        state = _inv_mix_columns(state)
    state = [
        state[0], state[13], state[10], state[7],
        state[4], state[1], state[14], state[11],
        state[8], state[5], state[2], state[15],
        state[12], state[9], state[6], state[3],
    ]
    state = [inv_s_box[b] for b in state]
    return bytes([s ^ k for s, k in zip(state, round_keys[0])])

def aes_256_cbc_decrypt(ciphertext, key, iv):
    rks = _expand_key(key)
    plaintext = bytearray()
    prev = iv
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i+16]
        dec = _decrypt_block(block, rks)
        plaintext.extend(bytes([d ^ p for d, p in zip(dec, prev)]))
        prev = block
    return bytes(plaintext)

def wecom_decrypt(b64, aes_key):
    k = base64.b64decode(aes_key + "=")
    cipher = base64.b64decode(b64)
    raw = aes_256_cbc_decrypt(cipher, k, k[:16])
    pad = raw[-1]
    raw = raw[:-pad]
    n = struct.unpack("!I", raw[16:20])[0]
    return raw[20:20 + n].decode("utf-8", "replace")

# ---------- 状态与日志 ----------
_CONFIG = {}
_TK = {"v": None, "exp": 0, "lock": threading.Lock()}

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)

# ---------- 配置加载 ----------
def load_config():
    global _CONFIG, PORT, TOKEN
    cfg = {}
    if os.path.exists(CFG):
        for line in open(CFG, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    if os.environ.get("LOCAL_CMD_PORT"):
        cfg["LOCAL_CMD_PORT"] = os.environ.get("LOCAL_CMD_PORT")
    _CONFIG = cfg
    if cfg.get("LOCAL_CMD_PORT", "").isdigit():
        PORT = int(cfg["LOCAL_CMD_PORT"])
    TOKEN = cfg.get("RELAY_PUSH_TOKEN") or cfg.get("WECOM_TOKEN") or ""
    return cfg

def get_cfg(k, default=""):
    return _CONFIG.get(k, default)
def apply_config():
    global _CONFIG, PORT, TOKEN
    res = load_config()
    if isinstance(res, tuple):
        p, t, pref = res
        _CONFIG["LOCAL_CMD_PORT"] = str(p)
        _CONFIG["RELAY_PUSH_TOKEN"] = t
        _CONFIG["WECOM_TOKEN"] = t
        _CONFIG["RESTART_ALLOW_PREFIX"] = pref
        PORT = p
        TOKEN = t
        return p, t, pref
    return PORT, TOKEN, get_cfg("RESTART_ALLOW_PREFIX", "*")


# ---------- 企微 API 通信 ----------
def get_qyapi_base():
    host = get_cfg("RELAY_HOST", "").strip()
    port = get_cfg("RELAY_PORT", "").strip()
    if host and port:
        return "http://%s:%s/cgi-bin" % (host, port)
    return "https://qyapi.weixin.qq.com/cgi-bin"

def get_access_token():
    with _TK["lock"]:
        now = time.time()
        if _TK["v"] and now < _TK["exp"] - 120:
            return _TK["v"]
        corpid = get_cfg("WECOM_CORP_ID")
        secret = get_cfg("WECOM_SECRET")
        if not corpid or not secret:
            raise RuntimeError("未配置 WECOM_CORP_ID 或 WECOM_SECRET")
        base = get_qyapi_base()
        q = urllib.parse.urlencode({"corpid": corpid, "corpsecret": secret})
        url = "%s/gettoken?%s" % (base, q)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
        if d.get("errcode") != 0:
            raise RuntimeError("gettoken 失败: %s" % d)
        _TK["v"] = d["access_token"]
        _TK["exp"] = now + int(d.get("expires_in", 7200))
        return _TK["v"]

def send_wecom(text, touser="@all"):
    tk = get_access_token()
    agentid = int(get_cfg("WECOM_AGENT_ID", "1000007"))
    payload = {
        "touser": touser,
        "msgtype": "text",
        "agentid": agentid,
        "text": {"content": text}
    }
    base = get_qyapi_base()
    url = "%s/message/send?access_token=%s" % (base, tk)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def sync_menu():
    tk = get_access_token()
    agentid = int(get_cfg("WECOM_AGENT_ID", "1000007"))
    menu_data = {
        "button": [
            {
                "name": "状态查询",
                "sub_button": [
                    {"type": "click", "name": "运行状态", "key": "状态"},
                    {"type": "click", "name": "磁盘用量", "key": "磁盘"},
                    {"type": "click", "name": "温度", "key": "温度"}
                ]
            },
            {
                "name": "阵列",
                "sub_button": [
                    {"type": "click", "name": "阵列健康", "key": "阵列"},
                    {"type": "click", "name": "容器列表", "key": "容器"}
                ]
            },
            {
                "type": "click",
                "name": "帮助",
                "key": "帮助"
            }
        ]
    }
    base = get_qyapi_base()
    url = "%s/menu/create?access_token=%s&agentid=%d" % (base, tk, agentid)
    req = urllib.request.Request(url, data=json.dumps(menu_data, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

# ---------- 指令白名单与执行 (原有成熟逻辑，100% 保持) ----------
COMMANDS = {
    "status": ("阵列与系统状态", "mdcmd status | grep -E '^mdState|^mdNumDisks|^mdNumMissing'"),
    "array": ("阵列健康与校验", "mdcmd status | grep -E '^mdState|^mdResync|^mdNumInvalid|^sbNumDisks|^mdNumDisabled'"),
    "disk": ("磁盘使用", "df -h /mnt/user | tail -2"),
    "temp": ("CPU/核心温度", "sensors 2>/dev/null | head -20"),
    "docker": ("运行中容器列表", "docker ps --format 'table {{.Names}}\\t{{.Status}}'"),
    "uptime": ("系统运行时间与负载", "uptime"),
}

ALIASES = {
    "status": "status", "状态": "status",
    "array": "array", "阵列": "array",
    "disk": "disk", "磁盘": "disk",
    "temp": "temp", "温度": "temp",
    "docker": "docker", "container": "docker", "containers": "docker", "容器": "docker",
    "uptime": "uptime", "运行时长": "uptime", "负载": "uptime",
    "help": "help", "帮助": "help", "?": "help", "menu": "help",
}

def sh(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "").strip() or (p.stderr or "").strip() or ""
    except Exception:
        return ""

def _kv(text):
    d = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d

def fmt_status():
    d = _kv(sh("mdcmd status | grep -E '^mdState|^mdNumDisks|^mdNumMissing|^mdResync|^mdNumInvalid'"))
    if not d: return "无法读取阵列状态（mdcmd 无输出）。"
    state_map = {"STARTED": "已启动", "STOPPED": "已停止", "NEW_ARRAY": "新阵列", "DISABLED": "已禁用"}
    lines = ["【阵列与系统状态】"]
    st = d.get("mdState", "未知")
    lines.append("阵列状态：%s" % state_map.get(st, st))
    if "mdNumDisks" in d: lines.append("已安装磁盘：%s 块" % d["mdNumDisks"])
    if "mdNumMissing" in d: lines.append("缺失磁盘：%s 块" % d["mdNumMissing"])
    if d.get("mdResync") not in (None, "", "0"): lines.append("正在进行校验/重建：%s" % d["mdResync"])
    return "\n".join(lines)

def fmt_array():
    d = _kv(sh("mdcmd status | grep -E '^mdState|^mdResync|^mdNumInvalid|^sbNumDisks|^mdNumDisabled'"))
    if not d: return "无法读取阵列健康信息（mdcmd 无输出）。"
    lines = ["【阵列健康与校验】"]
    st = d.get("mdState", "未知")
    state_map = {"STARTED": "已启动", "STOPPED": "已停止", "NEW_ARRAY": "新阵列", "DISABLED": "已禁用"}
    lines.append("阵列状态：%s" % state_map.get(st, st))
    resync = d.get("mdResync", "0")
    lines.append("校验状态：未在校验" if resync in (None, "", "0") else "校验状态：进行中（%s）" % resync)
    if "sbNumDisks" in d: lines.append("缓存池磁盘：%s" % d["sbNumDisks"])
    if "mdNumDisabled" in d: lines.append("禁用磁盘：%s" % d["mdNumDisabled"])
    return "\n".join(lines)

def fmt_disk():
    out = sh("df -h /mnt/user 2>/dev/null | tail -1")
    parts = out.split()
    if len(parts) >= 5:
        return ("【磁盘使用】\n总容量：%s\n已用：%s\n可用：%s\n使用率：%s" % (parts[1], parts[2], parts[3], parts[4]))
    return "无法读取磁盘使用情况。"

def fmt_temp():
    out = sh("sensors 2>/dev/null | head -20")
    if not out: return "未检测到温度数据。"
    lines = ["【CPU / 核心温度】"]
    for line in out.splitlines():
        if "°C" in line: lines.append(line.strip())
    return "\n".join(lines[:12]) if len(lines) > 1 else "【CPU 温度】\n" + out.splitlines()[0]

def fmt_docker():
    out = sh("docker ps --format '{{.Names}}\\t{{.Status}}'")
    if not out: return "当前没有正在运行的容器。"
    lines = ["【运行中容器列表】"]
    for row in out.splitlines():
        cols = row.split("\t")
        name = cols[0].strip()
        status = cols[1].strip() if len(cols) > 1 else ""
        if status.startswith("Up"):
            status = "运行中 " + status[2:].strip()
            if "healthy" in status: status = "运行中（健康）"
        elif status.startswith("Exited"): status = "已退出 " + status[6:].strip()
        lines.append("%s：%s" % (name, status))
    return "\n".join(lines)

def fmt_uptime():
    out = sh("uptime")
    if not out: return "无法读取系统运行时间。"
    if " up " in out:
        up = out.split(" up ", 1)[1]
        if "," in up and "load average" in up:
            up_part, load_part = up.split(",", 1)
            return "【系统运行时间与负载】\n运行时长：%s\n%s" % (up_part.strip(), load_part.replace("load average:", "平均负载：").strip())
    return "【系统运行时间与负载】\n" + out

FORMATTERS = {
    "status": fmt_status, "array": fmt_array, "disk": fmt_disk,
    "temp": fmt_temp, "docker": fmt_docker, "uptime": fmt_uptime,
}

def fmt_help():
    lines = ["【Unraid 指令菜单】"]
    order = ["status", "array", "disk", "temp", "docker", "uptime"]
    zh = {"status": "状态", "array": "阵列", "disk": "磁盘", "temp": "温度", "docker": "容器", "uptime": "运行时长"}
    for k in order:
        desc = COMMANDS.get(k, ("", ""))[0]
        lines.append("%s / %s - %s" % (zh.get(k, k), k, desc))
    prefix = get_cfg("RESTART_ALLOW_PREFIX", "*")
    if prefix == "*": lines.append("重启 <容器名> - 重启任意容器")
    elif prefix: lines.append("重启 <容器名> - 重启指定容器（前缀 %s*）" % prefix)
    else: lines.append("重启 <容器名> - 未启用")
    lines.append("帮助 / help - 本菜单")
    return "\n".join(lines)

def restart_container(name):
    name = (name or "").strip()
    if not name: return "用法: 重启 <容器名>"
    prefix = get_cfg("RESTART_ALLOW_PREFIX", "*")
    if not prefix: return "重启已被禁用（未配置允许前缀）"
    if prefix != "*" and not name.startswith(prefix):
        return "重启不被允许：%s（仅允许前缀 %s*）" % (name, prefix)
    if not name.isascii() or not all(c.isalnum() or c in "._-" for c in name):
        return "容器名非法"
    exists = sh("docker ps -a --format '{{.Names}}' | grep -Fx %s" % json.dumps(name))
    if not exists: return "未找到容器: %s" % name
    sh("docker restart %s" % name, timeout=60)
    time.sleep(2)
    st = sh("docker ps --filter name=^/%s$ --format '{{.Status}}'" % name)
    return "【重启】%s → %s" % (name, st or "已执行")

def dispatch(cmd):
    raw = (cmd or "").strip()
    if not raw: return fmt_help()
    low = raw.lower()
    if low.startswith("重启") or low.startswith("restart"):
        parts = raw.split(None, 1)
        if len(parts) < 2: return "用法: 重启 <容器名>"
        return restart_container(parts[1])
    key = ALIASES.get(raw) or ALIASES.get(low)
    if key == "help": return fmt_help()
    if key in COMMANDS:
        fmt = FORMATTERS.get(key)
        if fmt:
            out = fmt()
            if out: return out
        return sh(COMMANDS[key][1]) or "（无输出）"
    return "未知指令: %s\n\n%s" % (raw, fmt_help())

def handle_incoming_wecom(plain):
    try:
        root = ET.fromstring(plain)
        from_user = (root.findtext("FromUserName") or "").strip()
        msg_type = (root.findtext("MsgType") or "").strip()
        content = (root.findtext("Content") or "").strip()
        event = (root.findtext("Event") or "").strip()
        event_key = (root.findtext("EventKey") or "").strip()
        if msg_type == "event":
            cmd = event_key or "帮助" if event == "click" else ("帮助" if event in ("subscribe", "enter_agent") else "")
        elif msg_type == "text":
            cmd = content
        else:
            return
        if not cmd or not from_user: return
        log("CALLBACK RECV user=%s cmd=%r" % (from_user, cmd))
        res = dispatch(cmd)
        send_res = send_wecom(res, from_user)
        log("CALLBACK REPLY user=%s errcode=%s" % (from_user, send_res.get("errcode")))
    except Exception as e:
        log("CALLBACK FAIL err=%s" % e)

# ---------- HTTP 服务 ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _send_json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _q(self):
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

    def do_GET(self):
        load_config()
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        q = self._q()

        # 企微 URL 验证 (echostr)
        if "echostr" in q:
            token = get_cfg("WECOM_TOKEN")
            aes_key = get_cfg("WECOM_AES_KEY")
            sig = q.get("msg_signature", [""])[0]
            ts = q.get("timestamp", [""])[0]
            nonce = q.get("nonce", [""])[0]
            echo = q.get("echostr", [""])[0]
            calc = hashlib.sha1("".join(sorted([token, ts, nonce, echo])).encode()).hexdigest()
            if calc != sig:
                log("GET echostr sig mismatch")
                return self._send(403, "sig mismatch")
            try:
                plain = wecom_decrypt(echo, aes_key)
                log("GET echostr verify OK: %s" % plain)
                return self._send(200, plain)
            except Exception as e:
                log("GET echostr decrypt FAIL: %s" % e)
                return self._send(500, "decrypt fail")

        if path == "/api/status":
            return self._send_json(200, {
                "ok": True,
                "status": "running",
                "port": int(get_cfg("LOCAL_CMD_PORT", "8181")),
                "agent_id": get_cfg("WECOM_AGENT_ID", ""),
                "corp_id": get_cfg("WECOM_CORP_ID", ""),
                "has_secret": bool(get_cfg("WECOM_SECRET")),
                "has_token": bool(get_cfg("WECOM_TOKEN")),
                "has_aes_key": bool(get_cfg("WECOM_AES_KEY")),
            })

        if path == "/api/recent_logs":
            lines = []
            if os.path.exists(LOG):
                try:
                    all_lines = open(LOG, encoding="utf-8", errors="ignore").readlines()
                    lines = [l.strip() for l in all_lines[-20:] if l.strip()]
                except Exception:
                    pass
            return self._send_json(200, {"ok": True, "logs": lines})

        self._send(200, "WeComHub 2.0 is running")

    def do_POST(self):
        apply_config()
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        q = self._q()
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""

        # 1. WeCom XML 回调：包含 msg_signature 且包含 Encrypt，或 raw 以 <xml 开头
        if "msg_signature" in q or raw.strip().startswith(b"<xml"):
            token = get_cfg("WECOM_TOKEN")
            aes_key = get_cfg("WECOM_AES_KEY")
            sig = q.get("msg_signature", [""])[0]
            ts = q.get("timestamp", [""])[0]
            nonce = q.get("nonce", [""])[0]
            try:
                root = ET.fromstring(raw.decode("utf-8", "replace"))
                enc = (root.findtext("Encrypt") or "").strip()
                calc = hashlib.sha1("".join(sorted([token, ts, nonce, enc])).encode()).hexdigest()
                if calc != sig:
                    log("POST sig mismatch")
                    return self._send(200, "ok")
                plain = wecom_decrypt(enc, aes_key)
                threading.Thread(target=handle_incoming_wecom, args=(plain,), daemon=True).start()
            except Exception as e:
                log("POST parse/decrypt fail %s" % e)
            return self._send(200, "ok")

        # 2. 内部 API
        if path == "/api/test_send":
            try:
                p = json.loads(raw.decode("utf-8")) if raw else {}
                touser = p.get("touser", "@all")
                res = send_wecom("【WeComHub】测试消息发送成功！当前时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"), touser)
                log("TEST_SEND res=%s" % res)
                return self._send_json(200, {"ok": res.get("errcode") == 0, "res": res})
            except Exception as e:
                log("TEST_SEND FAIL err=%s" % e)
                return self._send_json(500, {"ok": False, "error": str(e)})

        if path == "/api/sync_menu":
            try:
                res = sync_menu()
                log("SYNC_MENU res=%s" % res)
                return self._send_json(200, {"ok": res.get("errcode") == 0, "res": res})
            except Exception as e:
                log("SYNC_MENU FAIL err=%s" % e)
                return self._send_json(500, {"ok": False, "error": str(e)})

        if path == "/notify":
            try:
                p = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                return self._send_json(400, {"ok": False, "err": "bad json"})
            token = get_cfg("RELAY_PUSH_TOKEN") or get_cfg("WECOM_TOKEN")
            if token and p.get("token") != token:
                return self._send_json(403, {"ok": False, "err": "forbidden"})
            text = p.get("text", "")
            if not text:
                return self._send_json(400, {"ok": False, "err": "empty text"})
            try:
                res = send_wecom(text, p.get("touser", "@all"))
                log("NOTIFY_RELAY errcode=%s" % res.get("errcode"))
                return self._send_json(200, {"ok": True, "res": res})
            except Exception as e:
                log("NOTIFY_RELAY FAIL %s" % e)
                return self._send_json(502, {"ok": False, "err": str(e)})

        # 3. /exec 与根路径 / (JSON 指令契约)
        if path in ("/exec", "/"):
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                return self._send_json(400, {"ok": False, "err": "bad json"})
            token = get_cfg("RELAY_PUSH_TOKEN") or get_cfg("WECOM_TOKEN")
            req_token = str(data.get("token", ""))
            if not token or not constant_time_eq(req_token, token):
                return self._send_json(403, {"ok": False, "err": "forbidden"})
            cmd = data.get("cmd", "")
            return self._send_json(200, {"ok": True, "result": dispatch(cmd)})

        # 4. 未知路径
        self._send_json(404, {"ok": False, "err": "not found"})
        return

def main():
    apply_config()
    server = None
    bound_port = None
    log("Starting WeComHub 2.0 service on port %d" % PORT)
    while True:
        apply_config()
        port = PORT
        if server is None or port != bound_port:
            if server is not None:
                server.server_close()
                log("端口变更 %s -> %s，已重新监听" % (bound_port, port))
            try:
                server = HTTPServer(("", port), Handler)
            except OSError as e:
                log("监听端口 %s 失败: %s" % (port, e))
                if server is None:
                    raise
                continue
            bound_port = port
            log("WeComHub 2.0 cmd service listening on :%d" % port)
        server.handle_request()

if __name__ == "__main__":
    main()
