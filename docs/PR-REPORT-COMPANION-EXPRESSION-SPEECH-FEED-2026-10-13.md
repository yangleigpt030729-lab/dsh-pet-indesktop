# 陪伴增强增量：表达风格、摸头设置、共享点击朗读与投喂气泡协调

基线：`15345e3e110c4f193002fa8f4ef8986f29fc6d23`；分支：`feature/win10-companion-memory`；日期：2026-10-13。
本轮仅增量修补，不重新开发P2-C～P5、不改动画/WebM、不合并main。历史：[上轮完整报告](PR-REPORT-COMPANION-COMPLETE-2026-10-13.md)；操作：[Windows指南§8](WINDOWS10-COMPANION-ACCEPTANCE.md#8-本轮最小复测表达风格摸头与投喂)。

## 核心特性与真实根因

1. 三条AI通路原先只有独立任务Prompt，不消费`dialogue_mode`；Overlay子宠视图也未列入风格/音色/文件解读设置。现通过同一小型适配器读实际目标配置：角色Prompt先保留，再独立风格约束，最后任务/隐私规则。legacy自然友善；whale_maid温柔女仆；custom不外发私人固定台词，采用角色自身加中性友善规则。原custom JSON仅有原Agent等事件固定句，没有新的AI事件规则或云端授权，不假装存在授权。模式快照参与身份校验，异步旧风格结果失效；Fake“主人～”是确定性验证，不是真实模型语言质量保证。
2. 原摸头开关归AI页，原点击朗读显隐/音频生命周期只依赖普通点击。现唯一摸头开关位于**互动 → 点击与音效 → 摸头 AI**，配置仍为`companion_interaction.head_touch_enabled`、默认关闭。共享`self_talk_speak_enabled`在普通点击或摸头开启时可见并立即保存；绑定和预缓存仍仅属于普通点击。搜索/深链保留，no-chat不创建摸头控件或额外AI音频消费者。
3. 原摸头只显示文字，没有进入旧点击朗读链。现成功展示回执后只把同一句交给原通道，带目标身份、配置/授权代次和30秒期限。合成/排队/缓存播放前重校验；关闭朗读、关闭摸头、角色/风格变化、取消、隐藏、销毁、退出、记忆授权撤销（包括失败保存及快速关后再开）均撤销旧票据。主动问候和趣味投喂仍无TTS。合成失败只保留原文字、记录失败，不用TTS错误气泡覆盖摸头文字。
4. 原真实投喂回执依次调用内容解读和趣味反馈，而`FileInterpretController.offer`把不支持文本解读误报为“读不了”；文本确认也可能被统计/趣味回复覆盖。现不支持解读的图片/ZIP/目录安静返回False，原动画与后台统计继续，先展示统计，再最早2秒后合并趣味回复。开启解读且存在支持文本才询问；确认/运行期间拥有气泡优先权，包括子宠气泡；新增投喂仍记录统计，但不夺取已有确认或进度。
5. 拒绝解读恢复统计/安全元数据趣味回复；接受解读只保留原独立文本会话，不再插入趣味回复覆盖结果。明确确认前不读内容、不发送文件名/路径到模型；混合输入只解读支持的文本，不递归读目录。接受后原文本文件名/内容会进入该宠授权会话，这是原功能；趣味AI始终仅类别/数量/粗略大小。重复/陈旧确认不二次读取请求；两种拓扑确认时重新检查解读开关，Overlay目标销毁/换角色后不能确认。Overlay共享一个原解读控制器，但会话Store随主/子配置身份切换，避免先子后主仍写子会话。

## 修改文件说明

以下增删基于基线提交；新增文件标“新增”，无删除文件。素材、动画引擎、WebM、原`persona_phrases.py`和正式依赖版本保持原实现。

| 文件 | 增删 | 改了什么 / 为什么 |
|---|---|---|
| `CONTEXT.md` | +4/−0 | 记录唯一设置归属、原朗读复用、文件授权与当前边界，供后续任务接续。 |
| `DEVELOPMENT_PLAN_WIN10.md` | +4/−0 | 把本轮增量作为最新范围，保留历史全阶段计划及已实测事实。 |
| `docs/INDEX.md` | +2/−0 | 登记本轮交付报告，满足项目文档证据门。 |
| `docs/PR-REPORT-COMPANION-EXPRESSION-SPEECH-FEED-2026-10-13.md`（新增） | +154/−0 | 汇总逐文件变更、红绿/回归/性能/真实应用与Windows未验收证据。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +28/−4 | 新增网页ZIP最小复测、风格/共享朗读/文本同意清单及真实联网/声音边界。 |
| `pet/app.py` | +13/−14 | 共享音频消费者支持独立摸头；原缓存/唯一通道接受目标配置与撤销guard。 |
| `pet/chat/ai_settings_page.py` | +1/−1 | AI域只构建投喂控件，避免摸头重复设置。 |
| `pet/companion/expression_style.py`（新增） | +26/−0 | 新增公共小型适配器，独立消息与本地降级、私人custom不外发。 |
| `pet/companion/expression_styles.json`（新增） | +16/−0 | 新增内置安全规则/降级文案数据；不修改原persona固定台词语义。 |
| `pet/companion/head_speech.py`（新增） | +49/−0 | 新增薄适配层：旧语音开关、内存授权代次、实际主/子消费者及原宿主分派。 |
| `pet/companion/interaction_runtime.py` | +10/−1 | 目标身份含风格；解读确认/进度阻挡瞬时回复；子宠解读委托原Key解析。 |
| `pet/companion/interaction_service.py` | +29/−13 | 独立风格Prompt/匹配降级；成功回执后仅摸头交给旧朗读；安全feed延迟统计展示。 |
| `pet/companion/interaction_settings.py` | +31/−23 | 提取唯一现有设置行构造/即时保存，支持归入不同域，不新建配置键。 |
| `pet/companion/proactive_service.py` | +4/−2 | 主动Prompt使用同一风格适配器，未保存模式变化也参与身份失效。 |
| `pet/feed_presentation.py`（新增） | +61/−0 | 新增小型优先权接缝，复用原解释器和子宠follower，不另造投喂系统。 |
| `pet/file_eater.py` | +13/−5 | 真实Legacy后台投喂回执先尊重解读确认，拒绝后再统计和安全AI。 |
| `pet/file_interpret.py` | +56/−27 | 非文本安静返回；明确同意/撤销/陈旧回调；实际目标角色与会话Store；Fake无Key且live校验。 |
| `pet/modern_settings_dialog.py` | +7/−8 | 共享朗读即时保存与OR显隐，AI页只保留投喂归属，普通绑定依赖不变。 |
| `pet/overlay_shell.py` | +3/−0 | 主/子缓存视图加入现有风格、音色及独立文件解读字段，保持真实slot身份。 |
| `pet/settings_deeplinks.py` | +7/−0 | 摸头/点击音效别名定位互动的原click任务Tab。 |
| `pet/settings_interaction.py` | +9/−2 | 唯一摸头控件靠近普通点击/共享朗读；说明动态缓存与旧在线回退。 |
| `pet/sprite_feeding.py` | +19/−9 | Overlay真实投喂回执按目标派发确认、拒绝恢复，销毁/换库不回调旧宠。 |
| `pet/voice_chime_service.py` | +56/−20 | 给原缓存/合成/深度1队列加可选guard/config；目标音色音量；旧调用兼容；失败保留摸头文字。 |
| `pet/window_alerts.py` | +5/−3 | 原点击朗读入口接受已展示摸头票据，原普通点击调用不变。 |
| `scripts/benchmark_companion_interactions.py` | +11/−0 | 实测风格上下文和授权快照成本，保留原有界统计/互动RSS指标。 |
| `scripts/build_linux.sh` | +1/−0 | 原onedir参数包含新增表达风格JSON，避免冻结后缺数据。 |
| `scripts/build_macos.sh` | +1/−0 | 同上，保持原平台资源装配，不升级依赖。 |
| `scripts/build_onedir.ps1` | +1/−0 | 同上，Windows分隔符遵循原PyInstaller格式，不打包Key。 |
| `scripts/capture_settings_pages.py` | +12/−1 | 拍摄移动后的头部/共享朗读行，区分AI域与互动域。 |
| `scripts/run_companion_acceptance.py` | +22/−5 | Fake回复实际体现内置模式；原TTS及预合成/播放边界离线可记录。 |
| `scripts/smoke_companion_increment.py`（新增） | +96/−0 | 新增真实AppShell/素材、原Drop/stat、本地风格降级冒烟；异常显式失败。 |
| `scripts/stress_companion_proactive.py` | +5/−0 | 满载族加入新风格/语音/投喂/解释/启动回归，仍4CPU×3轮。 |
| `tests/test_companion_acceptance_launcher.py` | +3/−1 | 离线fixture完整恢复原TTS函数，避免测试间污染。 |
| `tests/test_companion_expression.py`（新增） | +81/−0 | 新增三模式×六事件的实际ProviderPrompt/角色/隐私及切换失效回归。 |
| `tests/test_companion_feed_consent.py`（新增） | +82/−0 | 新增非文本安静、拒绝/明确确认、撤销/陈旧回调和一次消费回归。 |
| `tests/test_companion_feed_presentation.py`（新增） | +213/−0 | 新增两拓扑/主子实际QtDrop/确认follower、stat、隐私、失败及会话身份回归。 |
| `tests/test_companion_final_settings.py` | +1/−1 | AI域归属断言保留为投喂；移动的摸头在新测试检查唯一互动归属。 |
| `tests/test_companion_head_speech.py`（新增） | +269/−0 | 新增设置显隐/持久化、精确同句原朗读、撤销、子宠音色缓存、Fake/no-chat回归。 |
| `tests/test_file_interpret.py` | +2/−2 | 原不支持应错误提示改为新投喂静默契约，文本授权原断言保留。 |

## 实现调用链与线程边界

- 主动：原scheduler/额度/语义去重 → `ProactiveService` GUI快照角色与风格 → 后台Prompt预检/只读授权记忆 → 原`ChatService`异步Provider → 原真实气泡回执与配额结算。独立到期待办原通路保持。
- 摸头：原Legacy/Overlay头部核心路由 → `Target`实际主/子配置 → `InteractionService`单flight与冷却 → 角色+独立风格+任务安全Prompt → 原异步聊天 → `Target.present`本次文字回执 → `head_speech.speak_target` → `window_alerts.speak_click_self_talk` → 宿主`on_self_talk_speak`（Legacy原slot wrapper/Overlay原子宿主）→ `AppShell.speak_self_talk` → 原静态缓存或`VoiceChimeService.speak` → 原后台`_TTSWorker`/原一个播放器。可选guard/config参数保留旧调用签名；声音忙时仍沿原深度1队列，不建第二服务或播放器。
- 投喂：原QDropEvent → 原动画立即播放 + 原FeedWorker后台stat/统计 → GUI回执 → `feed_presentation.offer`询问原解读控制器是否拥有展示 → 非文本/关闭解读或明确拒绝：原统计气泡、原安全metadata聚合与延迟AI；明确接受：原解读确认 → 原有界文本读取/SessionStore/ChatService → 原进度/结果。趣味AI不调用`extract_text`、不写会话或长期记忆。Qt只在GUI线程，DeepSeek和在线TTS仍在原后台线程，无新增主线程网络等待。
- Fake：默认启动器分别注入聊天/主动Provider，记录原共享朗读请求，禁止urllib/系统凭据；原合成worker与播放边界均离线，定时预合成也不能访问Edge。每个ChatService有独立Provider对象，不串手动会话。显式授权解读在实际synthetic Provider下无Key可运行；live仍验证真实配置/Key，不能填假Key绕过。

## 性能分析

命令：`python scripts/benchmark_companion_interactions.py`；Linux x86_64 / Python3.12.14 / Qt6.12.0/offscreen，合成输入及Fake模型，与回归有部分重叠，不是独占CPU或Windows/真实联网基准。

| 指标 | 样本及实测 |
|---|---|
| 风格上下文+独立消息 | 20000次，均摊2.136µs |
| GUI授权代次快照（3个既有内存锁） | 20000次，均摊2.909µs，无SQLite/密钥/文件读取 |
| 原头部核心判断 | 20000次，均摊1.119µs |
| 1000次连续摸头请求 | 只接受1次，4.451ms；冷却/单flight继续生效 |
| 合成完整互动 | 200次，中位3.897ms，最大5.207ms；200次后Worker0、cooldown1项、recent12项 |
| RSS样本 | 第20次46.227MiB，末次46.285MiB，差0.059MiB；不代表无限时长保证 |
| 单文件stat | 200次，中位0.006640ms，最大0.040641ms |
| 原有界目录统计 | 5001条输入，32.070ms，partial=True；不读文件内容 |

稳态没有新增动画tick、轮询器、播放器、Provider或TTS服务。摸头+朗读开启时保留原VoiceChimeService及其原定时器，普通点击可关闭；关闭所有声音消费者时仍释放。风格JSON仅模块加载读一次；新CPU成本发生于请求快照/回执/音频复核，不是每帧读取私人库。动态语音只在明确摸头且共享朗读开启、文字成功展示后使用原缓存和原后台线程；不是无界预合成。已有音频缓存清理仍为MAX_CACHE_FILES=200及原节流，静态台词预缓存含义不变。投喂2秒展示窗口复用既有feed_timer，不增加请求次数；连续投喂仍合并，模型失败仍120秒退避。本轮未测Windows稳态CPU/真实Edge合成延迟；原Qt6.8菜单包装残留见限制，不用短样本RSS宣称全部零增长。

## 实机运行记录

用户证据（Windows10 22H2 x64、Python3.12 x64、Qt6.8.3约束）：GUI/桌宠、Fake主动气泡、摸头AI气泡、身体原动画已经成功；普通身体自言自语独立开关默认关闭。图片/ZIP等先“读不了”再趣味AI的矛盾气泡由用户实机报告，本轮修补；不把已有成功全部重标NOT TESTED，也不把这些成功当成新增功能全部验收。

云端真实应用/素材运行：

```bash
source /workspace/.onboarding/dsh-pet-env.sh
PET_RENDER_TOPOLOGY=overlay PET_FRAMESEQ=0 /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_increment.py
PET_RENDER_TOPOLOGY=legacy PET_FRAMESEQ=0 /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_increment.py
PET_FRAMESEQ=0 /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_proactive.py
```

前两项无Provider/network mock，使用实际AppShell、素材、Qt窗口、原Drop/FeedWorker/stat以及关闭聊天配置后的原本地降级；都输出`PASS: real AppShell/assets, local maid head + original drop/stat/fun bubble, no Provider request, no TTS`。第三项用阻塞Fake网络边界，观察实际动画帧推进后释放模型、解码帧透明Alpha、多媒体素材、真实单气泡及安全退出，输出原PASS。`PET_FRAMESEQ=0`只用于短时单进程素材冒烟，完整回归没有设置该开关。最初验证脚本固定坐标在实际动画透明像素上触发未接受断言，已改为真实opaque hit并让Qt回调异常显式退出失败；最终两条命令没有该断言。没有据此改动画/点击命中算法。

`capture_settings_pages.py --companion-details --width 1100`（浅色）、`--width 720 --dark`：实际设置页截图已人工查看，摸头/共享朗读在互动，普通点击关时共享朗读可见，控件唯一、长提示换行且可滚动，原AI投喂仍在AI页。截图留云端`/tmp/companion-increment-ui-*`，不是Windows截图。设置测试覆盖搜索/深链和持久化；原菜单/设置隔离回归继续执行。

环境探针实际输出：`OS: Linux 6.18.44 Python: 3.12.14 Qt: 6.12.0`、`Qt platform: offscreen audio outputs: 0`，没有可用真实音频输出或Win10原生窗口/WASAPI，因此真实声音、中文Windows系统字体/DPI、真实多屏透明窗口、系统拖放/睡眠注销及EXE不能在此证明。真实DeepSeek语言效果/联网与真实Edge声音 **NOT TESTED**；Windows本轮EXE **NOT BUILT**。仅把原JSON资源加入已有三平台onedir打包参数，未升级依赖或打包真实Key。复测清单见Windows指南§8。

## 测试与验证

红/绿：在`git archive 15345e3`的临时只读基线源码副本（公共assets未变化）运行同样31个风格、唯一设置/门控、原guard及投喂授权测试：**31失败 / 0通过 / 0跳过，2.22s**；当前源码同样选择：**31通过 / 0失败 / 0跳过，1.65s**。主要断言是缺少独立style message、原UI归属、原音频门控、guard参数缺失、“读不了”气泡、无consent回执/重复拒绝接口。没有删/放宽失败断言；原“无文本应提示错误”断言按用户新的投喂语义改为安静，不删除文本授权测试。

真实Qt新增范围：31基础红绿之外，覆盖主/子两拓扑图片/ZIP/目录、多文件、文本拒绝/确认/关闭、一次控制器跨子→主切换会话、确认时新投喂/子宠退出、原头部气泡精确一次朗读、关开授权/风格/角色/取消/过期/隐藏/销毁、合成失败、原缓存复用及子宠音色/语速/音高/音量、Fake零真实凭据/网络/TTS、no-chat不创建消费者。早期聚焦一个错误使用SessionStore不存在的instance_id测试字段已更正为检查实际会话root，另一个目标重叠测试先拖开子宠再命中主宠；保留真实调用链断言。

第一轮完整主组：1失败、4638通过、37跳过、18警告，631.47s。发现新音频消费者扫描在原最小Overlay启动替身没有_spawned时抛AttributeError；改为安全空集合，原启动测试不更改。修补后`tests/test_overlay_shell.py tests/test_companion_head_speech.py` **58通过，5.11s**，再完整复跑下表。初轮满载结果仅为中间证据；最终门禁单独记录。

| 门禁 | 真实结果 |
|---|---|
| 最终完整主组 Qt6.12 | 4642通过 / 37跳过 / 0失败 / 19警告；641.87s |
| 最终独立WebM组 | 41通过 / 0跳过 / 0失败 / 0警告；26.36s |
| 最终独立lowwarm组 | 27通过 / 0跳过 / 0失败 / 0警告；31.38s |
| 最终frameseq复验（与主组重复） | 37通过 / 0跳过 / 0失败 / 0警告；1.00s |
| 最终4CPU满载×3（含原启动族） | 每轮704通过 / 2跳过 / 0失败 / 4警告；197.07 / 201.94 / 210.04s |
| 最终Qt6.8.3聚焦+原启动族 | 202通过 / 0跳过 / 0失败 / 0警告；109.50s |
| Qt6.8.3原菜单独立普查 | 1失败 / 5通过 / 0跳过 / 0警告；2.15s，旧+645 QAction残留未修 |
| 文档纪律 | 85通过 / 0跳过 / 0失败 / 0警告；1.03s（与主组重复） |
| Node桥接 | 34通过 / 0跳过 / 0失败；220.65ms |
| bridge verify_import | import、退役面与source bans通过 |
| Ruff、compileall、diff check | 均通过；包括所有改动的Python脚本 |

完整CI分组唯一Python用例合计**4710通过、37跳过、0失败、19警告**（主组+41WebM+27lowwarm）。frameseq/文档/Qt6.8/满载复跑不重复计入唯一总数。19项均为原Qt `mirrored`、`QDragEnterEvent`、`QHoverEvent`弃用警告，其中原随机移动路径多命中一次`mirrored`，没有未捕获线程/销毁警告。满载4项为原拖放弃用警告。offscreen的raise/propagateSizeHints/无音频后端stderr单独说明，不冒充pytest失败。Qt6.8菜单额外失败不纳入Qt6.12 CI通过数，已明确保留，不能称全平台全绿。

主组命令严格沿CI分组：

```bash
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_companion_proactive.py
ruff check pet/ tests/ scripts/run_companion_acceptance.py scripts/stress_companion_proactive.py scripts/capture_settings_pages.py scripts/benchmark_companion_interactions.py scripts/smoke_companion_increment.py
python -m compileall -q pet packaging scripts
git diff --check
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
```

Qt6.8聚焦命令：同解释器`/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q`接`tests/test_companion_expression.py tests/test_companion_head_speech.py tests/test_companion_feed_consent.py tests/test_companion_feed_presentation.py tests/test_companion_acceptance_launcher.py tests/test_file_interpret.py tests/test_voice_chime_service.py tests/test_companion_final_settings.py tests/test_settings_interaction_tabs.py tests/test_architecture.py`。首次174通过、115.72s；最终扫描修补/no-chat补测见表。均为Linux，不能据此宣称Windows全兼容。

## 已知限制与后续

- Qt6.8.3原菜单普查本轮独立复现：**1失败、5通过、0跳过/警告，2.15s**；15轮QMenu1保持，QAction57→702（+645）。与上轮旧基线对照同幅度，不是本次风格/投喂改动引入；测试保留，未修/未假装全平台绿。Qt6.12同断言在完整主组及满载继续验证。Windows长期菜单循环仍需观察。
- 真实DeepSeek、真实Edge声音、实际Win10增量配置/拖放/子宠/音频与打包验收待用户；本轮新增可运行源码，未合并main。用户此前WebM reader退役池/慢帧未收到完整新日志，不能证实与本轮关联，动画/解码路径未动，独立reader/lowwarm组验证另列。
- 自定义私有固定台词不上传，无新的自定义AI云规则授权入口。Fake示例没有真实模型创造力，安全prompt只能由后续真实联网验收验证语言表现。
- 解读确认/运行拥有气泡优先权；期间额外投喂统计照常保存，但不排成过时趣味消息长队。明确接受会记录原内容解读会话，趣味AI则始终零会话/记忆写入。
- 共享通道保留原深度1待播、旧缓存与200文件清理策略；动态摸头不预生成无限音频。声音正播放时不强制中断原报时/节日，撤销保证待合成/排队的新播放失效，已经播放的声音仍沿原播放器生命周期。已经起飞的原后台网络合成不能撤回已授权发送；这里复核的是是否允许随后起播，没有新建可撤回网络的TTS系统。

## 风险与回滚

无配置schema迁移、无新增开关或自动云端授权。回滚本轮提交恢复旧设置归属和只文字摸头；用户原开关字段/统计/记忆/会话均保留，不删除数据。应先退出全部宠及设置，再切源码，不覆盖用户APPDATA、隔离目录、素材或生产配置。新JSON必须随源码/onedir资源一起更新。交付后停止新增开发，等待集中Windows验收。
