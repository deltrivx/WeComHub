<?php
/**
 * WeComHub 2.0 配置保存与操作接口
 */

$CFG_DIR = '/boot/config/plugins/WeComHub';
$CFG     = $CFG_DIR . '/wecom.hub.cfg';
$WECOM_ENV = $CFG_DIR . '/wecom.env';
$AGENT_VARS = $CFG_DIR . '/agent-vars.conf';

header('Content-Type: application/json; charset=utf-8');

function fail($msg) {
    echo json_encode(['ok' => false, 'error' => $msg]);
    exit;
}

function get_cmd_port() {
    global $CFG;
    $port = 8181;
    if (is_file($CFG)) {
        foreach (file($CFG, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            if (str_starts_with(trim($line), 'LOCAL_CMD_PORT=')) {
                $p = trim(explode('=', $line, 2)[1]);
                if (ctype_digit($p)) { $port = (int)$p; }
            }
        }
    }
    return $port;
}

$action = $_POST['action'] ?? $_GET['action'] ?? 'save';

// ---------- 1. 状态与日志查询 ----------
if ($action === 'get_status') {
    $port = get_cmd_port();
    $ctx = stream_context_create(['http' => ['timeout' => 3]]);
    $status_res = @file_get_contents("http://127.0.0.1:{$port}/api/status", false, $ctx);
    $logs_res   = @file_get_contents("http://127.0.0.1:{$port}/api/recent_logs", false, $ctx);

    $status = $status_res ? json_decode($status_res, true) : ['ok' => false, 'status' => 'stopped'];
    $logs   = $logs_res ? json_decode($logs_res, true) : ['ok' => false, 'logs' => []];

    echo json_encode([
        'ok' => true,
        'status' => $status,
        'logs' => $logs['logs'] ?? []
    ]);
    exit;
}

// ---------- 2. 测试发信 ----------
if ($action === 'test_send') {
    $port = get_cmd_port();
    $ctx = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => json_encode(['touser' => '@all']),
            'timeout' => 15
        ]
    ]);
    $res = @file_get_contents("http://127.0.0.1:{$port}/api/test_send", false, $ctx);
    if (!$res) { fail("无法连接到本地 WeComHub 服务 (127.0.0.1:{$port})"); }
    echo $res;
    exit;
}

// ---------- 3. 同步菜单 ----------
if ($action === 'sync_menu') {
    $port = get_cmd_port();
    $ctx = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => '{}',
            'timeout' => 15
        ]
    ]);
    $res = @file_get_contents("http://127.0.0.1:{$port}/api/sync_menu", false, $ctx);
    if (!$res) { fail("无法连接到本地 WeComHub 服务 (127.0.0.1:{$port})"); }
    echo $res;
    exit;
}

// ---------- 4. 保存配置 ----------
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    fail('method not allowed');
}

$ALLOWED_KEYS = [
    'WECOM_CORP_ID',
    'WECOM_AGENT_ID',
    'WECOM_SECRET',
    'WECOM_TOKEN',
    'WECOM_AES_KEY',
    'LOCAL_CMD_PORT',
    'RELAY_HOST',
    'RELAY_PORT',
    'RELAY_PUSH_TOKEN',
    'ENABLE_CMD',
    'RESTART_ALLOW_PREFIX'
];

$existing = [];
if (is_file($CFG)) {
    foreach (file($CFG, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || !str_contains($line, '=')) { continue; }
        [$k, $v] = explode('=', $line, 2);
        $existing[trim($k)] = trim($v);
    }
}

$out = $existing;
foreach ($ALLOWED_KEYS as $k) {
    if ($k === 'ENABLE_CMD') {
        $out[$k] = isset($_POST[$k]) ? 'yes' : 'no';
    } else {
        if (isset($_POST[$k])) {
            $v = trim((string)$_POST[$k]);
            // 如果用户未修改密码字段（传了空且已有原值），保留原值
            if (in_array($k, ['WECOM_SECRET', 'WECOM_TOKEN', 'WECOM_AES_KEY', 'RELAY_PUSH_TOKEN']) && $v === '' && !empty($existing[$k])) {
                $out[$k] = $existing[$k];
            } else {
                $out[$k] = $v;
            }
        }
    }
}

// 基础校验
if (!empty($out['LOCAL_CMD_PORT']) && !ctype_digit($out['LOCAL_CMD_PORT'])) {
    fail("LOCAL_CMD_PORT 必须为数字端口");
}
if (!empty($out['RELAY_PORT']) && !ctype_digit($out['RELAY_PORT'])) {
    fail("RELAY_PORT 必须为数字端口");
}

if (!is_dir($CFG_DIR) && !@mkdir($CFG_DIR, 0755, true)) {
    fail('无法创建配置目录');
}

$lines = [
    "# WeComHub 2.0 Unified Configuration",
    "# Managed by WeComHub WebGUI. Do not edit by hand.",
    ""
];
foreach ($out as $k => $v) {
    $lines[] = sprintf('%s=%s', $k, $v);
}
$body = implode("\n", $lines) . "\n";

if (@file_put_contents($CFG, $body) === false) {
    fail('写入配置文件失败');
}
@chmod($CFG, 0600);

// 同步回填 wecom.env 与 agent-vars.conf，保证旧出站脚本 100% 正常
$env_lines = [
    "WECOM_CORP_ID=" . ($out['WECOM_CORP_ID'] ?? ''),
    "WECOM_SECRET=" . ($out['WECOM_SECRET'] ?? ''),
    "WECOM_AGENT_ID=" . ($out['WECOM_AGENT_ID'] ?? '1000007'),
];
@file_put_contents($WECOM_ENV, implode("\n", $env_lines) . "\n");
@chmod($WECOM_ENV, 0600);

$agent_vars = [
    "RELAY_HOST=" . ($out['RELAY_HOST'] ?? '[IP]'),
    "RELAY_PORT=" . ($out['RELAY_PORT'] ?? '8484'),
    "RELAY_PUSH_TOKEN=" . ($out['RELAY_PUSH_TOKEN'] ?? ''),
    "TITLE=",
    "MESSAGE="
];
@file_put_contents($AGENT_VARS, implode("\n", $agent_vars) . "\n");
@chmod($AGENT_VARS, 0600);

// 重启后台服务使新端口与新凭据生效
@shell_exec('/etc/rc.d/rc.WeComHub restart >/dev/null 2>&1 &');

echo json_encode(['ok' => true]);
