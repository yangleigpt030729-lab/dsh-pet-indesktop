# 陪伴增量：取消成功冷却与双朗读开关

分支 `feature/win10-companion-memory`；基线 `eee8c18`。不合并main，不改动画/WebM、发行依赖或正式数据。本轮用户已报告此前Windows10 Fake集中测试全部正常；新增需求的Windows实测、真实DeepSeek和Edge声音分别独立记录，不能冒充已验收。验收步骤见[Windows指南§10](WINDOWS10-COMPANION-ACCEPTANCE.md)。

## 修改文件说明

以下按基线eee8c18的最终diff逐文件登记；无删除文件。新增4个文件，其余为原链路增量。没有新TTS服务/播放器。

| 文件 | + / − | 改动与原因 |
|---|---:|---|
| `CONTEXT.md` | 5 / 1 | 登记新声音契约与用户既有Windows证据，防止后续沿用仅摸头朗读假设。 |
| `docs/INDEX.md` | 2 / 0 | 登记本报告，提供验收入口。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | 25 / 5 | 网页ZIP/UTF8/四组合/连续互动/待办/撤销验收及独立未测项，去除过时冷却说明。 |
| `pet/app.py` | 2 / 2 | 更新共享音频通道生命周期说明，原服务创建/播放逻辑不变。 |
| `pet/companion/head_speech.py` | 118 / 20 | 复用历史入口拓展双声音授权，精确回执与弱隐藏监听、独立角色配置/授权/任务guard，外部撤销优先；保留无chat路径。 |
| `pet/companion/interaction_runtime.py` | 1 / 1 | 将头部事件说明从旧成功冷却改为处理中消费手势，不动事件/动画引擎。 |
| `pet/companion/interaction_service.py` | 14 / 10 | 删除成功冷却，保留单飞/错误退避/合并协调；新事件撤销旧语音、新投喂使旧同宠结果失效，接入趣味朗读。 |
| `pet/companion/interaction_settings.py` | 2 / 2 | 说明频繁互动API费用、无成功冷却/独立错误退避与统计静音。 |
| `pet/companion/proactive_runtime.py` | 16 / 1 | 捕获实际显示宿主并在既有delivered信号接主动语音，原AI调度/预算不变。 |
| `pet/companion/proactive_settings.py` | 10 / 1 | 现有主动区域唯一独立语音行及在线/私人待办同意说明，即时保存，不跟主动总开关禁用。 |
| `pet/config.py` | 4 / 1 | 新默认关字段的默认、重载与bool清洗，旧被动key保留。 |
| `pet/modern_settings_dialog.py` | 2 / 3 | 被动语音行始终可发现，不要求身体点击/摸头开启。 |
| `pet/overlay_shell.py` | 3 / 1 | 仅per-slot字段与旧子宠新授权缺省False；无动画/媒体变更。 |
| `pet/settings_deeplinks.py` | 10 / 1 | 两声音名称/旧点击名称深链，复用既有页面。 |
| `pet/settings_interaction.py` | 2 / 2 | 旧行改名及私密在线语音说明，没有重复开关。 |
| `pet/todo_reminder.py` | 26 / 0 | 只在成功气泡边界捕获可撤销附加声音；GUI下一拍执行，保留原记录/通知分支。 |
| `pet/voice_chime_service.py` | 6 / 3 | 原guard失败保持所有陪伴文字；排队/失败附加日志不包含语音文本，服务/播放器/worker不新增。 |
| `pet/window_alerts.py` | 22 / 8 | 点击和周期在真实展示后各调用一次共用被动适配，图片失败才回退文字。 |
| `scripts/benchmark_companion_interactions.py` | 2 / 2 | 固定时钟验证连续成功请求，记录有界投喂数量而非已删除冷却字典。 |
| `scripts/capture_settings_pages.py` | 1 / 1 | 现有截图工具增加主动语音行，不创建演示模型。 |
| `tests/test_chat_persona_priority.py` | 1 / 1 | 移除旧冷却清理，保留人设优先/旧结果失效断言。 |
| `tests/test_config_schema.py` | 1 / 0 | 同步登记新增默认关字段的显式schema快照；保留所有集合/白名单严格断言。 |
| `tests/test_click_self_talk_speech.py` | 1 / 1 | 原周期文字现在也需要被动音频通道，保持其它默认与点击断言。 |
| `tests/test_companion_expression.py` | 0 / 1 | 取消旧冷却字典清理，表达约束/隐私断言不变。 |
| `tests/test_companion_head_speech.py` | 3 / 5 | 被动行始终可见、投喂也可朗读，保留所有原摸头/撤销/音色回归。 |
| `tests/test_desktop_pet_features.py` | 2 / 1 | 绑定/预缓存仍随点击，被动声音行独立可见。 |
| `tests/test_overlay_self_talk.py` | 4 / 1 | 真实点击观察原音频边界现在接收guard/config，并验证其有效；不绕过实际GUI。 |
| `scripts/benchmark_companion_speech.py` | 48 / 0 | 新增两拓扑主/子两开关的真实回执成本/RSS基准；只记录音频边界。 |
| `scripts/stress_companion_speech.py` | 27 / 0 | 新增4CPU×3的受影响时序族复验，沿原压力烧CPU工具。 |
| `tests/test_companion_dual_speech.py` | 589 / 0 | 新增113例真实Qt、文件、异步Provider、语音边界与重启/授权矩阵。 |
| `docs/PR-REPORT-COMPANION-DUAL-SPEECH-2026-10-13.md` | 127 / 0 | 新增交付证据、性能/实际运行/测试/限制与回滚。 |

