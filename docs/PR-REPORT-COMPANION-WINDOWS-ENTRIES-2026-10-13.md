# P2-B Windows 实机问题修补：右键设置与默认 Fake 主动气泡

基线：`67626f0aa2a87e617857689c7356d0f19d18610a`；分支：`feature/win10-companion-memory`；日期：2026-10-13。
范围限于本轮两个实机断点和验收脚本；动画引擎、正式依赖、数据库schema未改，P2-C/P3/P4/P5未进入，main未合并。
关联：[Windows复测指南](WINDOWS10-COMPANION-ACCEPTANCE.md)、[上一轮交付](PR-REPORT-COMPANION-PROACTIVE-HARDENING-2026-10-12.md)。

## 根因、修复与完整调用链

**右键设置**：默认拓扑是overlay。`SpriteMenuFacade.on_open_modern_settings` 正确绑定被点sprite，`close_on_trigger` 正确把命令加入根菜单，`ShellOverlayWindow.contextMenuEvent` 也正确在 `exec()` 后取出并投递。实际断点在 `OverlayShell.open_settings_for`：只调用 `AppShell.open_settings_process`，它看到验收Config的 `settings_process_isolation=False` 返回False；调用方没有进程内回退。灵动岛走 `PetInstance.open_modern_settings`，原来就有回退，因此两条入口表现不同。没有证据表明本次Legacy正常菜单链具有同一根因。

- Legacy：`contextMenuEvent → _show_context_menu → registry modern_settings QAction → connect_action → defer_menu_callback → QMenu.exec返回 → take_deferred_menu_callbacks → QMenu销毁 → PetWindow context-bound singleShot → PetInstance.open_modern_settings`。
- Overlay：`contextMenuEvent → sprite_at → build_sprite_full_menu / SpriteMenuFacade → 同一action/defer → QMenu.exec返回 → _dispatch_deferred_menu_callbacks（定时器绑overlay窗）→ open_settings_for`。
- 修复后主宠overlay委托现有主 `PetInstance.open_modern_settings`；因此右键和 `AppShell._open_settings_from_island` 共享同一个ModernSettingsDialog。子宠先尝试独立进程；关闭隔离或启动失败时，辅助模块以同一用户base及对应slot Config创建轻量PetInstance，只复用设置生命周期，不创建PetWindow或动画库。
- 进程内：`_open_modern_settings_in_process → ModernSettingsDialog(Config, include_ai) → _present_dialog → show/raise/activate`。重复点击复用，finished清引用并应用现有配置链，destroyed仅清对应旧窗口，避免清掉后来打开的新窗。
- 独立进程：`open_settings_process → settings.lock/正在启动闸门 → _launch_settings_process → python -m pet --settings [--settings-base 外部目录] [--instance slot-N] [--settings-fake] → _run_settings → _exec_settings → standalone ModernSettingsDialog`。Fake标志仅由验收宿主显式传递，不写入生产Config；普通live子进程没有此标志。

审查同时发现两处关联问题：自定义Config原来未传给独立设置进程，可能打开默认APPDATA；`_present_dialog` 的60ms重试没有QObject context，在隐藏的设置窗口销毁后仍访问失效对象。现在显式传base、绑定dialog并检查isValid；销毁无finished的隐藏窗口也能清引用。Overlay设置打开期间沿用气泡抑制，子窗关闭不会解除仍打开的主窗抑制。

**Fake主动AI**：原启动器仅替换 `ChatService.__init__`；运行期 `proactive_runtime.sync → ProactiveService(..., provider=None)`，虽然内部ChatService实际Fake，`ProactiveService.fake=False`。后台预检走live密钥验证，在无Key时停住，没有API尝试或气泡。

修复链：`launcher.main → install_fake_chat → 显式ProactiveService构造注入独立FakeProvider → AppShell.start → proactive_runtime.sync → tick/调度候选 → 异步SQLite预留与Prompt准备 → 独立ChatService/QThread/Fake.stream → queued结果与去重/授权复核 → mark_presenting → proactive_runtime.present → host.try_show_bubble → SpeechBubble新文字回执 → finish持久结算`。默认约1.5秒额外tick只发起首次候选检查，原30秒定时、每天10条、30分钟间隔和所有让路条件仍在。

