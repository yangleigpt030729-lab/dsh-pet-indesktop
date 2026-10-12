# P2-B 收尾加固与 Windows 10 验收准备

基线 `6052b15`（实现 `586b776` 已由用户核实），分支 `feature/win10-companion-memory`。
本轮只做P2-B加固与Windows验收准备，不进入P2-C/P3/P4，不重构动画引擎，不合并main。
关联：[Windows具体步骤](WINDOWS10-COMPANION-ACCEPTANCE.md)、[上一轮报告](PR-REPORT-COMPANION-PROACTIVE-2026-10-12.md)。

## 修改文件说明

| 文件 | 增/删 | 修改原因 |
|---|---:|---|
| `CONTEXT.md` | +8/−0 | 登记新回执、v2日账与固定标签隐私约束 |
| `docs/INDEX.md` | +3/−0 | 登记报告和Windows验收指南 |
| `docs/PR-REPORT-COMPANION-PROACTIVE-2026-10-12.md` | +4/−0 | 保留上一轮历史，追加第二轮链接 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | +124/−0 | 网页ZIP、依赖、Fake/live、两种窗口与人工验收清单 |
| `packaging/constraints-win10-companion.txt` | +50/−0 | Python3.11 x64/Qt6.8.3验收版本约束，含Windows投影依赖 |
| `pet/companion/proactive_context.py` | +18/−1 | worker前后检查预约日期与lease，继续只读 |
| `pet/companion/proactive_repeat.py` | +17/−0 | 固定类别白名单摘要，原文永不上传 |
| `pet/companion/proactive_service.py` | +20/−9 | 安全摘要、过期请求阻断、实际回执时间/结算反馈、Fake不读凭据 |
| `pet/companion/proactive_state.py` | +61/−11 | v2配额/间隔快照，结算复核、午夜fence、崩溃时间上界持久化 |
| `pet/overlay_shell.py` | +2/−0 | 复核真实新文字呈现序号 |
| `pet/speech_bubble.py` | +11/−0 | 新增公开接受序号/匹配查询，保留show_text协议 |
| `pet/window.py` | +2/−1 | Legacy新文字回执，拒绝旧可见/旧同文案 |
| `scripts/package_companion_test.py` | +121/−0 | 确定性源码ZIP、秘钥/用户数据过滤、原子输出和逐文件校验 |
| `scripts/prepare_windows_companion.ps1` | +28/−0 | 固定Windowsvenv与依赖检查，不读密钥，不改全局执行策略 |
| `scripts/run_companion_acceptance.py` | +92/−0 | 隔离目录/凭据ref，默认Fake与显式live，仅验收入口 |
| `scripts/stress_companion_proactive.py` | +1/−1 | 新增加固族纳入三轮4CPU负载 |
| `tests/test_companion_acceptance_launcher.py` | +35/−0 | 目录隔离/凭据ref/禁止Fake读系统keyring |
| `tests/test_companion_acceptance_package.py` | +69/−0 | 确定性/排除私人文件/真密钥体拒绝/自检误报/篡改及原子保护 |
| `tests/test_companion_proactive_hardening.py` | +244/−0 | 旧气泡、午夜结算/崩溃/6进程、撤销摘要/过期API、无TTS截图 |

本报告自身统计在结束时校准。核心变更：SpeechBubble真实文本呈现序号；两种宿主回执复核；SQLite主动状态v1→v2的额度/间隔快照和崩溃时间高水位；固定语义标签摘要替代上传旧台词；请求与展示的日期/过期边界；Windows源码验收包、约束与隔离启动器。

## 修补与不变量

初始8个针对性用例全部真实失败：两种旧可见/旧同文案气泡的假回执、跨日转借满额账、结算未复核10条、回执时钟回拨、崩溃跨午夜绕过30分钟，以及授权开启/关闭时历史私密词继续进入Prompt。现在对应用例与扩展回归转绿。

`show_text()`调用协议与返回值不变。仅在实际更新文本、show并设定隐藏定时器后递增呈现序号。`text_was_presented(text, after)`同时复核新序号、文本内容、text类型和可见性；Legacy不再只看isVisible，Overlay也复核底层接受状态。交互审批保护拒绝新文字时，即使旧气泡恰好相同文字也不消耗成功额度。Qt接受与操作系统实际像素可见仍有边界，Windows遮挡/DWM需实机验收。

