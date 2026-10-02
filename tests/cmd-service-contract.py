#!/usr/bin/env python3
"""WeComHub 指令服务契约冒烟测试。

目标：在不启动真实网络端口的前提下，验证 Handler 的路径契约、鉴权、
指令白名单/中文别名、restart 前缀约束与响应码。

契约必须与既有中转侧保持一致（POST /exec -> {"ok": true, "result": ...}），
任何改动都应同步更新本文件。

用法: python3 tests/cmd-service-contract.py
"""
import importlib.util
import io
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD_PATH = os.path.join(ROOT, "wecom-hub-cmd.py")


def load_module():
    """以隔离方式加载 wecom-hub-cmd.py，避免触发 main() 与真实监听。"""
    spec = importlib.util.spec_from_file_location("wecom_hub_cmd", CMD_PATH)
    mod = importlib.util.module_from_spec(spec)

    class FakeHTTPServer:
        def __init__(self, addr, handler):
            pass

        def serve_forever(self):
            raise SystemExit(0)

    http_server = types.ModuleType("http.server")
    http_server.HTTPServer = FakeHTTPServer

    class Base:
        pass

    http_server.BaseHTTPRequestHandler = Base
    sys.modules["http.server"] = http_server
    spec.loader.exec_module(mod)
    return mod


class FakeHandler:
    """拼装一个够用的 Handler 实例，绕过 socket 层。"""

    def make(self, mod, body, headers=None, path="/exec", raw=None):
        if raw is None:
            raw = json.dumps(body).encode("utf-8")
        h = mod.Handler.__new__(mod.Handler)
        h.path = path
        h.headers = {"Content-Length": str(len(raw))} if headers is None else headers
        h.rfile = io.BytesIO(raw)
        h.code = None
        h.body = None

        def send_response(code):
            h.code = code

        def send_header(k, v):
            pass

        def end_headers():
            pass

        h.send_response = send_response
        h.send_header = send_header
        h.end_headers = end_headers
        h.wfile = types.SimpleNamespace(write=lambda b: setattr(h, "body", b.decode("utf-8")))
        return h


def run(mod, token, cmd=None, path="/exec", arg=None, prefix=""):
    """执行一次 do_POST，返回 (code, parsed_json_or_None, raw_body)。"""
    mod.TOKEN = token
    mod.RESTART_ALLOW_PREFIX = prefix
    body = {"token": token}
    if cmd is not None:
        body["cmd"] = cmd
    if arg is not None:
        body["arg"] = arg
    h = FakeHandler().make(mod, body, path=path)
    h.do_POST()
    try:
        parsed = json.loads(h.body)
    except Exception:
        parsed = None
    return h.code, parsed, h.body


def result_of(parsed):
    return parsed.get("result", "") if isinstance(parsed, dict) else ""


