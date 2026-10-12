# 完整陪伴增强版交付（2026-10-13）

基线：`8847826ebb697256e5d8bdef668184788c04026f`。分支：`feature/win10-companion-memory`。本轮依用户最新完整任务书连续完成全部阶段；本报告最终文档提交的HEAD在最终交付消息和 `git rev-parse HEAD` 可核实。原main未合并/覆盖。

关联：[最终Windows验收指南](WINDOWS10-COMPANION-ACCEPTANCE.md)、[上一轮正式入口修补](PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md)、[开发计划](../DEVELOPMENT_PLAN_WIN10.md)、[文档索引](INDEX.md)。

## 一、完成状态与提交

| 范围 | 状态 | 实际行为 |
|---|---|---|
| P2-C | IMPLEMENTED | 原TodoStore/面板内JSON v2可靠回执、10分钟宽限、异步Timer磁盘、有限恢复，无第二待办库/自然语言日程 |
| 普通主动范围 | IMPLEMENTED | 1～9999条/天、1～99分钟，默认10/30，旧0/>99保守暂停，runtime/SQLite贯通 |
| P3 | IMPLEMENTED | 可见头部核心单击独立瞬时AI，模糊/身体普通点击，拖动/探头/黄金回旋优先，两拓扑/子宠 |
| P4 | IMPLEMENTED | stat类型元信息AI、立即吃动画、后台统计、突发合并/正确宠归属，原解读独立授权 |
| P5设置/迁移/回归 | IMPLEMENTED | 原ModernSettingsDialog唯一组、识屏短记录改名、深链/试听、数据安全迁移、Fake全通路 |
| 旧问题修补 | PARTIAL | deadQObject监视器、聊天QThread和音乐menu信号桥生命周期已修；Qt6.8原菜单包装对象残留保留对照，尚未解决 |
| P5 Windows原生包 | PARTIAL | 干净Chat onedir脚本、固定依赖/构建工具与文档已完成；EXE **NOT BUILT**、PowerShell/安装 **NOT TESTED** |
| Windows完整验收/真实DeepSeek | NOT TESTED | 保留用户已有基础Win10证据；本輪新增功能及正式修补仍待集中原生验收 |
| 第二待办系统、AI猜测日程、动画重写 | NOT IMPLEMENTED（依用户要求） | 使用原系统；不增加重复Provider、会话、托盘或设置程序 |

阶段提交（完整SHA见下表；最终验证/产物文档提交另外列在交付消息）：

- `dc710a8d505490d5e43b99b7d07c96409603546e` — fix: confirm existing todo delivery with durable claims and bounded recovery
- `76865490689ae629d412b5c6f66d9899d2461421` — feat: make proactive limits configurable with conservative legacy migration
- `4e232b0a971e4fadb8cb7691228e00d283d3d268` — feat: route explicit head clicks to an isolated asynchronous companion channel
- `2e61c75710fa54a586a96245ea3ab757185f0884` — feat: add private stat-only AI feeding feedback with asynchronous drop handling
- `4378117bf6e2c4b2ad2b4d1df86b25b867ee1c72` — feat: integrate companion settings, safe migration and Windows Chat build workflow

- `1141ed5b82578974a1c29e165905099b49d0c097` — 音乐菜单worker信号拥有者收尾、素材署名保留、逻辑DPR测试及扩展负载。

## 二、修改文件说明

共68个文件（67个既有/新增源码、测试、指南文件，加本报告），无删除文件。以下逐文件增删针对 `git diff --numstat 8847826`（提交前包含已暂存/工作区最后文档）。新增均注明；无删除文件。报告自身表格更新后复核行数，执行最终差异即可得到全部精确值。

