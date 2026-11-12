---
title: 公众号预览编辑、保存与同步前检查
type: guide
status: active
created: 2026-10-24
updated: 2026-11-12
tags: [公众号, 预览编辑, 人工修订]
related:
  - "[排版入口](../SKILL.md)"
  - "[机器合同](../skill.contract.yaml)"
  - "[架构说明](architecture.md)"
---

# 公众号预览编辑、保存与同步前检查

作者在本机服务页直接改字、删除内容,独立控制选区红色和粗体,点击“保存草稿”真正保存到 Markdown 与正文 HTML。保存后仍可撤销或重做,再保存形成新修订,无需导出或另存。公众号同步需要单独确认。

## 打开能直接保存的预览

用户只说“公众号排版这篇 md”时,默认按 [SKILL.md](../SKILL.md) 完成 minimal 排版与 HTML 校验,保留实际渲染来源,直接执行以下两条命令并交付服务 URL,无需再询问是否编辑。只有明确只读、非 minimal 或来源无法可靠映射时,说明编辑限制并交付只读预览；已有基线来源漂移仍按冲突停止处理,不借只读降级绕过保存检查。

```bash
python3 "{{skill_root}}/scripts/wrap_preview.py" ./article.html ./article-preview.html \
  --editable --source-md ./article.md

python3 "{{skill_root}}/scripts/serve_preview.py" \
  --manifest ./article.gzh-edit-manifest.json
```

`{{skill_root}}` 是安装后的 gzh-format 目录。第一条绑定来源,第二条启动本机保存服务;打开第二条 stdout 首行打印的 URL,在服务页编辑和保存。

保存时保持服务进程运行;后续预检可在另一个终端执行,或由 Agent 保留服务进程。

| 参数 | 作用 |
|---|---|
| `./article.html` | 已校验的正文 HTML,不含预览外壳。 |
| `./article-preview.html` | 可选预览路径;首次省略为正文同目录 `article_预览.html`,已有基线时省略复用绑定路径。 |
| `--editable` | 建立受控文字块与来源基线。 |
| `--source-md ./article.md` | 实际 Markdown 来源,也是保存回填目标;工作副本之外的原稿不会同时回填。 |
| `--manifest <路径>` | 绑定这一篇文章的本地基线;wrap 默认正文同目录 `article.gzh-edit-manifest.json`,serve 必须显式指定。 |
| `--port 0` | serve 的可选端口,默认 0 自动选择空闲端口;只监听 `127.0.0.1`。 |
| `--ready-file <未存在路径>` | serve 可选新建的 0600 就绪 JSON,含 `url/origin/pid`,供调用方读取;已有文件不会覆盖,应换新路径或省略。 |

只支持能从实际 Markdown 确定性重现的 `minimal` HTML。manifest 绑定 `preview_file`;源 MD、正文 HTML、manifest 和预览路径互异,包括 symlink 别名。旧 HTML 对不上源文、基线绑定其它路径或来源漂移时停止,不猜测反写。

随机 URL 是本机保存会话入口,按本机资源保管。服务验证同源、会话身份及单篇文章绑定,不接受 HTTP 指定文件路径;会话 token 不写入 manifest 或正文,ready-file 也不含显式 token。此服务不访问微信或外部网络。`file://` 旧预览没有保存服务,“保存草稿”按钮禁用并提示从服务打开,不会以浏览器内存或 localStorage 假装保存。

## 直接改稿并保存

静态预览和可编辑预览都默认按 390 CSS px 手机阅读宽度显示，窄于此宽度时随窗口收缩；正文保持原字号、行距和段间距，方便直观看到换行与文章长度。在手机宽度正文里直接修改、删段、改标题并保存，无需切回宽屏编辑页。这里模拟阅读宽度，不是微信客户端像素级还原，也不代表手机可以访问仅监听电脑回环地址的保存服务。

服务页默认处于可编辑状态。主动点击“切换为预览”会进入只读查看状态，点击“继续编辑”即可在同页恢复，手机阅读宽度保持不变。

编辑工具条吸附在顶部“复制到公众号”栏下方；滚到正文中部或底部，仍可直接使用标红、加粗、撤销和保存。窄屏时按钮自动换行。已打开的本机服务页先保存当前修改，再刷新即可加载新的工具条样式。