def main():
    mod = load_module()
    TOKEN = "RELAY_PUSH_TOKEN"  # 占位符，非真实凭据

    checks = []

    def check(name, cond, extra=""):
        checks.append((name, bool(cond), extra))

    # ---- 路径契约 ----
    code, j, raw = run(mod, TOKEN, "help")
    check("POST /exec 返回 200", code == 200, "code=%s" % code)
    check("/exec 响应为 JSON 且 ok=true", isinstance(j, dict) and j.get("ok") is True, "raw=%r" % raw)
    check("/exec 响应含 result 文本", isinstance(result_of(j), str) and result_of(j) != "", "raw=%r" % raw)

    code, j, raw = run(mod, TOKEN, "help", path="/")
    check("根路径 / 兼容返回 200", code == 200, "code=%s" % code)

    code, j, raw = run(mod, TOKEN, "help", path="/other")
    check("未知路径返回 404", code == 404, "code=%s" % code)
    check("404 响应为 JSON ok=false", isinstance(j, dict) and j.get("ok") is False, "raw=%r" % raw)

    # ---- 鉴权 ----
    code, j, raw = run(mod, TOKEN, "help")
    mod.TOKEN = TOKEN
    h = FakeHandler().make(mod, {"token": "wrong", "cmd": "help"})
    mod.TOKEN = TOKEN
    h.do_POST()
    check("错误令牌返回 403", h.code == 403, "code=%s" % h.code)
    check("403 响应为 JSON ok=false", json.loads(h.body).get("ok") is False, "body=%r" % h.body)

    # fail closed：未配置令牌时拒绝全部
    code, j, raw = run(mod, "", "help")
    check("未配置令牌时 fail closed 403", code == 403, "code=%s" % code)

    # ---- help / 空指令 ----
    code, j, raw = run(mod, TOKEN, "help")
    check("help 返回菜单", "Unraid 指令" in result_of(j), "result=%r" % result_of(j))
    code, j, raw = run(mod, TOKEN, "")
    check("空 cmd 走 help 分支", "Unraid 指令" in result_of(j), "result=%r" % result_of(j))
    code, j, raw = run(mod, TOKEN, "帮助")
    check("中文别名『帮助』可用", "Unraid 指令" in result_of(j), "result=%r" % result_of(j))

    # ---- 白名单存在性 ----
    for c in ("status", "array", "disk", "temp", "docker", "uptime"):
        check("白名单含 %s" % c, c in mod.COMMANDS)

    # ---- 中文别名解析 ----
    for zh, en in [("状态", "status"), ("磁盘", "disk"), ("温度", "temp"),
                   ("容器", "docker"), ("阵列", "array")]:
        resolved = mod.ALIASES.get(zh) or mod.ALIASES.get(zh.lower())
        check("中文别名『%s』解析为 %s" % (zh, en), resolved == en, "resolved=%r" % resolved)

    # ---- 未知指令 ----
    code, j, raw = run(mod, TOKEN, "rm -rf /")
    check("未知指令返回 200 且 ok=true", code == 200 and j.get("ok") is True, "code=%s" % code)
    check("未知指令走拒绝分支", result_of(j).startswith("未知指令:"), "result=%r" % result_of(j))
    check("未知指令不在白名单", "rm -rf /" not in mod.COMMANDS)
    check("未知指令附带菜单", "Unraid 指令" in result_of(j))

    # ---- restart 约束（返回文本，不再是 403 状态码）----
    code, j, raw = run(mod, TOKEN, "重启 nginx", prefix="")
    check("未配置前缀时 restart 被拒（文本）", "禁用" in result_of(j), "result=%r" % result_of(j))

    code, j, raw = run(mod, TOKEN, "重启 nginx", prefix="wecom")
    check("前缀不匹配 restart 被拒（文本）", "不被允许" in result_of(j), "result=%r" % result_of(j))

    # 通配模式：允许任意容器（必须显式配置为 *）
    # 注意：只断言「已通过授权」，不断言 docker 是否可用（CI 容器里 docker 必然不可用）。
    code, j, raw = run(mod, TOKEN, "重启 _definitely_missing_", prefix="*")
    check("通配 * 通过授权（未报未授权）",
          "不被允许" not in result_of(j) and "禁用" not in result_of(j),
          "result=%r" % result_of(j))
    check("通配 * 未报容器名非法", "非法" not in result_of(j), "result=%r" % result_of(j))

    code, j, raw = run(mod, TOKEN, "重启 wecom;rm -rf /", prefix="wecom")
    check("非法容器名被拒（文本）", "非法" in result_of(j), "result=%r" % result_of(j))

    # 通配模式下字符集校验仍然生效（关键安全断言）
    code, j, raw = run(mod, TOKEN, "重启 ;rm -rf /", prefix="*")
    check("通配下非法字符仍被拒", "非法" in result_of(j), "result=%r" % result_of(j))

    # 非 ASCII 容器名必须被拒绝（isalnum() 对中文为 True，须显式限定 ASCII）
    code, j, raw = run(mod, TOKEN, "重启 wecom容器", prefix="wecom")
    check("非 ASCII 容器名被拒", "非法" in result_of(j), "result=%r" % result_of(j))

    code, j, raw = run(mod, TOKEN, "重启", prefix="wecom")
    check("restart 缺参数给出用法", "用法" in result_of(j), "result=%r" % result_of(j))

    code, j, raw = run(mod, TOKEN, "restart wecom-x", prefix="wecom")
    check("英文 restart 亦走重启分支", result_of(j) != "", "result=%r" % result_of(j))

    # ---- 非法 JSON ----
    h = FakeHandler().make(mod, None, headers={"Content-Length": "6"}, path="/exec", raw=b"notjs")
    mod.TOKEN = TOKEN
    h.do_POST()
    check("非法 JSON 返回 400", h.code == 400, "code=%s" % h.code)
    check("400 响应为 JSON ok=false", json.loads(h.body).get("ok") is False, "body=%r" % h.body)

    # ---- 常量时间比较 ----
    check("constant_time_eq 等长相等", mod.constant_time_eq("abc", "abc"))
    check("constant_time_eq 等长不等", not mod.constant_time_eq("abc", "abd"))
    check("constant_time_eq 不等长", not mod.constant_time_eq("abc", "abcd"))

    # ---- 默认端口 ----
    check("默认 LOCAL_CMD_PORT 为 8181", mod.PORT == 8181, "port=%s" % mod.PORT)

    failed = [c for c in checks if not c[1]]
    for name, cond, extra in checks:
        print("%s %s%s" % ("OK  " if cond else "FAIL", name,
                           ("  <- " + extra) if (not cond and extra) else ""))
    print()
    print("==> %d/%d 通过" % (len(checks) - len(failed), len(checks)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