| 文件 | 增/删 | 修改与原因 |
|---|---:|---|
| `CONTEXT.md` | +5/−0 | 记录唯一设置归属、交互/线程边界和最终授权范围，避免后续按旧计划重复建设。 |
| `DEVELOPMENT_PLAN_WIN10.md` | +5/−0 | 置顶最终用户确认：原待办增强、新范围、单击核心/身体优先，修正早期候选架构。 |
| `docs/INDEX.md` | +2/−0 | 登记本交付报告，关联最终验收入口。 |
| `docs/ONEDIR_PACKAGING.md` | +6/−0 | 追加显式解释器、安全Fake冒烟和未原生构建边界。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +82/−86 | 重写集中验收、网页ZIP更新/旧venv/UTF-8、普通权限拖放、live费用及安全回退。 |
| `packaging/pet_entry.py` | +5/−1 | 冻结入口在导入AppShell前支持隔离Fake验收分流。 |
| `packaging/requirements-companion-build.txt`（新增） | +6/−0 | 仅新增独立构建工具固定版本，不调整正式运行依赖。 |
| `pet/__main__.py` | +3/−0 | 源码模块入口复用验收启动器，避免第二启动逻辑。 |
| `pet/agent_link.py` | +7/−1 | 已销毁Qt监视器停止后台发信号，只吞该明确销毁异常。 |
| `pet/app.py` | +11/−1 | 接线单击头部、设置深链/无父试听；通知返回真实可见回执。 |
| `pet/chat/ai_settings_page.py` | +3/−0 | 原AI页承载唯一互动设置组。 |
| `pet/chat/service.py` | +3/−0 | 已完成QThread在queued清理后deleteLater，释放原生连接及Prompt持有。 |
| `pet/companion/data_migration.py`（新增） | +53/−0 | 同base变体SQLite backup含WAL、短预算/临时原子落地、保留源和已有目标。 |
| `pet/companion/feeding_metadata.py`（新增） | +62/−0 | 只stat安全类别/数量/大小，目录扫描条数/时间有界，无文件内容/路径进入Prompt。 |
| `pet/companion/feeding_worker.py`（新增） | +85/−0 | 单进程单daemon有界队列，后台统计/原JSON写入，Qt queued回执和取消。 |
| `pet/companion/interaction_config.py`（新增） | +13/−0 | 独立default-off头部/投喂typedbool设置，复用即时opt-out policy。 |
| `pet/companion/interaction_runtime.py`（新增） | +176/−0 | 弱宠身份、可见性/手动聊天/暂停保护；原鼠标与投喂链小型适配。 |
| `pet/companion/interaction_service.py`（新增） | +255/−0 | 复用ChatService的瞬时互动通路；并发/冷却/费用/隐私/撤销/本地降级，不写会话。 |
| `pet/companion/interaction_settings.py`（新增） | +32/−0 | 原AI域内两个即时开关与成本/隐私提示，保存失败opt-out仍当前生效。 |
| `pet/companion/proactive_config.py` | +16/−1 | 新数值边界与旧0/>99保守迁移，保留legacy_ranges。 |
| `pet/companion/proactive_policy.py` | +7/−5 | 扩展原policy的feature键，避免建立第二全局设置管理器。 |
| `pet/companion/proactive_runtime.py` | +5/−0 | 退出/暂停取消互动通路，保留主动服务原控制。 |
| `pet/companion/proactive_service.py` | +1/−1 | 原配额结算接收新用户范围，不保留旧10硬编码。 |
| `pet/companion/proactive_settings.py` | +18/−8 | 精确输入新范围/费用/迁移确认；去除无功能日程占位。 |
| `pet/companion/proactive_state.py` | +4/−4 | immutable reservation计数cap支持9999，原SQLite v2交易/跨日限制保留。 |
| `pet/companion/touch_region.py`（新增） | +16/−0 | 复用catalog头部框定义中央上部可见核心，模糊边缘身体优先。 |
| `pet/config.py` | +18/−3 | 嵌套互动normalize，旧数据迁移pending暂停主动请求，不覆盖现配置。 |
| `pet/context_menus/shared.py` | +31/−18 | 主动识屏菜单深链；原音乐worker桥不再随窗口删除，弱目标/登记表/线程完成Event避免native emit竞态。 |
| `pet/file_eater.py` | +29/−4 | 实际Legacy拖放立即动画、异步元信息/统计，原解读授权与同步测试seam保留。 |
| `pet/modern_settings_dialog.py` | +11/−15 | 唯一组归属、识屏记录短名/正确清除作用域、深链与试听fallback。 |
| `pet/overlay_settings.py` | +4/−4 | 原PetInstance生命周期传递initial_page，保留slot/base及失败回退。 |
| `pet/overlay_shell.py` | +25/−5 | 全部重绑定接线头部互动；子宠投喂/设置归属，取消旧worker。 |
| `pet/settings_deeplinks.py`（新增） | +27/−0 | 深链自动化区域及parentless正式试听转原Shell，控制Dialog行数。 |
| `pet/sprite_feeding.py` | +43/−6 | 命中宠立即动画，背景统计后反馈到同宠；role/library改变丢迟到结果。 |
| `pet/sprite_menu_facade.py` | +6/−0 | 对应角色的主动识屏深链callback。 |
| `pet/todo_async.py`（新增） | +96/−0 | 原Todo服务单disk executor、GUI queued展示、generation撤销及投递时再验宽限。 |
| `pet/todo_delivery.py`（新增） | +93/−0 | 原TodoStore内持久claim/实际回执，QLockFile跨进程事务和有限崩溃恢复。 |
| `pet/todo_panel.py` | +3/−1 | 既有面板忙锁保存失败提示，避免用户误以为删除已落盘。 |
| `pet/todo_reminder.py` | +93/−20 | JSON v2兼容v1，reserve/finish实际回执，跨日与时间回拨、不先吞提醒。 |
| `pet/window.py` | +9/−2 | 完整release单击小型hook、透明/拖动守卫和深链callback，无动画引擎重构。 |
| `pet/window_optional_services.py` | +3/−0 | 原投喂处理器接线安全AI反馈。 |
| `scripts/benchmark_companion_interactions.py`（新增） | +98/−0 | 可复现核心/目录/千连点/200完成及RSS的合成本地性能探针。 |
| `scripts/build_onedir.ps1` | +24/−10 | 显式PythonExe/UTF-8、拒绝强杀开关、两入口Fake隔离冒烟与LICENSE/第三方署名，原DLL/素材/瘦身校验保留。 |
| `scripts/build_windows_companion.ps1`（新增） | +45/−0 | 全新干净Windows Chat构建暂存与venv、固定工具/Qt、真实SHA输出。 |
| `scripts/capture_settings_pages.py` | +14/−0 | 新组可滚动截图，窄宽/明暗/字体放大人工视觉检查。 |
| `scripts/package_companion_test.py` | +4/−3 | 源ZIP额外排除原待办/统计/活动/会话数据并保留第三方素材署名；维持密钥格式与校验拒绝。 |
| `scripts/run_companion_acceptance.py` | +14/−4 | 首个Fake目录启用三个功能、重启保持opt-out、独立Provider/模块入口复用。 |
| `scripts/stress_companion_proactive.py` | +10/−0 | 四CPU三轮扩展到全部新增时序族。 |
| `tests/test_companion_acceptance_launcher.py` | +76/−0 | 两拓扑安装版Fake，真实鼠标/drop到Qt气泡，零Key/网络/TTS、不串会话。 |
| `tests/test_companion_acceptance_package.py` | +13/−1 | 合成私人状态和sessions排除，保留可复现/凭据拒绝。 |
| `tests/test_companion_build_workflow.py`（新增） | +31/−0 | 构建脚本契约和真实源码模块Fake启动。 |
| `tests/test_companion_custom_limits.py`（新增） | +74/−0 | 1/10/9999×1/30/99、新范围最后一格、热更新/重启/旧数值迁移。 |
| `tests/test_companion_data_migration.py`（新增） | +94/−0 | 记忆/配额/todo/统计、已有目标优先、损坏重试、真实WAL与pending停用。 |
| `tests/test_companion_feeding.py`（新增） | +161/−0 | stat隐私/大目录/即时动画/突发合并/子宠真实气泡，不读原字节。 |
| `tests/test_companion_final_settings.py`（新增） | +91/−0 | 即时关闭保存失败、两SQLite不误清除、深链、正式parentless试听及唯一AI归属。 |
| `tests/test_companion_interactions.py`（新增） | +147/−0 | 真实ChatService worker、并发/撤销/删除/关闭/无Key/错误有界、无记忆写。 |
| `tests/test_companion_known_regressions.py`（新增） | +80/−0 | deletedQObject监视器、销毁surface拒绝互动、完成QThread原生释放及音乐桥存活/弱目标。 |
| `tests/test_companion_proactive_state.py` | +2/−2 | 仅同步明确授权的新数值边界，保留旧跨日/交易断言。 |
| `tests/test_companion_proactive_ui.py` | +1/−2 | 新范围并移除误导日程占位，保留保存/关闭检查。 |
| `tests/test_companion_settings_entry.py` | +40/−0 | 两拓扑真实子菜单显示/关闭后的深链，保留上一轮角色/隔离回退全覆盖。 |
| `tests/test_companion_touch.py`（新增） | +121/−0 | 缩放/镜像/偏移/逻辑DPR核心及两拓扑实际release，身体/透明/拖动/子宠互斥。 |
| `tests/test_config_schema.py` | +2/−1 | 登记显式normalize的新嵌套组，保持白名单/默认值快照护栏。 |
| `tests/test_desktop_pet_features.py` | +1/−1 | 原图标先于PyInstaller的顺序断言适配显式解释器命令。 |
| `tests/test_file_eater.py` | +2/−0 | 异步实际拖放以事件完成同步，保留原统计断言。 |
| `tests/test_sprite_feeding.py` | +7/−0 | 原投喂测试等待worker完成，保留动画/统计/来源断言。 |
| `tests/test_todo_delivery.py`（新增） | +182/−0 | 失败/重启/忙锁删除/跨日/多实例/GUI外磁盘/宽限复检的可靠投递。 |
| `tests/test_todo_reminder.py` | +5/−0 | 原fake宿主提供真实bool回执，原提醒规则断言保留。 |
| `docs/PR-REPORT-COMPANION-COMPLETE-2026-10-13.md`（新增） | +233/−0 | 本次逐文件/红绿/性能/平台边界证据与集中验收索引。 |

