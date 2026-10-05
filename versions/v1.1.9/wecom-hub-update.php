<?php
/**
 * WeComHub 更新检查
 *
 * 读取远端 versions/index.json，与本地已安装版本比对，返回是否有新版本。
 * 只读操作，不自动安装；安装由 Unraid 插件系统根据用户操作完成。
 */

$INDEX_URL = 'https://raw.githubusercontent.com/deltrivx/WeComHub/main/versions/index.json';
$LOCAL_VER = trim(@file_get_contents('/usr/local/emhttp/plugins/WeComHub/version') ?: '');

header('Content-Type: application/json; charset=utf-8');

$ctx = stream_context_create(['http' => ['timeout' => 8]]);
$raw = @file_get_contents($INDEX_URL, false, $ctx);
if ($raw === false) {
    echo json_encode(['ok' => false, 'error' => '无法获取版本索引']);
    exit;
}
$info = json_decode($raw, true);
if (!is_array($info)) {
    echo json_encode(['ok' => false, 'error' => '版本索引格式异常']);
    exit;
}

// 兼容两种写法：latest（纯版本号）/ latest_version（带 v 前缀）
$latest = (string)($info['latest'] ?? '');
if ($latest === '' && !empty($info['latest_version'])) {
    $latest = ltrim((string)$info['latest_version'], 'v');
}
if ($latest === '') {
    echo json_encode(['ok' => false, 'error' => '版本索引缺少版本号']);
    exit;
}

$current = ltrim($LOCAL_VER, 'v');

echo json_encode([
    'ok'      => true,
    'latest'  => $latest,
    'current' => $LOCAL_VER,
    'hasUpdate' => ($current !== '' && version_compare($latest, $current, '>')),
    'downloadUrl' => $info['downloadUrl'] ?? '',
    'pluginUrl'   => $info['pluginUrl'] ?? '',
]);
