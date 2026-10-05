<?php
/**
 * WeComHub 配置保存（设置 → 通知 → WeComHub 页面提交到此）
 *
 * 只处理指令侧键；通知侧（RELAY_*）由官方通知代理页面管理，写入 agent 脚本。
 * 写入 /boot/config/plugins/WeComHub/wecom.hub.cfg，值做基础校验。
 * 配置内容不回显到页面响应（仅返回 ok/error）。
 */

$CFG_DIR = '/boot/config/plugins/WeComHub';
$CFG     = $CFG_DIR . '/wecom.hub.cfg';

header('Content-Type: application/json; charset=utf-8');

function fail($msg) {
    echo json_encode(['ok' => false, 'error' => $msg]);
    exit;
}

// 指令侧键
$ALLOWED = [
    'ENABLE_CMD'           => 'bool',
    'LOCAL_CMD_PORT'       => 'port',
    'RESTART_ALLOW_PREFIX' => 'prefix',
];

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    fail('method not allowed');
}

// 保留 cfg 中不属于本页的既有键（例如历史遗留），避免保存时丢失
$existing = [];
if (is_file($CFG)) {
    foreach (file($CFG, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || !str_contains($line, '=')) { continue; }
        [$k, $v] = explode('=', $line, 2);
        $existing[$k] = $v;
    }
}

$out = $existing;
foreach ($ALLOWED as $key => $kind) {
    if ($kind === 'bool') {
        $v = isset($_POST[$key]) ? 'yes' : 'no';
    } else {
        if (!isset($_POST[$key])) { continue; }
        $v = trim((string)$_POST[$key]);
    }
    switch ($kind) {
        case 'port':
            if ($v !== '' && !ctype_digit($v)) { fail("$key must be numeric"); }
            break;
        case 'prefix':
            // 容器名范围：* 或 ASCII 字母数字 . _ -，避免被当作 shell 片段
            if ($v !== '' && $v !== '*' && !preg_match('/^[A-Za-z0-9._-]+$/', $v)) {
                fail("$key invalid");
            }
            break;
    }
    $out[$key] = $v;
}

if (!is_dir($CFG_DIR) && !@mkdir($CFG_DIR, 0755, true)) {
    fail('cannot create config dir');
}

$lines = ["# WeComHub configuration", "# Managed by the plugin UI. Do not edit by hand.", ""];
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