## 行为与调用链

成功摸头/投喂不再有10/20秒固定冷却；上一条完全完成可立即再次请求。处理中摸头只保留原动画并消费手势，不加入队列；投喂按同宠合并元数据，最多32个目标、每个30秒有效期、数字上限9999，约2秒统计展示协调保留。新的同宠投喂使旧互动结果静默失效；尚未发起的旧模型请求可以跳过，已经发出的不能撤回费用。无额外成功时间门；错误后120秒退避只跳过模型并可显示本地备用文字，没有自动付费重试。原主动额度/间隔/相似去重不变。

两个声音偏好均独立于原功能开关：旧 `self_talk_speak_enabled` 原值直接复用，名称变为“被动互动朗读”，覆盖摸头、点击/周期文本和趣味投喂；图片与统计无声。新 `proactive_bubble_speak_enabled` 默认为False，只覆盖成功展示的普通主动问候/喝水/休息/关怀与原待办提醒。不因报时/节日自动开启。原旧子宠文件缺少新字段时保持False，不继承主宠的新在线语音同意；新生子宠仍按原设置继承机制。设置立即保存、关闭再开/重启保持，搜索和旧名称深链兼容。进程内关闭优先于写盘失败；较早的进程内开启不能覆盖外部设置进程已经保存的关闭，避免刷新后恢复私密朗读。

- 摸头/投喂：原事件 → `InteractionService`单飞异步模型/本地备用 → `Target.present`新文字回执 → 被动朗读适配。
- 点击/周期：原 `window_alerts`实际显示文字 → 同一被动适配；共享随机选择不内置朗读，因此点击和周期各自一次，不重复。图片加载失败实际回退文字时可朗读，定时频率和静默让路不变。
- 主动：原 `ProactiveService`异步生成 → `proactive_runtime.present`捕获实际宿主 → 原 `delivered` → 主动朗读适配，不再请求模型生成语音文案。
- 待办：原领取 → `_notify_fire`成功气泡回执 → 原送达记录/结算提交 → GUI下一拍执行已捕获的附加语音请求。原到期、领取、持久化、确认、删除、重试和重复投递防护完全沿用；通知分支不接线。未改 `todo_delivery.py` / `todo_async.py`。
- 全部语音：`head_speech`可撤销票据 → 原 `AppShell.speak_self_talk` → 同一个 `VoiceChimeService` → 静态文件/动态语音缓存优先 → 原TTS worker → 原播放器。队列沿原有界容量，覆盖旧内容不会播放旧票据，声音不叠加。静态自动预缓存仍只处理固定点击台词；AI回复仅在实际展示/用户开启后按原缓存流程合成。

