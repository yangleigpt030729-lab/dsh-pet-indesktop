# P1.1 长期记忆隐私过滤与回忆检索加固

基线 `c81f26f014fa3699fdbc43d049759fed973cbb5a`；分支 `feature/win10-companion-memory`。
实际环境 Linux 6.18.44 x86_64 / Python 3.12.14 / PySide6 6.12.0。
**NOT TESTED ON WINDOWS 10 22H2 x64；未请求真实 DeepSeek、未打包 EXE。**
关联：[P1 接入审计](AI-COMPANION-INTEGRATION-NOTES.md)、[P2 待确认方案](P2-PROACTIVE-CHAT-IMPLEMENTATION-PLAN.md)、[任务书](../DEVELOPMENT_PLAN_WIN10.md)。

## 一、核心特性

原 P1 自动提取会把邮箱、部分联系方式与精确住址持久化；仅双字匹配的检索既漏掉“你还记得我以前告诉过你什么吗”，也会把“火星的颜色”与个人蓝色喜好混淆。

P1.1 统一加固提取/写入/检索的隐私检查。接受明确的个人回忆总览和喜好总览，具体主题只返回该主题；普通知识/对方喜好问题不引入个人事实。最多 5 条、600 字。旧私人条目仍可本地查看/删除，检索不发送，不暗中清库。

## 二、修改文件说明

统计来自最终 `git diff --numstat`，本报告行数在结束时校准。新增为检索模块、测试、基准脚本及两份文档；无文件删除。未修改配置/授权协议、SQLite schema（仍 v2）、ChatService、SessionStore、UI 布局、动画、气泡、待办服务或网络路径。

| 文件 | 增删 | 具体原因 |
| --- | --- | --- |
| `docs/AI-COMPANION-INTEGRATION-NOTES.md` | +4/−2 | 更新 P1.1 当前隐私边界和意图检索，保留原 P0 历史证据。 |
| `docs/INDEX.md` | +4/−0 | 登记新交付报告和待确认 P2 计划。 |
| `docs/P2-PROACTIVE-CHAT-IMPLEMENTATION-PLAN.md` | +115/−0 | 源码审计、具体接口风险、配置/限流/只读记忆/到期恢复及测试计划；仅文档。 |
| `docs/PR-REPORT-COMPANION-MEMORY-HARDENING-2026-10-12.md` | +114/−0 | 本报告，记录逐文件变化、实测、失败测试与平台边界。 |
| `pet/companion/memory_extract.py` | +37/−1 | Unicode/混淆值归一、邮箱/电话/地址/私人字段过滤；修正技术兴趣 false positive。 |
| `pet/companion/memory_retrieve.py` | +63/−0 | 个人总览、偏好/称呼/具体主题意图及小规模同义词；抑制普通知识问题/明确不回忆请求。 |
| `pet/companion/memory_store.py` | +14/−13 | 接入 scoped 检索，限制数量/字数，过滤旧敏感记录并保持管理可见；更新拒绝文案。 |
| `scripts/benchmark_companion_memory_hardening.py` | +39/−0 | P1/P1.1 同机合成数据对照；不打开真实用户数据。 |
| `tests/test_companion_memory_hardening.py` | +186/−0 | 93 项参数化/集成回归：隐私拒绝与误识别、回忆范围、旧记录不发送、授权/删除/真实进程退出。 |

## 三、隐私与检索语义

