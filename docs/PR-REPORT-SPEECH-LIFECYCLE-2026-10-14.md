# 气泡语音生命周期与定点修复交付（2026-10-14）

基线 `5556459d4ca50fc56427906b245d994134691c69`；独立修复分支 `fix/tts-bubble-lifecycle-and-interactions`。阶段 A `d775ae4`，阶段 B `f12762a` / `eb855e9`，阶段 C `6c98bc4`。源码收尾 `cf2cfd5`（播放器销毁加固 `5afd0b8`；独立回执 `8f5aad3`），最终证据提交与远端状态见交付回复。对应[Windows 源码验收清单](WINDOWS10-SPEECH-LIFECYCLE-ACCEPTANCE.md)，[原已确认语音/体验基线](PR-REPORT-COMPANION-LATENCY-VOLUME-2026-10-13.md)。本轮不重打包、不重建或发布 v1.0.0，不操作用户 AppData。

## 修改文件说明

新增文件均在下表；没有删除文件。增删行数相对基线 `5556459`。

| 文件 | 增删 | 改动及原因 |
|---|---:|---|
| `CONTEXT.md` | +4 / −0 | 记录本轮独立分支范围与原Windows证据保护。 |
| `docs/INDEX.md` | +2 / −0 | 登记本轮报告及源码验收指南。 |
| `docs/PR-REPORT-SPEECH-LIFECYCLE-2026-10-14.md` | +138 / −0 | 本交付证据、文件清单、性能及限制。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +7 / −0 | 增加源码验收入口，不修改旧构建流程。 |
| `docs/WINDOWS10-SPEECH-LIFECYCLE-ACCEPTANCE.md` | +98 / −0 | 独立目录、逐条PowerShell命令与本轮Windows复验清单。 |
| `pet/character_names.py` | +40 / −0 | 核心层同进程别名通知，只刷新标题；不依赖可选chat包，不重载会话。 |
| `pet/chat/legacy_widgets.py` | +7 / −1 | 经典对话使用统一显示名并接收即时改名。 |
| `pet/chat/providers.py` | +6 / −2 | SSE解析保留结束原因，可选返回流结束元数据。 |
| `pet/chat/service.py` | +8 / −1 | 可选严格完成检查，普通聊天默认接口兼容。 |
| `pet/chat/widgets.py` | +7 / −2 | 现代对话统一名称优先级和即时刷新。 |
| `pet/companion/head_speech.py` | +16 / −9 | 实际回执创建绑定；手动识屏也可按主动授权启动原通道。 |
| `pet/companion/interaction_service.py` | +4 / −3 | 摸头预算256与完整性回退；待播过期保留，健康长播放不受30秒限制。 |
| `pet/config.py` | +3 / −1 | 别名成功保存后通知对应配置身份的窗口。 |
| `pet/festival_service.py` | +16 / −1 | 原独立节日语音绑定已展示气泡，支持停止。 |
| `pet/manual_screen_speech.py` | +95 / −0 | 手动识屏发起者/请求/阶段/隐藏和销毁保护。 |
| `pet/overlay_shell.py` | +37 / −9 | Overlay对应发起者展示、使用其配置并接入朗读。 |
| `pet/speech_binding.py` | +135 / −0 | 唯一任务、状态、守卫、等待/停滞释放与销毁安全。 |
| `pet/speech_bubble.py` | +60 / −0 | 仅暂停绑定隐藏计时；保留分页并接媒体进度及正确结束。 |
| `pet/voice_chime.py` | +12 / −5 | 时间感知默认选择与英文时间；保留自定义优先级/调度/缓存键。 |
| `pet/voice_chime_quotes.py` | +41 / −0 | 中英时段候选，不调用AI或推测用户事实。 |
| `pet/voice_chime_service.py` | +178 / −19 | 原单播放器的任务结算、媒体顺序、排队释放与合成编号。 |
| `pet/window.py` | +37 / −7 | Legacy手动识屏提示和最终回复接入可撤销共享朗读。 |
| `scripts/benchmark_speech_binding.py` | +68 / −0 | 离线真实Qt绑定/策略/文案耗时和对象回收测量。 |
| `scripts/run_companion_acceptance.py` | +6 / −1 | Fake无音频时释放显示等待，仍完全离线。 |
| `scripts/stress_companion_speech.py` | +3 / −0 | 将五个新增测试族纳入原四CPU三轮门禁。 |
| `tests/test_chat_display_name.py` | +50 / −0 | 别名/恢复默认/重开/切角/不改会话身份。 |
| `tests/test_chime_time_context.py` | +30 / −0 | 七时段、中英、跨日、定时稳定、自定义及关附加台词。 |
| `tests/test_companion_completion.py` | +63 / −0 | 真实SSE与Qt worker的length/EOF/网络异常/兼容/接近80字。 |
| `tests/test_companion_dual_speech.py` | +11 / −4 | 第二个响应使用事件同步，保持合并和并发断言。 |
| `tests/test_companion_head_speech.py` | +4 / −0 | 缓存复播前模拟真实结束，不要求叠音。 |
| `tests/test_companion_interactions.py` | +1 / −1 | 验证仅摸头预算提高为256。 |
| `tests/test_companion_volume.py` | +3 / −0 | 模拟第二条媒体结束后复验缓存/静音，保持最新音量断言。 |
| `tests/test_manual_screen_speech.py` | +126 / −0 | 真实菜单/线程/主子/拓扑/权限/提示竞争/长回复/取消。 |
| `tests/test_speech_binding.py` | +369 / −0 | 真实气泡和模拟设备的分页/队列/缓存/结束/取消/销毁/迟到结果。 |
| `tests/test_sprite_menu_parity.py` | +2 / −0 | 手动菜单测试建立真实可见宿主前提。 |
| `tests/test_sprite_menu_target.py` | +2 / −0 | 主子菜单定位测试使用实际可见Overlay。 |
| `tests/test_voice_chime.py` | +8 / −15 | 默认时段契约与旧自定义轮换；保留真实Qt而只模拟设备。 |