## 三、真正的接入链、数据与边界

**待办：**原面板 → `TodoReminderService.set_items/apply_config` → 原Timer `request_tick` → 一个 `TodoDiskWorker` → `todo_delivery.reserve`（QLockFile、最新JSON、先持久claim）→ queued GUI `_notify_fire` → 原 `try_show_bubble`/`system_notify` bool → `finish`后台持久回执。JSON v1可读，v2每条按lead/due保存slot/signature/token/status/lease，只有实际显示才fired戳；迟到lead与due合并为due。失败写claim不展示；成功展示写回失败用当前进程 `_confirmed` 防重复。任务删除/完成/禁用/签名变化/停止generation不能复活。每次GUIhandoff重新检查原宽限和回拨，不在睡眠几天后弹陈旧任务。待办无需Key、记忆、识屏或普通主动额度；不额外调用模型/语音。

GUI展示和JSON落盘不能在进程崩溃时原子完成。模糊交付30秒lease后在原10分钟内可能重试，**不承诺跨崩溃exactly-once**；相邻多实例由原文件锁协调。面板忙锁删除保留pending并提示，后续tick先落地最新编辑；其他进程与GUI刚好并发编辑后的展示仍存在两阶段交付固有竞争窗口。未改变原系统通知在Windows的可见性能力，实际通知可达性须原生验证。

