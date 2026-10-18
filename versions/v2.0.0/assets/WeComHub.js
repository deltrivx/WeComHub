/* WeComHub 2.0 前端控制脚本 */
(function () {
  var form = document.getElementById('wh-form');
  var msg = document.getElementById('wh-action-msg');
  var btnSave = document.getElementById('btn-save');
  var btnTest = document.getElementById('btn-test');
  var btnSyncMenu = document.getElementById('btn-sync-menu');
  var badge = document.getElementById('wh-service-badge');
  var statusText = document.getElementById('wh-status-text');
  var logViewer = document.getElementById('wh-log-viewer');

  function setMsg(text, ok) {
    if (!msg) return;
    msg.textContent = text;
    msg.className = ok ? 'ok' : 'err';
  }

  function fetchStatus() {
    fetch('/plugins/WeComHub/wecom-hub-save.php?action=get_status')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !badge || !statusText) return;
        var dot = badge.querySelector('.wh-dot');
        if (data.status && data.status.ok && data.status.status === 'running') {
          if (dot) { dot.className = 'wh-dot running'; }
          statusText.textContent = '运行中 (:' + data.status.port + ')';
        } else {
          if (dot) { dot.className = 'wh-dot stopped'; }
          statusText.textContent = '未运行';
        }

        if (logViewer && data.logs && data.logs.length > 0) {
          logViewer.textContent = data.logs.join('\n');
          logViewer.scrollTop = logViewer.scrollHeight;
        } else if (logViewer && (!data.logs || data.logs.length === 0)) {
          logViewer.textContent = '暂无最新日志记录';
        }
      })
      .catch(function () {
        if (statusText) statusText.textContent = '状态获取异常';
      });
  }

  // 保存表单
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      setMsg('正在保存并应用配置…', true);
      btnSave.disabled = true;
      var data = new FormData(form);
      fetch(form.action, { method: 'POST', body: data })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btnSave.disabled = false;
          if (res.ok) {
            setMsg('配置已保存并热重启成功！', true);
            setTimeout(fetchStatus, 1500);
          } else {
            setMsg('保存失败：' + (res.error || '未知错误'), false);
          }
        })
        .catch(function (err) {
          btnSave.disabled = false;
          setMsg('网络请求异常：' + err, false);
        });
    });
  }

  // 测试发信
  if (btnTest) {
    btnTest.addEventListener('click', function () {
      setMsg('正在向企业微信发送测试消息…', true);
      btnTest.disabled = true;
      fetch('/plugins/WeComHub/wecom-hub-save.php?action=test_send', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btnTest.disabled = false;
          if (res.ok) {
            setMsg('测试消息发送成功，请查收企微通知！', true);
            setTimeout(fetchStatus, 1000);
          } else {
            setMsg('发信失败：' + (res.error || JSON.stringify(res.res || res)), false);
          }
        })
        .catch(function (err) {
          btnTest.disabled = false;
          setMsg('发信请求失败：' + err, false);
        });
    });
  }

  // 一键同步菜单
  if (btnSyncMenu) {
    btnSyncMenu.addEventListener('click', function () {
      setMsg('正在同步预设菜单至企业微信应用…', true);
      btnSyncMenu.disabled = true;
      fetch('/plugins/WeComHub/wecom-hub-save.php?action=sync_menu', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          btnSyncMenu.disabled = false;
          if (res.ok) {
            setMsg('企业微信应用菜单同步成功！', true);
            setTimeout(fetchStatus, 1000);
          } else {
            setMsg('菜单同步失败：' + (res.error || JSON.stringify(res.res || res)), false);
          }
        })
        .catch(function (err) {
          btnSyncMenu.disabled = false;
          setMsg('菜单请求失败：' + err, false);
        });
    });
  }

  // 初始加载与周期轮询
  fetchStatus();
  setInterval(fetchStatus, 10000);
})();
