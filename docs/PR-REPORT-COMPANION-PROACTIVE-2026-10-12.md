# P1.1 收尾与 P2-A/P2-B 主动文字陪伴交付

基线 `5b10e33`，分支 `feature/win10-companion-memory`。
本轮使用 Fake Provider 与模拟 HTTP/SSE；没有真实 API Key。
**Windows 10 22H2 x64 与真实 DeepSeek 联网：NOT TESTED。**
**P2-C（可靠日程 outbox、重启补发）、P3/P4/P5：NOT IMPLEMENTED。**
关联：[P1.1](PR-REPORT-COMPANION-MEMORY-HARDENING-2026-10-12.md)、[P2 方案](P2-PROACTIVE-CHAT-IMPLEMENTATION-PLAN.md)、[P0/P1 接缝](AI-COMPANION-INTEGRATION-NOTES.md)。本轮范围以用户上传的正式 P1.1/P2-A/B 任务书为准。

## 核心特性

明确个人回忆意图才打开私人记忆数据库；“我想知道火星的颜色”和“请帮我解释蓝色光”不读取。主动功能默认关闭，沿用现有 AI 设置域、角色 PromptBuilder、Provider/ChatService 与两种桌面气泡。普通消息共享硬上限：每日最多10条、至少30分钟；可调为更少条或更长间隔，不能绕过上限。模型失败跳过并退避，不播放固定台词。

## 修改文件说明

本轮不修改动画引擎、SessionStore 或 Todo 实现。以下是最终源码/测试/截图的 `git diff --cached --numstat`；本报告自身统计在末尾列出。