票据绑定精确文字/气泡代次、隐藏代次、配置路径/角色/音色、授权generation、任务generation/原磁盘worker身份和30秒有效期；播放前重查。换角色、关闭/快速关再开、隐藏/销毁/退出、记忆撤销、任务删除/编辑/关闭、被新事件/文字取代均撤销尚未播放的结果。普通文本朗读无需加载ChatSettings，保留无chat构建。每个气泡只增加一个弱引用隐藏监听，不随互动增加监听；去重按同一展示回执。已播放音频沿原生命周期处理，不能撤回已发送的模型或在线TTS请求。

趣味投喂继续安全元数据，不发送内容/名称/路径、不改变原文件；统计第一条永远静音，第二条实际趣味/本地备用文字才可朗读。原内容解读确认/进度保持优先且会撤销不适合的附加声音。设置明确告知在线语音可发送私人待办文字；默认关闭，额外日志不写标题。TTS失败只跳过声音，不改变气泡或新建错误气泡。报时/节日的独立开关和原服务生命周期保留。

## 性能分析

Linux/Python3.12.14/Qt6.12.0 offscreen，无真实网络。最终代码门禁后执行 `python scripts/benchmark_companion_speech.py`：真实Qt宿主/合成素材、两拓扑×主/子×被动/主动，每组200次新文字回执、2000次播放前校验，共1600回执/16000校验；只有音频边界记录，没有Provider或Edge。记录器只保留一个guard，不累积回调。入队适配平均86.384～190.761µs，单组最大168.854～2104.809µs；校验平均16.277～44.810µs，单组最大226.932～15001.257µs。实际峰值15.001ms含系统调度/配置mtime检查，不能承诺零GUI延迟或Windows慢盘表现；不是逐帧调用，只在少量展示/播放边界发生。

首次构建多个Qt宿主后RSS80.699→154.695MiB，不是纯语音增量。各组第20到第200次RSS差异：Legacy被动主宠+0.059MiB，其余Legacy≤0.004MiB；Overlay首个被动路径主宠+13.570MiB、子宠+6.668MiB，随后主动路径主宠+0.043MiB、子宠0MiB。该基准同时创建/显示四种Qt宿主并保留原缓存；不能把总增长归因到语音或宣称“零增长”，Windows长时间CPU/RSS仍须实测。适配不保留历史票据列表，原缓存清理/队列上限不变。

`python scripts/benchmark_companion_interactions.py`1000次高速请求只接受1次，4.458ms；随后固定时钟、不手动推进成功冷却，连续完成200次本地异步备用文字：中位3.929ms、最大5.720ms。热后RSS46.234→46.305MiB（+0.070）；最近文本12、待投喂0、残留worker0。20000次权限戳3.274µs/次，角色头部判断1.158µs/次，表达约束2.022µs/次；单文件统计200次中位0.00672ms，5001项目录31.858ms并按原上限标partial。这些只测本地/Fake边界，不推断模型/在线TTS成本。

稳态不增加逐帧工作或常驻高频定时器；新操作只发生在成功展示、原队列播放检查、偏好变更边界。每个已开启的展示可能查原语音缓存/配置mtime，未命中时沿原后台网络合成和磁盘缓存，可能增加在线合成流量与API费用；无新增服务/播放器/音频线程。待办附加一次Qt零延迟调度，不增加磁盘worker或数据库。两个陪伴开关均关时没有额外陪伴消费者，报时/节日仍按自身设置存在。全量门禁与压力曾并行执行，门禁墙钟时间不用于前后性能比较。