**普通主动：**原 `proactive_service` → SQLite v2 immutable reservation → 原实际气泡回执 `mark_presenting/finish`。值范围更改而schema不改；每个reservation保存当时quota/interval，跨午夜/回拨/重启/多进程不借用另一日额度。默认10/30，用户9999/1不会被硬编码10/30截断。每日请求预算2×用户展示额度，每次96输出token；类别冷却/活动/忙碌/语义去重仍保留，不保证达满。旧每日0或间隔>99把总开关暂停，原值保存在legacy_ranges且range_review待确认；用户明确确认后按新范围启用，不静默加费。

**P3：**Legacy `PetWindow.mouseReleaseEvent` → 原拖动/探头分支后hook → `legacy_head` → catalog head_box核心/alpha/press-release → 原点击动画/Q弹 → `InteractionService.request('head', Target)`；Overlay原鼠标release → 探头/回旋优先 → `_companion_head_click` → `overlay_head` → 原behavior/squash → 同服务。头部核心为head_box内中央上部（x内缩22%、y15～70%），模糊边界身体优先，避开整个重叠body_box吞头。普通body/disabled沿旧 `_on_click`；一次操作只一个主互动。没有新动画名或引擎/`pet_sprite.py`重构。

**P4：**Legacy原DropFilter / Overlay `dropEvent`命中sprite → 原吃动画立即 → 进程共用 `FeedWorker` Queue32后台 `describe`/原统计JSON → queued对应宠基础反馈 → `offer_feeding`750ms合并 → 瞬时互动ChatService → 对应气泡。目录扫描最多5000条/.5秒检查，partial体积unknown、原统计标“至少”；单个OS stat/scandir在异常网络盘上仍可能慢，放后台保证UI不等待。只发送类别计数/根文件及文件夹数/大小区间，未知扩展归other；不发文件名/路径/图片/代码/音频/目录内容，不假装读过。原 `interpret_offer` 是另一授权流程，未绕过。角色library变化、死目标或退出丢弃迟到UI；源文件未修改。

