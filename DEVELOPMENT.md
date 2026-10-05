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

### 8. 改 VPS 侧 env 后必须重启对应服务

推送令牌存在 VPS 的两处 env（`/etc/wecom-unraid.env`、`/etc/unraid-exec.env`）。
中转服务在**进程启动时**读取它们，改文件**不会**自动生效。

实测现象：轮换令牌后，Unraid 侧指令全部 `200 ok=True`（本地服务已热加载），
但通知返回 `403 forbidden` —— 因为 VPS 上的中转进程仍握着旧令牌。

**正确做法**：改完 env 后重启对应服务。

```bash
systemctl restart wecom-unraid-cb.service
```

> 注意：热加载（v1.1.7）只实现在 **Unraid 侧**的指令服务上；VPS 侧服务仍需重启才加载新 env。

### 9. 轮换凭据的顺序：备份 → 写入 → 重启 → 验证 → 最后才删备份

一次完整的令牌轮换要跨两台机器、四处配置（VPS 两处 env + Unraid 配置与快照）。
顺序错了会导致两端令牌不一致，且旧令牌可能已经泄露、需要清理。

推荐顺序：

1. **备份**两侧要改的文件；
2. 生成新令牌（等长同字符集，如 64 位十六进制），写入全部位置；
3. 重启依赖该令牌的服务（见第 8 条）；
4. **实测验证**：指令 `200 ok=True` + 通知 `HTTP 200` 且返回含 `msgid`；
5. 验证通过后，才删除备份与交接文件。

**切勿先删备份**——验证失败时就没有回滚退路了。

### 10. 含明文凭据的文件用 `shred` 删除，并逐处确认清零

轮换过程中会产生含明文令牌的交接文件与备份。这些文件必须用覆写后删除：

```bash
shred -uf /tmp/new_token.txt    # 而非普通 rm
```

清理后要在**每台机器**上逐处确认（不能只在本地确认就认为干净）：

```bash
ls /tmp | grep -iE "new_token|apply_rotate"
ls /etc/*.bak-rotate-*
```

另外：Git 历史也要扫。判断某段 40 位十六进制是不是真泄漏时，注意它可能是 commit SHA（本身即 40 位十六进制），
要用 `git log -S <真实值>` 精确比对，避免误报。

### 11. 打包为 txz 后必须自己管权限与属主

改动的核心是把 13 个逐个下载的 `<FILE>` 合并成**单个 txz**（持久化到闪存），
开机由 `upgradepkg` 本地解包还原 `/usr`，从而**不依赖网络**。

机制（已读 dynamix `plugin` 源码确证）：文件已存在时 plugin-manager 只打印
`skipping: ... already exists`，但**仍会执行** `Run` 属性里的命令。
所以“跳过下载”不等于“跳过解包”，这正是离线安装能成立的关键。

踩到的坑：

- **`<FILE Mode="0755">` 失效**：原先每个 FILE 靠 Mode 属性施加权限，改 txz 后这层也没了。
  tar 会把构建机的文件模式与 uid 原样带进包里，真机解包后 `rc.WeComHub` 变成
  `-rw-------` 且属主 `UNKNOWN:UNKNOWN`，执行直接 Permission denied。
  必须在打包前显式 chmod，并用 `tar --owner=0 --group=0` 强制归 root。
- **同版本会被跳过解包**：`upgradepkg --install-new` 在登记仍在时打印
  `Skipping package (already installed)` 且**不解包**。此时若 `/usr` 已被清空就再也回不来。
  必须加 `--reinstall` 强制重装同版本。
- **XML 注释里不能出现连续双横线 `--`**：写 `--reinstall`、`--install-new` 会直接让 XML 解析失败。
  说明文字里改用空格分隔的写法，或把它挪到 `<CHANGES>` 正文中。

### 12. 校验脚本不要用 grep 统计 XML

曾用 `grep -cE '<URL>'` 统计联网条目数，结果把**注释里的字面量** `<URL>` 也数进去
（故障说明中正好提到“逐个走 `<URL>` 下载”），计数虚高导致误判。
必须按 XML 语义解析：

```python
root = ET.parse(plg).getroot()
print(sum(1 for f in root.findall("FILE") if f.find("URL") is not None))
```
