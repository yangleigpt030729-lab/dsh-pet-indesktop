# DeepSeek 大肥鱼 AI 陪伴增强版 — Codex / Work 开发任务书

## 2026-10-13 用户确认的最终范围（优先于下方原候选方案）

本轮授权连续完成 P2-C、频控范围、P3、P4、P5，最后统一 Windows 验收。最终实现复用原 TodoStore/面板（JSON v2可靠投递），不建第二待办库/自然语言日程；普通主动范围1～9999条/天、1～99分钟，默认10/30；旧0或>99保留原数并停用等待明确确认。头部单击采用可见核心、模糊处身体优先，无长按或抚摸；身体点击和拖拽保留。P3/P4复用ChatService独立瞬时通路，不串写手动会话/记忆，默认关闭；投喂只stat类别/大小统计，原解读独立授权。所有设置在原ModernSettingsDialog中唯一归属；主动识屏活动记录清除不涉及长期SQLite。Windows干净Chat onedir流程已准备，原生EXE NOT BUILT、真实DeepSeek NOT TESTED。详细真实验证见[完整交付报告](docs/PR-REPORT-COMPANION-COMPLETE-2026-10-13.md)与[最终验收指南](docs/WINDOWS10-COMPANION-ACCEPTANCE.md)。下方早期候选架构/头部优先/原固定上限按本节修正，不再代表当前授权或实现。