工具条另提供“删除整行”和“添加一行”：前者清空当前正文、H2/H3 或微标题块并可撤销，保存后从源文移除；后者在当前光标/选区结束位置添加一个保留现有样式的软换行。H2 的大号章节序号和 H3 标题前缀序号都可直接选中、修改或删除，序号改动和标题正文共用保存、撤销/重做与自动保存事务。点击 H2 序号也会激活所属标题块。操作不改变图片集合、块顺序或 H3 数量。编辑器内的标红只处理作者明确选中的文字；初次排版的语义锚点还会拒绝句首和泛化引导词，避免把普通句首误当关键词。

本机保存服务页默认每 2 分钟检查一次未保存修改；有修改时自动提交当前快照，正在输入法组字、已有保存请求或没有本机保存桥接时跳过。自动保存失败会保留页面内容和未确认提交状态，下一轮或手动点击“保存草稿”继续按原事务重试；手动保存按钮仍保留，用于立即提交。已有 `gzh-manual-revision:v1` 的历史语义锚点会在保存时保留，不会因新一轮初排标红门禁升级而阻断回填；新建稿仍执行句首和泛化引导词校验。

正文上方显示可编辑的“文章标题”文本框，用于查看和修改当前标题。标题与正文共用“保存草稿”、未保存提示和撤销/重做；后续同步按原有流程使用已保存的标题，无需单独复制或粘贴标题。只读预览显示只读标题；可传 `--source-md` 供只读预览取真实标题，不传时仅回退 HTML 文件名。

标题依次取 Markdown frontmatter 的非空 `title`、首个正文 H1、Markdown 文件名。保存改变的标题时，安全地写入或新增单行 `title`，同步已有唯一 H1；原文无 H1 就不新增，不改文件名或链接。只改标题时正文 HTML 原字节保留，不重新标红或排版。标题必须是非空单行纯文字，控制字符拒绝。

标题映射只接受可明确定位的普通、单引号或 JSON 兼容双引号 YAML 标量；多行、锚点、标签、flow 值、重复 title、多个正文 H1 或 H1 含内联注释等显示原因并让标题只读，仍允许可靠映射的正文编辑。需要改这类标题时先在源 Markdown 中明确修改，再重建来源基线，不能强行猜测回填。

现有 `gzh-edit/v1` 包新增可选纯文字 `title` 字段；旧 manifest 首次读取从已核验源文补入内存，旧包缺失标题时保持当前标题，包括同一会话已保存过新标题的情况。新客户端只在服务响应返回同一提交标题时确认保存成功；保存途中继续改题仍保持未保存。保存新标题不会恢复会话旧题或清空撤销历史。

| 区块 | 编辑范围 |
|---|---|
| 文章标题框 | 独立纯文字，保存同步 `title` 与已有唯一 H1，不进入正文复制区。 |
| 普通段落、H2、H3、引用、micro 小标题 | 开放可靠映射的文字；H2 序号和 H3 序号可单独编辑/删除，H3 数量受保护。 |
| 显式 Markdown 列表项 | 修改列表文字,保留原前缀和结构。 |
| 双链/图片语法块、图片、代码、表格、固定作者页尾 | 只读,保留源结构。 |
| 自动问题组/示例组等无独立源列表行的区块 | 只读,不猜测回填范围。 |

直接输入或删除,选区后点击标红/取消红色、加粗/取消粗体,四个动作独立。粘贴只取纯文字,原链接地址保留。H2 序号在独立的大号序号行中编辑，H3 序号在标题前缀中编辑；点击“删除整行”可显式清空正文、H2/H3 或微标题，不能重排图片或删除剩余 H3 块。

点击“保存草稿”后,或等待每 2 分钟自动保存时,页面通过同源请求提交当前改稿,共享事务核对来源、备份并回填绑定的 Markdown、正文 HTML、预览和 manifest。只有实际提交成功才显示已保存,不下载文件,也没有导出/另存按钮。完成输入法组字后再保存。

- **保存后继续撤销**:保存不清当前页 undo/redo 历史。删段→保存→撤销可恢复段落,再次点保存把恢复结果写成新修订;重做后也可再保存。
- **保存时继续输入**:请求只提交触发时的版本。请求期间的新输入留在页面,返回后仍显示有未保存修改,由下一轮自动保存或手动保存继续提交;不能把后续输入算进已保存版。
- **关页或停止服务**:关闭页面、刷新或重开后不恢复原 undo 历史,仅保留磁盘稿。Ctrl+C 结束服务不删除已保存稿;关页前须等保存完成并确认无未保存修改。
- **来源冲突**:反向同步或其它会话改稿后,服务拒绝过期来源保存。保留页面作对照,核对新来源与 manifest 后重开服务,不能以旧页面强行覆盖。

每次实际修订在正文同目录归档:

