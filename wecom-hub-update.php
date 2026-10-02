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
if (!is_array($info) || empty($info['latest'])) {
    echo json_encode(['ok' => false, 'error' => '版本索引格式异常']);
    exit;
}

echo json_encode([
    'ok'      => true,
    'latest'  => $info['latest'],
    'current' => $LOCAL_VER,
    'hasUpdate' => ($LOCAL_VER !== '' && version_compare($info['latest'], $LOCAL_VER, '>')),
    'downloadUrl' => $info['downloadUrl'] ?? '',
    'pluginUrl'   => $info['pluginUrl'] ?? '',
]);