Fake安装幂等；每个服务创建自己的Provider，即使显式传入live Provider也由Fake验收进程替换，避免泄漏到网络。主动服务继续 `notify_global=False`，不写会话或记忆；手动聊天独立完成一次。Fake系统凭据get/set返回空/失败，urllib网络被阻断；独立设置子进程同样安装此边界。没有填假Key绕过live校验，正式live服务和Provider验证未修改。

## 修改文件说明

共16个文件，+785/−56；以下为相对67626f0的 `git diff --numstat`。新增文件均是源码/测试/报告，无删除文件、无用户数据库或密钥。

| 文件 | 改动及原因 | 增删行 |
|---|---|---|
| `pet/app.py` | 复用进程内设置入口，dialog销毁与重试收口，overlay设置抑制，独立子进程传base/Fake身份 | +33 / −10 |
| `pet/overlay_shell.py` | 主宠设置委托和子宠回退；退出关闭子设置 | +10 / −9 |
| `pet/overlay_settings.py`（新增） | 每slot设置owner缓存与关闭，避免创建Legacy渲染窗 | +43 / −0 |
| `pet/__main__.py` | 设置子进程接收显式base与Fake标志，保留轻量入口 | +8 / −1 |
| `scripts/run_companion_acceptance.py` | 主动Provider显式注入、每服务隔离、幂等、成功回执诊断 | +15 / −2 |
| `scripts/prepare_windows_companion.ps1` | 可选3.12和所有Python操作UTF-8，保留3.11默认与原约束 | +8 / −8 |
| `scripts/stress_companion_proactive.py` | 高负载复跑纳入本轮菜单与启动器测试 | +1 / −0 |
| `scripts/benchmark_companion_entries.py`（新增） | 临时配置与Fake的可重复真实设置生命周期测量 | +55 / −0 |
| `tests/test_companion_settings_entry.py`（新增） | 实际菜单嵌套循环、两种拓扑、回退/独立进程、关闭重开、子身份、销毁取消 | +294 / −0 |
| `tests/test_companion_acceptance_launcher.py` | 真Qt气泡、默认启动器真实AppShell子进程、零Key/网络/捕获/语音、手动隔离 | +140 / −0 |
| `tests/test_settings_process_isolation.py` | 更新自定义base的精确子进程命令契约 | +1 / −1 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | 记录用户Windows证据、网页ZIP更新、已有3.12解释器、UTF-8安装和复测清单 | +41 / −25 |
| `CONTEXT.md` | 记录两个实际断点和用户Windows实测边界 | +13 / −0 |
| `docs/INDEX.md` | 登记新的交付报告 | +2 / −0 |
| `docs/PR-REPORT-COMPANION-PROACTIVE-HARDENING-2026-10-12.md` | 保留上一轮结果并追加本轮现场反馈链接 | +4 / −0 |
| `docs/PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md`（新增） | 可审查根因、红绿证据、全部真实测试与未验证边界 | +117 / −0 |

## 红绿证据与测试验证

修补前新增测试真实运行，未替换菜单追踪或设置构造：

```text
python -m pytest -q tests/test_companion_settings_entry.py tests/test_companion_acceptance_launcher.py
3 failed, 5 passed in 12.29s
FAIL overlay：等待后modern_settings_dialog仍None
FAIL custom settings process：--settings-base缺失
FAIL default Fake：未配置有效凭据；等待配置更改，不请求网络
```

新增子宠进程内回退同样在原实现返回False。另一次独立的dialog生命周期红测试：

```text
python -m pytest -q tests/test_companion_settings_entry.py::test_pending_dialog_presentation_drops_when_destroyed
1 failed in 1.39s
RuntimeError: libshiboken: Internal C++ object (ModernSettingsDialog) already deleted.
```