主动SQLite schema v2为reservations增加quota和spacing（旧行保守默认10和1800秒）；每次prepare display与finish在BEGIN IMMEDIATE内重查账与占位总和。只有预约所属本地日、未过期且展示窗口内的真实回执才结算；成功数条件UPDATE严格小于min(10,预约额度)。校验失败保留不确定占位，不夹成10或伪造成功、不挪新日额度。结算幂等，6个真实进程同时结算最后一槽仅一个成功。成功时间取max，避免晚到旧回执把上次展示时间倒退。GUI记录呈现后的回执时间，后台反馈结算是否确认，不再笼统报告成功。

未知崩溃展示另存tentative UTC，即展示准备时间+5秒（有效UI交付窗口上界）。删除昨日过期预约后仍保存其时间约束，避免凌晨重启跳过间隔；明确未展示/取消才清掉该预约的临时约束。正常成功仍精确满足29分钟拒绝/30分钟允许；不确定崩溃会额外保守等至上界，不收费、不伪造发送。午夜前最后5秒及跨日/过期请求暂缓，不构成夜间免打扰。请求重生成也核对本地日和lease；ChatService worker在读记忆前后检查request window，防止排队后的旧日请求启动付费Provider。

完整近期台词仍仅在本地用于文字/语义去重，**任何授权状态下都不上传旧文本摘要**；仅发送固定白名单greeting/drink/break/care标签。历史v1记录未知来源、授权撤销、删除、use_memory关闭及保存失败时的运行期撤销，均无法通过摘要侧路重新上传私人词；无需猜测旧台词是否有私人事实。当前少量事实仍由只读记忆上下文和双授权控制；不修改P1长期记忆schema/revision策略。

费用上限维持每日最多20次/1920预留输出token（额度调低则相应调低）、每候选最多2次；输入token仍计费。语义去重及手动聊天优先不变。测试把TTS、屏幕/窗口截图和全局完成回调设成失败钩子，普通主动链没有触发它们。Fake Provider不解析系统凭据。

## 性能分析

在相同Linux/Python3.12环境测量Qt6.12与Qt6.8.3。命令为 `python scripts/benchmark_companion_proactive.py`，Qt6.12与完整回归并行的Linux/Python3.12.14/cgroup4CPU样本：纯tick 10000次中位2.66µs/p95 4.69µs，关闭预约10000次1.44/2.64µs，后台SQLite拒绝预约500次149.84/317.54µs，100条本地语义去重500次1651.67/2452.02µs。2000次空历史读取Python局部分配当前32字节、峰值2195字节，样本库36864字节；不是整体RSS。与上轮同类SQLite拒绝144.57µs中位相比约增加5.27µs（不同并行负载，不作严格性能因果结论）。未测Windows CPU/RSS/帧率。新窗口回执仅GUI内计数/文本比较，不执行网络/SQLite。v2增加短事务断言与元数据；迁移一次、后续后台访问。历史摘要固定最多3条标签，本地台词仍100条/30天，未引入无界线程或缓存。

## 实机运行记录

Windows10 22H2 x64、Windows Python3.11、PowerShell准备脚本、真实DeepSeek、EXE构建均 **NOT TESTED**。本次仅Linux真实Qt/offscreen和Fake/模拟HTTP；不把下载到Windows轮子当Windows安装成功。Qt6.8.3 Linux兼容性检查与标准Qt6.12云端检查分别报告。

Windows网页下载分支ZIP、安装依赖、Fake/live独立目录、Legacy/Overlay、原版入口python -m pet、人工清单与源码测试ZIP详见 [WINDOWS10-COMPANION-ACCEPTANCE](WINDOWS10-COMPANION-ACCEPTANCE.md)。源码ZIP固定时间/权限/顺序并校验逐文件SHA256，不复制用户数据与凭据；测试密钥格式/JSON凭据拒绝构建、symlink拒绝、篡改拒绝、相同源码两次相同ZIP。使用GitHub ZIP不需要.git或GitHub Desktop。固定Qt6.8.3配置是测试环境，非正式发行EXE。