| 文件 | 增/删 | 原因 |
|---|---:|---|
| `.gitignore` | +1/−0 | 排除主动状态库及journal等私人文件 |
| `CONTEXT.md` | +12/−0 | 登记主动文字陪伴、费用与P2-C边界 |
| `docs/INDEX.md` | +2/−0 | 登记本报告 |
| `docs/screenshots/companion-proactive/1100-dark/controls-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-dark/controls-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-dark/limits-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-dark/limits-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-light/controls-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-light/controls-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-light/limits-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/1100-light/limits-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-dark/controls-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-dark/controls-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-dark/limits-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-dark/limits-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-light/controls-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-light/controls-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-light/limits-False.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `docs/screenshots/companion-proactive/720-light/limits-True.png` | 二进制 | 真实Linux/offscreen设置页截图；二进制，不适用行数 |
| `pet/app.py` | +13/−0 | AppShell进程持有、懒启动、配置更新、WTS、正常退出和会话结束收口 |
| `pet/chat/ai_settings_page.py` | +3/−0 | 在原AI页装配主动陪伴设置行 |
| `pet/chat/providers.py` | +14/−2 | 向后兼容ProviderError附带Retry-After并解析数值/HTTP-date |
| `pet/chat/service.py` | +37/−6 | 独立实例跳过全局完成、手动启动订阅、结构化错误、主动限长和后台cancel close |
| `pet/companion/memory_context.py` | +5/−1 | 无关查询且无获授权待提取事实时不打开SQLite |
| `pet/companion/memory_retrieve.py` | +6/−1 | 个人回忆主体/意图门禁，不把知识求解误当回忆 |
| `pet/companion/proactive_config.py` | +24/−0 | 默认关闭、严格布尔、每日10/间隔30硬边界及quiet_hours归一化 |
| `pet/companion/proactive_context.py` | +45/−0 | 双授权安全事实、删除revision检查、完成无写入 |
| `pet/companion/proactive_policy.py` | +16/−0 | 同进程退出授权立即失效，保存失败也拒绝旧快照 |
| `pet/companion/proactive_repeat.py` | +36/−0 | 规范化、中文片段/英文词相似度和多标签冷却 |
| `pet/companion/proactive_runtime.py` | +101/−0 | 公共host快照、单次呈现、Chat懒装配、输入事件让路与WTS注册 |
| `pet/companion/proactive_schedule.py` | +60/−0 | 纯候选调度、活动计时、睡眠重置、quiet-hours状态门禁 |
| `pet/companion/proactive_service.py` | +287/−0 | 串行后台状态、独立ChatService、deadline、generation、只读记忆与回执链 |
| `pet/companion/proactive_settings.py` | +60/−0 | 共用设置控件、即存合并、依赖、费用说明和未实施日程状态 |
| `pet/companion/proactive_state.py` | +155/−0 | 独立SQLite日账/预约/多标签历史/退避，损坏保留、原子互斥 |
| `pet/config.py` | +5/−0 | 默认配置、reload专门归一化和set归一化 |
| `pet/modern_settings_dialog.py` | +1/−0 | 将新行认领到AI与对话域 |
| `pet/overlay_shell.py` | +18/−0 | 普通气泡真实回执、主宠显隐/飞行/暂停/重要提示门禁 |
| `pet/window.py` | +15/−0 | Legacy普通气泡回执并保留show_bubble协议 |
| `scripts/benchmark_companion_proactive.py` | +43/−0 | 仅合成临时库的可复现时延与局部分配测量 |
| `scripts/capture_companion_proactive.py` | +40/−0 | 原设置系统720/1100、明暗及开关截图 |
| `scripts/stress_companion_proactive.py` | +30/−0 | 可复现四CPU负载下三轮相关线程/状态族回归；子进程与退出均有界 |
| `scripts/smoke_companion_proactive.py` | +78/−0 | 真实AppShell、阻塞Fake模型期间帧推进与气泡持久回执 |
| `tests/test_companion_proactive_failures.py` | +47/−0 | 401/429/断网/空与超长输出、错误不泄漏与有限请求 |
| `tests/test_companion_proactive_network.py` | +102/−0 | 生产Provider模拟HTTP/SSE、Prompt/token、Qt/SQLite线程及阻塞close |
| `tests/test_companion_proactive_schedule.py` | +29/−0 | 候选状态/活动/睡眠与同义、多标签去重 |
| `tests/test_companion_proactive_service.py` | +297/−0 | 真实ChatService+Fake Provider、取消、手动优先、角色切换、记忆授权/删除与不写回 |
| `tests/test_companion_proactive_state.py` | +177/−0 | 10条额度/30分钟、午夜/重启进程/并发、回拨/时区/DST、锁/损坏/Crash/重试 |
| `tests/test_companion_proactive_ui.py` | +230/−0 | 原设置域即存、保存失败退出授权、真实两种气泡、单宿主、无Chat与退出/挂起 |
| `tests/test_companion_recall_intent.py` | +20/−0 | 个人回忆正例及知识问题禁止打开SQLite反例 |
| `tests/test_config_schema.py` | +1/−1 | 显式登记新配置专门合并键 |

## 工作流程与持久化

Qt 获取状态快照 → 30秒 tick 产生候选 → 单后台 executor 做凭据、角色、SQLite 预约 → 独立 ChatService 的 QThread 调 Provider → 后台过滤/去重/确认记忆 revision → Qt 当前 host 的 `try_show_bubble` 回执 → 后台持久化成功。

`companion_proactive.sqlite3` 位于 `Config.dir`（既有本地用户数据目录），schema v1：`days` 保存本地日期、成功数、请求次数及预留输出token；`meta` 保存最后成功UTC、观察时间高水位、401凭据/配置摘要及退避；`reservations` 保存唯一请求、候选事件、类别、pending/presenting、过期时间与最多2次尝试；`utterances` 保存最近文本、多语义标签、UTC、本地日与事件。每操作独立连接、BEGIN IMMEDIATE、300ms SQLite等待；损坏/新版本不自动覆盖。

pending 预约60秒过期释放。呈现前先持久化 presenting；Qt接受后成功数只递增一次。不接受则释放并保持成功数不变。窗口显示与SQLite不能原子提交：异常退出的 presenting 留作保守占位，当天不会重新出售该名额；它不伪造成功记录。最近台词最多100条/30天，日账最多60天，跨午夜仍用UTC保持间隔；时钟回拨保守暂停至墙上时间追上已观察时间，运行中另用单调时钟防止前拨跳过间隔。时区/夏令时改变不重置已有日期的账。

问候按本地上午/下午/晚上，一事件只展示一次，同类6小时冷却；休息需连续活动1小时、饮水1.5小时，关心2小时；同类两小时冷却。睡眠/离开/挂起/过长tick间隔重置活动累计；间隔门禁期间仍累计活动。夜间没有默认禁言时段；支持合法 quiet_hours 两元素 HH:MM 配置，默认null。

去重：NFKC/大小写/标点规范化、中文双字片段及英文词 Jaccard、问候/喝水/休息多标签及主题冷却。不调用 embedding。相同文本、近似文本、混合主题重叠会拒绝；最多追加一次生成。规则无法理解所有自然语言同义，属于保守近似。

## 配额、费用、隐私与生命周期

SQLite互斥事务同时检查成功数+在途/不确定占位、共享间隔和唯一事件；默认最后一个槽不能并发抢两次。失败与重复不计成功数，但消耗请求预算。每日硬上限为两倍展示额度（默认20次），每次max_tokens=96，即最多预留1920输出token；这不是总费用保证，输入token也计费，仍需关注供应商价格。25秒总截止计时器+不超过20秒网络读超时；超长/空输出丢弃。401暂停至配置/凭据摘要变化，429读取数字或HTTP-date Retry-After并有界退避，其余错误指数退避。错误字符串不写状态库或日志。无凭据缓存不可用状态，配置变化前不循环解析/请求。

只在关心主题且 `use_memory` 与 `chat.memory_enabled` 双重授权时读取最多3条/300字安全近期事实；复用P1.1过滤与授权策略，并核对删除revision。独立 ReadOnlyMemory.completed 为无操作，不调用 MemoryContext.completed，不伪装用户ChatMessage、不保存会话、不解析相对日期创建任务。关闭记忆/删除时在途旧结果丢弃。主动气泡不走全局手动完成监听/岛预览，不触发TTS、录音、截图、摄像头。

AppShell持有一服务；窗口动态选择一次，不广播多宠。Overlay本轮只选择主sprite；主宠单独隐藏时暂缓，未把主动服务扩展为逐子宠选址。隐藏、暂停、飞行/设置抑制、重要提示、全屏、锁屏、手动聊天均让路。原 show_bubble 协议不变，新增普通消息回执接口。手动 ChatService 启动立即取消主动请求；打开/输入聊天由Qt事件过滤与可见聊天窗快照让路。generation及配置摘要拒绝旧角色/旧结果。关闭/关机无主线程网络等待；主动取消的response.close放后台，未结束QThread保留强引用。不增加主动识屏或语音服务。无Chat不导入或创建主动聊天实例。

## 设置契约

全部归属“AI 与对话 / 主动 AI 陪伴”，沿用SettingRow、ToggleSwitch、BrowserSpinBox，设置即存且合并最新配置。`enabled` 默认false，其他主题/use_memory/去重开关true；daily_limit默认10、范围0–10；间隔默认30、范围30–180；quiet_hours默认null，无额外夜间门禁。主题控件依赖enabled，记忆仍依赖长期记忆授权。开关失败时提示并保留同进程退出授权；独立设置进程写盘失败无法通知另一进程，需处理权限后重试。scheduled_reminders默认true仅意向，UI禁用并明确“尚未实现 / NOT IMPLEMENTED”，不改变Todo。

## 性能分析

Linux x86_64 / Python3.12.14 / PySide6 6.12 / cgroup4 CPU。
命令：`source /workspace/.onboarding/dsh-pet-env.sh`，然后 `python scripts/benchmark_companion_proactive.py`。合成临时库，完整回归并行时样本，单位微秒：

| 路径 | 样本 | 中位数 | p95 |
|---|---:|---:|---:|
| 纯调度tick | 10000 | 2.66 | 3.91 |
| 关闭状态预约（无I/O） | 10000 | 1.42 | 1.48 |
| SQLite拒绝预约（后台） | 500 | 144.57 | 297.53 |
| 100条语义去重（后台） | 500 | 1608.51 | 2211.52 |

2000次空recent SQLite读取，tracemalloc当前32字节、峰值2171字节，样本数据库36864字节。此测量只覆盖Python局部分配，**不等同整体RSS、Qt内存或Windows CPU/帧率**。启用后30秒Qt timer、一个按需executor线程、最多一在途模型QThread；取消关闭response另用至多一daemon closer。关闭功能无模型请求/周期timer，已创建服务可能保留空闲executor至进程关闭。没有按每只宠物增加调度器。

## 实机运行记录

仅Linux云端真实Qt/offscreen。`PET_FRAMESEQ=0 python scripts/smoke_companion_proactive.py` 已输出 PASS：真实AppShell、阻塞Fake Provider期间原版解码动画帧推进、带透明度的真实帧、窗口绘制、单个真实气泡、持久回执、正常退出。PET_FRAMESEQ=0是仓库支持的短启动模式，不作为全量测试的全局开关。

设置截图脚本 `scripts/capture_companion_proactive.py` 复用既有capture_settings_pages的主题；证据在 [screenshots/companion-proactive](screenshots/companion-proactive)，720/1100、明/暗、启用/关闭、上部控件/下部限制各一张，共16张。滚动可达，中文换行；没有Windows/Cocoa实机截图。

## 自动化验证

最终主套件 **4420 passed / 37 skipped / 21 warnings / 0 failed，310.01s**。这是本次实际运行，未套用此前4207或4349基线。21个警告包括既有agent-monitor-dsh在对象删除后emit及Qt弃用API；没有把警告计作通过测试。

```bash
source /workspace/.onboarding/dsh-pet-env.sh
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python -m pytest -q tests/test_companion*.py tests/test_chat*.py tests/test_todo*.py tests/test_architecture.py tests/test_session_end_ffmpeg_guard.py tests/test_session_lock_suspend.py
ruff check pet/ tests/ scripts/benchmark_companion_proactive.py scripts/capture_companion_proactive.py scripts/smoke_companion_proactive.py scripts/stress_companion_proactive.py
python -m compileall -q pet packaging scripts
git diff --check
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
```

| 检查 | 结果 |
|---|---|
| 相关companion/chat/Todo/架构/会话族 | 488通过、8跳过，20.18s |
| 4 CPU满载时序/服务族（上面的新P2测试+companion_chat+chat_service） | 89通过×3，7.38/7.13/7.15s，无失败/跳过/警告 |
| Ruff / compileall / diff check | 通过 |
| Node桥接七文件 | 34通过，0失败/跳过 |
| hermetic bridge import | 通过 |
| 实际AppShell+Fake模型冒烟 | PASS |

满载命令为 `python scripts/stress_companion_proactive.py`：4个multiprocessing整数运算循环与pytest并行，finally Event终止并join；并非固定sleep编舞。其pytest名单为全部7个新增companion测试、companion_chat、chat_service。FrameSeq独立复跑中的用例已包含主套件，不重复累加总数。独立WebM：41通过、0跳过/失败/警告，25.38s；低优预热：27通过、0跳过/失败/警告，31.32s；FrameSeq：37通过、0跳过/失败/警告，0.92s。

失败记录：TDD反例曾真实复现普通查询读库、正常退出缺少直接收口、隐藏主sprite冒泡，均有对应修补和最终绿测试。中间完整主套件曾1失败/4410通过/37跳过（新增锁屏参数不兼容无Chat替身），现仅Chat变体追加回调，原替身不需修改。两次主套件在后续实现修正时主动中断，不计作完整通过。一次focused误选不存在文件名（0 tests）已更正，不计入验证。旧会话reader对照测试另一次focused曾1失败/36通过：reader未启动即断言；该测试与WebM实现本轮未修改，后续相关族及完整套件通过，保留为既有时序隐患。

旧 `python tests/smoke.py` 本次实跑仍失败：`assert len(names)==51`，实际106；原脚本未修改。对应真实AppShell新增冒烟通过。

## 未验证与下一阶段

Windows10 22H2 x64透明/置顶/高DPI、Legacy/Overlay桌面实景、多屏多宠、原拖动点击/文件投喂、WTS锁屏/睡眠/注销/关机、Windows SQLite锁与用户目录权限、钥匙串、系统代理/TLS、真实DeepSeek全system任务兼容性/流式取消/限流与费用、最终EXE：**NOT TESTED**。Linux回归或Windows API fake不代替实机验收。

P2-C可靠日程与补发仍 **NOT IMPLEMENTED**；不从“明天/下周”自动创建任务。本轮停止，等待用户审查。后续先做Windows真实Provider验收，再按独立授权实施P2-C，P3/P4/P5另行批准。

回滚：先关闭“主动 AI 陪伴”，待在途任务作废，再revert本轮提交；保留本地两份SQLite，不删除用户状态/记忆。若长期墙上时间错误，保守高水位可能暂停到时间追上；修正系统时间后等待，不自动清空配额库。

## Git 与审查

实现提交 `586b776` 已推送到 `feature/win10-companion-memory`，未覆盖或合并main。实际执行 `gh pr create --draft` 后，GitHub GraphQL API 返回 Forbidden，未创建PR；可通过该提交审查代码，独立补丁见交付消息。

本轮合计51文件（含16张截图）；本报告自身新增 159 行，删除0行。
