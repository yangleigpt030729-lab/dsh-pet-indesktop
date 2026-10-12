# P0/P1：DeepSeek 大肥鱼 SQLite 长期记忆

基线 `27495f9b67bd7529c633392927b185e9a2ccd685`；分支 `feature/win10-companion-memory`。
目标 Windows 10 22H2 x64。执行环境 Linux-6.18.44 x86_64 / glibc 2.41、Python 3.12.14、Qt/PySide6 6.12.0。
**NOT TESTED ON WINDOWS 10；未生成增强版 EXE；未请求真实 DeepSeek API。**
关联：[接入审计](AI-COMPANION-INTEGRATION-NOTES.md)、[任务书](../DEVELOPMENT_PLAN_WIN10.md)、[文档索引](INDEX.md)。

## 一、核心特性

默认关闭的本地长期记忆：开启读取后支持明确要求记住；自动提取另行授权。跨新会话、跨实际进程退出保存，支持查看、编辑、删除、删除全部和本地备份。SQLite 与 JSON 聊天历史独立。

只从用户本人确定陈述提取偏好、属性/称呼及重要事件。不把 assistant 输出、附件正文、问句、猜测、凭据、支付信息或病史写成用户事实。识别范围见审计；未识别表达不猜测，用户可手工确认录入。

原聊天 QThread 在请求前检索最多 5 条/600 字相关引用数据，成功且未取消时本地提取并写库；不新增 API 调用。空记忆也明确提示模型不要推测用户事实。用户编辑/删除及授权变化阻止旧提取任务复活已删数据。

## 二、修改文件说明

新建文件均为真实实现、测试、证据，没有空的 P2–P5 模块。逐文件统计由 `git diff --numstat` 生成，报告自身按最终行数校准；二进制截图无文本行数。无文件删除。

| 文件 | 增删 | 改了什么与为什么 |
| --- | --- | --- |
| `.gitignore` | +3 / −0 | 忽略固定记忆数据库、journal 与备份，防止提交私人数据。 |
| `CONTEXT.md` | +9 / −0 | 增加长期记忆、独立授权与历史删除边界的领域术语。 |
| `docs/AI-COMPANION-INTEGRATION-NOTES.md` | +73 / −0 | P0 源码接缝审计、schema、身份/线程、设置契约与当前基线。 |
| `docs/INDEX.md` | +4 / −0 | 登记审计与 PR 报告，保持文档入口可发现。 |
| `docs/PR-REPORT-COMPANION-MEMORY-2026-10-12.md` | +147 / −0 | 本报告：真实验证、性能、逐文件变更与 Win10 验收。 |
| `docs/screenshots/companion-memory/dark-1100/manager-memory.png` | binary | Linux/offscreen 合成数据截图：管理窗口，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/dark-1100/settings-memory.png` | binary | Linux/offscreen 合成数据截图：AI 域记忆设置，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/dark-720/manager-memory.png` | binary | Linux/offscreen 合成数据截图：管理窗口，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/dark-720/settings-memory.png` | binary | Linux/offscreen 合成数据截图：AI 域记忆设置，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/light-1100/manager-memory.png` | binary | Linux/offscreen 合成数据截图：管理窗口，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/light-1100/settings-memory.png` | binary | Linux/offscreen 合成数据截图：AI 域记忆设置，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/light-720/manager-memory.png` | binary | Linux/offscreen 合成数据截图：管理窗口，用于明暗与宽窄可达性审查。 |
| `docs/screenshots/companion-memory/light-720/settings-memory.png` | binary | Linux/offscreen 合成数据截图：AI 域记忆设置，用于明暗与宽窄可达性审查。 |
| `pet/chat/ai_settings_page.py` | +33 / −0 | 现有 AI 域的两项立即生效授权与管理入口；写盘失败时取消旧任务并提示。 |
| `pet/chat/legacy_widgets.py` | +5 / −1 | 经典聊天窗口在授权后传入 MemoryContext；关闭时原协议不变。 |
| `pet/chat/models.py` | +4 / −2 | ChatSettings 严格布尔值、默认关闭、序列化 round trip。 |
| `pet/chat/prompt.py` | +21 / −3 | 保持现有角色/历史协议；新增可选引用数据消息，空记忆不编造用户事实。 |
| `pet/chat/service.py` | +16 / −4 | 原 QThread 中检索/提取/落盘；所有 Provider 网络请求继续异步。 |
| `pet/chat/widgets.py` | +8 / −1 | 新版聊天接入；仅提取用户亲自输入文字，排除附件正文。 |
| `pet/companion/__init__.py` | +1 / −0 | 可选能力包，无 eager Qt/数据库导入。 |
| `pet/companion/memory_context.py` | +91 / −0 | 不可变请求快照、实时授权/取消代数、故障回退与完成时事务。 |
| `pet/companion/memory_dialog.py` | +124 / −0 | 后台 CRUD/备份；查看、编辑、删除和删除全部的可访问界面。 |
| `pet/companion/memory_extract.py` | +59 / −0 | 保守中文明确陈述提取与不确定/敏感信息拒绝；不采纳 assistant 事实。 |
| `pet/companion/memory_store.py` | +213 / −0 | SQLite v2、版本备份迁移、连接归属、主题/内容唯一约束、删除版本屏障、限量检索。 |
| `pet/config.py` | +4 / −0 | chat 特例域默认值与严格解析；旧配置关闭记忆，无新顶层键。 |
| `pet/modern_settings_dialog.py` | +1 / −0 | 把三行记忆设置接入现有 AI 与对话域，不增加一级域。 |
| `scripts/benchmark_companion_memory.py` | +39 / −0 | 可复现实测，临时合成数据，原 PromptBuilder 同环境对照。 |
| `scripts/capture_companion_memory.py` | +52 / −0 | 复用现有设置截图工具的深色调色板，生成合成记忆明暗/宽窄截图。 |
| `tests/test_companion_chat.py` | +240 / −0 | 真实 ChatService/两种窗口、异步线程、跨新会话、附件隔离、取消/删除/关闭、锁/损坏回退。 |
| `tests/test_companion_memory.py` | +161 / −0 | SQLite CRUD、去重、主题冲突、跨真实进程退出、版本迁移/备份/损坏/并发/隔离、配置与 Prompt。 |
| `tests/test_companion_memory_ui.py` | +79 / −0 | 设置立即保存、现有能力域归属、后台管理 CRUD 和损坏提示。 |