- 先 NFKC/零宽字符归一，邮箱检查额外处理空白及 `[at]/[dot]` 写法；电话覆盖手机号分隔、区号、国际加号。检测住址层级/门牌/室号、常见英文街道、联系方式/社交账号、证件、出生/收入/年龄等不必要私人字段；拒绝 URL 和用户文件路径。
- 规则也作用于显式“请记住”和手工写入，且失败事务不改变旧记录。不是通用 PII/所有语言检测器；特殊编码、未识别地址/表达仍有边界，不能宣称绝对匿名或自动加密。
- “密码学”“tokenization”“生日蛋糕”、普通日期、明确授权的城市粒度信息不误判成密码/生日/精确家庭地址。不改变 automatic=false 的授权要求；联系方式和安全偏好分句时只提取安全句子。
- 明确个人泛指回忆按更新时间取最近的有限已确认事实；偏好总览排除事件/工作等无关事实，也识别 P1 管理器以 kind=fact 写入的手工喜好。
- 具体颜色/配色/色彩或称呼问题保留具体 topic；“知道/记不记得/么/那些”等常见问法归一；不使用 LLM、embedding 服务或额外 API 请求。
- 普通知识问题、询问模型自己的喜好、反向“你告诉我哪些知识”、明确“不要读取/回忆”不枚举个人记录。查询文本最多处理 4000 字，返回和内容预算不扩大；不是无界会话历史检索。
- 旧库私人数据本地仍可由用户管理；不自动迁移/删数据，不把历史 JSON/备份当成已清除。现有授权 generation、SQLite revision 删除屏障与跨进程持久化机制不变。

## 四、性能分析

命令：`source /workspace/.onboarding/dsh-pet-env.sh; python scripts/benchmark_companion_memory_hardening.py`。
需本地 Git 有 `c81f26f` 基线对象；baseline 搜索使用该提交代码。同一临时 SQLite：300 事件+100 偏好+100 工作事实，500 行；对照时完整回归并行，属于该云机样本，不是 Win10 帧率结论。

| 路径 | n | 中位数 ms | P95 ms | 返回 |
| --- | ---: | ---: | ---: | ---: |
| P1 考试检索 | 100 | 6.3171 | 7.1801 | 5 |
| P1.1 考试检索 | 100 | 7.3482 | 8.6051 | 5 |
| P1 喜好总览 | 100 | 6.1330 | 7.0324 | 0 |
| P1.1 喜好总览 | 100 | 4.3218 | 7.2738 | 5 |
| P1.1 泛指个人回忆 | 100 | 4.1583 | 7.3251 | 5 |
| P1 邮箱检查 | 1000 | 0.0020 | 0.0021 | 未拒绝 |
| P1.1 邮箱检查 | 1000 | 0.0018 | 0.0019 | 拒绝 |
| P1.1 逐句提取 | 1000 | 0.0093 | 0.0098 | 1 安全句 |
| P1.1 意图识别 | 1000 | 0.0030 | 0.0032 | 偏好 |

考试检索中位数增加 1.0311ms（包含逐行隐私检查）；均在现有聊天后台线程，未加 GUI 数据库 IO。喜好总览改善主要是正确限制范围，P1 返回 0 与 P1.1 返回 5 不是同一种工作量，不声称普遍加速。邮箱样本命中早退出，也不是全部语料的性能保证。

20 次预热后再检索 100 次：tracemalloc retained delta 0 bytes、peak 251358 bytes，SQLite 192512 bytes。此为有界合成样本，不声称数小时 RSS 零增长。没有新 timer、线程、网络或持久缓存；原 SQLite 读取次数不增加，scoped 检索及正则计算增加后台 CPU。关闭授权时原 MemoryContext 不开库，P1 的轻量关闭路径未改动。

## 五、实机运行记录

当前 Linux 实际 SQLite/Qt 事件循环，网络边界为 fake Provider，无密钥/真实费用：