## 实现与调用链

- 名称：`Config.set_character_alias → 同进程信号 → 两种 ChatWindow._apply_character_theme → Config.character_display_name`。只有显示头部更新，不重建会话或更改 character_id。原应用外部配置刷新仍保留。
- 无聊天变体：把通知放在核心 `pet.character_names`，冷子进程阻断全部 `pet.chat` 导入仍能保存角色别名；原对话窗口仍使用相同信号，无新设置。
- 摸头：原 96-token 预算、SSE 丢弃 finish_reason、EOF 被默认为完成，是可以由模拟响应证明的缺口。摸头专用预算提高为256，投喂保留96，普通聊天配置不变。交互通过可选 require_complete 获知 reason/终止标记；length、无终止标记的断流及网络异常转一次本地备用，不追加标点或无限重试。DONE 但无 reason、普通无新参数的兼容 Fake Provider 均继续有效。在隔离的基线5556459实际SSE/worker/交互调用链，以固定合成半句加length事件探测：`partial_shown=true, requests=1, head_budget=96`；相同探针运行修复源码：`partial_shown=false, requests=1, head_budget=256`。这是模拟网络证据，不是真实DeepSeek样本。无法以这些代码证据认定用户所有偶发半句只有一个根因，真实联网样本仍未复验。
- 报时：七个本地时段，每种语言每时段32个组合候选；日期加原日内调度序号确定性轮换，同一时刻气泡/语音/预缓存使用同一文案。用户语言自定义台词沿原日期洗牌规则；关附加台词只报时间。保留中文口播/数字显示，英文默认时间与文案均为英文。不调用 AI，不迁移配置。
- 绑定：业务成功文字回执 → head_speech → SpeechTicket → AppShell.speak_self_talk → 原缓存 / VoiceChimeService / 单一 QMediaPlayer。任务携带唯一 ID、气泡 text_presentation_id、可撤销 guard 和等待/合成/排队/加载/播放/完成/失败/取消状态。暂停的只是该次展示的 hide timer；不改 sticky，不介入无 TTS 气泡、音乐或聊天窗口消息。
- 播放：只有匹配当前源、确实起播的 EndOfMedia 才结算正常完成；StoppedState 等一个 GUI 事件轮次再判断取消，兼容状态/结束信号顺序；原生播放器destroyed及时释放当前和待播绑定；旧播放/错误事件先比对当前真实媒体状态，拒绝旧Playing/NoError回调。媒体失败/无效/静音/授权撤销/销毁释放绑定并恢复普通计时。取消有效绑定会收口其音频；旧任务不能关闭新展示或另一只宠的气泡。迟到合成由串行编号丢弃，缓存键不含任务 ID。
- 分页：完整原始回复只交 TTS一次；内部翻页不改展示编号、不触发 hidden。等待时保留原翻页；起播从第一页配合实际 duration/position 按页字符比例顺序翻页，无进度时沿用原翻页时长。短音频提前结束时继续展示遗漏的页，最后页保留约1.5秒。绝不通过每页重新合成或停止分页来延长气泡。
- 手动识屏：菜单原回调 → 捕获发起者的 ManualScreenRequest → 原线程截图/视觉请求 → 带请求身份的 queued 结果 → 原目标的成功展示 → 主动类别绑定。独立于自动识屏开关/白名单，不新增背景截屏；前置提示阶段在最终结果到达时作废，不读错误详情，保留原历史同步回调。声音开关关闭不改变手动识屏的正常文字流程；角色/Provider 变化、隐藏再显示、取消、销毁丢弃旧结果。业务忙碌/原4秒操作间隔保持。
- 独立消费者：报时和节日记录本次新展示编号，拒绝把旧的同文气泡当成成功回执；关闭显示时保留独立声音行为。只绑定它们确实已展示的气泡，沿原独立声音/显示开关；两个陪伴朗读开关不覆盖这两者。Fake 只记录请求、释放没有真实音频的等待，不连接模型/语音服务。