未修改动画引擎、角色素材、PetWindow、文件投喂、气泡、TTS/主动识屏、原 SessionStore、依赖声明、CI 或打包脚本。

## 三、实现要点

- SQLite `PRAGMA user_version=2`；`memories` 保存 id、subject、topic、content、kind、source、创建/更新时间、规范化内容键；`memory_meta.revision` 是在途写入的删除/编辑屏障。
- `(subject,topic)` 和 `(subject,content_key)` 唯一。主题更新覆盖旧事实；与手工条目去重后仍保留已识别主题，以便下一次偏好变化替换旧条目。最多 500 条，旧记录淘汰。
- 默认 `local-owner`，同一用户目录跨角色/多窗共享；每个配置文件的授权独立。不同用户/变体目录隔离。
- 连接在执行操作的线程内创建并关闭；参数化 SQL、300ms busy timeout、短事务、DELETE journal、secure_delete；Win10 未验证 WAL，故不开启。
- v1→v2 用 SQLite backup API 做一致快照后迁移/去重；不复制正在使用的数据库。未知版本和损坏保留原文件，普通聊天回退。管理备份亦保留在本地目录。
- 两项授权只接受 JSON true，默认 false；沿用 chat 域配置合并/序列化。授权立即保存，关闭的运行期屏障不依赖保存成功；失败提示重试，原 provider 草稿不被覆盖。
- 数据文件为 `cfg.dir/companion_memory.sqlite3`，Win10 使用既有 `%APPDATA%/<APP_DIR_NAME>`。备份/日志/原 JSON 历史不会因删除单条记忆而自动删除，管理页有明确说明。

## 四、性能分析

命令：`source /workspace/.onboarding/dsh-pet-env.sh; python scripts/benchmark_companion_memory.py`。
数据：临时目录 500 条合成记忆，无用户内容；与基线 `27495f9` 原 PromptBuilder 代码同进程对照。此轮同时有完整测试套件运行，结果是该云机器观测，非 Win10 性能保证。

| 操作 | 样本 | 中位数 ms | P95 ms |
| --- | ---: | ---: | ---: |
| 500 条检索 | 100 | 6.4680 | 8.0359 |
| 写入/去重 | 100 | 0.1659 | 0.5132 |
| 本地提取两个确定句子 | 1000 | 0.0098 | 0.0111 |
| 原版 PromptBuilder | 1000 | 0.0008 | 0.0009 |
| 新版 PromptBuilder（关闭记忆） | 1000 | 0.0009 | 0.0009 |
| 关闭记忆的 worker 边界 | 1000 | 0.0002 | 0.0002 |

20 次预热后再检索 100 次，tracemalloc 当前分配增加 32 bytes，峰值 256225 bytes；500 条 SQLite 文件 188416 bytes。只是有界样本，不声称长时 RSS 零增长。