```text
.gzh-edits/<article_id>/rNNNN-<8hex>/
  source.md                 保存前 Markdown
  body.html                 保存前正文 HTML
  manifest.json             保存前来源基线
  package.gzh-edit.json      内部事务记录,无需用户另存
  saved.md                  保存后 Markdown
  saved.html                保存后正文 HTML
```

保存保留原 CRLF/LF 换行与未编辑源片段,使用 `<manifest路径>.lock` 互斥。失败保留页面并可重试,不把未确认状态冒充成功;写入失败尝试恢复 MD/HTML/manifest/绑定预览并留 `failed.txt`。以预检核实磁盘状态;进程崩溃遗留锁需确认保存进程已停止并检查文件后人工处理,不自动删锁继续覆盖。

## 保留作者样式

实际改动保存后,源文有 `<!-- gzh-manual-revision:v1 -->`,编辑文字用 `data-gzh="manual-style"` span 保存独立 `data-red` 与 `data-bold`。它们是可重新渲染的保存格式,不要清理掉。

初排按语义锚点规则选择原文短语;人工修订后作者文字、删除和样式优先,上游不重新补红、恢复删文或联动红色/粗体。固定页尾只读,未编辑结构保留。

## 同步前检查

确认页面最新改稿已显示保存完成、没有未保存修改,再执行:

```bash
python3 "{{skill_root}}/scripts/preflight_edit.py" \
  --manifest ./article.gzh-edit-manifest.json
```

`--manifest` 检查 `status: saved`、当前 MD/HTML 哈希与已知旧兼容包。常规 JSON 返回 `manifest_file/status/article_id/revision/source_md/html_file/source_sha256/html_sha256`,供上游交接同一磁盘修订。初始 `baseline` 不能冒充已保存稿;磁盘预检也不能检测浏览器刚输入的 dirty 状态。

CLI 同步可用 `--edit-manifest` 显式绑定,也会发现正文同目录同名 manifest;MCP 编排先运行共享预检。作者仅确认“保存草稿”不授权微信写入;确认最新保存版同步后,再交给 `wechat-draft-sync`。本地/线上/成功基线三方比较、原草稿 ID 更新、冲突展示和写后回读继续适用,没有新增线上自动合并。

## 同步后元数据登记

同步成功后,微信草稿 ID、同步时间和简介等会写回 Markdown frontmatter,使文件 SHA 改变。它们可以在严格验证后登记到编辑基线,避免下一轮编辑被误判成正文冲突。

```bash
python3 "{{skill_root}}/scripts/preflight_edit.py" \
  --manifest ./article.gzh-edit-manifest.json \
  --refresh-metadata-from "<成功同步返回的写前源备份>" \
  --expected-revision <发送时修订号> \
  --expected-source-sha256 <发送时源文哈希> \
  --expected-html-sha256 <发送时正文HTML哈希>

python3 "{{skill_root}}/scripts/preflight_edit.py" \
  --manifest ./article.gzh-edit-manifest.json \
  --refresh-metadata-from "<成功同步返回的写前源备份>" \
  --expected-revision <发送时修订号> \
  --expected-source-sha256 <发送时源文哈希> \
  --expected-html-sha256 <发送时正文HTML哈希> --apply
```

`--refresh-metadata-from` 必须指向本次成功同步写回之前的源文备份,不能随便选一个旧稿。第一条默认只校验,第二条的 `--apply` 才刷新 manifest 来源映射/哈希和绑定预览,保持人工 `revision`、原保存时间和已导入包记录。此模式不修改正文源文或正文 HTML;`--apply` 不能脱离 `--refresh-metadata-from` 单独用于预检。

登记须同时满足:备份 SHA 恰等 manifest 旧 `source_sha256`;当前正文 HTML 哈希不变;前后都有完整 frontmatter;正文和非白名单元数据完全一致。只允许以下完整键变化:

```text
digest
wechat_draft_media_id
wechat_draft_synced_at
wechat_draft_status
wechat_draft_title
wechat_thumb_media_id
```

CLI 在成功 writeback 后自动调用共享登记;MCP 成功回写时可由编排复用同一命令。登记不是正文或任意元数据的重建基线工具,发现其它变化就阻断。返回 `metadata_refreshed: true` 后,旧保存会话若检测到来源漂移,先核对当前基线并重开本机服务继续编辑;重开不保留原页 undo 历史。若登记失败时微信草稿已经存在,先保留成功回执/本地写回中的草稿 ID 和写前备份,解决冲突,不要再执行 create 生成重复草稿。

## 失败处理