## 性能分析

Linux x86_64 / Python3.12.14 / PySide6 6.12.0 / offscreen，完全离线的 `python scripts/benchmark_speech_binding.py`。实测如下（微秒；纯绑定样本不包含控件重绘，策略样本使用隔离合成配置文件）：

| 路径 | 样本数 | 中位数 µs | P95 µs |
|---|---:|---:|---:|
| 原普通 show_text | 200 | 132.654 | 271.589 |
| 新绑定创建/释放 | 200 | 51.487 | 86.911 |
| 纯有效性回调检查 | 2000 | 0.621 | 0.672 |
| 配置指纹/授权/音量文件策略检查 | 2000 | 78.673 | 120.121 |
| 时段默认文案选择 | 2000 | 2.494 | 2.634 |

定向释放后该气泡仍存活，子 SpeechTicket 对象数为0。每个活动任务四次/秒的配置策略校验按本机中位数约0.315ms/秒；这不是实际声卡或完整动画性能指标。空闲没有绑定计时器。新建每个绑定包含一次UUID随机数获取和Qt计时器注册；活动守卫有配置stat/JSON读取，不把这些系统调用描述为零成本。没有新增磁盘写入和网络合成请求；文件读取限于原授权/音量配置。

对Native RSS没有长期实声运行曲线，不能据对象数为0断言进程RSS零增长。

未增加播放器、网络请求、TTS合成次数或音频线程；日期候选计算只在原报时计算触发。活动绑定每250ms检查一次，只有仍在等待/播放的有界任务有计时器，完成后立即停表并由 Qt 删除。真实策略校验包含原配置指纹及音量文件读取；表中另列其成本，不能把纯 lambda guard 的成本当成真实文件校验。等待/合成/排队120秒释放，原摸头更短的待播失效保护保留；正常播放没有固定30秒总时长上限，仅180秒无进度才判停滞。原共享单飞合成与最新一条待播队列不扩容，目标与展示作废立即释放；无活动任务不新增常驻检查。需要真实音频设备才能测硬件声道/实际声音结束，模拟 duration 不算声音性能。

## 实机运行记录

用户此前已在 Windows10 确认新微软接口、音量热调/静音/设置同步、快速投喂、自动识屏提示及最终语音、灵动岛聊天/授权/动画拖拽通过。本报告不撤销这些证据；本轮新增改动**未 Windows 实测**。

