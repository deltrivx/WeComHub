#!/usr/bin/env python3
"""WeComHub 指令服务契约冒烟测试。

目标：在不启动真实网络端口的前提下，验证 Handler 的鉴权、白名单、
参数校验与响应码契约。通过直接构造 Handler 并注入假的 rfile/headers 实现。

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
    """以隔离方式加载 wecom-hub-cmd.py，避免触发 main()。"""
    spec = importlib.util.spec_from_file_location("wecom_hub_cmd", CMD_PATH)
    mod = importlib.util.module_from_spec(spec)
    # 阻止 serve_forever：把 HTTPServer 换成记录参数的假对象
    captured = {}

    class FakeHTTPServer:
        def __init__(self, addr, handler):
            captured["addr"] = addr
            captured["handler"] = handler

        def serve_forever(self):
            raise SystemExit(0)

    http_server = types.ModuleType("http.server")
    http_server.HTTPServer = FakeHTTPServer

    class Base:
        pass

    http_server.BaseHTTPRequestHandler = Base
    sys.modules["http.server"] = http_server
    spec.loader.exec_module(mod)
    return mod, captured


class FakeHandler:
    """拼装一个够用的 Handler 实例，绕过 socket 层。"""

    def make(self, mod, body: dict, headers=None):
        raw = json.dumps(body).encode("utf-8")
        h = mod.Handler.__new__(mod.Handler)
        h.headers = {"Content-Length": str(len(raw))} if headers is None else headers
        h.rfile = io.BytesIO(raw)
        h.code = None
        h.body = None
        h._sent = {}

        def send_response(code):
            h.code = code

        def send_header(k, v):
            h._sent[k] = v

        def end_headers():
            pass

        def wfile_write(b):
            h.body = b.decode("utf-8")

        h.send_response = send_response
        h.send_header = send_header
        h.end_headers = end_headers
        h.wfile = types.SimpleNamespace(write=wfile_write)
        return h


def run(mod, token, body, headers=None):
    h = FakeHandler().make(mod, body, headers)
    mod.TOKEN = token
    h.do_POST()
    return h.code, h.body


def main():
    mod, captured = load_module()
    mod.RESTART_ALLOW_PREFIX = ""
    TOKEN = "RELAY_PUSH_TOKEN"  # 占位符，非真实凭据

    checks = []

    def check(name, cond, extra=""):
        checks.append((name, cond, extra))

    # 1. 鉴权失败
    code, body = run(mod, TOKEN, {"token": "wrong", "cmd": "help"})
    check("错误令牌返回 403", code == 403, "code=%s body=%s" % (code, body))

    # 2. 正确令牌 + help
    code, body = run(mod, TOKEN, {"token": TOKEN, "cmd": "help"})
    check("正确令牌返回 200", code == 200, "code=%s" % code)
    check("help 列出 status", body is not None and "status" in body, "body=%r" % body)

    # 3. 空 cmd 等价于 help
    code, body = run(mod, TOKEN, {"token": TOKEN})
    check("空 cmd 走 help 分支 200", code == 200, "code=%s" % code)

    # 4. 白名单指令存在
    for c in ("status", "docker", "uptime", "disk"):
        check("白名单含 %s" % c, c in mod.COMMANDS)

    # 5. 未知指令 404，且不落到 shell 执行路径
    code, body = run(mod, TOKEN, {"token": TOKEN, "cmd": "rm -rf /"})
    check("未知指令返回 404", code == 404, "code=%s body=%s" % (code, body))
    # 响应必须是固定的拒绝文案，而不是命令执行输出
    check(
        "未知指令走拒绝分支而非执行",
        body is not None and body.startswith("未知指令:"),
        "body=%r" % body,
    )
    # 白名单外的命令名不应出现在 COMMANDS 键中
    check("未知指令不在白名单", "rm -rf /" not in mod.COMMANDS)

    # 6. restart 默认禁用
    code, body = run(mod, TOKEN, {"token": TOKEN, "cmd": "restart", "arg": "nginx"})
    check("未配置前缀时 restart 被拒 403", code == 403, "code=%s" % code)

    # 7. restart 前缀不匹配
    mod.RESTART_ALLOW_PREFIX = "wecom"
    code, body = run(mod, TOKEN, {"token": TOKEN, "cmd": "restart", "arg": "nginx"})
    check("前缀不匹配 restart 被拒 403", code == 403, "code=%s" % code)

    # 8. restart 参数字符集非法
    code, body = run(mod, TOKEN, {"token": TOKEN, "cmd": "restart", "arg": "wecom;rm -rf /"})
    check("非法容器名返回 400", code == 400, "code=%s body=%s" % (code, body))

    # 9. 非法 JSON -> 400
    h = FakeHandler().make(mod, {})
    h.headers = {"Content-Length": "5"}
    h.rfile = io.BytesIO(b"notjs")
    h.do_POST()
    check("非法 JSON 返回 400", h.code == 400, "code=%s" % h.code)

    # 10. 常量时间比较
    check("constant_time_eq 等长相等", mod.constant_time_eq("abc", "abc"))
    check("constant_time_eq 等长不等", not mod.constant_time_eq("abc", "abd"))
    check("constant_time_eq 不等长", not mod.constant_time_eq("abc", "abcd"))

    # 11. 默认监听地址与端口占位
    check("默认 LOCAL_CMD_PORT 为 8181", mod.PORT == 8181, "port=%s" % mod.PORT)

    failed = [c for c in checks if not c[1]]
    for name, cond, extra in checks:
        print("%s %s%s" % ("OK  " if cond else "FAIL", name, ("  <- " + extra) if (not cond and extra) else ""))
    print()
    print("==> %d/%d 通过" % (len(checks) - len(failed), len(checks)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
