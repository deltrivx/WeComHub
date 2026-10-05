/* WeComHub 设置页交互（仅指令侧表单） */
(function () {
  var form = document.getElementById('wh-form');
  var msg = document.getElementById('wh-msg');
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
})();