本机探针：Linux x86_64、Python3.12.14、Qt6.12.0；`powershell.exe`、`pwsh`、`wine`、`ISCC.exe` 均不存在。因此没有 Windows 原生执行、声卡/Edge在线播放或新安装包构建结果。按本轮任务不重打包；NOT TESTED：真实 Edge/DeepSeek/视觉模型、本轮 Win10 声音与分页、多宠/退出硬件信号顺序。原已发布安装程序未改动。

实际 Linux offscreen 进程：`PET_RENDER_TOPOLOGY=legacy` / `overlay` 下执行 `python -X utf8 scripts/run_companion_acceptance.py --data-dir <全新/tmp目录> --auto-close-seconds 6`。两种拓扑都输出 `FAKE: synthetic proactive bubble displayed`；自动退出随后报“帧序列供给线程2000ms内未退出”和 `QThread: Destroyed while thread ... is still running`，进程退出134，**退出冒烟失败**。将基线5556459源码只读归档到独立/tmp目录、使用新的Fake数据目录执行同一6秒退出，复现同样报错/退出134，因此是已有的Linux短自动退出/后台帧序列边界，不能报告本輪正常退出PASS。本轮按用户保护要求没有修改动画/帧序列；这项已知风险保留，不推测Windows同样失败。

该记录仅是真Linux Qt进程与模拟Provider的操作，既不是Windows GUI，也不是实际声音验收。

## 测试与风险

红→绿：名称/流完成首轮7失败；时间感知文案首轮14失败、2通过；基础绑定10失败；手动真实 Qt 菜单入口在替换回阶段B源文件后4失败、4通过（两个拓扑×主/子宠；验证真实朗读请求），恢复修复后通过；独立报时/节日的旧同文气泡回执又补2条失败→通过用例。初次探针类名误写导致的 collection error不作为行为失败证据。

完整聚焦首次947通过、3跳过；Qt6.8.3首次聚焦630通过、1跳过；最终源码聚焦635通过、1跳过（无显示环境不截屏）；播放终止顺序聚焦113通过；原生播放器销毁先1失败后相关159通过；无聊天兼容先1失败后38通过。补充：Qt6.12在独立回执收尾时完整主分组5133通过/50跳过/18警告（810.17s）；最终增加原生播放器/无聊天兼容后，Qt6.12主分组在 `tests/test_library_shared_media.py::test_owner_exit_hands_warm_responsibility_to_peer` 原生Bus error（退出135），没有完整统计。磁盘/tmp及共享内存均未满；同文件独立复跑14通过（0.88s），未定位长序列稳定触发条件，不修改素材/动画代码、不忽略该文件。最终标准Qt6.12主分组重跑完整通过：**5136通过、50跳过、19条Qt弃用警告，790.14s**。源码与上一中断轮完全相同，没有关功能、改断言或排除崩溃文件。

目标Qt6.8.3完整主分组：**5130通过、50跳过、6失败、4警告，918.34s**。六项在独立原基线5556459逐项复现（3项0.87s，另3项0.40s），均保留失败：`test_menu_tree_release::test_repeated_context_menu_rounds_leave_no_qt_residue`（QAction残留）、`test_pet_sprite::test_mirror_frame_falls_back_to_mirrored_without_flipped`（测试删除本来没有的API）、`test_requested_regressions::test_ojingjing_entry_hover_survives_widget_children`（hover）、`test_sprite_dpr::test_needed_transforms_still_run_in_order`、`test_sprite_dpr::test_mirror_uses_flipped_horizontal`（两项flipped API）、`test_sprite_menu::test_scale_action_sets_sprite_scale_and_moves_check`（scale勾选）。本轮不改变动画/菜单，也不把这个版本完整回归写成PASS；相关本轮聚焦635通过/1跳过。

最终标准CI的不同pytest测试合计**5204通过、50跳过**（5136主分组 + 41 WebM + 27预热；37帧序列属于重复复验，不重复计入）。标准主分组警告为QImage.mirrored、QDragEnterEvent、QHoverEvent弃用；没有把弃用警告当失败或关闭警告。

四CPU满载（cgroup 400000/100000，四个burner，`python scripts/stress_companion_speech.py`）三轮：715通过/1跳过（168.80s）、715通过/1跳过（168.96s）、716通过/1跳过（166.45s，加入最后的无聊天兼容用例）；原生播放器绑定时序三轮一致，最后的模块迁移不改变时序实现。