关闭时无数据库/授权文件读写；原 prompt 中位数差为 0.0001ms（亚微秒测量噪声范围），窗口调用只多读现有配置对象，不新增计时器。开启后每次手动聊天产生授权文件检查、SQLite 检索和少量参数化 SQL，成功完成且有可识别陈述才写入；这些操作均在已有 QThread。管理动作每次创建一个短命 daemon 线程，拒绝重复提交直到完成。无新增网络调用、无限缓存或后台轮询。

## 五、实机运行记录

当前真实 Linux 容器，`QT_QPA_PLATFORM=offscreen`，没有物理图形桌面/声卡。这是实际 Qt/SQLite/FFmpeg 执行，不能代替 Win10 实机验收。

- 新 Qt 前端/经典前端实际构造，输入“请记住我喜欢蓝色”，后台完成后换新会话，检查 Provider 实际收到的消息包含本地记忆；网络边界是可控 fake Provider，不把模型回答当作真实 API 证据。
- 真实独立 Python 进程写 SQLite、进程退出后重新检索；编辑/删除跨新连接持久化；v1 备份迁移与损坏保留均检查原文件。
- `PET_FRAMESEQ=0 python /workspace/.onboarding/dsh-pet-smoke.py` 退出 0：`PASS: AppShell startup, 106 media metadata, decoded alpha frame, animation advancement, window rendering, graceful shutdown`。使用原开发开关省去大批帧缓存生成，真实 WebM 解码仍在执行。CPU 压力期间有 60/92ms 慢帧日志，未把此结果当作帧率/长稳保证。
- 旧 `python tests/smoke.py` 退出 1：`AssertionError: 106`，因为固定断言 51 项过时。保持该文件不变，未削弱旧断言。
- 数据库损坏时管理界面显示“记忆数据库暂不可用；原文件已保留”，聊天仍完成；数据库独占锁期间 Qt timer 能处理、请求后台超时回退。
- CJK 字体仅在云工具目录安装，不加入项目依赖或发布物。设置与管理页真实渲染到 [screenshots/companion-memory](screenshots/companion-memory)，四种 light/dark × 720/1100 宽度；长文案换行、按钮可达。截图仅含合成示例。
- 原 `scripts/capture_settings_pages.py` 亦完成 720 宽度全域捕获；新增捕获命令：`python scripts/capture_companion_memory.py <destination> --width 720 [--dark]`。Cloud 为 CJK 加 `FONTCONFIG_FILE=/workspace/.sysdeps/fonts/fonts.conf`。无可用 macOS/Cocoa，未提供伪装成 Cocoa 的截图。

## 六、测试与验证

所有 Python 命令在仓库根目录，先 `source /workspace/.onboarding/dsh-pet-env.sh`，设置 offscreen、可写 XDG data/cache、null keyring、已补齐的 PipeWire 客户端配置。测试没有真实 API Key 或收费请求。

| 验证 | 命令 | 真实结果 |
| --- | --- | --- |
| 本次原聊天基线 | `python -m pytest -q tests/test_chat_service.py tests/test_chat_subsystem.py tests/test_chat_shared_behavior.py tests/test_session_store_async.py` | 178 passed / 1 skipped，14.43s，退出 0 |
| 本次原主套件基线 | 以下 CI 主命令，修改原文件前执行 | 4213 passed / 37 skipped，251.89s，退出 0 |
| 最终记忆/线程聚焦 | `python -m pytest -q tests/test_companion_memory.py tests/test_companion_chat.py tests/test_companion_memory_ui.py tests/test_chat_service.py` | 45 passed，3.98s，退出 0 |
| 5 个 CPU 压力进程下三轮聚焦 | 同一聚焦命令，与 5 个 bounded CPU hog 进程并行，finally 停止 hog | 45 passed × 3；退出码均 0，命令耗时 5.87/4.89/5.01s |
| 原聊天/配置/附件/架构/会话相关回归 | 相关聚焦命令见下 | 253 passed / 1 skipped，16.28s（此前轮次）；最终主套件也包含这些项 |
| WebM 隔离族 | `python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py` | 41 passed，25.82s，退出 0 |
| 低优预热隔离族 | `python -m pytest -q tests/test_low_priority_warm_interaction_yield.py` | 27 passed，31.43s，退出 0 |
| 最终 CI 主套件 | 下述命令 | 4254 passed / 37 skipped，21 warnings，266.20s，退出 0 |
| Ruff | `ruff check pet/ tests/ scripts/benchmark_companion_memory.py scripts/capture_companion_memory.py` | All checks passed，退出 0 |
| 编译 | `python -m compileall -q pet packaging scripts` | 退出 0 |
| 差异空白检查 | `git diff --check` | 退出 0 |
| Bridge | CI 七文件 `node --test ...` + `node integrations/dsh-pet-bridge/verify_import.mjs` | 34 pass / 0 fail，hermetic smoke OK，退出 0 |

