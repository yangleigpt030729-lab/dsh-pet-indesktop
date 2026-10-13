# System Prompt 收尾：保存的用户人设优先于角色资源默认

日期：2026-10-13；分支`feature/win10-companion-memory`；基线`8c4d21b1b6df3ead3a1dac6649a9ae42464ef08c`。仅修本缺口，不合并main，不重构摸头朗读/表达风格/投喂协调。前次：[增量报告](PR-REPORT-COMPANION-EXPRESSION-SPEECH-FEED-2026-10-13.md)；操作：[Windows指南§9](WINDOWS10-COMPANION-ACCEPTANCE.md#9-本轮收尾用户-system-prompt-优先)。

## 修改文件说明

| 文件 | 增删 | 改了什么 / 为什么 |
|---|---|---|
| `CONTEXT.md` | +4/−0 | 补充共享人设选择顺序、默认恢复及旧异步失效的当前契约。 |
| `docs/INDEX.md` | +2/−0 | 登记新的收尾报告，满足文档证据门。 |
| `docs/PR-REPORT-CHAT-PERSONA-PRIORITY-2026-10-13.md`（新增） | +121/−0 | 交付逐文件、红绿、真实性能、实际设置保存和平台边界证据。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +10/−0 | 追加现有编辑器人设/清空恢复/热切换复验，明确Fake语言与真实模型区别。 |
| `pet/chat/legacy_widgets.py` | +8/−1 | 同样使旧人设请求失效并保留历史，与新版窗口一致。 |
| `pet/chat/prompt.py` | +5/−1 | 仅修共享优先级：非出厂用户文本在manifest前，空白/缺资源安全回退。 |
| `pet/chat/widgets.py` | +8/−1 | 仅在保存的人设变化时取消旧请求和打字机缓存，重建已存会话显示。 |
| `scripts/benchmark_chat_persona.py`（新增） | +42/−0 | 真实临时manifest、本地基线/当前每路径20000次实测，无网络或Key。 |
| `scripts/stress_chat_persona.py`（新增） | +27/−0 | 复用原CPU burner，对受影响聊天/人设异步族执行4CPU×3轮。 |
| `tests/test_chat_persona_priority.py`（新增） | +283/−0 | 25个真实manifest、保存/新进程、四通路载荷、双UI热切换、旧缓存及子宠/无关刷新回归。 |

## 根因、优先级与热更新

`PromptBuilder.effective_system_prompt`原来先读取角色manifest，即使用户已在原AI编辑器保存不同的System Prompt，也会被资源默认遮住；上轮风格测试用了不存在manifest的角色，未覆盖这次真实并存条件。本轮新增实际临时`characters/shenshen/manifest.json`，保留原解析器，只替换测试资源根目录，不用假的Prompt解析结果。

新优先级：调用者明确的单次`role_prompt`（保留原API）→ 非空且不同于出厂原句的已配置用户文本 → 角色`manifest.chat.system_prompt` → 出厂提示。原普通聊天/主动问候/摸头/趣味投喂都已有同一Builder调用，无需重写服务。角色外观/资源主题不变，未自定义时保持资源默认人设。

现有配置预填非空出厂原句，不能简单把所有非空文本视为用户自定义。空白/恢复出厂原句表示撤销自定义；旧存档非出厂文本直接按新优先级生效，无schema/字段/默认值迁移、无新预设/滑块/编辑器。已有单次显式role_prompt API仍优先（生产四通路未使用该参数），不改变其契约。

普通聊天两个窗口的原`refresh_settings`仅重取设置，既不停止旧请求，也未清理新版已完成网络但仍等待打字机的文字。本轮仅在保存的System Prompt文本变化时：先作废request id，原`service.stop`取消，原`_reset`清空缓存，再从已存会话重建显示。历史不删除，不重写旧会话的人设元数据；下一次发送读取新设置。无关设置刷新不取消当前聊天。主动/摸头/投喂及待播摸头语音沿原配置身份/授权代次检查失效，未修改这些服务。

表达风格仍为独立附加system message，明确“不覆盖角色人设、任务安全、文件隐私或记忆授权”；现在这里的人设由用户优先选择。任务/记忆引用安全消息仍独立后置；safe_metadata、授权确认、只读记忆、事实提取和声音通道完全未改。人设文本不能增加本地读取文件/记忆/截图/语音权限。测试检查实际Provider载荷的首条人设及后续安全规则，不把模型是否一定遵从指令当作已实测。

## 性能分析

命令`python scripts/benchmark_chat_persona.py`；Linux x86_64 / Python3.12.14 / Qt6.12.0环境，真实临时manifest，单路径各20000次，基线方法来自本地`git show 8c4d21b:pet/chat/prompt.py`，无联网/密钥。基准开发脚本需本地Git历史，Windows普通源码启动不需要Git。

| 路径 | 基线 | 当前 |
|---|---|---|
| 未自定义、实际资源人设 | 13.833µs/次 | 13.128µs/次 |
| 已自定义、资源仍存在 | 12.268µs/次（错误选择资源） | 0.345µs/次（正确选择用户文本） |

这不是相同结果的加速对比：自定义路径语义已经改正，且无需额外读manifest。默认路径保留原读盘；亚微秒差异不宣称稳定性能提升，测试与其它回归有部分重叠。RSS37.977→39.406MiB（+1.430MiB，混合冷热样本）；没有新常驻缓存或保留Prompt列表，但不是无限时长内存保证。新增分支为strip/比较及一个短生命周期ChatSettings默认实例，每次构建请求一次；热更新仅System Prompt变更时复用原取消/显示重建，没有逐帧工作。无新增定时器、线程、播放器、网络请求或私有库读取；模型输入文本按用户人设变化，原请求频控/费用预算不变。真实模型成本、Windows取消延迟未测。

## 实机运行记录

可用环境为Linux/Qt offscreen，不是Windows。实际文件验证使用原AI设置页保存合成自定义Prompt到隔离Config，并启动全新Python进程读取同一真实临时manifest+Config，解析结果确认为用户Prompt；未用Fake替代文件解析/持久化。原设置页和两种实际聊天Qt窗口在测试中构造，网络边界用FakeProvider；旧请求取消/保留历史/新Prompt发送、待输出缓存失效均经实际事件循环检查，不能冒充真实模型或Windows验收。

另在pytest外使用真实`ModernSettingsDialog`与其原`_save()`：临时创建资源manifest、填写合成用户人设、保存，再用新Config重读，输出`PASS: actual shared settings dialog save, real manifest plus user persona persisted and reloaded; no Fake/Provider`及`PLATFORM: Linux 6.8.3 offscreen`。原AI页独立保存另验证了清空后回退资源，输出`PASS: actual Qt AI editor, isolated config save/reload, real manifest coexistence, user override and clear-to-resource fallback; no Provider or Fake`。720px宿主截图`/tmp/persona-priority-real-dialog.png`已查看，原System Prompt编辑器仍唯一，API Key为空，无新布局。该Linux/offscreen探针无法证明Win10窗口/真实网络模型。

实际文件/宿主验证的关键命令（在原环境中执行，无API）：

```bash
/workspace/.venvs/dsh-pet-qt68/bin/python - <<'PY'
import json, tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.chat.prompt import PromptBuilder
from pet.modern_settings_dialog import ModernSettingsDialog
app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base/'characters'
    (root/'shenshen').mkdir(parents=True)
    (root/'shenshen'/'manifest.json').write_text(json.dumps({'chat': {'system_prompt': 'RESOURCE-DEFAULT'}}), encoding='utf-8')
    cfg = Config(base=base/'data')
    builder = PromptBuilder(root)
    assert builder.effective_system_prompt(cfg.chat_settings(), 'shenshen') == 'RESOURCE-DEFAULT'
    dialog = ModernSettingsDialog(cfg, include_ai=True)
    dialog.ai_page.prompt.setPlainText('SYNTHETIC-USER')
    dialog._save()
    assert builder.effective_system_prompt(Config(base=base/'data').chat_settings(), 'shenshen') == 'SYNTHETIC-USER'
    print('PASS: real settings save and manifest coexistence')
    dialog.close()
PY
```Windows10用户已有GUI/Fake问候/摸头气泡/身体动画的确认仍保留；本轮新增人设优先/原生保存与热更新没有Windows实测。真实DeepSeek语言遵从和真实声音 **NOT TESTED**；未提供或使用真实Key，没有新EXE构建。Fake固定台词和本地降级文案不解析任意自定义人设，不用于判定模型语言表现。

Qt UI review：`pet/chat/widgets.py`、`pet/chat/legacy_widgets.py` ✓ pass（仅人设变更取消/显示重建，无新控件、布局、主题或编辑器；不触碰输入编辑器与已有焦点处理、保留已存会话；无关刷新保留请求）。设置契约检查：复用原字段/保存入口、默认恢复/持久化/子宠身份及热更新均有测试；新增控件的能力矩阵/几何截图不适用，不声称Windows原生焦点已验收。

## 测试与验证

同样首批22例：修补前 **15失败、7通过、0跳过，1.01s**；修补后 **22通过、0失败、0跳过，1.42s**。包括资源+自定义并存、空白/出厂值/缺资源回退、真实AI编辑器保存与全新进程重启、两种普通聊天窗实际Provider、三类陪伴载荷、保存热切换/旧异步/新版待输出缓存失效。随后补两种无关刷新保持当前请求、子宠独立保存，共25新增用例。未删或放宽失败断言。测试root覆盖仅改变资源位置，不模拟文件内容或Prompt优先级；Fake只替代网络。

相关聚焦命令：`python -m pytest -q tests/test_chat_persona_priority.py tests/test_chat_subsystem.py tests/test_chat_service.py tests/test_chat_shared_behavior.py tests/test_companion_expression.py tests/test_companion_interactions.py tests/test_companion_proactive_service.py tests/test_companion_feeding.py tests/test_companion_feed_consent.py tests/test_companion_head_speech.py tests/test_file_interpret.py tests/test_architecture.py`，**301通过、1跳过、0失败、0警告，23.83s**。

| 检查 | 真实结果 |
|---|---|
| 完整主组 Qt6.12 | 4669通过 / 37跳过 / 0失败 / 19警告；445.16s |
| 独立WebM组 | 41通过 / 0跳过 / 0失败 / 0警告；25.94s |
| 独立lowwarm组 | 27通过 / 0跳过 / 0失败 / 0警告；31.46s |
| frameseq复验（与主组重复） | 37通过 / 0跳过 / 0失败 / 0警告；1.01s |
| Qt6.8.3人设/聊天/陪伴覆盖组 | 267通过 / 1跳过 / 0失败 / 0警告；19.01s |
| 4CPU满载×3 | 每轮124通过 / 0跳过 / 0失败 / 0警告；8.86 / 8.84 / 8.78s |
| Node桥接 | 34通过 / 0跳过 / 0失败；230.99ms |
| bridge verify_import | import / subtraction / source bans通过 |
| Ruff / compileall / diff check | 通过，含全部改动Python脚本 |

完整CI唯一Python用例**4737通过、37跳过、0失败、19警告**（主组+41WebM+27lowwarm）。其它重复覆盖组不累加唯一数量。警告均为已有Qt mirrored/DragEnter/HoverEvent弃用，没有未捕获线程警告。Qt6.8覆盖中的跳过沿原Linux能力条件；未复跑/宣称修复上一轮Qt6.8菜单普查失败。offscreen插件的raise/propagateSizeHints stderr与pytest警告分开。

完整分组与静态命令：

```bash
source /workspace/.onboarding/dsh-pet-env.sh
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_chat_persona.py
ruff check pet/ tests/ scripts/benchmark_chat_persona.py scripts/stress_chat_persona.py
python -m compileall -q pet packaging scripts
git diff --check
```

Qt6.8命令：`/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q tests/test_chat_persona_priority.py tests/test_chat_subsystem.py tests/test_chat_service.py tests/test_companion_expression.py tests/test_companion_interactions.py tests/test_companion_proactive_service.py tests/test_companion_head_speech.py tests/test_file_interpret.py tests/test_architecture.py`。Node桥接沿原7测试文件与`verify_import.mjs`，具体数量见表，不据此宣称原生Windows兼容。

## 限制与回滚

用户优先解决的是Provider请求实际人设来源，Fake/本地固定降级文案与真实模型语言遵从分开验收。原配置无法区分“从未修改的出厂原句”与“有意重新输入同一原句”，本轮统一视其为恢复角色默认；没有新增隐式授权或配置标志。

上轮已记录Qt6.8旧菜单QAction残留及用户WebM退役池/慢帧待排查，本轮未动这些路径、未扩大修补范围；本次Qt6.8人设覆盖不是全平台全套通过声明。模型请求取消仍复用原服务，不能撤回已经发送的请求；本修补保证旧UI结果不继续显示/入会话，真实联网取消延迟未测。历史已完成回复保留。

退出程序后回滚本轮提交即可恢复旧优先级/聊天刷新行为；用户Prompt原字段和历史数据仍保留。交付后停止，等待Windows集中复验。
