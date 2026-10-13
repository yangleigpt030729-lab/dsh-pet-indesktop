# 陪伴投喂延迟、识屏前置朗读与统一音量控制

基线：`feature/win10-companion-memory`，`929e0938b1481db881f94d0a85821be3ff0bfcb8`，2026-10-13；完成复验日期2026-10-14（Asia/Shanghai）。用户已确认上一轮微软新接口/岛聊天/投喂及授权解读语音/最终识屏语音在Windows10实机通过；本次增量需另行验收。补充[Windows指南§13](WINDOWS10-COMPANION-ACCEPTANCE.md#13-已验收基线后的增量投喂速度识屏提示朗读和音量控制)、[上一轮报告](PR-REPORT-EDGE-TTS-ISLAND-RESULT-SPEECH-2026-10-13.md)及[设置门禁](SETTINGS-CHANGE-GATES.md)。未合并main，不修改微软新地址、模型、岛聊天、文件授权或动画。

## 行为与调用链

- 前置语音：原实际识屏/dHash/频控成功边界 → pre_cue检查 → 原成功展示回执present_reply(active=True) → 原head_speech/VoiceChimeService。只按主动朗读，普通主动AI总开关与被动开关均不参与；没有通用气泡朗读钩子。任务代次/角色/功能/precue/授权/隐藏/替换/时效仍检查。相同固定短提示采用现有MP3缓存；无新启动预生成请求。首次冷合成若超过原2.5秒显示窗口或被最终回复替换，迟到结果只缓存不播放，下一次合法触发可命中。最终AI回复沿同一有界音频通道，进度/统计/余额静音规则不变。
- 合成：原_TTSWorker.run直接候选音色合成/重试/默认回退，不再先等refresh_voice_list。真实SDK成功后由原queued桥把元数据刷新请求送GUI，再检查当前授权/停止状态；一个独立元数据线程、无队列，2.5秒timeout，成功列表TTL六小时，失败尝试至少隔15分钟。内置/历史表先支持解析，随后表刷新维持下架检测。所有代理/TLS/SDK DRM/新微软WSS接口/缓存键均保留；Fake worker不会启动元数据网络。
- 投喂：原后台统计/安全元数据就绪 → 立即静音统计 → offer_feeding的50毫秒首批合并窗口（后续输入不延长） → 原单飞ChatService → 合格回复实际展示后立即替换统计 → 原被动朗读。删除not_before+2，不加秒级等待。32项待处理上限、30秒失效、在飞/批内合并、防重复/角色/手动聊天优先、120秒错误退避保留；忙时原pending检查仍保留，完成后立即推进。每批只有一条模型请求，无额外预先生成/语音专用文案/重试；快速输入的合并批次边界受微窗口与实际在飞时长影响，实际费用应按调用记录确认。
- 音量：现代默认布局/旧用户模板补全/自定义隐藏/Legacy → 同一个voice_volume子菜单(QWidgetAction) → 原voice_chime_volume，仅另存默认False的voice_chime_muted。静音保持数值，恢复同一值；滑动解除静音。设置原音量行即时单键落盘、GUI事件绑定刷新；保存时取最新磁盘值，不把旧窗口值覆盖回去。跨进程用QFileSystemWatcher，进程内用信号；无新增常驻定时器/轮询。
- 播放：原VoiceChimeService/QMediaPlayer/QAudioOutput，当前宠物配置 → 最新有效音量，当前播放热更新、待播/新音频起播时再读取。切换音频配置立即断开旧binding，避免DeferredDelete前串宠。未增加播放器/语音线程/实际音量副本，不改系统/音乐/点击音效。原语音缓存、报时/节日消费者生命周期继续使用原通道。
- 失效：mtime改为有界128项语义文件签名缓存，忽略仅音量/静音/slot ownership metadata；其它配置/角色/任务/授权变化仍撤销。每个改变的文件一次读/hash，未变化仅stat；不记录配置原文。投喂、普通主动和共享语音统一采用该签名。原App配置监听在只有音量变化时不重启任务/动画。

## 修改文件说明

| 文件 | + / − | 修改与原因 |
|---|---:|---|
| `CONTEXT.md` | 6 / 2 | 登记用户已通过实机基线及本轮四项增量，避免沿用旧静音/固定等待描述。 |
| `docs/INDEX.md` | 2 / 0 | 登记本交付报告，保持审查入口可发现。 |
| `docs/PR-REPORT-COMPANION-LATENCY-VOLUME-2026-10-13.md` | 100 / 0 | 新增本报告：逐文件、性能、真实环境与测试证据，区分旧实机成功及新未测范围。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | 141 / 0 | 新增§13全新源码/WorkDir/绿色目录构建与回退及验收矩阵，保留旧包/数据。 |
| `pet/app.py` | 6 / 0 | 配置监听遇到仅音量/静音变化时不重启任务，避免热调整撤销有效朗读。 |
| `pet/companion/head_speech.py` | 3 / 5 | 语音身份排除纯音量变化，采用语义文件签名；保留其他授权/角色失效条件。 |
| `pet/companion/interaction_runtime.py` | 2 / 4 | 互动目标身份采用同一语义签名，音量变化不使已展示回复失效。 |
| `pet/companion/interaction_service.py` | 26 / 3 | 删除2秒not_before，50ms首批合并；保留单飞/上限/隐私，新增有界数字耗时。 |
| `pet/companion/proactive_service.py` | 2 / 4 | 主动服务语义签名忽略音量变化，保留每日/间隔/代次控制。 |
| `pet/companion/proactive_settings.py` | 1 / 1 | 既有主动语音说明纳入识屏前置提示，保持一个主动开关。 |
| `pet/config.py` | 3 / 0 | 默认/规范化/热重载加入muted=False，保持原音量key及旧用户数值。 |
| `pet/context_menus/icons.py` | 9 / 1 | 新增统一矢量音量图标，不依赖外部图片或平台字体。 |
| `pet/context_menus/legacy.py` | 2 / 0 | Legacy菜单接入同一音量子菜单，保持原其他入口。 |
| `pet/context_menus/registry.py` | 9 / 3 | 注册音量action/标签/图标/默认布局，支持原编辑器与旧模板补全。 |
| `pet/context_menus/voice_volume.py` | 72 / 0 | 新增主题化QWidgetAction滑块/百分比/静音，操作保持菜单打开，关闭随菜单释放。 |
| `pet/menu_templates/modern-default-v1.json` | 1 / 0 | 默认大小旁插入音量控制，显式隐藏仍由原布局规范处理。 |
| `pet/overlay_shell.py` | 1 / 0 | 每slot配置同步名单补充muted，防止主子宠串用。 |
| `pet/proactive.py` | 4 / 3 | 实际成功显示的识屏前置提示接原主动语音回执，并附precue有效性条件。 |
| `pet/voice_chime_service.py` | 107 / 9 | 合成前不等音色表；受授权的单线程后台节流刷新；原共享播放器热音量及分段计时。 |
| `pet/voice_chime_settings.py` | 23 / 3 | 原音量行即时定点保存、监听菜单变化及保存时取最新值，避免旧窗口覆盖新数值。 |
| `pet/voice_volume.py` | 154 / 0 | 新增唯一音量/独立静音、少量键原子落盘、语义签名和事件绑定，兼容稀疏slot/跨进程；非对象JSON安全撤销。 |
| `scripts/benchmark_companion_latency.py` | 65 / 0 | 新增真实Qt四宿主投喂链路分段基准，仅模型/音频边界合成，便于复现。 |
| `scripts/stress_companion_speech.py` | 3 / 0 | 将新测试及菜单身份族纳入既有四CPU负载三轮门禁。 |
| `scripts/verify_bundle_tts.py` | 2 / 0 | 冻结归档必须包含新增状态及菜单模块，保留全部既有TTS安全检查。 |
| `tests/test_companion_latency.py` | 136 / 0 | 新增7项：音色表不阻塞、单飞节流、取消/Fake零网络、50ms投喂及分段链路。 |
| `tests/test_companion_precue_speech.py` | 101 / 0 | 新增26项：实际frame信号、双开关/拓扑组合与角色/任务/关闭/隐藏/替换撤销。 |
| `tests/test_companion_volume.py` | 274 / 0 | 新增15项：真实菜单/设置/子进程同步、静音恢复、热音量、主子身份和旧binding取消。 |
| `tests/test_config_schema.py` | 1 / 0 | 显式更新默认/同步名单快照，保留其他键完整断言。 |
| `tests/test_desktop_pet_features.py` | 1 / 0 | 显式更新现代菜单快照，保留全部原入口断言。 |
| `tests/test_menu_layout.py` | 5 / 1 | 更新默认action/标签快照，验证新入口经原菜单模型渲染。 |

设置契约：voice_chime_volume沿用原key/default80/0–100/语音域唯一所属行；voice_chime_muted新默认False，旧配置无字段为未静音。mute是高频菜单命令及持久状态，没有第二个实际音量设置或第三个陪伴朗读开关。无新设置域/模型/音色依赖；每宠按本slot路径写音量，保留其它字段，稀疏slot不扩写默认值。设置保存/试听/搜索位置原样，Volume说明新增右键同步/解除静音语义。

UI技能审查：现代/Legacy共享Menu Action Model；使用原字体/矢量图标/色彩，QWidgetAction按钮不触发关闭动作。实际Qt点击和左右键、恢复原值、保持菜单打开、菜单树释放均验证。亮/暗菜单截图以及720/1100设置截图已检查，说明自动换行42/21px无截断。设置新增行/信息架构迁移/多层披露门禁不适用；新静音状态默认/持久/旧数据恢复及主子路径有测试。Windows原生hover/focus/DPI仍待验。

## 性能分析

环境：Linux x86_64、Python3.12.14、Qt6.12 offscreen；Qt6.8.3另跑聚焦。网络/音频是合成边界，不是Windows真实网络或听感。

1. `python scripts/benchmark_companion_latency.py`：实际Qt拖入PNG→后台安全统计→原模型线程→真实气泡→原通道播放器调用，2拓扑×主子×3=12样本，均一条模型/一条合成，无真实联网。平均/最大(ms)：统计14.76/48.75；模型调用67.24/99.92；回复70.80/103.33；回复到播放调用7.46/21.06；投喂到播放调用78.26/124.39。仅提供合成MP3和Fake播放器边界，不据此宣称真实声音78ms。
2. 基线对比：只恢复929e093的interaction_service，保留同样统计/模型/播放边界，4拓扑/主子样本，随后完整恢复当前实现。平均/最大(ms)：模型调用2828.63/2904.10；回复2832.24/2907.19；播放调用2840.18/2923.70。确认原2秒条件+750/1000ms检查造成额外等待；新版50ms首批合并取消这段等待。源码基线比较没有修改动画或输入统计。
3. 音色表阻塞：旧worker在人工阻塞的音色表边界无法在2秒内完成合成；新worker不等待该边界，同样合成立即完成。实际微软音色表/网络没有在Linux测量，不把该人工2秒写成真实厂商耗时。新的产品数字日志分别记录queue/cache_hit/cache_miss/synthesis_total/tts_network/voice_list_refresh/play_request/player_playing；不含私密台词/文件名/路径。player_playing是Qt状态，并非声学采样。
4. `python scripts/benchmark_companion_speech.py`：同时完整回归/四CPU burner负载下，1600回执、16000guard；入队组均值443.62–840.38µs，最大33.585ms；guard组均值61.86–202.69µs，最大34.982ms。RSS80.90→149.69MiB包含依次创建的Qt/动画宿主和缓存，不能据此宣称长时间无增长或无抖动。原始每组JSON供审查，不是Windows性能结论。
5. 稳态/触发成本：没有新增音量轮询/长期预缓存，音量监听是事件驱动且stat未变不读JSON。音量保存仅目标文件少数键，原原子替换/有限共享冲突重试保留。语义签名LRU128、语音/投喂时序各deque32、metadata单线程且节流；音量自身不请求模型/音色表。原网络合成仍受SDK导入、网络、重试和设备初始化影响；不会虚报零延迟。不得对大量动态AI文字无限预缓存。

## 实机运行记录

- 已确认的Windows证据（用户）：新微软接口实际声音、岛聊天、投喂及授权解读被动朗读、最终识屏主动朗读、余额/统计/进度静音。保留这些已验收状态，不重新标成完全未测。
- 本轮真实Qt窗口/菜单/键盘/字段同步/气泡回执、真实文件后台统计、子进程Config写入和目录通知在Linux执行；截图/模型/网络/音频的边界合成。没有Windows/powershell.exe/wine/远程Win运行器；既有GitHub Actions REST被代理CONNECT403，未改变该环境或触发发布。故新Windows便携ZIP尚未生成，原生功能/真实语音延迟 **NOT TESTED**。
- 本轮实际PyInstaller6.19.0冻结Linux诊断并运行：`FROZEN endpoint adapter PASS: api.msedgeservices.com; synthetic/offline; real audio NOT TESTED`。真实归档门禁 `[tts] bundle TTS stack OK (29 modules required, 939 frozen)`，包括新volume状态/控件模块及既有微软地址修复；不是桌宠Windows绿色包。
- 本机重建/更新/隔离Fake/live/数据回退步骤在指南§13，复用原新WorkDir流程、UTF8/BOM预解析、Qt/DLL/资源/安全/EXE/独立设置窗口检查。旧用户数据、旧虚拟环境和当前已通过绿色包保留，源码不覆盖main/旧包。

## 测试与风险

先红后绿：初始3项（音色表阻塞、固定2秒逻辑、菜单缺入口）全失败；旧识屏前置行下4应朗读组合失败/4静音通过；原语音/身份guard下4拓扑/主子音量热更新失败。测试分别在真实Qt/业务边界补入，临时恢复基线后已恢复当前代码。最后审查补充JSON数组异常：原签名函数抛TypeError（1 failed），修补后安全撤销且拒绝覆盖异常文件（48 passed）。

所有Python命令均先 `source /workspace/.onboarding/dsh-pet-env.sh`，offscreen/空keyring/隔离XDG；未关闭frameseq以逃避测试。

| 门禁/命令 | 实际结果 | 原始记录 |
|---|---|---|
| CI主组：`python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py` | 5008 passed，48 skipped，18 warnings，841.85s | experience-main-verified.log |
| `python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py` | 41 passed，0 skipped，27.73s | experience-webm.log |
| `python -m pytest -q tests/test_low_priority_warm_interaction_yield.py` | 27 passed，0 skipped，32.58s；一次通过 | experience-lowwarm.log |
| `python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py` | 37 passed，0 skipped，2.18s；已包含于主组，额外独立复跑 | experience-frameseq.log |
| `python -m pytest -q tests/test_companion_latency.py tests/test_companion_precue_speech.py tests/test_companion_volume.py tests/test_pr_report_discipline.py` | 143 passed，0 skipped，6.07s | experience-delivery-focus.log |
| 相关语音/互动/菜单/设置及报告聚焦 | 529 passed，0 skipped，49.08s | experience-final-focus.log |
| Qt6.8.3（`/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q` 加相关聚焦文件，不含报告门禁） | 434 passed，0 skipped，162.30s | experience-qt68.log |
| `python scripts/stress_companion_speech.py`，4CPU burners×3轮 | 每轮640 passed、1 skipped；259.95/230.48/221.81s | experience-pressure.log |
| 最后JSON格式保护：Qt6.8.3新三文件聚焦、四CPU三轮复跑（`python /tmp/experience_format_pressure.py`） | Qt6.8.3 48 passed/3.35s；每轮48 passed，7.74/5.61/7.02s，0 skipped | experience-qt68-final.log / experience-format-pressure.log |
| `python -m pytest -q tests/test_app_lazy_imports.py tests/test_idle_low_fps.py tests/test_tick_driver_idle_stop.py tests/test_first_frame_budget.py tests/test_meta_cache_budget.py tests/test_library_idle_frame_trim.py tests/test_settings_and_resources.py` | 101 passed，0 skipped，13.66s | experience-resource.log |
| `node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js` | 34 passed，0 skipped | experience-node.log |
| `node integrations/dsh-pet-bridge/verify_import.mjs` | 零依赖桥门禁PASS | experience-bridge.log |
| `python -m ruff check pet/ tests/ scripts/benchmark_companion_latency.py scripts/stress_companion_speech.py scripts/verify_bundle_tts.py` | All checks passed | experience-ruff-final.log |
| `python -m compileall -q pet scripts tests`；`git diff --check` / `git diff --cached --check` | PASS | experience-compile-final.log及Git退出码 |
| 冻结诊断：`python -m PyInstaller --noconfirm --clean --onedir --name companion-volume-offline --paths . --collect-all edge_tts --collect-all certifi --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module tkinter --distpath /tmp/experience-frozen/dist --workpath /tmp/experience-frozen/build --specpath /tmp/experience-frozen scripts/smoke_edge_endpoint_frozen.py`；运行产物；`python scripts/verify_bundle_tts.py --exe /tmp/experience-frozen/dist/companion-volume-offline/companion-volume-offline` | Linux实际冻结/运行与29模块门禁PASS；不是Windows EXE | experience-frozen-build/smoke/verify.log |

主组首次运行发现三个旧快照未登记新muted键/菜单项，于39%主动中断：3 failed、1974 passed、17 skipped、4 warnings，577.71s。显式补快照后同族111 passed（25.61s），重新开始主组。第二次约86%时因审查发现新签名异常分支，主动停止，未作为完整结果；最终版本再次从头执行（experience-main-verified.log）。保留两份中断日志，不宣称首次全绿。最终主组告警与唯一计数：5076 passed、48 skipped（5008+41+27），18条既有Qt弃用告警：QImage.mirrored、QDragEnterEvent及QHoverEvent旧构造，未改变这些动画/事件调用。

复现辅助：`python scripts/benchmark_companion_latency.py`、`python scripts/benchmark_companion_speech.py`；测试源包用 `python scripts/package_companion_test.py --output <全新source.zip>`，再 `--verify <source.zip>`。构建安全/资源/DLL/原生冒烟仍由既有Windows构建脚本执行，新版原生结果待用户提供。

最终不重复pytest集合只加CI主组/WebM/低优预热；frameseq、聚焦/压力/报告是额外验证，不能重复叠加。平台专有skip（含Windows原生探针）不算成功。Fake确保不访问真实DeepSeek/Edge/凭据，不能验证真声音。

风险：冷提示在线合成可能晚于2.5秒显示窗口，此时静默缓存而不读迟到内容；已有播放沿旧生命周期。短时合并窗口缩短，真实快速输入费用以实际批次/单飞记录核实，未添加重复或语音专用模型调用。厂商接口/音色表可能变化，元数据失败继续用旧表与默认回退。瞬时Windows配置共享冲突沿原有限重试，实际菜单响应/DPI/设备延迟/长时间内存仍需验收。完成本轮后停止，等待用户Windows集中复验。