**瞬时AI：**共用原Provider实现/ChatService/PromptBuilder角色；单独ChatService实例 `notify_global=False`，不把内部head/feed包装成用户聊天，不保存会话或长期事实。头部只有记忆授权才后台读取少量安全readonly记忆，投喂从不读记忆；SQL token和Config身份在展示前复核，撤销/删除丢结果。head同宠10秒/feed20秒，合并队列TTL30秒、最多32目标、一个singleflight；失败120秒退避、无自动付费retry，20秒providertimeout/25秒watchdog、本地不同短语回退。近期互动文字只本地deque12、字面/Jaccard去重，未上传私人摘要。手动ChatService开始即取消；显式互动取消普通主动候选。新三类文字不TTS、不截图、不启动麦克风/摄像头；原用户语音配置未被禁用。

**设置：**原右键action → close_on_trigger → deferred菜单关闭 → PetInstance.open_modern_settings / Overlay.open_settings_for → 同ModernSettingsDialog，slot/base/process隔离保留上一轮修复。主动识屏菜单携initial_page定位Automation；独立子进程传settings-page/base/instance/Fake，启动失败原inprocess fallback。原无父Overlay设置试听现在转Shell.trigger_voice_chime_now，standalone仍原本地试听宿主。新开关原AI域唯一归属/即时保存，失败opt-out通过原policy立即阻止新请求；取消结果，不建立第二设置管理器。识屏清除只原proactive_screen_memory.json，两个SQLite不变。

**迁移/打包：**同base旧普通目录 → 新Chat变体首次Config；原目标优先、源留作回退，SQLite readonly backup带WAL、1秒进度deadline/.2秒busytimeout、临时原子替换；失败保留pending且暂停普通主动以免配额重置。源旧schema继续由原Store migrate处理，不伪造新quota。Fake自有base不导入生产APPDATA。Config首次迁移是启动阶段同步有界backup，不在每帧或每个tick跑；大量原sessions复制沿旧启动路径，可能增加首次启动时间。构建wrapper安全源暂存→全新venv→原Chat onedir，runtime pins未升级，工具另文件固定；两入口Fake临时目录、不强杀用户EXE，保留QtDLL/ffmpeg/素材/瘦身/中文/bridge门。

## 四、性能分析

环境：Linux x86_64、Python3.12.14、PySide6/Qt6.12.0、Qt offscreen；与Qt6.8.3补测分开。以下为真实测量，Fake模型不代表DeepSeek网络延迟；部分命令与完整回归/负载同时运行，非严格独占CPU基准。

| 命令/样本 | 实测 |
|---|---|
| `python scripts/benchmark_companion_entries.py`，20次真实设置创建/关闭 | 冷869.723ms、热中位617.270ms/max666.801ms；20轮原生dialog残留均0；warm第5轮RSS122.441MiB→最后123.133MiB |
| 同脚本100次Fake ChatService构造 | 中位0.014ms/max0.211ms |
| `python scripts/benchmark_companion_interactions.py`，20000核心判断 | 修补后平均3.365µs/次，只用户release触发，不加每帧系统调用 |
| 同脚本200次本地单文件stat | 中位0.006710ms/max0.096606ms |
| 同脚本5001目录项 | 98.761ms，有界partial/unknown，不读文件内容 |
| 同脚本千连点 | 3.920ms、只接受1个请求（无千并发） |
| 同脚本200次完成 | 合成端到端中位3.858ms/max35.259ms；cooldown1键/recent12/worker0；warm45.840MiB→45.902MiB |
| 原生QThread释放修补前同200次 | RSS45.988→48.012MiB（增长2.024MiB）；修补后同样本增长0.063MiB；强观察引用下也释放native对象 |