完整 pytest 按仓库 CI 分成主套件与 4 个隔离文件，**没有关闭记忆相关断言或丢掉隔离族**；不是零测试检查。最终主命令：

```bash
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
```

相关聚焦命令（253/1 轮次）：

```bash
python -m pytest -q tests/test_companion_chat.py tests/test_companion_memory.py tests/test_companion_memory_ui.py tests/test_chat_service.py tests/test_chat_subsystem.py tests/test_chat_shared_behavior.py tests/test_chat_attachments.py tests/test_session_store_async.py tests/test_config_schema.py tests/test_architecture.py
```

红→绿证据：未实现时模块导入失败；随后 Prompt/config 缺失 2 failed；授权保存失败会让在途写回的回归 1 failed；空引用缺防猜测提示 1 failed；手工去重丢主题回归 1 failed。对应行为补全后最终聚焦全通过。中途发现后两项时没有沿用旧完整结果，取消并重新启动最终完整验证。旧冒烟脚本失败与 Windows 专属 skips 单独记录。21 warnings 中包含既有 `agent-monitor-dsh` 对已删除 Qt signal 发射的线程警告；P0 原基线也记录同一堆栈，本阶段未修改或屏蔽 `agent_link.py`。其他主要为上游 Qt deprecated API 警告。

## 七、Windows 10 人工验收（全部 NOT TESTED）

1. Win10 22H2 x64、普通用户、Python 3.11，核对 Qt/PySide6 官方支持矩阵与实际安装版本；按任务书/ONEDIR_PACKAGING 准备 Chat WebM 开发环境。当前 Linux 的 Qt 版本不等于已验证 Win10 发布锁定。
2. 删除自动化用的 `QT_QPA_PLATFORM=offscreen`，运行 `python -m pet`。检查透明背景、动画、点击与拖动、文件投喂、气泡、托盘、角色切换和现有设置均正常。
3. AI 与对话中两项记忆默认关闭。开启“启用长期记忆”，用原官方 UI 配置 DeepSeek；输入“请记住我喜欢蓝色”，管理页出现条目。重启程序、新会话问颜色，模型得到该记录。
4. 管理页编辑为绿色，重启再问；删除后在新会话问不得继续注入蓝/绿记录。历史会话里的原句仍存在，应另行清理。备份只存本地，记忆删除不删除备份。
5. 关闭自动提取，普通“我喜欢蓝色”不保存；开启后保存。否定/改变偏好只保留当前同主题事实；问句、推测、密码/病史不保存。
6. 长回复期间删除/关闭记忆，在途旧结果不得写回。保存失败提示后修复目录权限并重试保存。长请求、401/429/超时只影响聊天，不卡动画。
7. 程序关闭后复制合成损坏库/模拟文件锁，重新运行应普通聊天回退，管理显示可操作错误，原文件未重置。恢复前退出所有进程，使用 SQLite 一致备份恢复，不复制活跃 db。
8. 100%/125%/150% DPI，720/1100 窗宽、明暗、中文长文案、Tab 焦点、键盘按钮检查。多角色新会话共享同用户目录记忆，其他 Windows 账户不可读取。
9. 由 Win10 执行 `scripts/build_onedir.ps1 -Variant webm-chat`，在无 Python 的新账户启动；本次未构建或分发安装包。

## 八、已知限制、回滚与下一阶段

- 本地规则提取和字符相关性检索，复杂自然语言、未识别属性及更细的矛盾需手工纠正；没有泛化 LLM 抽取或向量索引。模型遵守“不要推测/引用不是指令”的实际表现仍需有凭据的 Win10 验收，不声称可对外部模型作绝对保证。
- SQLite 未加密，依赖 OS 账户目录权限；删除不追溯已发送 API、已有 JSON 历史或备份。500 条上限会淘汰旧条目，重要记录可本地备份。
- 并发事务采用保守 revision：人工修改或另一个已完成提取更改版本时，丢弃当前旧候选，不猜测合并；管理页显示真实库状态。
- 回滚分支提交不会自动删除用户库；两个授权默认 false，旧代码忽略新配置字段。不要删用户文件或把 db 放进 Git。
- P2–P5 **NOT IMPLEMENTED**。P1 审查后，再按任务书单独开展 P2 主动问候/提醒/频控；不在本次加入摸头、智能投喂反馈、主动 TTS 或截屏。先完成上述 Win10/真实 API/P1 人工验收更有助于确定发布边界。
