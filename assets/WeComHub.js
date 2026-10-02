/* WeComHub 设置页交互 */
(function () {
  var form = document.getElementById('wh-form');
  var msg = document.getElementById('wh-msg');
  var testBtn = document.getElementById('wh-test');
  if (!form) { return; }

  function setMsg(text, ok) {
    if (!msg) { return; }
    msg.textContent = text;
    msg.className = ok ? 'ok' : 'err';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    setMsg('保存中…', true);
    var data = new FormData(form);
    fetch(form.action, { method: 'POST', body: data })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        setMsg(j.ok ? '已保存' : ('保存失败：' + (j.error || '未知错误')), !!j.ok);
      })
      .catch(function (err) { setMsg('保存失败：' + err, false); });
  });

  if (testBtn) {
    testBtn.addEventListener('click', function () {
      setMsg('请到企业微信查看是否收到测试通知（保存后生效）', true);
    });
  }
})();
