# 开发约定

## 构建与发布

- **禁止本地构建后上传**。所有 `plg` / `txz` 由 `.github/workflows/build-release.yml` 在云端生成并挂到 Release。
- 本地 `scripts/build-release.sh` 仅用于自测；产物在 `dist/`，已加入 `.gitignore`。
- 发布流程：更新 `RELEASES.md` → 提交 → 打 `v*` tag → Actions 自动构建。

## 配置安全

- 仓库与文档中**不得出现真实凭据**。地址/端口/令牌一律用占位符：
  `RELAY_HOST`、`RELAY_PORT`、`RELAY_PUSH_TOKEN`、`LOCAL_CMD_PORT`。
- `verify.yml` 会扫描疑似真实 token（`sk-` / `ghp_` / `gho_` 前缀），命中即失败。
- 页面不回显已保存令牌；仅提示"已设置"。

## 命令执行安全

- `wecom-hub-cmd.py` 只执行白名单命令，不拼接任意 shell。
- `restart` 受 `RESTART_ALLOW_PREFIX` 前缀限制，且校验容器名字符集。
- 令牌比较使用常量时间比较。

## 文件布局

| 路径 | 作用 |
| --- | --- |
| `agents/WeComHub.xml` | 通知代理定义（渲染到 设置 → 通知 → 通知代理） |
| `WeComHub.page` | 插件自身配置页 |
| `wecom-hub-save.php` | 保存配置 |
| `wecom-hub-notify-agent.sh` | 通知转发 |
| `wecom-hub-cmd.py` | 本地指令服务 |
| `scripts/event-started.sh` | 阵列启动事件钩子（开机自启） |
| `scripts/rc.WeComHub` | 服务启停（不依赖 `/boot/config/go`） |
| `wecom.hub.cfg` | 配置模板（占位值） |
| `wecom.hub.plg` | 插件描述（构建时替换版本/MD5） |
| `scripts/build-release.sh` | 构建（云端调用） |
| `scripts/verify-release.sh` | 产物校验 |


## 版本号规则（重要）

Unraid 插件安装器用 `strcmp()` 比较版本字符串，**不是**语义化版本比较：

```php
// dynamix.plugin.manager/scripts/plugin:730
if (strcmp($version, $installed_version) < 0) {
    write("plugin: not installing older version\n");
```

因此 `1.0.10` 会被判定为比 `1.0.8` **旧**（第 5 位 `1` < `8`），升级被拒绝。

**规则**：补丁号达到两位数时，必须提升次版本号：

| 当前版本 | 错误（被拒） | 正确（可升级） |
| --- | --- | --- |
| `1.0.8` | `1.0.10` | `1.1.0` |
| `1.0.9` | — | `1.1.0` |

发版前务必确认新版本号 `strcmp` 大于所有已发布版本。

## 排障与验证教训（重要，均为实际踩坑）

### 1. 验证必须用 shell 语义，不能用正则

曾用正则 `[#]{6,100}(.*?)[#]{6,100}` 解析变量块，正则能读出 64 字符就判定“配置正常”，
但真机文件里标记与变量值粘在同一行：

```bash
############RELAY_HOST="1.2.3.4"     # 整行以 # 开头 -> bash 视为注释，变量从未赋值
```

结果：正则说“通过”，bash 实际一个变量都没设置，通知一直静默失败。

**正确做法**：让 shell 真实执行来验证——

```bash
bash -n "$AG"                    # 语法
# 探针法：把 AGENT 路径替换成探针脚本，看它实际收到什么
# 探针输出 host_len/token_len 正确才算通过
```

### 2. 判断“是否真的发出去”，看远端响应，不看退出码

agent 在未配置时会**静默退出 0**（设计如此，避免影响 Unraid 其他通知）。
因此 `echo $?` 为 0 **不等于**通知成功。

**正确做法**：直接请求中转，检查 `HTTP 200` 且返回体含 `msgid`。

### 3. `exec` 不会传递未导出的 shell 变量

agent 配置文件通过 `exec` 调用程序本体，未 `export` 的变量不会被传递：

```bash
FOO="bar"
exec body.sh     # body.sh 里 FOO 为空

export FOO
exec body.sh     # body.sh 里 FOO=bar  ✅
```

变量块后必须有 `export`，否则程序本体读到的地址/令牌恒为空。

### 4. plg `<FILE>` 会被无条件覆盖

Unraid 安装/升级时对 `<FILE>` 清单内的文件**无条件下载覆盖**（实测确认）。
因此：

- **程序本体**（`wecom-hub-notify-agent.sh` 等）→ 放 `<FILE>`，随升级更新
- **用户配置**（`agents/WeComHub.sh`）→ **绝不能**放 `<FILE>`，否则每次升级把用户填的地址/令牌重置为占位符

新增逻辑时先问：这段逻辑要覆盖存量用户吗？
若要，必须写在**程序本体**（在 `<FILE>` 内）才能随升级分发；
写在 agent 配置文件里则永远到不了存量用户。

### 5. `source` 含 `exec` 的脚本会吞掉后续命令

验证时若用 `source agent.sh` 再 `echo`，`exec` 会替换当前 shell，后续 echo 根本不执行，
表现为“无输出”，容易误判成脚本坏了。

### 6. 网络：`github.com` 与 `api.github.com` 链路不同

两者解析到不同 IP。曾出现 `github.com` 直连正常（`git push` 成功），
而 `api.github.com` 直连超时（`gh` / REST 查询失败）。

排查时分别验证，不要把其中一条的失败当成整体网络故障。

### 7. 长路径在工具输出里会被显示为 `…`

如 `/usr/l…ecom-hub-save.php` 是**显示层截断**，文件里是完整 ASCII 路径。
构造替换字符串时若照抄带 `…` 的显示结果会匹配失败。
用字节级检查（`has_utf8_ellipsis`）确认，不要凭显示判断。