- 未改动前 P1/ChatService/架构聚焦：55 passed，4.32s，退出 0。
- 新增第一轮真实失败：60 failed / 16 passed；复现邮箱/住址存储、回忆缺失和无关检索。另补社交账号/年龄后 4 failed / 2 passed；同义问法补充 7 failed / 86 passed；对应修补后最终聚焦全部通过。
- 实际聊天输入合成“邮箱+蓝色喜好”两句，SQLite 只保存蓝色；已存在的合成邮箱条目在 list 可见，fake Provider 的实际 payload 不含该邮箱。
- 限制数量/字数、喜好排除事件与工作、具体颜色仅选颜色，已用真实 SQLite 检查。关闭记忆不注入，clear 后新请求不再引用；真实子进程读总览并删除，进程退出后主进程为空。
- 原 P1 UI 授权、关闭/删除/取消在途任务、保存失败屏障、SQLite 损坏/锁回退、两种聊天窗口及真实跨进程退出测试都纳入本轮。不是把前次 P1 数字当成此次结果。
- Linux 无 Win10 登录桌面；未验证 Win10 原生透明/拖拽/全屏/DPI/托盘及真实模型回答。继续使用 P1 报告的实机验收清单，加入下面的新用例即可；不以 fake Provider 输出代替真实 DeepSeek 记忆理解。

## 六、测试与验证

所有命令在仓库根目录并先 `source /workspace/.onboarding/dsh-pet-env.sh`，offscreen/可写 XDG/已验证 PipeWire 配置不变。日志命令直接重定向，未用 pipeline 隐藏退出码。

| 检查 | 结果 |
| --- | --- |
| 最终聚焦+架构 | 148 passed，4.25s，退出 0 |
| 受影响记忆/聊天线程族满载三轮 | 5 个 CPU hog，138 passed ×3，耗时 5.60/5.25/5.46s，退出均 0 |
| 原聊天/相关回归前一轮 | 283 passed / 1 skipped，15.95s；最终主套件含其全部文件 |
| 最终 CI 主套件 | 4349 passed / 37 skipped / 21 warnings，270.15s，退出 0 |
| WebM 三个隔离文件 | 41 passed，25.85s，退出 0 |
| 低优预热隔离文件 | 27 passed，31.44s，退出 0 |
| 文档交付纪律 | 75 passed，0.42s，退出 0 |
| Ruff、compileall、diff check | 退出 0，Ruff All checks passed |

最终聚焦：

```bash
python -m pytest -q tests/test_companion_memory_hardening.py tests/test_companion_memory.py tests/test_companion_chat.py tests/test_companion_memory_ui.py tests/test_chat_service.py tests/test_architecture.py
```

完整 pytest 沿用仓库 CI 分组，没有丢弃隔离族或削弱断言：

```bash
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
ruff check pet/ tests/ scripts/benchmark_companion_memory_hardening.py
python -m compileall -q pet packaging scripts
git diff --check
```

旧 `tests/smoke.py` 固定 51 项素材的已知失败未修改；原基线 DSH 已删除 signal 警告/Qt deprecated warnings 不在 P1.1 里屏蔽或扩展修复。无新增模型请求、P2 timer 或 reminder config。

## 七、Win10 未验证项与验收补充

全部 **NOT TESTED ON WINDOWS 10**：用实际普通账户/原 DeepSeek UI 逐个输入合成邮箱、电话、住址，确认没有长期记忆；普通偏好仍保存；三个总览/具体问法只注入有限相关条目。重启检查喜好、删除再问、关闭授权再问；老库合成私人条目可管理但不发送。验证原动画、透明窗口、拖动/点击、投喂、DPI、托盘以及真实模型对引用事实和不确定性的处理。

## 八、下一阶段和回滚

[P2 方案](P2-PROACTIVE-CHAT-IMPLEMENTATION-PLAN.md) 给出实际源码接缝与测试矩阵，**PLAN ONLY / NOT IMPLEMENTED，等待用户确认**。其中必须解决原 public show_bubble 返回 None（无法确认送达）、Todo 宽限外静默跳过/先盖戳再显示、ChatService 全局完成监听可能触发岛预览、主动提示不能走 P1 写事实路径。

P1.1 无 schema/设置迁移，回退该提交保留已有库，但会恢复原先较弱的过滤和检索；不自动删除数据库、聊天历史或备份。规则不是全语言隐私扫描/向量语义检索；未识别地址或复杂表达仍需用户手工管理。