> 项目：[`MerZlin/dsh-pet-indesktop`](https://github.com/MerZlin/dsh-pet-indesktop)  
> 目标平台：**Windows 10 22H2 x64**（最低兼容性边界须按 Qt/PySide6 依赖核实；目标不是 Windows 11）  
> 编制日期：2026-10-12  
> 文档状态：**开发规格与执行计划，不代表功能已经实现**  
> 基础仓库：https://github.com/MerZlin/dsh-pet-indesktop  
> 开发方式：在个人 Fork 的独立分支分阶段实现，绝不直接更改上游 `main`。

## 0. 给 Codex / ChatGPT Work 的执行指令（先读）

你是一名熟悉 Python 3.11、PySide6、Qt 事件循环、Windows 桌面程序和 SQLite 的工程师。**请在真实仓库中完成本规格，而不是只输出建议或伪代码。**

1. 首先克隆/打开仓库，阅读根目录 `AGENTS.md`、`CONTEXT.md`、`docs/INDEX.md`、`docs/SETTINGS-CHANGE-GATES.md`、`docs/DEV-HANDOVER.md`、`docs/PR-REPORT-TEMPLATE.md`，以及受影响领域的文档；对照当前 `main` 核实本文提到的路径、类和接口，记录 HEAD commit SHA。仓库可能持续更新，**本文件中的候选新模块和接口仅为建议，不应未经检查盲写**。
2. 检查工作区状态并保护已有修改：不要覆盖脏工作区，不要重置他人代码，不要提交密钥、用户聊天记录、构建产物或数据库。读 LICENSE、第三方素材声明。使用 Git 分支（例如 `feature/win10-ai-companion`）。
3. 建立基础测试与打包基线，**测试先行**，每阶段完成才进入下一阶段。Qt 主线程只能触碰 Qt UI；后台线程做网络/SQLite 处理，通过 queued signals 回 UI。保持 UI 响应性、避免 `QThread: Destroyed while running`。
4. 新功能应是**可关闭且默认隐私保护**的增强；不破坏原聊天、原吃文件动画、原拖拽、原待办提醒、多窗/overlay 架构和系统托盘。不要在 `pet/window.py` 堆砌大段逻辑，遵守原项目的架构测试和行数预算。
5. 最终提交可运行源码、自动化测试、迁移说明、Windows 10 x64 实机测试步骤、打包办法。每个 PR 产出 `docs/PR-REPORT-<主题>-<日期>.md`，包含逐文件变更及 `git diff --numstat`、性能数字与真实运行证据，并在 `docs/INDEX.md` 登记，遵守上游 `AGENTS.md` 的最新规则。
6. 如果当前执行环境**不是 Windows 10**，只能完成跨平台测试和静态检查；Win10 透明窗口、拖入文件、鼠标区域、打包启动等必须标为 **未实机验证**，交付可重现的人工验收清单，不得虚报通过。
7. 优先实现 P0/P1/P2（基础回归、长期记忆、主动气泡），然后 P3/P4（摸头/点击、文件反馈），最后 P5（配置界面/发布）。如时间或工具限制，按阶段提交可工作的最小增量，明示剩余工作。

---

## 1. 用户需求：精确定义

在原版 DeepSeek 大肥鱼桌宠上添加以下能力：

- **主动 AI 问候**：上午/下午/晚上适时主动打招呼、偶尔提及以前聊过的喜好或正在做的事情，必须是模型根据当前上下文生成，不能单纯随机抽同一批固定台词。
- **生活提醒**：喝水、久坐休息；用户明确添加的待办/日程提醒。对于未获授权的日程不得凭空臆测。
- **长期记忆**：例如用户称呼、偏好、明确要求记住的事实、需要后续关注的重要事件；本地 SQLite 持久化，退出重启后依旧存在；支持查看、纠错和删除，不把短期上下文冒充长期记忆。
- **防重复**：不仅避免字面重复，还避免用不同措辞反复说同一个提醒；利用类别频控、近期消息历史、相似性拒绝、生成重试（有限次数）实现。
- **主动文字气泡**：**不做 TTS/朗读、不自动截屏**。不干扰游戏、会议、全屏窗口或正在进行的输入，必要时延后普通问候。
- **文件投喂增强**：复用现成拖放、吃文件动作与统计；投喂图片、代码、音频、压缩包、目录等时按**扩展名、数量、体积**产生合理有趣、变化的 AI 反馈。默认**不得读取、上传**文件内容、文件全路径或私人文件名；原版“询问是否解读文件”功能继续独立工作，必须经用户确认。
- **鼠标互动**：摸头（点头部）与普通点击（点身体）有不同动画/气泡反应；支持短时间连点合并与冷却；保留原版拖拽、Q 弹和聊天交互。
- **AI 聊天融合**：主动话语和用户聊天接入相同会话/记忆链，尽量复用现有 ChatService；不能让主动任务打断用户正在进行的流式聊天。
- **只针对 Windows 10 x64** 提供安装和验收说明，优先兼容 Win10 22H2；最低版本需以已锁定 Qt/PySide6 构建为准。

### 1.1 用户最终配置（必须照此落地）

```json
{
  "proactive_chat": {
    "enabled": true,
    "greetings": true,
    "break_reminders": true,
    "water_reminders": true,
    "scheduled_reminders": true,
    "use_memory": true,
    "daily_limit": 10,
    "min_interval_minutes": 30,
    "quiet_hours": null,
    "avoid_semantic_repeats": true
  }
}
```

**语义边界**：`daily_limit: 10`、`min_interval_minutes: 30` 约束**普通主动话语/非关键生活提醒**。用户主动触发的聊天、鼠标点击、文件投喂回复不计入该配额；用户明确设置的到期待办提醒不得因普通配额被静默丢弃，应单独通知/排队/记录。`quiet_hours: null` 表示不设固定静默时间，并不表示必须每 30 分钟讲话。所有自动发言仍需考虑状态、冷却和上下文。

### 1.2 明确不做

- 不做语音识别、TTS、语音报时、复杂情感/亲密度数值、不另造桌宠物理动画引擎。
- 不引入 AstrBot、QQ、NapCat，不依赖 Ollama 或本地大模型。
- 不默认读取图片像素、代码正文、文档内容、音频内容和屏幕截图。
- 不实现跨设备云端记忆同步；不默认将本地 SQLite 上传至云端。
- 不让 AI 自行执行任意系统命令、打开链接、删除文件或修改日程；模型只返回文本建议，任何工具动作须专门白名单与确认。

---

## 2. 源码入口与核查清单（截至 2026-10-12 的公开仓库）

以下是**需要先确认的接入点**，非对未来版本的硬编码保证：

| 已知/候选文件 | 当前职责 / 开发动作 |
| --- | --- |
| `AGENTS.md` | 首先阅读，Qt 线程规则、测试门禁、PR 证据要求 |
| `pet/__main__.py` | `python -m pet` 入口；确认 Chat 版与普通版如何启动 |
| `pet/chat/prompt.py` | `PromptBuilder.build_messages(...)` 整合角色 prompt、历史聊天；扩展记忆检索注入的候选位置 |
| `pet/chat/service.py` | `ChatService`、模型流式处理、异步/取消；复用现有调用路径，但避免主动请求与人工请求竞争 |
| `pet/chat/session_store.py` | 对话历史持久化，不能用它替代长期记忆数据库 |
| `pet/file_eater.py` | `FileEaterDropHandler.eat_paths(paths)` 已统计、调用吃动画/气泡、保留原文件；新增结构化投喂事件和响应扩展口 |
| `pet/proactive.py` | 现有主动**识屏**机制（不是纯主动聊天）；参考其频控/暂停/信号，不要让本任务开启截图 |
| `pet/catalog.py` | `character_head_box()` / manifest `head_box`，用于摸头点击命中区；需核实坐标变换 |
| `pet/window.py` / overlay 相关文件 | 窗口与渲染；仅通过小型适配层挂接，避免破坏单窗/多窗架构 |
| `docs/SETTINGS-CHANGE-GATES.md` | 新持久化配置的发布门禁 |
| `docs/ONEDIR_PACKAGING.md`, `scripts/build_onedir.ps1` | 需要打包时再阅读/使用，不重新发明构建系统 |

源码核查时，输出 `docs/AI-COMPANION-INTEGRATION-NOTES.md`，写明真正的事件发送/接收关系、当前类名、角色头部坐标、气泡 show 接口、原有待办提醒路由、聊天会话身份和数据目录；如与此文不同，依**实际源码**修正文档。

**架构约束特别注意：** 仓库的 `AGENTS.md` 描述了 `PetWindow` legacy/capture 与 `OverlayShell`/`PetSprite` 等渲染拓扑以及进程级共享模块。新调度器应是**每用户配置/会话身份唯一一个**，而非每只宠物或每个窗口各跑一个循环导致双倍提醒；气泡表现层使用可切换的适配器。避免强行实例化已经废弃的多进程机制。

---

## 3. Windows 10 本地开发环境：逐条操作

### 3.1 准备

1. 确认 Windows 10 **x64 / 建议 22H2**，`winver` 查看版本，PowerShell 中 `python --version` / `py --list` 查看 Python。
2. 安装 **Python 3.11 x64**（和上游 CI 一致）、Git for Windows、VS Code；如需 Codex 用其编辑器扩展或终端 CLI。
3. 如已有正式版，先完全退出大肥鱼，并备份 `%APPDATA%\dsh-pet-standalone*` 下**实际存在**的配置/会话目录。不要假设所有变体共用一个目录。
4. 以官方 README 和 LICENSE 为准选定源码基线；不要安装来源不明的预编译 EXE。Windows 10 的常规支持已结束，建议更新补丁并降低未知程序权限。

### 3.2 用 PowerShell 克隆、安装、测试

```powershell
# 在普通用户目录下操作，不必用管理员权限
cd "$HOME\Documents"
git clone https://github.com/MerZlin/dsh-pet-indesktop.git
cd dsh-pet-indesktop
git status --short
git rev-parse HEAD

git switch -c feature/win10-ai-companion
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 基线静态检查和测试
.\.venv\Scripts\python.exe -m ruff check .
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall pet packaging scripts
Remove-Item Env:QT_QPA_PLATFORM

# 真实桌宠显示（在已登录的 Windows 10 图形桌面上进行）
.\.venv\Scripts\python.exe -m pet
```

- 如果 `ruff` 或其他 CLI 不可用，检查 `requirements.txt` / `pyproject.toml` 与仓库 CI 命令再修正；不要擅自升级所有依赖。
- `QT_QPA_PLATFORM=offscreen` 只用于自动测试，**人工图形验收必须删掉**。
- 如系统限制 PowerShell 执行 `.ps1`，上面全部直接调用 `.venv\Scripts\python.exe`，不需要修改执行策略。
- 不要将本项目的 API Key 放进源码仓库。优先复用上游 keyring / 凭据配置。

### 3.3 锁定兼容性

在仓库当前依赖清单基础上，以 Windows 10 实机验证过的版本制定锁定策略。Qt for Python 官方支持 Windows 10 1809+ x64，但将来 Qt 主版本可能结束 Win10 支持；不要任意更新到未验证的 Qt/PySide6。记录 Python、PySide6、Qt、PyInstaller、FFmpeg 相关组件的确切版本，确保构建与测试一致。

---

## 4. 总体模块设计

```text
用户聊天 ──────────────────────────────┐
摸头/点击事件 ────┐                    │
文件投喂事件 ────┼──> InteractionRouter ├──> AI Request Coordinator
                  │                    │        │
时间/日程/空闲 ─> ProactiveScheduler ───┘        ▼
                                      MemoryRetriever + PromptBuilder
                                                 │
                                                 ▼
                                          ChatService / DeepSeek
                                                 │
                                                 ▼
                                      BubblePresenter (Qt 主线程)
                                                 │
                           ┌─────────────────────┴──────────────────┐
                           ▼                                        ▼
                   SessionStore / UtteranceLog                 MemoryExtractor
                                                                    │
                                                                    ▼
                                                              SQLite MemoryDB
```

推荐把纯业务逻辑放在可单元测试的新模块，名称可按原项目习惯微调：

```text
pet/companion/
    __init__.py
    models.py                 # 纯数据类型 / 枚举 / 事件
    config.py                 # 配置校验、默认值与迁移
    scheduler.py              # 触发器：问候、喝水、久坐、到期提醒
    limiter.py                # 每日上限、最短间隔、类别去重、跨重启状态
    repetition.py             # 字面 + 近似语义去重
    memory_store.py           # SQLite 初始化、迁移、增删改查
    memory_extract.py         # DeepSeek 结构化记忆提取（显式/低频）
    memory_retrieve.py        # 按相关性选取记忆、长度限制
    prompts.py                # 主动话语 / 投喂 / 摸头提示词
    feed_metadata.py          # 严格过滤的文件元信息
    coordinator.py            # 单飞任务、优先级、异步与 Qt 信号桥
    presenter.py              # BubblePresenter 接口与现有窗口适配
    interaction.py            # 摸头/点击分类和连点防抖
    reminders.py              # 明确设定待办提醒的衔接与去重

tests/test_companion_config.py
      test_companion_scheduler.py
      test_companion_limiter.py
      test_companion_repetition.py
      test_companion_memory.py
      test_companion_feed.py
      test_companion_interaction.py
      test_companion_integration.py
```

不要一次性建空文件；每阶段只创建已经实现且有测试的模块。不要为实现同一目标产生第二套 ChatService、第二套会话 ID、第二套系统托盘。

---

## 5. 数据模型与持久化规格

### 5.1 SQLite 数据库

使用 `cfg.dir` 所属的数据目录下 `companion_memory.sqlite3`（用实际 Config API 确认），不是源码目录，也不能放在 PyInstaller 的临时目录。SQLite 连接限定在拥有它的线程中，使用短事务、参数化 SQL、合理 busy timeout；`WAL` 模式应在 Win10 文件系统实测后启用。定期备份/恢复可通过 SQLite backup API 实现，不要复制正在写入的 db 文件造成损坏。

建议表结构（由 Codex 细化并迁移）：

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS utterances (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    category TEXT NOT NULL,
    text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    emitted_at TEXT NOT NULL,
    event_key TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    title TEXT NOT NULL,
    due_at TEXT NOT NULL,
    timezone TEXT NOT NULL,
    recurrence TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    last_fired_at TEXT,
    user_created INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS scheduler_state (
    state_key TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
);
```

**身份策略**：个人桌宠默认只为本地使用者建立 `subject_id=local-owner`，多窗/多角色需要确认是否共享记忆的策略；不可无意把其他 Windows 用户或角色的内容混在一起。若上游已有 user/session ID，应优先沿用。

### 5.2 记忆机制

- **写入**：用户说“记住我喜欢蓝色”这类明确表达时优先写入；可选用 AI 从日常对话低频提取“长期可用的非敏感事实”，但**默认关闭隐式自动提取或先提供明确授权**。不自动存储口令、支付信息、健康病史等敏感信息。
- **去重/冲突**：同一 subject 同一主题的旧事实和新事实冲突时，更新或请求澄清；“我不再喜欢 X”要能覆盖“我喜欢 X”。
- **读取**：每次普通聊天 / 主动问候之前读取少量高度相关记忆，例如最多 5 条、总字符上限约 600（可配置）；只将选中内容发送 DeepSeek，不能无限灌入历史数据库。
- **删除**：设置中可查看、编辑、删除单条以及全部记忆；删除后新聊天不能再次引用，历史会话如果另有保存，应向用户说明那是独立数据源。
- **AI 生成**：记忆内容来自不可信用户输入，不允许记忆注入覆盖 system/developer 安全规则；注入时作为**引用的数据**而非指令。
- **故障**：数据库损坏或网络不可达时仍能本地显示桌宠与旧聊天；记忆模块故障只停记忆，不崩溃整只鱼。

---

## 6. 主动聊天与提醒：详细行为

### 6.1 触发器（独立于原主动识屏）

1. **首次打开的问候**：当天该会话/用户首次启动并有合适窗口状态时，可选生成一次。不要开机一分钟内连续发声。
2. **时段问候**：上午、下午、晚上可按自然时段候选，但同一时段一天最多 1 次；不要把日历时段当作每小时必须发言的命令。
3. **久坐**：以用户活动/前台会话的可用指标为准，避免将电脑睡眠时间计入“连续工作”。若无法可靠测量，显示提示“久坐判断可能不准确”，允许关闭。
4. **喝水**：使用周期性候选提醒，用户忽略/稍后提醒时降低频率；同一类型拥有独立较长冷却期（建议 2 小时，按用户设置）。
5. **明确日程**：从用户在桌宠待办系统设置的已确认提醒同步，**绝不默认扫描私有日历文件**。去重同一提醒 ID，超时恢复可按 grace period 补发一次，不重复弹十次。
6. **基于记忆的关心**：仅在有近期有效记忆时可能触发；禁止编造“昨天你说过”这种未保存的事实。

### 6.2 调度优先级

`用户直接互动 > 明确设定的到期待办提醒 > 正在进行的聊天 > 普通喝水/休息提醒 > AI 随机问候`。

- 普通事件需要满足：`enabled`、没有正在进行的 ChatService 流请求、没有全屏/重要场景、没有正在输入、达到 30 分钟全局冷却、当日次数 < 10、类别冷却满足。
- 明确到期提醒**不计入普通主动次数**，但需尊重用户手动“稍后提醒/已完成”、同一提醒重复抑制和窗口可用性。如果无法显示，应排队并在恢复后标注延期；不要悄悄吞掉。
- `quiet_hours=null` 代表全天候有资格触发；但是睡眠、锁屏、全屏、用户忙碌、连续忽略、离开座位等仍可延后普通信息。
- 跨越午夜按本地时区重置每日计数；防止时间回拨、夏令时和系统休眠造成重复提醒，优先存储 UTC 事件时间 + 本地日期键。
- **不必每 30 分钟调用模型**：先经过纯本地触发器筛选，真正需要时才生成，降低 token 消耗。

### 6.3 AI 文本生成（仅文字气泡）

为每种触发设计不同意图（greeting, water, break, scheduled, memory_followup, feed, head_pat, body_click），作为模型输入传入**事件参数**和相关记忆：

```json
{
  "intent": "break",
  "time_local": "2026-10-12T15:10:00+08:00",
  "cause": "active_session_90min",
  "recent_utterances": ["上一句已发的话"],
  "remembered_facts": ["用户更喜欢简短问候"],
  "constraints": {"max_chinese_chars": 65, "no_speech": true}
}
```

系统提示要求：**一句到两句、最多约 65 字、不用每句都喊“主人”、不编造亲历事实、无权限时不假装看到用户屏幕、语气温柔活泼、有轻微随机性、不能强行卖萌；文件投喂不声称看过文件内容。**

防重复分两层：

- **事件级**：`water/break/greeting` 的独立冷却，尤其不能多次变换说法重复催喝水；同一 scheduled reminder 用持久化 `event_key` 幂等。
- **文本级**：保留最近约 30 条自动发言的归一化文本，检查完全重复、字符 3-gram Jaccard 或 `difflib.SequenceMatcher` 相似性（例如相似度 >0.80 作为候选），加上事件类型的最近话题重复检查；最多重试生成 1 次，依然过近则跳过。阈值需用中文单元测试调优，避免不同但有用的句子被误杀。

原版气泡接口可能接受展示时长（如 `show_bubble(text, duration_ms=...)`），但**不得从非 Qt 线程直接调用**。发言成功显示后再写入发送日志与 quota；AI 请求失败或被合并丢弃不能计入发送成功。气泡需要可关闭/鼠标忽略策略正确、不遮住用户输入。

### 6.4 定时事项真实可靠性

提醒不应只存在 LLM 文本里：必须存一条有 `due_at`、`timezone`、状态的结构化 Reminder；如果用户用自然语言说“明天下午两点提醒我提交报告”，解析后应**向用户确认解析后的日期时间**再入库，避免无意建错事项。调用系统本地时间与时区；不得假设系统时区等于用户常驻时区。

---

## 7. 摸头、点击、文件投喂

### 7.1 摸头与身体点击

- 使用 `pet/catalog.py::character_head_box()` 及角色 manifest 提供的头部框；头部框在**角色素材原像素坐标**，需根据当前缩放、镜像、裁切、帧 offset、DPI 和 PetWindow/Overlay 渲染坐标映射到鼠标局部坐标。
- `MousePress` 和 `MouseRelease` 区分：按下到释放位移 > 一定阈值时认定为拖动，不触发摸头；消除快速连点冒泡、按住/拖拽误判。
- 头部命中为 `head_pat`，否则按原点击为 `body_click`；尽量复用原有 Q 弹/点击动画，摸头动画如果素材库没有对应 clip 就使用平稳回退，不要添加虚构资源名称。
- 两类互动可用短语池瞬时反馈，**AI 请求异步低优先级**；建议最短 5～10 秒同类冷却，连续点击合并，防止用鼠标点击耗尽 API。
- 所有角色都要回退处理 `head_box` 不存在、透明区域命中、翻转或缩放超界等情况。至少测试单宠/多宠、常见 DPI 100%/125%/150%。

### 7.2 文件投喂反馈

在 `FileEaterDropHandler.eat_paths` 后添加一个可选 `FeedEvent` 回调/信号，不改变原文件统计、吃动画以及原可选“解读文件”权限流程。禁止阻塞该 UI 事件处理程序。

建议 `FeedEvent` 只携带以下**允许上传**的最小信息（默认不上传真实文件名和路径）：

```json
{
  "category": "code",
  "extension_group": [".py", ".js"],
  "items": 2,
  "folders": 0,
  "total_size_band": "small",
  "feed_sequence": 17
}
```

扩展名示例：图片 `.png/.jpg/.webp`、代码 `.py/.js/.ts`、文档 `.md/.txt/.pdf`、音频 `.mp3/.wav`、压缩 `.zip/.7z`、目录 `folder`、其他 `unknown`。不要遍历巨大目录获取所有扩展名；已有统计如果可能深遍历，沿用上游规则并检查大目录 UI 性能。

反馈示例（用作人格风格提示，不是最终固定台词）：

- 图片：“这口像彩色糖果，今天吃得亮晶晶的！”
- 代码：“咔嚓，好多括号，吃出一点 Bug 味！”
- 音频：“哇，嚼起来像在打拍子！”
- 压缩：“好硬的一大包，得慢慢消化。”
- 文件夹：“这不是零食，是一整盒便当呀！”

**重要**：AI 只能根据分类“角色扮演”做反馈，绝不能声称已知道照片里的人、代码中错误、文档观点、音乐曲风；除非用户另外授权使用原文件解读流程。AI 失败时随机挑本地短语作为 fallback，让吃动画/气泡仍正常且延迟低。

---

## 8. 配置/可视化设置

用户要求的 JSON 属于目标新配置，**原版不能直接粘贴后就生效**。先遵守 `docs/SETTINGS-CHANGE-GATES.md` 完成配置默认值、读取、迁移、验证、UI 绑定、重置和测试。

设置页（可在现有设置面板增加“小鱼陪伴”分区）包含：

- 主动聊天总开关
- 时段问候、喝水、休息、到期待办提醒开关
- 每天最多 10 条普通消息（范围 0~20，0 表示普通消息禁用）
- 普通消息最短间隔 30 分钟（最小值正数，建议 15~180）
- 免打扰：默认“不设置” (`null`)，可选按时间区间配置
- 长期记忆读取开关、自动记忆提取授权开关（后者默认关闭）
- 最近主动发言记录、清空历史、防重复开关
- 长期记忆“查看/编辑/删除/导出”
- 启用/关闭摸头反馈、文件 AI 反馈、互动短语降级
- **静音文字模式**：关闭本增强功能主动触发的 TTS；检查上游已有 `self_talk_speak_enabled` 及其他语音选项，避免误关闭用户已有其他功能之外的系统行为。

性能、安全和可用性：设置变更立即生效或清晰提示需要重启；多窗口配置一致；关闭模块后不得继续后台计时/发起新网络请求；用户删除数据后不能被异步任务重新写回。

---

## 9. 分阶段执行（按小 PR / 小提交推进）

### P0 — 基线审计与部署（必须先过）

- [ ] 克隆/检查 HEAD，读 `AGENTS.md`、上游迁移/设置/网络/打包文档，确认 LICENSE 是 MIT，并检查角色素材第三方许可。
- [ ] 查实际代码：ChatService、PromptBuilder、Config、SessionStore、Bubble 接口、窗口多拓扑、文件投喂事件、待办系统、`head_box`。
- [ ] 把实际集成点写进 `docs/AI-COMPANION-INTEGRATION-NOTES.md`，包含是否需要改 API、模块生命周期图。
- [ ] Windows 10 Python 3.11 创建 venv、跑 ruff/pytest/compileall 基线，记录初始测试失败和原因，不在新增代码里兜底掩盖。
- [ ] 增加 feature flag（初始可关闭）和严格配置解析测试，遵守配置变更门禁。

**完成条件**：未打开增强时原版功能完全无变化，基线测试无新增失败。

### P1 — SQLite 长期记忆（第一个可交付成果）

- [ ] 编写 `MemoryStore` 独立测试：初始化、CRUD、删除、迁移、跨重启、并发隔离、损坏回退、记忆冲突。
- [ ] SQLite schema migration 和备份；记忆查看/删除先可用最简单的设置界面或菜单。
- [ ] 把“明确记住”写入路径接入真实用户 Chat 完成事件；待用户确认后再尝试自动提取。
- [ ] 在 `PromptBuilder` 的上游调用逻辑中注入检索后的**少量引用数据**；避免改变已有 `build_messages` 调用协议导致所有测试失败（可新增 optional param 并扩展测试，具体以实际源为准）。
- [ ] 测试：关闭程序重新启动、换新会话后回忆某个喜欢的颜色；删除该条记忆后不再使用。

**完成条件**：真实跨重启的长期记忆有效；旧聊天、历史压缩、角色人设无回归。

### P2 — 主动消息和提醒调度（第二个可交付成果）

- [ ] TDD 实现 `limiter.py`：30 分钟、10 条/本地日、跨重启、午夜切换、睡眠唤醒、时间回拨、不同提醒类别冷却。
- [ ] TDD 实现 `scheduler.py`：问候/喝水/久坐/日程事件来源，进入 full-screen/typing/busy 状态时延后普通消息。
- [ ] 实现 `repetition.py` 与中文相似句测试。限制 AI 重试最多 1 次，超预算/超时跳过。
- [ ] 模型调用只用原有 ChatProvider/ChatService 的可信路径或抽象出可复用 provider API，不破坏手动流式会话状态；采用后台任务单飞、优先级、取消、Qt queued signal。
- [ ] 把主动话语渲染到原版气泡并保存适当聊天历史；禁止自动开启屏幕捕获。
- [ ] 用户设定的 due reminder 优先级独立于 10 条普通消息、准确一次提醒，重启/暂停恢复幂等。

**完成条件**：AI 生成多样问候；同主题不会短时反复出现；不在用户手打字/全屏时抢占；提醒不漏/不连发。

### P3 — 摸头与普通点击（第三个可交付成果）

- [ ] 研究当前鼠标事件与动画，不改已有拖动触发逻辑。
- [ ] `head_box` 坐标转换，单窗/overlay 多角色兼容；跨 DPI/缩放/镜像测试。
- [ ] 摸头与身体点击分流，不拥有独立素材则回退原点击动画；AI 回应和可即时本地短语之间做合理优先级。
- [ ] 防抖和 5~10 秒同类 cooldown，禁止连点造成网络风暴。

**完成条件**：点头和点身体出现可识别的不同反馈，拖动不误触发；原点击动画不退化。

### P4 — 文件投喂元信息反馈（第四个可交付成果）

- [ ] `FeedEvent` 的纯函数分类与隐私过滤测试，拒绝路径/完整文件名/正文进入 API payload。
- [ ] 在 `eat_paths` 接上**非阻塞**异步 AI 反馈，吃动画即时触发；原 `interpret_offer` 明确授权机制保留。
- [ ] 与最近反馈日志联合去重，AI 超时回落本地短语。
- [ ] 测试大目录、多个文件、无法读取的路径、中文/emoji 文件名、文件夹快捷方式/符号链接；确保源文件字节不被改写。

**完成条件**：不同文件类型反馈差异明显，响应多样；没有默认内容泄露或卡 UI。

### P5 — Windows 10 打包/文档/长测（发布阶段）

- [ ] 设置 UI 与配置迁移、开关、长期记忆管理页。
- [ ] 复核原有语音与主动识屏设置，文本模式不触发朗读或未授权截屏。
- [ ] Windows 10 x64 在 100%/125%/150% 缩放下实际运行；主屏/副屏、睡眠唤醒、任务栏自动隐藏、DPI 切换、Win10 通知、全屏游戏、Windows 账户注销。
- [ ] `ruff`、全量 `pytest`、`compileall`、架构预算测试和受影响 Qt 时序测试。
- [ ] 用上游 `docs/ONEDIR_PACKAGING.md` 和 `scripts/build_onedir.ps1` 构建 **Chat WebM** 变体；不能假设直接 `pyinstaller pet.py` 适配原版资源。
- [ ] 测试无 Python 环境的新 Win10 x64 账户能启动发行包，数据可迁移、卸载不删除用户未确认的数据。
- [ ] 输出包含真实数字的性能报告，完整列明改动文件、问题/限制与人工实测证据，并创建 PR。

**完成条件**：可交付 Win10 Chat 版包，配有安装与回退说明，实测记录可复核。

---

## 10. 自动化验收矩阵（必须新增/覆盖）

| 编号 | 验收 | 断言/方法 |
| --- | --- | --- |
| T01 | 配置读取 | 用户给定 JSON 正确生效，`quiet_hours=null` 不自动生成静默时间 |
| T02 | 频控 | 发言 10 次后第 11 条普通消息不显示，明确到期提醒仍可通知 |
| T03 | 最短间隔 | 前一条普通气泡发送后未满 30 分钟，下一条候选不触发 |
| T04 | 事件去重 | 5 分钟内重复收到 drink 事件不重复催；同一提醒 ID 不重复通知 |
| T05 | 相似句去重 | “快喝水呀”和“记得喝口水哦”被判定为提醒同类，不连续输出 |
| T06 | 重启恢复 | 关闭再启动仍知道今日 quota、最近提醒键、长期记忆 |
| T07 | SQLite 删除 | 删除某记忆后新 AI 请求不再收到该记忆内容 |
| T08 | 用户隐私 | 投喂一个含机密文件名的 `.pdf` 时，AI 请求没有文件名/路径/内容 |
| T09 | AI 故障 | DeepSeek 超时、401、429、空文本时显示合适降级；不会卡界面 |
| T10 | 点击分流 | 头部点击触发摸头；身体点击触发普通点击；拖拽不误触发 |
| T11 | 大目录 | 文件夹元信息获取不能造成不可接受 UI 阻塞，原文件未改动 |
| T12 | 对话竞争 | 主动任务与手动聊天并发时先保留用户聊天，不能串写会话 |
| T13 | 窗口生命周期 | 关掉宠物/多窗口变化后计时器停止或迁移，无重复气泡和悬挂线程 |
| T14 | 时间变化 | 跨本地午夜、系统时钟回拨、休眠唤醒不会重复扣 quota 或轰炸消息 |
| T15 | 语音与截屏 | 本增强触发中没有调用 TTS，也没有未授权的屏幕捕获 |
| T16 | 原版回归 | 原聊天、原拖放、吃动画、窗口移动、菜单、待办、角色切换工作正常 |
| T17 | 多窗 | 多只鱼不同时发相同提醒，不发生显示到已销毁窗口 |
| T18 | 迁移 | 老用户数据不丢失，关闭增强模块后原程序正常工作 |

测试中尽量**注入时钟、可控模型假客户端、内存/临时 SQLite**，不要在 CI 里发真实 DeepSeek 请求；Qt GUI 测试在合理的真实 event loop 上使用信号同步，避免固定 `sleep` 赌时序。对网络行为及用户隐私，用断言检查 mock provider 的实际消息体。

---

## 11. Windows 10 真人测试脚本（交付安装包前执行）

### 安装与启动

1. 在 Win10 x64 22H2 机器登录普通用户，先备份原版设置。安装自编译 Chat WebM 安装包或解压便携版。
2. 启动，确认小鱼显示透明背景、动作流畅、任务栏/托盘正常、没有命令行黑框常驻。
3. 在设置中输入 DeepSeek API Key（通过原版官方 UI），连接测试一次；确认 API Key 不会出现在日志/SQLite/打包目录里。
4. 关闭语音朗读、启用增强项；通过设置选择用户配置中的 10 次与 30 分钟。

### 记忆与自然对话

5. 聊天输入“请记住我喜欢蓝色。”；打开记忆管理查看新记录，关闭程序重开后问“我喜欢什么颜色？”；新会话仍能合理答“蓝色”。
6. 删除该记录，再次提问不得引用已经删除的数据。对于无记忆内容应表达不确定，不编造。

### 动画、触摸、投喂

7. 正常单击小鱼身体；点击头部；长按拖动；观察三种行为。放大 DPI 至 125%，再测头部命中。
8. 依次拖 `test.png`、`hello.py`、`sound.mp3`、`data.zip`、一个空目录。吃动画应仍出现，AI 气泡应区别类型。
9. 投喂包含敏感信息的文件（内容中放入人工构造的测试字符串 `DO_NOT_SEND_SECRET_123`）；用 mock 网络或调试代理验证**没有**将文件内容、真实路径和文件名发送给模型。不得把该测试字符串上传到真实服务。

### 主动提醒/稳定性

10. 使用调试时钟/测试模式模拟 30 分钟间隔、10 次每日上限及午夜切换，确认仅普通消息受限。
11. 创建明确的 1 分钟后待办提醒，确认准点到期仅提醒一次；锁屏/睡眠后恢复时不会短时间重复弹 N 次。
12. 全屏打开应用并与大肥鱼聊天，确认不会把全屏画面强制顶出、不会打断流式回复。
13. 连续运行几小时，记录内存（工作集 MB）、CPU%、API 请求次数、平均气泡延迟、UI 卡顿与线程数量；与 P0 基线比较。

### 发布结果证据

保存截图/录屏、环境版本、操作步骤、相关日志（先隐去 API Key、隐私和聊天内容）、自动测试结果、内存数字。无法实测 Win10 时必须标注 `NOT TESTED ON WINDOWS 10`。

---

## 12. 安全/错误处理/费用

- DeepSeek 每次 API 调用可能收费；点击和投喂事件需节流；普通主动发言每天最多 10 次，确保全局异步单飞，模型失败仅有限重试。
- 网络失败不能影响本地宠物动画。API 401/429 不能无限重试；返回可读的非敏感诊断，日志隐藏 token 和私有内容。
- 记忆被注入模型前检查长度、敏感词/授权、来源，数据库不可存硬编码明文密钥；可以给用户提供仅本地使用/关闭记忆的选择。
- SQLite 与聊天历史是两个数据源：删除一个不必然删除另一个，UI 必须说明并提供各自管理选项。
- 不对投喂的源文件执行修改、移动、删除、解压、执行或全文读取；文件夹/快捷方式遍历注意性能及符号链接循环。
- 禁止从 AI 回复中直接执行 Python/shell/系统命令；防 prompt injection。主动事件不得暗中开启麦克风、摄像头、屏幕读取。
- Windows 10 官方安全生命周期风险由用户知悉；程序开发不能声称替代系统安全更新。

---

## 13. 每次 Codex 迭代的交付格式

每个阶段输出以下内容（可落地到 `docs/PR-REPORT-...md`）：

1. **改动摘要**：具体文件、修改内容、必要性、`git diff --numstat`。
2. **命令与结果**：实际执行的 ruff / pytest / compileall / 冒烟测试命令与退出码、失败项。
3. **性能证据**：可重复运行的脚本及真实数字（调用开销、UI 帧暂停、数据库、内存）。
4. **风险和未做完的事**：未实机验证/未打包/兼容性/安全隐患。
5. **下一阶段**：可独立执行的小任务列表，PR/commit SHA。
6. **Windows 10 手工验收步骤**：每一项按操作与预期结果陈述。

任何功能没有完成时写明 `NOT IMPLEMENTED`；没在 Win10 实机执行写明 `NOT TESTED`，不能把设计书或模拟测试当作已完成的 EXE。

---

## 14. 交给 Codex 的第一轮可复制提示词

> 下面整段可以复制到 Codex 的新任务中，也可以直接上传本 Markdown 然后让 Codex 阅读。

```text
请按仓库根目录 DEVELOPMENT_PLAN_WIN10.md 实现 DeepSeek 大肥鱼 AI 陪伴增强版。目标 Windows 10 22H2 x64、Python 3.11、原有 PySide6 桌宠。用户设定：主动问候、喝水/久坐/日程提醒、SQLite 长期记忆、语义防重复、10 条/天普通消息、30 分钟普通发言间隔、全天无固定免打扰、只要文字气泡不要 TTS；保留原版桌面动画/文件投喂，按文件类型等最小元信息生成有变化的反馈，不读取上传文件内容；头部摸头与身体点击分开，已有聊天共享记忆。

第一轮仅执行 P0 + P1，不要一下实现所有功能：
(1) 检查工作区和 AGENTS.md、CONTEXT.md、docs/INDEX.md、SETTINGS-CHANGE-GATES 与受影响代码，确认当前 HEAD；
(2) 运行并记录原仓库测试基线，建立独立分支；
(3) 写源码集成点审计文档；
(4) 先写 memory_store 及相关测试，再实现 SQLite CRUD、迁移、跨重启持久化、删除；
(5) 在现有聊天路径注入经过筛选的少量长期记忆，保留原聊天功能；
(6) 执行相关测试、全量测试、ruff/compileall，产出 AGENTS.md 要求的文件变更、性能和实机报告（未实测则明确说明）。

请直接修改代码和测试，不要只提供建议。若仓库版本或接口与计划不同，以实际源码为准并更新计划。第一轮完成后列出 commit SHA、测试命令和结果、下一轮 P2 的具体任务。不要提交任何私有数据或 API Key。
```

**P1 完成后给 Codex 的下一条消息**：`继续读取 DEVELOPMENT_PLAN_WIN10.md，严格实施 P2，先写调度、限流、去重的测试，再接入真实 UI 气泡。完成后运行全量测试并报告。`  
**P2 完成后**：`继续 P3（摸头/点击），注意 Qt 坐标/DPI/多窗和原拖拽回归。`  
**P3 完成后**：`继续 P4（投喂反馈），要求仅最小元信息上传、原动画即时播放。`  
**P4 完成后**：`继续 P5（配置、Win10 打包、实机验收、PR 报告）。`

---

## 15. 核查来源（开发时应再次以最新仓库为准）

- 主仓库 / README：https://github.com/MerZlin/dsh-pet-indesktop
- 工程指南：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/AGENTS.md
- 设置变更门禁：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/docs/SETTINGS-CHANGE-GATES.md
- 文档索引：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/docs/INDEX.md
- Chat prompt：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/pet/chat/prompt.py
- Chat service：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/pet/chat/service.py
- 文件投喂：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/pet/file_eater.py
- 主动识屏参考：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/pet/proactive.py
- 原项目许可：https://github.com/MerZlin/dsh-pet-indesktop/blob/main/LICENSE
- 官方 Qt for Python 受支持平台：https://doc.qt.io/qtforpython-6/overviews/qtdoc-supported-platforms.html

> **本文件只是一份详细开发计划。** 截至编制时，未克隆/修改 GitHub 仓库，未在 Windows 10 实测，亦未生成增强版 EXE。后续由具有项目文件及命令执行能力的 Codex/Work 环境落地和验收。