稳态：不改动画tick/引擎；开关关闭时事件分支typedbool判断，不读私人库/网络。新增成本发生于用户click/drop或原30秒todo/proactive tick；todo新增一个单线程executor，feed共用一个daemon Queue32，互动一个lazy单线程executor和原每请求QThread；网络仍原Provider，最多单flight，文件stat/原统计和SQLite readonly在后台。Config首次迁移有SQLite backup启动开销；不是周期复制。容量固定的recent/队列与期限cooldown控制逻辑缓存；200样本RSS显示有限增长，**不是无限时长稳定性保证**。原菜单Qt6.8 wrapper普查问题另列，不能用本节宣称所有缓存都零增长。

追加文档/包/构建契约组 `pytest -q tests/test_pr_report_discipline.py tests/test_companion_acceptance_package.py tests/test_companion_build_workflow.py`：**94通过、0跳过/警告、17.67s**。

截图命令：`python scripts/capture_settings_pages.py /workspace/artifacts/final-settings-wide --width 1100 --companion-details`；窄版改destination并加 `--width 720 --dark --companion-details --font-scale 1.25`。人工查看AI增强组、数值/费用hint：无控件重叠，中文换行/滚动可达。仅Linux Qt布局证据，Windows字体/DPI原生及macOS未验。新开关沿原SettingRow/ToggleSwitch键盘/accessible机制，无新焦点或动效体系。

## 五、实机运行记录

用户已确认Win10 22H2 x64/Python3.12 x64、Qt6.8.3约束：基本启动/桌宠、主动设置、灵动岛设置、临时Fake显式注入后的合成气泡成功；原右键无反应/原默认Fake不触发失败。本轮正式代码及全部新增功能 **尚未Windows复验**，保留此前证据而不标成全部NOT TESTED。

当前探针为Linux（`sys.platform=linux`），无Windows Shell/UAC/native通知/Win32窗口/DPI桌面或Windows构建工具。`PET_FRAMESEQ=0 python scripts/smoke_companion_proactive.py`在真实AppShell/原WebM解码、阻塞Fake模型下观察原动画帧推进，透明alpha不同值、实际Qt气泡/持久回执、优雅退出，输出 `PASS: real AppShell, blocked fake model + advancing animation, transparent decoded frame, single real bubble, durable receipt, graceful shutdown`。**Provider是Fake、平台offscreen，不冒充原生Windows或真实模型实机证据。** 两拓扑真实鼠标/drop/菜单嵌套loop到气泡/设置另外由事件测试覆盖。原生声音、Windows拖放UAC、DPI/多屏、睡眠/锁屏/通知/注销/EXE仍NOT TESTED；具体集中步骤见指南。

## 六、测试与验证

所有计数为本任务实际执行，不借用前轮4207/4469。Red阶段证据保留在本机/tmp日志（不提交私人数据）：

| 切片 | 修补前 | 修补后 |
|---|---|---|
| P2-C投递 | 初次3失败/5通过；async/midnight追加缺实现失败 | 阶段todo/chime/architecture103通过；收尾宽限+迁移55通过 |
| 范围 | 9失败/4通过 | 相关95通过 |
| P3 | 首次15失败（核心函数/事件接线缺失）；瞬时通路追加红测试后实现 | 阶段105通过 |
| P4 | 5失败/1通过 | 72通过/4 Qt弃用警告 |
| P5设置 | 5失败；LinuxWin-only控件测试补capability seam | 相关入口+UI+架构53通过，最终设置/触摸组结果见下 |
| 打包workflow | 1失败/1通过 | build/package/slim/encoding32通过 |
| 迁移 | 3失败 | 相关20通过，最终新增WAL/pending/宽限组合55通过 |
| dead监视器 | 1失败 | agent族203通过/2跳过 |
| 已完成QThread释放 | 1失败 | chat+proactive+互动83通过；最终销毁事件同步9通过 |
| 私人状态源包排除 | 1失败 | package/build/lifecycle13通过；追加署名拒绝缺失1失败后package/build11通过 |
| 实际Fake头部+投喂 | 完整新增接线回归 | 两拓扑2通过，零credentials/network/TTS截获，零私库/会话 |
| 实际主动识屏子菜单 | 先测试时未显示子菜单导致即刻执行；修正为真实可见submenu后 | 两拓扑2通过，deferred关闭后原Config深链 |