聚焦集含本轮两个文件及 `settings_process_isolation`、`sprite_menu_target`、`sprite_menu_parity`、`menu_tree_release`、`context_menu_lifecycle`、`overlay_per_slot_settings`、`companion_proactive_hardening/state/service/network/ui/failures/schedule`、`companion_chat`、`chat_service`、`architecture`。初次修补后主环境 **211 passed / 0 skipped，51.68s**。最终主CI分组 **4469 passed、37 skipped、21 warnings，351.56s**；不沿用此前4451通过。

覆盖普通配额、间隔、重试上限、语义去重、删除/撤销记忆/跨重启、手动聊天优先及原版聊天由相关旧测试实际复跑。本轮新增默认Fake真实UI路径禁止系统Key读取和urllib调用，禁止截屏、语音、QCamera.start和QAudioSource.start；Provider与全局完成事件各自独立。另有两个完整AppShell子进程直接运行原启动器，不改源码/不依赖.bak，分别断言一次真实Qt气泡和一次SQLite成功结算。

相关聚焦的完整命令：

```bash
python -m pytest -q tests/test_companion_settings_entry.py tests/test_companion_acceptance_launcher.py tests/test_settings_process_isolation.py tests/test_sprite_menu_target.py tests/test_sprite_menu_parity.py tests/test_menu_tree_release.py tests/test_context_menu_lifecycle.py tests/test_overlay_per_slot_settings.py tests/test_companion_proactive_hardening.py tests/test_companion_proactive_state.py tests/test_companion_proactive_service.py tests/test_companion_proactive_network.py tests/test_companion_proactive_ui.py tests/test_companion_proactive_failures.py tests/test_companion_proactive_schedule.py tests/test_companion_chat.py tests/test_chat_service.py tests/test_architecture.py
```

### 最终执行命令与结果

以下命令在已初始化环境（`source /workspace/.onboarding/dsh-pet-env.sh`）执行，Linux Python3.12.14 / Qt6.12.0；Qt6.8.3复验另用 `/workspace/.venvs/dsh-pet-qt68/bin/python`。

| 命令 | 本轮真实结果 |
|---|---|
| `python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py` | 4469通过、37跳过、21警告，351.56s |
| `python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py` | 41通过、0跳过，27.34s |
| `python -m pytest -q tests/test_low_priority_warm_interaction_yield.py` | 27通过、0跳过，62.49s（无重试） |
| `python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py` | 37通过、0跳过，1.61s（主组已含，不重复相加） |
| `python scripts/stress_companion_proactive.py` | 四个CPU burner：126通过×3、各0跳过/警告；51.87s、48.67s、49.45s |
| `ruff check pet/ tests/ scripts/run_companion_acceptance.py scripts/stress_companion_proactive.py scripts/benchmark_companion_entries.py` | All checks passed |
| `python -m compileall -q pet packaging scripts`；`git diff --check` | 退出0 |
| `node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js` | 34通过、0跳过、0失败，224.996ms |
| `node integrations/dsh-pet-bridge/verify_import.mjs` | import + subtraction surface + source bans OK |
| `python -m pytest -q tests/test_pr_report_discipline.py` | 81通过、0跳过，0.38s |

Qt6.8.3：同一相关聚焦组最初 **210通过、1失败，53.19s**；失败为已有 `test_menu_tree_release.py::test_repeated_context_menu_rounds_leave_no_qt_residue` 的GC包装对象计数。隔离运行该文件：5通过、1失败；QAction 57→702，QMenu仍1。用 `git archive 67626f0` 的未修改临时快照运行完全相同命令也得到5通过、1失败、57→702，1.11s，证明不是本轮引入。该测试未删除/削弱，主环境完整CI中照跑通过。随后明确选择本轮相关文件（不含这个既有菜单普查族）的Qt6.8.3聚焦组 **205通过、0跳过，51.50s**；包括全部19项入口/启动器测试及架构检查。没有宣称Qt6.8.3完整回归通过；Linux包装对象计数问题不能直接推断Windows同样失败。

警告：主组2条 `PytestUnhandledThreadExceptionWarning` 来自原 `agent-monitor-dsh` 的 `RuntimeError: Signal source has been deleted`（旧agent_link线程销毁问题，本轮未改）；其余19条为Qt镜像/拖动/hover API弃用提示。Offscreen的raise/键盘抓取/propagateSizeHints提示属于无原生桌面的能力边界。旧 `tests/smoke.py` 素材数量51断言与106实际素材不符的问题保留，不混入本轮通过数。