完整CI视频分组：Qt6.8.3 WebM41通过26.43s、帧序列37通过0.97s（帧序列在主分组也执行，不重复计唯一测试）；低优先级预热首轮原生崩溃，按原CI单次重试27通过31.41s。Qt6.12同组也分别41/37/27通过，预热首轮同样原生崩溃、单次重试通过，均保留首轮日志。Node34通过，零依赖bridge导入通过。Ruff全pet/tests及本轮scripts、compileall pet/scripts/tests、git diff --check最终通过，以上均为Linux/模拟设备测试；原生QObject删除是Qt运行验证，也没有播放硬件声音。

修复过程中发现并处理的测试问题：两次缓存复播测试未发出前一条媒体结束回执；现在仍检验原缓存、最新音量和唯一播放器，同时模拟真实结束。投喂合并测试用瞬时空闲断言区分两个快速请求，改用第二个网络响应的 Event 控制，继续严格检查单飞、合并、旧结果静默。原 Overlay菜单测试补真实窗可见前提，不能把隐藏宿主当成可点击菜单。销毁测试仅投递目标气泡的 DeferredDelete，避免跨用例批量销毁其他Qt对象；绑定销毁回调不再触碰正在拆卸的 QWidget。语音报时测试去掉伪造整个 QtCore 模块，只模拟音频设备，避免 import 顺序掩盖依赖。

无新增持久配置或迁移，两个朗读开关默认关闭、自定义台词、音色/语速/音调/音量、原缓存均保持。主/子、Legacy/Overlay 使用原配置身份；无真实私人数据进入测试或日志。剩余重点验收：真实QtMultimedia信号次序、慢网络排队/取消、超长回复分页、原单独设置窗口、在线音色和声音结束。对于缺少任何结束元数据的兼容非SSE Provider，仍按其正常迭代结束兼容，无法凭空判断句子语义是否完整；不擅自改写输出。


### 实际执行命令

先 `source /workspace/.onboarding/dsh-pet-env.sh`；目标版本命令将 `python` 替换为 `/workspace/.venvs/dsh-pet-qt68/bin/python`，其余参数不变。

```bash
python -X faulthandler -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py --junitxml=/tmp/bubble-final-verified.xml
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_companion_speech.py
python scripts/benchmark_speech_binding.py
ruff check pet tests scripts/benchmark_speech_binding.py scripts/stress_companion_speech.py scripts/run_companion_acceptance.py
python -m compileall -q pet scripts tests
git diff --check
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
```

Qt6.8.3聚焦命令：

```bash
python -m pytest -q tests/test_speech_binding.py tests/test_manual_screen_speech.py tests/test_companion_completion.py tests/test_chat_display_name.py tests/test_chime_time_context.py tests/test_voice_chime_service.py tests/test_companion_head_speech.py tests/test_companion_precue_speech.py tests/test_companion_result_speech.py tests/test_companion_dual_speech.py tests/test_vision.py tests/test_voice_chime.py tests/test_festival.py -rs
```

50跳过：Windows专有识屏设置、JobObject、原生console/前台窗口/逐像素穿透、QUNS、WTS/窗口消息、PowerShell5.1/ISCC/PATHEXT、winmm和明确启用的实声冒烟；macOS/AppKit/Cocoa；无显示环境截图；未生成的可选GIF。跳过没有改成通过，真实Windows和声卡/网络能力仍NOT TESTED。

Qt UI review：聊天头部只替换显示名并接收对应配置通知，无布局/色彩/控件重排；气泡保留分页、原交互sticky、图片和角色定位，通用show_bubble没有加无差别朗读。✓源码与Qt接缝审查通过；实际Windows HighDPI/声音/组件退出仍按[本地清单](WINDOWS10-SPEECH-LIFECYCLE-ACCEPTANCE.md)复验。

### Git及审查

基线5556459；独立修复分支，源代码最后提交cf2cfd5，后续提交仅交付证据。未改main、未重建/发布安装包、未操作用户正式数据。远端与PR状态在最终交付回复中列出；GitHub API访问若继续403，不伪造PR编号，以独立分支及比较链接提供可审查结果。