## 实机运行记录

可用环境Linux/offscreen，真实Qt6.8.3设置窗口已捕获1100与720宽、明暗主题两种朗读行（8张代表图）。实际查看换行、控件与滚动可达，未改视觉token、动画或导航层级。截图在 `/tmp/dual-ui-{light,dark}-{1100,720}`，生成命令 `python scripts/capture_settings_pages.py <dir> --width <width> --height 760 [--dark] --companion-details`，API Key空、无Provider/TTS，隔离临时Config。UI审查：新增/重命名行复用SettingRow，名称/隐私hint/搜索/深链独立，默认关闭、立即保存/迁移/主子身份均有测试；Windows原生焦点、高DPI与真实声音不由这些截图证明。

Qt6.8.3下实际执行两次独立完整AppShell/仓库资源/原拖放统计探针（pytest外、非Fake），命令：

```bash
PET_FRAMESEQ=0 PET_RENDER_TOPOLOGY=legacy /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_increment.py
PET_FRAMESEQ=0 PET_RENDER_TOPOLOGY=overlay /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_increment.py
```

均输出 `PASS: real AppShell/assets, local maid head + original drop/stat/fun bubble, no Provider request, no TTS`，退出码0；实际桌宠/文字气泡/统计/原文件保留经断言确认，动画资源经原加载器，没有Mock/Fake Provider。临时目录禁用聊天/所有音频，不查询凭据、不联网。`PET_FRAMESEQ=0`只用于这两个资源运行探针，未用于pytest门禁。系统探针为Linux offscreen，说明插件没有原生透明/raise/device能力，因此不能证明Windows桌面显示/声音。用户之前Win10/Python3.12/约束Qt6.8.3启动、GUI、Fake摸头/主动气泡及最新集中Fake验收通过的证据保留；本轮新增双开关与连续互动尚需Windows集中复验。真实DeepSeek联网/语言遵从、Edge音频/代理/设备、Win10 EXE **NOT TESTED / NOT TESTED / NOT BUILT**，没有使用或保存任何真实Key。

## 测试与验证

首批有效23例修补前21失败/2通过（1.88s），覆盖固定成功冷却、被动/主动四组合、定时朗读与设置；其中未依赖缺失API Key。修补后首批转绿，再补投喂实拖放/失败备用、单飞1000次/合并队列、图片回退、撤销、真实主动Provider四类别、到期待办记录、音色缓存与进程重启。另旧子宠缺新授权测试修补前1失败；旧运行时开启覆盖外部保存关闭的4个测试修补前4失败，均修补后通过。另真实持久化待办在同服务停止再启动、worker generation重新从零计数时的旧声音复活：1个失败测试证明根因；票据绑定原worker弱身份后通过，未改原待办重启机制。完整回归还捕获schema两处显式快照漏登记（单跑2失败/13通过）；只加入本次新字段，保持严格相等/重载断言，修补后15通过。测试脚手架初次fixture错误单独修正，不计为产品失败证据。原旧测试更新仅反映明确新增的周期/投喂朗读和取消成功冷却要求，未删除安全/身份/持久化断言。

最终完整CI唯一Python用例 **4852通过、37跳过、0失败、18警告**（主组4784+独立WebM41+独立lowwarm27）；聚焦、压力、报告门禁和Qt6.8重复覆盖不叠加唯一数量。本轮新增113个双语音/互动用例及新报告2个门禁用例。18警告为已有Qt mirrored/DragEnter/HoverEvent弃用，没有线程异常警告；offscreen raise/propagateSizeHints的插件stderr与pytest警告分开。