Windows cp311/win_amd64轮子在云端通过pip正常TLS/摘要验证下载；lunar-python无公开二进制轮子时用其已验证纯Pythonwheel，未放宽任何依赖pin或SSL。跨平台pip按Linux评估marker会额外下载Linux条件依赖，这是wheel下载探针的已知限制；实际Windows安装由Windows解释器评估marker。源码ZIP真实构建、校验857文件、无.git解压后Fake启动及有界退出已在Linux验证通过；最终源码快照两次构建比对SHA256，摘要另随交付给出，避免自引用。源码ZIP首次真实构建曾因检测器自身PEM格式文字误报而拒绝，没有包夹带密钥；已补自打包与真实密钥体/项目key格式测试，修正为识别实际密钥体而非孤立格式标记，保持拒绝真实内容。原build_onedir流程未改，本轮只准备源码验收构建，无EXE交叉编译或发布。

## 测试结果与已知问题

**最终完整主套件4451通过/37跳过/21警告/0失败，296.89s**。此前核心版本4448通过/37跳过/20警告，314.63s；源码包自检发现PEM标记误报后，修正并增加3例再跑完整主套件，未将中间结果充作最终结果。Qt6.12和Qt6.8.3的相关companion/chat/Todo/架构/气泡族均511通过/1跳过（22.20s /22.53s），新增构建/启动/隐私族修正后两种Qt均29通过。WebM41通过26.30s、预热27通过31.45s、FrameSeq37额外通过0.88s；4CPU满载107通过×3（9.12/7.57/10.03s）。桥接34通过，hermetic import通过；Ruff、compileall、diff check通过。两个Qt版本真实AppShell+阻塞Fake Provider/动画推进/透明帧/真实气泡/持久回执冒烟均PASS。隔离启动器Fake运行及退出通过；不是Windows实机结果。旧smoke.py本次实跑仍在固定51素材断言失败（实际106），保留原断言并单独记录；旧agent-monitor-dsh关闭时Signal source deleted及Qt弃用警告不是本轮私密摘要或新回执导致。真实API payload兼容性、WTS/睡眠/关机、Windows锁冲突和DPI均留待用户验收。

## 审查与回滚

新的v2主动库旧代码应安全拒绝而非覆盖。回滚先关闭主动开关，保留两个本地SQLite文件，不清空配额以绕过上限。原动画、手动聊天会话、原Todo/outbox均未重构。P2-C/P3/P4 **NOT IMPLEMENTED**。完成后停止，等待用户Windows实机验收。

## 实际验证命令

```bash
source /workspace/.onboarding/dsh-pet-env.sh
python -m pytest -q tests/test_companion*.py tests/test_chat*.py tests/test_todo*.py tests/test_architecture.py tests/test_speech_bubble*.py
/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q tests/test_companion*.py tests/test_chat*.py tests/test_todo*.py tests/test_architecture.py tests/test_speech_bubble*.py
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python scripts/stress_companion_proactive.py
PET_FRAMESEQ=0 python scripts/smoke_companion_proactive.py
PET_FRAMESEQ=0 /workspace/.venvs/dsh-pet-qt68/bin/python scripts/smoke_companion_proactive.py
PET_FRAMESEQ=0 python scripts/run_companion_acceptance.py --data-dir /tmp/p2b-acceptance-launch --auto-close-seconds 5
ruff check pet/ tests/ scripts/package_companion_test.py scripts/run_companion_acceptance.py scripts/stress_companion_proactive.py
python -m compileall -q pet packaging scripts
git diff --check
```

Win64/cp311依赖探针使用 `pip download --only-binary=:all: --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 -c packaging/constraints-win10-companion.txt` 后显式列出requirements中除lunar-python外的全部直接依赖、Windows投影和pywin32-ctypes；lunar-python1.4.8用 `pip wheel --no-deps` 取得纯Pythonwheel。最初把lunar-python放入only-binary全量下载触发ResolutionImpossible（没有公开二进制wheel），已定位，未放宽pins。Windows轮子可下载不是已安装、不是DLL/WinAPI已验证。

## 交付范围

仅提交本轮P2-B收尾和源码验收准备；Windows/真实DeepSeek/PowerShell/EXE仍NOT TESTED。实现保留在独立开发分支，不合并main，等待用户实机验收。

本轮基线6052b15，共20个文件；本报告自身新增 92 行、删除0行，其他增删见逐文件表。

## 2026-10-13 Windows 现场反馈及第二轮修补

保留以上原交付记录。用户已用Win10/Python3.12成功启动GUI、打开灵动岛设置，并在临时Fake注入后看到主动气泡；同时报告右键设置和原默认Fake失败。正式修补、红绿证据和重新执行的测试见[本轮报告](PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md)，旧测试数字不作为本轮结果。