## 性能分析

环境：Linux / Python 3.12.14 / PySide6、Qt 6.12.0，QT_QPA_PLATFORM=offscreen；命令：`python scripts/benchmark_companion_entries.py`。真实AppShell容器和ModernSettingsDialog，临时Config关闭音效，用合成Provider，20次打开/关闭，每次定向DeferredDelete；100次独立ChatService构造。实测：首开704.532ms；后19次打开中位数579.816ms、最大697.809ms；Fake ChatService构造100次中位数0.014ms、最大0.098ms。每次关闭后存活ModernSettingsDialog均为0；第5次后RSS122.180MiB，第20次122.852MiB（+0.672MiB）。20次样本不能证明无限期RSS无增长，也不能把Linux数字当Windows性能。

此修补没有新增动画帧/tick调用，没有新的稳态定时器，原主动调度仍30秒；新增身份辅助代码仅在用户打开/关闭设置时运行。打开子设置按原Config读取一次slot文件，独立进程增加两个CLI身份参数；没有新增网络或数据库schema。Fake修补使本来被拦住的测试请求正常启动既有后台SQL/Chat线程，受原预算约束，不能用合成耗时代表DeepSeek延迟/费用。设置对话框仍有已有构造成本，未借此阶段重构UI。

## 实机运行记录

**用户已提供的Windows现场事实**：Windows10 22H2 x64，Python3.12 x64，依赖按约束安装；源目录 `D:\Code\dsh-pet-indesktop`、解释器 `D:\Code\FishVenv312`、数据 `D:\Code\FishAcceptance`。GUI启动、桌宠可见、主动设置页完整、灵动岛设置、直接ModernSettingsDialog均成功；右键“桌宠设置”和原启动器Fake主动气泡失败；临时显式注入Fake后“合成测试”主动气泡成功。中文pip GBK报错经 `python -X utf8 -m pip install ...` 修复成功。这些是用户实机观察，不能全部标NOT TESTED，也不能宣称本轮正式补丁已在Windows通过。

**本轮本机**：Linux offscreen两种拓扑的真实QMenu.exec、真实ModernSettingsDialog、真实独立设置进程及默认启动器AppShell/动画/Qt气泡流程。网络仅Fake或已有模拟SSE，未提供或使用真实API Key。探针 `platform.system()` 输出Linux，`command -v pwsh` 无输出；所以Win32原生popup、窗口激活/透明、Shell编码、PowerShell执行、系统凭据及EXE构建不能在本机验收。

Qt UI review：两入口共享语义/对话框、角色身份、modeless非阻塞、菜单释放和关窗重开通过；未改布局/QSS/动画。原生键盘右键、DPI、焦点/激活和多显示器需用户Windows复验。

## Windows 更新与剩余验收

最简单步骤见[指南开头](WINDOWS10-COMPANION-ACCEPTANCE.md)：退出旧进程，GitHub选开发分支 → Code → Download ZIP → 解压到新目录，不叠加旧临时补丁/.bak。保留既有虚拟环境和隔离数据，执行已有解释器 `D:\Code\FishVenv312\Scripts\python.exe -X utf8 scripts\run_companion_acceptance.py --data-dir D:\Code\FishAcceptance`。已有成功展示的目录仍受持久频控；首次验证可选择新的外部 `D:\Code\FishAcceptanceRetest`，不改系统钟、不删库。

分别复验Legacy/Overlay右键、灵动岛复用、关闭重开、主/子宠正确角色、两种设置进程路径及隔离目录；默认Fake无Key应显示气泡并打印成功回执。拖动点击、透明窗口、投喂、手动聊天优先、退出/锁屏睡眠/跨日等完整原版回归仍需用户继续验收。真实DeepSeek联网、真实401/429/费用及动态措辞：**NOT TESTED**；准备脚本Windows执行、新EXE：**NOT TESTED / NOT BUILT**。现有Python3.12基础成功不推断任意依赖/平台全兼容。完成本轮后停止，等待Windows复验，不推进新阶段。