| 实际检查 | 结果 | 时间 |
|---|---|---:|
| 完整主组Qt6.12 | 4784通过 / 37跳过 / 0失败 / 18警告 | 782.68s |
| 独立WebM组 | 41通过 / 0跳过 / 0失败 / 0警告 | 26.38s |
| 独立lowwarm组 | 27通过 / 0跳过 / 0失败 / 0警告 | 31.43s |
| frameseq资源复验（主组重复） | 37通过 / 0跳过 / 0失败 / 0警告 | 0.90s |
| 最终双语音/待办/原通道聚焦 | 169通过 / 0跳过 / 0失败 / 0警告 | 9.04s |
| Qt6.8.3受影响组 | 302通过 / 0跳过 / 0失败 / 0警告 | 90.15s |
| schema严格快照Qt6.12 / Qt6.8 | 两者各15通过 / 0失败 | 1.05 / 0.86s |
| 4CPU压力×3 | 每轮253通过 / 0跳过 / 0失败 / 0警告 | 24.04 / 30.93 / 24.20s |
| Node桥接原7文件 | 34通过 / 0跳过 / 0失败 | 238.460ms |
| verify_import.mjs | import / subtraction / source bans通过 | 不计Python数量 |
| 报告/索引门禁 | 89通过 / 0失败 | 最终复验见日志 |
| Ruff / compileall / diff check | 全部通过 | 含全部改动脚本 |

发现后续边界时中断的早期主组不计完整结果；最终主组在产品/测试冻结后完整跑完，保存完整异常/警告与summary。两资源独立组在本轮已真实执行，后续修补只涉及授权票据/待办worker身份与schema测试快照，没有改资源/动画源码或依赖。Qt6.8为聚焦验证，不能声称该平台全套或Windows实机全部通过；之前记录的Qt6.8菜单包装对象普查问题未复跑/未修复。

最终聚焦命令：`python -m pytest -q tests/test_companion_dual_speech.py tests/test_todo_delivery.py tests/test_voice_chime_service.py`。
Qt6.8命令：`/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q tests/test_companion_dual_speech.py tests/test_companion_head_speech.py tests/test_voice_chime_service.py tests/test_todo_delivery.py tests/test_companion_proactive_service.py tests/test_companion_interactions.py tests/test_overlay_self_talk.py tests/test_click_self_talk_speech.py tests/test_self_talk_voice_precache.py tests/test_companion_feed_presentation.py tests/test_architecture.py`；schema另跑 `tests/test_config_schema.py`。
Node命令：`node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js` 及 `node integrations/dsh-pet-bridge/verify_import.mjs`。日志 `/tmp/dual-{main-verified,qt68-complete,final113,stress,webm,lowwarm,frame,node,bridge}.log`，最终性能JSON `/tmp/dual-{perf-delivery,interaction-perf-delivery}.json`。

```bash
source /workspace/.onboarding/dsh-pet-env.sh
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_companion_speech.py
ruff check pet/ tests/ scripts/benchmark_companion_interactions.py scripts/benchmark_companion_speech.py scripts/stress_companion_speech.py scripts/capture_settings_pages.py
python -m compileall -q pet packaging scripts
git diff --check
```

## 限制与回滚

新增真实联网TTS流量须用户明确同意；Fake仅记录合成请求，不能证明声音/Windows串行设备。真实模型成功后频繁互动可能比旧冷却增加费用，单飞不等于费用预算，错误120秒保护仍保留。已发送的请求无法撤回；仅保证未播放旧结果不再发声。

此前Qt6.8菜单包装对象普查残留、旧smoke素材数量断言过时及WebM退役池/慢帧问题未纳入本轮修补，不削弱断言、不声称已解决。语音Guard配置mtime使其它设置保存也可保守取消尚未开始的语音。待办JSON送达仍沿原非跨崩溃原子边界，未承诺声音与数据写入原子。

退出后可回退本轮提交；原被动字段、统计、待办/SQLite及历史不删除。旧代码忽略新主动朗读字段。提交开发分支后停止，等待用户Windows集中复验，不扩展功能。