第一轮完整主组：**4失败、4539通过、37跳过、19警告、375.20秒**。三个新增嵌套配置快照漏登记、一个PyInstaller字符串旧检查失效；保持白名单/顺序护栏，同步明确授权变化。第二轮完整主组在约50%处发生native segfault，堆栈为原 `context_menus/shared.py:728 worker` 的 `_worker_done.emit()`；没有pytest最终计数，不能算通过。新增桥生命周期测试修补前1失败，证明桥随目标销毁，修补后音乐/菜单/lifecycle **28通过、0跳过/警告、2.02s**：桥保持到worker发信号完全返回，Qt目标弱引用，外部显式删除先isValid、释放只在GUI线程，原音乐控制未重写。最终主组从头重跑通过（见下表），没有略过音乐/menu用例。扩展agent/menu负载的中间轮在新修补时主动中止（一轮503通过/2跳过/106.48s），不当作最终三轮结果。第一轮负载209通过/78.13s、209通过/74.18s，第三轮1失败/210通过/75.21s：原生销毁断言误将collection清空等同下一条queued deleteLater已执行，改为事件等待**原生已销毁**，未放宽断言；销毁修补后全新增族三轮为211通过/76.31s、211通过/74.06s、211通过/73.65s（均0跳过/警告）。最终额外把原agent线程/协议/状态、设置进程隔离、原菜单生命周期族也并入负载，见下表。

### 完整可执行命令与结果

环境前置 `source /workspace/.onboarding/dsh-pet-env.sh`（Qt offscreen、null keyring、隔离XDG；保留PipeWire配置，Qt6.12测试音频初始化否则可能native崩溃）。完整主套件**不设置PET_FRAMESEQ=0**；该开关只短时subprocess原AppShell smoke使用。

```bash
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_companion_proactive.py
ruff check pet/ tests/ scripts/run_companion_acceptance.py scripts/stress_companion_proactive.py scripts/capture_settings_pages.py scripts/benchmark_companion_interactions.py scripts/package_companion_test.py
python -m compileall -q pet packaging scripts
git diff --check
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
```

| 分组 | 最终真实结果 |
|---|---|
| 主pytest | **4558通过、37跳过、0失败、18个既有Qt弃用警告，527.77s**；collection4595，退出码0 |
| WebM reader/clip/first-frame独立组 | 41通过、0跳过/警告，26.47s |
| low-priority-warm独立组 | 27通过、0跳过/警告，32.36s |
| frameseq追加复验 | 37通过、0跳过/警告，1.84s（与主组有重复，不重复计入唯一总数） |
| 四CPU负载全部时序族三轮 | 每轮**521通过、2跳过、0失败/警告**；132.45s / 123.10s / 143.67s。四CPU，3轮全部退出码0，含原agent/menu/music/settings-process族 |
| 最终共享模型/入口/架构聚焦 | 66通过、0跳过/警告，37.98s |
| 新设置/触摸/范围 | 43通过、0跳过/警告，5.61s |
| Ruff/compileall/diff | Ruff、compileall、diff check均通过，最终推送前再次复核 |
| Node七组 | 34通过、0跳过/失败、260.94ms |
| bridge verify_import | import/subtraction/source bans OK |
| Qt6.8.3 Linux覆盖组 | **1失败、106通过、0跳过/警告，59.59s**；失败为原菜单Qt包装普查（下述） |
| Qt6.8.3 最终菜单/音乐lifecycle补测 | **1失败、27通过、0跳过/警告，3.24s**；同旧菜单包装普查，QAction118→763（+645）/QMenu9保持，音乐修补断言通过 |
| Qt6.8.3 最终聊天lifecycle补测 | 28通过、0跳过/警告，29.34s |
| Windows build依赖 | `pip download --only-binary=:all: --platform win_amd64 --python-version 312 --implementation cp --abi cp312 -r packaging/requirements-companion-build.txt -c packaging/constraints-win10-companion.txt`成功解析下载7个wheel；不是原生构建 |