同步后登记还必须传入实际发送请求时预检返回的 `--expected-revision`、`--expected-source-sha256`、`--expected-html-sha256`。三个值均须与当前 manifest 一致；缺失或请求期间另有本地保存即阻断。它们来自发送前计划，不能从发送后新版本临时取值。CLI 已自动传入，MCP 编排须一并保留。

元数据登记器保持零 YAML 依赖,对多行引号、跨行 flow 集合、tag/anchor/alias 等复杂标量停止自动登记,须显式比较后处理;不以行首疑似 `digest:` 吞掉其它字段中的内容。此限制不影响正文编辑和修改包导入。

| 情况 | 结果与处理 |
|---|---|
| HTML 不能由指定 Markdown 重现 | 停止生成基线;找回实际渲染源,不猜测反写。 |
| file:// 页面或服务已关闭 | 无法直接保存;从绑定 manifest 启动本机服务,不把页面内存当保存。 |
| MD/HTML 或基线变化 | 保存/预检阻断;保留页面和归档作对照,先比较修改,不删 manifest 强制覆盖。 |
| 页面仍有未保存修改或磁盘不是 saved | 完成保存并核对最新稿;同步预检不能替浏览器证明无 dirty。 |
| 危险链接、未知字段/DOM、图序、H3 数量变化 | 拒绝保存;撤销不支持的操作后重试。序号文字变化属于允许的人工修订。 |
| 保存失败或遗留锁 | 检查失败归档与预检;核实进程已停,人工恢复或处理锁后重试。 |
| 线上草稿也被修改 | 沿用三方比较,展示冲突并等待作者决定。 |
| 成功同步后的元数据登记失败 | 草稿可能已存在;保留 ID 与写前备份,解决冲突后登记,不重复 create。 |

## 附录:旧修改包兼容 CLI

包格式用于内部 HTTP 传输和归档,现行编辑器不提供导出/另存按钮。只有处理历史已存在的 `.gzh-edit.json` 时才使用:

```bash
python3 "{{skill_root}}/scripts/import_edit.py" ./legacy.gzh-edit.json \
  --manifest ./article.gzh-edit-manifest.json

python3 "{{skill_root}}/scripts/import_edit.py" ./legacy.gzh-edit.json \
  --manifest ./article.gzh-edit-manifest.json --apply
```

第一个位置参数是历史包的实际路径,`--manifest` 绑定可信来源。默认 dry-run 只验证并输出逐块 `changes`(`id/kind/before_text/after_text/before_runs/after_runs`);`--apply` 才走共享备份/回填事务。同包幂等,来源漂移仍阻断。不要手改 manifest 或把包直接交给公众号同步。兼容导入会改变来源,已有服务应核对新基线后重开。

常规预检自动只查 manifest 同目录 `*.gzh-edit.json`;历史包另在其它目录时,用可重复的 `--pending-package <路径>` 显式补充。预检无法自动证明其它下载目录没有历史包。这些是兼容检查,不是普通用户的保存步骤。

## 独立夹具验证

在 gzh-format 目录运行:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_editor_dom.cjs tests/test_editable_e2e.cjs
python3 scripts/release_check.py
```

第一条的 `-s tests` 指定测试目录,`-p 'test_*.py'` 运行模型/渲染/会话/服务夹具,`-v` 显示各用例,覆盖旧包兼容、16图/11个H3编号保真、保存后撤销恢复及服务保护。第二条的 `--test` 运行两个浏览器文件,覆盖选区、直接保存、在途新输入、撤销重做、file协议禁假保存和完整HTTP链路。第三条检查包完整性、链接、静态安全项和渲染回归。

浏览器命令的前提是当前 Node 能解析 `playwright` 模块,且有可用 Chromium/Chrome。复用已有依赖目录时可在命令前设置 `NODE_PATH="<已有 node_modules 目录>"`;已有浏览器可用 `GZH_TEST_BROWSER="<浏览器可执行文件>"` 指定,否则由 Playwright 查找其 Chromium。依赖无法解析属于环境未就绪,不当作用例通过或功能失败;调用方提供自己的现有路径,不把本机固定目录写入包。

本轮独立文章真实 HTTP＋Chrome 验收通过:保存→撤销已保存删段并再保存→重做再保存→重新加载修订3,16图与11个H3编号保持;未确认保存后的安全重试另有浏览器回归。首轮下载回填仅作历史证据,不代表当前用户步骤。

测试使用独立临时文章。夹具结果不代表真实文章端到端使用、微信公众号粘贴或线上同步已验收;真实文章由作者另选后测试。
