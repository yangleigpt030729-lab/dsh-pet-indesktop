# Edge TTS 新接口、灵动岛聊天和指定回复朗读交付

基线：`feature/win10-companion-memory`，`b6010dcd3d7dc93c92705ece289f42f48bdc6672`，2026-10-13。本报告补充[Windows验收指南§12](WINDOWS10-COMPANION-ACCEPTANCE.md#12-微软新语音接口岛聊天与两类回复朗读更新和试听)、[双朗读报告](PR-REPORT-COMPANION-DUAL-SPEECH-2026-10-13.md)及[原打包门禁](ONEDIR_PACKAGING.md)。不合并main，不改变模型、动画、原文件授权/统计或报时/节日独立规则。

## 根因、修改范围与调用链

用户真实Windows10反馈：旧 `speech.platform.bing.com` WebSocket403，直连/更换网络无效；临时把SDK的 `communicate.WSS_URL` 指向微软 `api.msedgeservices.com` 后成功生成、播放MP3。项目原worker直接使用SDK默认URL，因而仍走旧接口。修复仅在原后台合成worker懒加载SDK后，应用项目自己的地址兼容层；使用SDK的TRUSTED_CLIENT_TOKEN常量，不复制真实密钥，不改site-packages。Communicate、SSML、DRM/请求头、代理(trust_env)、TLS、音色、语速/音调/音量、缓存、重试/降级和播放器保留。音色列表刷新仍走原SDK voices接口及原缓存/内置音色回退，本轮未改该功能。

- 原「立即试听」与两类朗读 → 原 `VoiceChimeService` → 缓存命中直接播；未命中 → 原 `_TTSWorker._synthesize` → `edge_tts_compat.configure_endpoint` → 原SDK Communicate.save → 原播放队列。没有新TTS服务、播放器或独立线程。
- 岛卡片真实按钮 → `DynamicIsland._on_card_chat` → `open_chat_requested` → `AppShell._open_chat_from_island` → `PetInstance.open_quick_chat` → deferred `_show_quick_chat` → OverlayShell.open_quick_chat。原先Overlay的win=None提前返回；现在按拓扑分派。卡片收起保留；Legacy、隐藏宠物的IslandChatBubble、无聊天模块和退出前失效分支均保持。
- 自动识屏原异步视觉结果 → bridge携带任务代次/角色 → GUI `_present_reply` → 原首个可见宿主（不新增广播） → `head_speech.present_reply(active=True)` → 成功显示同一文字回执 → 原共享语音。只需要识屏自己的功能开关与主动朗读授权，不依赖普通proactive_chat总开关。
- 文件拖入 → 原offer/明确确认 → 原extract_text/ChatService → 原完成回调 → `present_reply(active=False)` → 成功展示「解读完成：…」后原共享语音。未确认不读取、不请求；原趣味投喂仍仅安全元数据，原文件不改。

`present_reply`只在这两个成功业务边界使用，通用show_bubble没有朗读钩子。进度、字数/耗时、开始/停止/失败、识屏前置提示、余额/Agent消费/计数、图片和投喂统计静音。空回复只保留原完成状态，静音。一次展示回执只提交一次语音；子宠不存在自己的气泡时不回退父宠语音。回执、任务代次、配置身份/mtime、业务开关、角色、朗读授权/记忆撤销、隐藏世代、30秒有效期、宿主销毁/退出在播放前再检查。TTS失败保留已展示文字，不插入错误气泡。已经开始的声音仍沿原播放器生命周期。

## 修改文件说明

相对基线的最终 `git diff --numstat`，23文件，新增6、无删除。

| 文件 | 增/删 | 修改及原因 |
|---|---:|---|
| `CONTEXT.md` | +4/−0 | 记录新接口、岛聊天及成功回复朗读边界，避免后续接入混淆。 |
| `docs/INDEX.md` | +2/−0 | 登记交付报告，提供唯一文档入口。 |
| `docs/PR-REPORT-EDGE-TTS-ISLAND-RESULT-SPEECH-2026-10-13.md` | +118/−0 | 记录根因、逐文件变更、性能/测试与原生未测证据。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +159/−0 | 新增网页ZIP更新、独立构建、在线试听、业务矩阵与回退§12。 |
| `pet/app.py` | +18/−2 | 修正win=None的Overlay聊天早退并检查deferred退出/窗口生命周期。 |
| `pet/companion/head_speech.py` | +31/−3 | 增加指定回复成功回执入口、独立消费者及业务配置失效，禁止子宠回退父气泡。 |
| `pet/companion/proactive_settings.py` | +1/−1 | 主动声音说明加入识屏及在线隐私告知，不改开关/默认值。 |
| `pet/edge_tts_compat.py` | +13/−0 | 新增项目内SDK地址兼容层，不改虚拟环境。 |
| `pet/file_interpret.py` | +16/−1 | 只在明确授权的非空完成回复成功展示后接被动朗读，任务/角色guard。 |
| `pet/multi_window_shared.py` | +7/−0 | 沿原首个可见宿主选择转发识屏最终回复，不改通用气泡。 |
| `pet/proactive.py` | +21/−6 | 携带代次/角色穿过原Qt桥接，成功回复按主动分类接共享语音。 |
| `pet/settings_interaction.py` | +1/−1 | 被动声音说明加入已授权文件回复和微软在线隐私告知。 |
| `pet/voice_chime_service.py` | +2/−0 | 原懒加载合成worker调用地址适配；缓存/通道/重试原样。 |
| `scripts/build_onedir.ps1` | +2/−0 | 归档TTS门禁失败停止，保留BOM和全部原检查。 |
| `scripts/smoke_edge_endpoint_frozen.py` | +35/−0 | 新增真实冻结适配执行诊断；网络边界合成且明确非Windows声音。 |
| `scripts/stress_companion_speech.py` | +4/−0 | 把新接口/岛按钮/识屏/文件回复纳入原四burner三轮压力族，包含共享多窗。 |
| `scripts/verify_bundle_tts.py` | +3/−0 | 要求项目适配、原worker和SDK常量实际进入冻结清单。 |
| `tests/test_companion_head_speech.py` | +1/−0 | 旧head-only生命周期用例显式关闭新的文件声音消费者。 |
| `tests/test_companion_result_speech.py` | +323/−0 | 109项实际Qt业务/四开关/主子/拓扑/取消/静音/失败/授权回归。 |
| `tests/test_edge_tts_endpoint.py` | +81/−0 | 真实SDK仅替换WS网络，验证新地址、TLS/代理/SSML、MP3写入及缺模块拒绝。 |
| `tests/test_island_overlay_chat_entry.py` | +69/−0 | 8项实际卡片按钮→信号→真实输入气泡，含隐藏/无聊天/退出。 |
| `tests/test_single_process_shared.py` | +6/−2 | 原多窗回归改走携带代次/角色的真实回复信号，保留首个可见宿主断言。 |
| `tests/test_voice_chime_edge_voice.py` | +2/−0 | 现有假SDK添加真实SDK模块形状，保留原音色回退测试。 |

原配置不迁移/新增字段：`self_talk_speak_enabled`继续兼容旧被动偏好，`proactive_bubble_speak_enabled`仍独立默认关闭，语音缓存与每只宠物音色配置不变。两个设置的说明更新为明确的在线合成隐私告知，控制器/保存/搜索位置不变。应用了仓库qt-ui-review检查：修改的两项说明与聊天路由 ✓ pass；760/1240px真实Qt窗口的说明自动换行63/42px，无截断，窄窗可滚动到整行。焦点/键盘控件没有改动；新schema、迁移、布局重排、平台显隐门禁不适用。Windows字体/DPI/实际键盘仍待实机。

## 性能分析

环境：Linux x86_64、Python3.12.14、Qt6.12.0 offscreen、edge-tts7.2.8、aiohttp3.14.5；音频/网络边界合成，真实Qt显示、回执与原guard执行。不是Windows性能或声音结果。

1. `python scripts/benchmark_companion_speech.py`：Legacy/Overlay×主/子×被动/主动，1600次回执、16000次guard。各组入队平均94.75–279.88µs，最大3.716ms；guard平均19.31–65.26µs，最大2.606ms。进程RSS81.04→146.14MiB，包含依次创建的Qt/动画宿主；Legacy热段保持92.09–100.42MiB，Overlay某组热段119.20→130.71MiB，后组154.02→145.32MiB。不能据此宣称长时间零内存增长。
2. `/tmp/edge_reply_benchmark.py`（调用真实present_reply，业务宿主、回执/guard与上一个脚本一致；仅音频回调记录）：8组各250，共2000次最终回复显示。平均427.10–883.95µs，最大20.039ms（含第一次文本布局/绘制与并行回归调度）；SDK地址赋值3×100000次，均值0.436/0.216/0.186µs。命令 `python /tmp/edge_reply_benchmark.py`，原始JSON保存在本次日志包。此临时测量脚本也随日志包提供用于复现。
3. 稳态：无新增定时器、扫描或预缓存；SDK适配只在原缓存未命中的语音合成时执行。新增业务入口只在已有AI完成事件触发一次，没有语音专用模型请求。现有配置身份guard加两个配置项，没有新增磁盘写、凭据读取、网络连接或线程。合成缓存、在线请求与播放成本沿原服务；主动识屏/授权文件回复在用户开启声音后可能增加微软在线合成流量。连续互动的DeepSeek费用规则不改。
4. 本次压力命令 `python scripts/stress_companion_speech.py`：原互动/两类语音/Todo时序族加新业务、岛按钮及接口测试，四CPU burner×三轮，结果见下表。原资源、懒加载、线程/行数预算和frameseq检查包含在完整CI分组，动画解码路径没有修改。

## 实机运行记录

- 用户已有Windows10 22H2 x64/19045、Python3.12、Qt6.8.3、PyInstaller6.19的旧绿色版GUI/独立设置/Fake交互成功；用户临时SDK新地址生成/播放MP3成功。之前四个PS5.1脚本parse PASS是用户证据，不代表本轮新build_onedir脚本已原生解析。
- 本轮Linux执行真实Qt按钮/信号/对话气泡、文件明确确认后原ChatService/真实Qt完成显示，以及识屏工作线程→GUI桥接→实际文本回执；模型、截图字节、网络、音频设备替换成合成边界。原回归仍保留严格Windows FFmpeg FreeConsole探针；没有放宽黑窗口断言。
- 使用PyInstaller6.19.0实际冻结独立离线诊断 `scripts/smoke_edge_endpoint_frozen.py`，耗时21.463s。运行真实ELF输出 `FROZEN endpoint adapter PASS: api.msedgeservices.com; synthetic/offline; real audio NOT TESTED`。真实归档检查输出 `[tts] bundle TTS stack OK (27 modules required, 936 frozen)`，含pet.edge_tts_compat、pet.voice_chime_service及edge_tts.constants。**这是Linux诊断包，不是桌宠Windows绿色包。** 官方PowerShell现在运行同一归档门禁，缺模块失败即停止。
- 当前环境无Windows/powershell.exe/wine/远程Windows运行器。GitHub Actions REST探针带现有GH绑定与匿名均被代理CONNECT403拒绝，未触发构建；Git分支推送通道仍可用。不索取/输出Token，不用tag触发发布，不放宽TLS或打包门禁。因此无法在这里生成/交付新的Windows x64便携ZIP，已提供完整本机原生构建/试听/回退入口（指南§12）。
- 修复后项目的Windows10聊天入口、两类新增朗读、真实微软网络/音频、原生EXE/FFmpeg无控制台及PS5.1新增归档命令均 **NOT TESTED**。真实DeepSeek及长时间音频/DPI/内存也NOT TESTED。源码/Fake通过不能代替这些结果。

## 测试与风险

先红后绿证据：原接口与实际Overlay岛按钮测试在基线出现2 failed/1 passed（Legacy通过）；32项文件/识屏四开关×主子×拓扑测试在基线16 failed/16 passed（应朗读的16项失败，静音组合通过）。测试夹具不模拟show_bubble，只替换网络/音频边界；修复后结果如下。首轮完整套件4957 passed/48 skipped/19 warnings、1 failed：旧共享多窗测试直接调用2参数私有桥接槽，已改为启用识屏后发送带代次/角色的真实4参数信号，保留首窗/次窗断言；该文件修正后13 passed（0.62s），随后再执行完整主套件与扩展压力族。某空回复测试发现验收启动器替换所有自定义Provider，已改为独立Fake Provider与单独音频边界，避免错误结果。

| 验证 | 真实结果 | 日志 |
|---|---|---|
| 完整CI主套件 | 4958 passed、48 skipped、18 warnings，901.19s | edge-main-final.log |
| WebM生命周期隔离 | 41 passed，26.07s | edge-webm.log |
| 低优预热隔离 | 27 passed，32.44s | edge-lowwarm.log |
| frameseq额外隔离复验 | 37 passed，2.21s | edge-frameseq.log |
| Qt6.12聚焦/相关12文件 | 325 passed、4 skipped，30.01s | edge-focus-final.log |
| Qt6.8.3聚焦/相关11文件 | 443 passed、1 skipped，34.09s | edge-qt68.log |
| 四burner三轮 | 每轮489 passed、1 skipped；59.74/61.93/60.54s | edge-pressure-final.log |
| 资源/性能/懒加载7文件 | 101 passed，11.32s | edge-resource.log |
| Node原7契约文件 | 34 passed、0 skipped | edge-node.log |
| Bridge hermetic import | PASS | edge-bridge.log |
| Ruff、compileall、diff check | PASS | edge-ruff.log、edge-compile.log |
| 定稿后报告门禁 | 93 passed，0.40s | edge-report-gate.log |
| 实际冻结执行/实际归档模块 | PASS；离线Linux诊断 | edge-frozen-smoke.log、edge-frozen-verify.log |

测试全程使用空keyring后端、隔离XDG目录；Windows命令也显式设置并恢复空后端，避免卡片自动余额刷新读取生产密钥。

实际命令（先 `source /workspace/.onboarding/dsh-pet-env.sh`）：

```bash
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python -m pytest -q tests/test_edge_tts_endpoint.py tests/test_island_overlay_chat_entry.py tests/test_companion_result_speech.py tests/test_companion_head_speech.py tests/test_voice_chime_edge_voice.py tests/test_voice_chime_service.py tests/test_file_interpret.py tests/test_proactive.py tests/test_overlay_chat_proactive.py tests/test_verify_bundle_tts.py tests/test_companion_build_workflow.py tests/test_powershell_encoding.py
/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q tests/test_edge_tts_endpoint.py tests/test_island_overlay_chat_entry.py tests/test_companion_result_speech.py tests/test_companion_dual_speech.py tests/test_companion_head_speech.py tests/test_voice_chime_edge_voice.py tests/test_voice_chime_service.py tests/test_file_interpret.py tests/test_proactive.py tests/test_overlay_chat_proactive.py tests/test_island_chat.py
python scripts/stress_companion_speech.py
python -m pytest -q tests/test_pr_report_discipline.py
python -m pytest -q tests/test_app_lazy_imports.py tests/test_idle_low_fps.py tests/test_tick_driver_idle_stop.py tests/test_first_frame_budget.py tests/test_meta_cache_budget.py tests/test_library_idle_frame_trim.py tests/test_settings_and_resources.py
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
ruff check pet/ tests/ scripts/verify_bundle_tts.py scripts/smoke_edge_endpoint_frozen.py scripts/stress_companion_speech.py
python -m compileall -q pet scripts packaging
git diff HEAD --check
```

实际冻结诊断与检查：

```bash
python -m PyInstaller --noconfirm --clean --onedir --name edge-endpoint-offline --distpath /tmp/edge-frozen/dist --workpath /tmp/edge-frozen/work --specpath /tmp/edge-frozen --paths /workspace/dsh-pet-indesktop --collect-all edge_tts --collect-all certifi --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module tkinter scripts/smoke_edge_endpoint_frozen.py
/tmp/edge-frozen/dist/edge-endpoint-offline/edge-endpoint-offline
python scripts/verify_bundle_tts.py --app-dir /tmp/edge-frozen/dist/edge-endpoint-offline
```

最终互不重复pytest结果：**5026 passed、48 skipped、18 warnings**（4958+41+27）。18项是原QImage.mirrored、QDragEnterEvent/QHoverEvent等弃用提示；offscreen另有不支持raise/窗口mask的Qt后端提示，不等同Windows行为。

命令和完整日志随本次测试日志包保留；主套件+WebM+低优预热是互不重复的完整pytest分组，frameseq、聚焦/Qt6.8/压力均为补充复验，不叠加计数。Windows专属跳过不能算原生PASS。

风险：微软接口未来可能再变化；voices列表仍依赖原服务与回退。只有显式开启分类朗读后，已显示的屏幕/文件AI文字才可能发给在线语音服务，应使用合成素材验收；不在额外日志记录私人回复。长回复超过现有30秒guard有效期时待播放语音会被取消，文字照常保留；没有为本轮扩大队列或修改播放器。原Overlay识屏共享宿主选择仍按原策略，不新增逐宠广播。暂不继续开发，待Windows集中复验。