此前原生deadQObject线程警告修复后，第一轮主组仅剩19个既有Qt弃用警告；最终主组18个Qt弃用警告（mirrored/DragEnter/HoverEvent），没有旧dead-monitor未捕获线程警告。offscreen的raise/grabKeyboard/propagateSizeHints stderr是平台插件提示，与pytest警告计数分开。完整CI唯一Python用例合计**4626通过、37跳过、0失败、18警告**（主组+41WebM+27warm；frameseq37为重复复验，不重复计数）。所有完整分组均执行；Qt6.8失败保留并报告，不称“所有平台全绿”。架构保持retired多进程模块缺席、模块行数预算和动画回归。

## 七、产物、兼容性与已知问题

Windows Chat EXE：**NOT BUILT**；Windows PowerShell/PE DLL/EXE/安装/真实DeepSeek：**NOT TESTED**。构建工具已解析下载win_amd64 wheel，原生脚本仍未执行；固定profile和build-dependencies记录保证流程可复现，不承诺不同Python补丁/时间戳下EXE字节完全相同。无伪造EXE/SHA。用户源码可用原3.12 venv运行；build wrapper从干净源/独立固定工具构建，不含真实Key/用户资料。

真实源码产物（不是EXE，不加入Git）：

| 项目 | 实测 |
|---|---|
| 路径 | `/workspace/artifacts/companion-complete-source.zip` |
| 大小 | **88,849,334字节** |
| SHA256 | `040efef829b481e9f3b08ecfe9c180e52a810b76184fff6d9cd0884c9324996b` |
| 代码/验证文档快照 | `9347bd07c0a41854c471898c6266ffdd3d4124db`；最终报告提交仅增加本产物记录，运行代码一致 |
| 实际验证 | 886个公开源文件checksum、凭据检查通过；完整源码重复构建得到相同SHA256 |
| 外部校验文件 | `/workspace/artifacts/companion-complete-source.zip.sha256` |

命令：`python scripts/package_companion_test.py --output /workspace/artifacts/companion-complete-source.zip`，再 `--verify`；repeat输出另一ZIP并用hashlib.file_digest比较。包内报告为上述快照版本（没有把自己的ZIP hash写回自己造成循环）；此处记录为最终Git报告。GitHub Download ZIP的目录/格式及最终报告更新不同，**不能拿本工具ZIP的SHA去比GitHub ZIP**。网页用户直接按最新开发分支/最终HEAD下载即可，运行源码相同。

已知非阻断旧问题：

1. Qt6.8.3 `tests/test_menu_tree_release.py::test_repeated_context_menu_rounds_leave_no_qt_residue`，当前覆盖组QAction821→1466（+645）、QMenu144保持；15轮每轮+43包装对象。旧67626f0/8847826隔离对照57→702同+645（5通过/1失败），证明非本轮引入；断言未删除/放宽，试验修改均撤销。怀疑binding隐藏signal持有，仅有假设，未宣称根因已修。Qt6.12主组同断言通过；Windows Qt6.8须原生长期菜单验收。本轮已解决另一agent-monitor-dsh deadQObject警告，原生聊天QThread释放通过新断言。
2. 原 `tests/smoke.py` 写死51素材，现106，保留旧失败对照；使用新真实AppShell Fake smoke进行本轮验证，不称旧脚本通过。
3. crash中UI与JSON不原子，原10分钟内有限重试可能重复展示；quota则保守记账，不借新日。SQLite/配置权限异常安全停用，不能保证断电时通知已被用户看到。
4. 本地规则敏感过滤/语义Jaccard不等于完整语言理解；拒绝不确认事实、保守readonly，不保证任意语言同义消重。用户原body语音配置/独立文件解读明确授权可另发网络，不是新增AI自动调用。
5. 移动盘/网络盘stat本身可卡后台OS调用，退出cancel取消后续UI但不能终止内核阻塞；Windows native退出/睡眠仍待测。200/1000压力样本不替代长时间Windows浸泡。

最终停止开发，等待统一Windows集中验收；不合main。下一步只按用户实机证据修复或确认发行，不再添加重复功能。先Fake普通权限双拓扑/子宠/旧数据回退，再独立live手动Key及费用/声音，最后原生构建/EXE/注销/跨日。
