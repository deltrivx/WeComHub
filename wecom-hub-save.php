<?php
/**
 * WeComHub 配置保存（设置 → 通知 页面提交到此）
 *
 * 只接受白名单键，写 /boot/config/plugins/WeComHub/wecom.hub.cfg
 * 值做基础校验：端口为数字、令牌为可打印字符、地址不含空白。
 * 配置内容不回显到页面响应（仅返回 ok/error）。
 */

$CFG_DIR = '/boot/config/plugins/WeComHub';
$CFG     = $CFG_DIR . '/wecom.hub.cfg';

header('Content-Type: application/json; charset=utf-8');

function fail($msg) {
    echo json_encode(['ok' => false, 'error' => $msg]);
    exit;
}

$ALLOWED = [
    'RELAY_HOST'      => 'host',
    'RELAY_PORT'      => 'port',
    'RELAY_PUSH_TOKEN'=> 'token',
    'LOCAL_CMD_PORT'  => 'port',
    'ENABLE_NOTIFY'   => 'bool',
    'ENABLE_CMD'      => 'bool',
    'MIN_IMPORTANCE'  => 'level',
    'RESTART_ALLOW_PREFIX' => 'prefix',
];

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    fail('method not allowed');
}

$out = [];
foreach ($ALLOWED as $key => $kind) {
    if (!isset($_POST[$key])) { continue; }
    $v = trim((string)$_POST[$key]);
    switch ($kind) {
        case 'port':
            if ($v !== '' && !ctype_digit($v)) { fail("$key must be numeric"); }
            break;
        case 'bool':
            $v = ($v === '1' || strtolower($v) === 'yes' || strtolower($v) === 'true') ? 'yes' : 'no';
            break;
        case 'level':
            if (!in_array($v, ['normal', 'warning', 'alert'], true)) { fail("$key invalid"); }
            break;
        case 'host':
            if ($v !== '' && preg_match('/\s/', $v)) { fail("$key must not contain whitespace"); }
            break;
        case 'token':
            if ($v !== '' && !preg_match('/^[[:print:]]+$/', $v)) { fail("$key invalid"); }
            break;
        case 'prefix':
            // 容器名前缀：仅允许 ASCII 字母数字 . _ -，避免被当作 shell 片段
            if ($v !== '' && !preg_match('/^[A-Za-z0-9._-]+$/', $v)) { fail("$key invalid"); }
            break;
    }
    $out[$key] = $v;
}

if (!is_dir($CFG_DIR) && !@mkdir($CFG_DIR, 0755, true)) {
    fail('cannot create config dir');
}

$lines = ["# WeComHub configuration", "# 由 设置 → 通知 页面生成，勿手工编辑", ""];
foreach ($out as $k => $v) {
    $lines[] = sprintf('%s=%s', $k, $v);
}
$body = implode("\n", $lines) . "\n";

if (@file_put_contents($CFG, $body) === false) {
    fail('cannot write config');
}
@chmod($CFG, 0600);

// 重启本地指令服务使配置生效
@shell_exec('/etc/rc.d/rc.WeComHub restart >/dev/null 2>&1 &');

echo json_encode(['ok' => true]);
