# Windows FFmpeg 控制台与 PowerShell 5.1 构建加固

基线 `c0c2c1157f5e007ae1088e4b78e13800f97db9f4`，分支 `feature/win10-companion-memory`。仅修复FFmpeg进程创建与构建脚本编码，未合并main。完整操作：[Windows指南第11节](WINDOWS10-COMPANION-ACCEPTANCE.md#11-ffmpeg-黑窗口修复重新打包与原生复验)，相关约束：[关机/注销保护](ISSUE-111-WINDOWS-SESSION-END-FFMPEG-2026-09-12.md)、[原打包门禁](ONEDIR_PACKAGING.md)。

## 根因与修复

直接源码缺口：`frameseq_provision._creation_flags()`只返回BELOW_NORMAL_PRIORITY_CLASS，直接Popen没有STARTUPINFO或CREATE_NO_WINDOW。无控制台的PyInstaller `--windowed` 父程序启动控制台FFmpeg时可创建可见黑窗口。这与用户观察到的内置 `ffmpeg-win-x86_64-v7.1.exe` 标题吻合；本环境未现场抓取Windows故障PID/调用栈，不能断言某次黑窗口必然来自该调用。

另发现覆盖漏洞：旧代理仅替换imageio `_io.subprocess.Popen`，而标准库check_output/check_call函数仍在原全局命名空间调用Popen。元数据和 `_utils` 冷版本探测会绕过捕获/Job；SDK0.6.0的STARTUPINFO只能隐藏窗口，没有CREATE_NO_WINDOW。修复将两SDK模块的subprocess引用各换为独立代理，四个便利函数call/check_call/check_output/run复用标准库函数体、默认值和关键字默认值，但全局名字绑定到代理。它们因此也进入原捕获入口；异常、超时kill/wait与管道收口保留标准库行为。

仅FFmpeg创建边界在Windows**按位OR** CREATE_NO_WINDOW；转换仍保留低优先级，SDK仍保留STARTUPINFO/新进程组等原标志。覆盖关键字和支持的Python3.11/3.12位置参数形式。SDK专属入口也支持重命名的IMAGEIO_FFMPEG_EXE。全局subprocess.Popen、其继承关系与其它产品进程调用没有修改；无全局猴子补丁。

| 运行入口 | 实际链路 / 防护 |
|---|---|
| 普通动画、素材切换、摸头/投喂动画、周期回收后的fresh reader | WebMClip._reader_local → Capture → SDK read_frames → 专属Popen → 标志OR → 原win_job.adopt/线程登记 |
| 首帧预热 | _decode_first_qimage → 原Capture/首帧进程登记 → 同上 |
| 元数据 | _ensure_meta的原后台/显式warm闸门 → 安装代理 → count_frames_and_secs → SDK check_output/run → 同上 |
| 冷启动exe版本验证 | _ensure_ffmpeg_exe / provision.ffmpeg_exe → 安装代理 → SDK _utils._is_valid_exe → check_call/call → 同上 |
| fps探测 | provision.probe_fps → 安装代理 → read_frames → 同上，原finally close |
| 动画菜单缩略图 | _decode_webm → 会话结束检查/安装代理 → read_frames → 同上，代表帧/像素/尺寸算法不变 |
| 后台帧序列转换 | convert_clip原预算/取消/会话闸门 → _popen → Capture._wrapped → 低优先级+无控制台+原Job，原on_proc/terminate/communicate/清理保留 |

未修改动画素材、WebM像素/透明通道/帧率、FFmpeg命令参数、预热/回收频率、供给预算、聊天/摸头AI/双朗读/System Prompt/投喂交互规则或正式依赖版本。新增缩略图会话结束检查只抑制退出中的新解码。转换与探测接入既有Job，没有新增Job服务或全局进程扫描清理。

正式PowerShell缺口：build_onedir.ps1包含中文却无UTF-8 BOM。Windows PowerShell5.1在执行前按本机ANSI代码页解码，PYTHONUTF8不能修复这一步。四个正式ps1统一UTF-8 BOM；另新增真实Parser.ParseFile预检查，检查BOM、严格UTF-8和语法，失败即停止。包装构建在新WorkDir创建/安装前及安全源码解压后检查，原onedir和准备脚本也检查；原瘦身/编码/DLL/资源/桥接/GUI冒烟保留。其它三个原ASCII脚本没有被证明有乱码故障，统一BOM用于可靠的后续中文维护。

## 修改文件说明

相对基线的最终 `git diff --numstat`，共20文件：产品3、辅助脚本7、测试5、文档5；新增9文件，无删除文件。

| 文件 | 增 / 删 | 改了什么、为什么 |
|---|---:|---|
| `pet/webm_clip.py` | 46 / 9 | SDK两模块的专属代理/标准库便利函数绑定、Windows标志合并、冷exe/meta安装；保留捕获/Job/线程与像素生命周期。 |
| `pet/frameseq_provision.py` | 8 / 4 | fps/exe冷入口先安装；低优先级OR无窗口；转换入原Job漏斗，保留原转换参数和取消接线。 |
| `pet/animation_thumbnail.py` | 3 / 1 | 缩略图冷入口纳入创建策略及会话结束防护，覆盖此前遗漏的spawn。 |
| `scripts/build_onedir.ps1` | 2 / 1 | BOM与真实预解析；直接构建也安全，保留所有打包检查。 |
| `scripts/build_windows_companion.ps1` | 3 / 1 | BOM；构建前及暂存解压后预解析，旧环境/包/数据不覆盖。 |
| `scripts/prepare_windows_companion.ps1` | 2 / 1 | BOM与安装前预解析，原UTF-8 pip命令不变。 |
| `scripts/check_powershell_scripts.ps1` | 24 / 0 | 新增：BOM/严格UTF-8/本机真实ParseFile验证，不执行被检脚本。 |
| `scripts/watch_windows_ffmpeg_console.py` | 130 / 0 | 新增：启动一个新隔离Fake EXE，抽样对应包FFmpeg控制台、进程身份/正常退出与孤儿，拒绝覆写数据/报告，不读取凭据。 |
| `scripts/benchmark_ffmpeg_process.py` | 131 / 0 | 新增：真实Qt/FFmpeg/Pillow管线与原SDK像素比较，基线创建边界CPU/一次性代理内存量化；需要Git基线。 |
| `scripts/stress_ffmpeg_process.py` | 34 / 0 | 新增：既有CPU burn函数，三轮受影响族复跑，保持WebM/low-warm原CI隔离边界。 |
| `tests/test_ffmpeg_console_flags.py` | 218 / 0 | 新增33例：真实SDK入口仅录制OS spawn、保留标志/位置参数/重命名exe、全局Popen不变、嵌套/线程隔离、真实标准库输出/错误/超时/退出与会话闸门。 |
| `tests/test_ffmpeg_windows_console.py` | 107 / 0 | 新增7个原生Windows情形：真实FFmpeg控制台附着探针/帧/退出；首帧逐字节比较SDK、reader重启、实际转换。Linux跳过。 |
| `tests/test_ffmpeg_job_object.py` | 5 / 2 | 原真实父进程强杀测试参数化新增转换路径，保留反例与清理。 |
| `tests/test_powershell_encoding.py` | 44 / 0 | 新增8例：BOM/门禁静态检查5例，真实PowerShell5.1正确/缺BOM/语法错误3例；Linux跳过原生部分。 |
| `tests/test_windows_ffmpeg_observer.py` | 58 / 0 | 新增4例：Linux拒绝原生认证、不覆盖旧目录/报告、不把PID复用/已退进程判为孤儿。 |
| `CONTEXT.md` | 4 / 0 | 当前接线/边界/用户已有Windows成功与本轮未验证状态。 |
| `docs/INDEX.md` | 2 / 0 | 注册报告。 |
| `docs/ISSUE-111-WINDOWS-SESSION-END-FFMPEG-2026-09-12.md` | 4 / 2 | 修正“缩略图不是spawn”旧说法，连接完整入口审计。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | 207 / 4 | 已有Windows实测状态与全套独立PowerShell命令；新目录更新/预检查/构建/原生EXE/八场景/日志/回退。 |
| `docs/PR-REPORT-FFMPEG-NO-CONSOLE-2026-10-13.md` | 127 / 0 | 新增：本次根因、逐文件清单、性能/真实运行/门禁与未验证边界。 |

## 性能分析

命令 `source /workspace/.onboarding/dsh-pet-env.sh` 后运行 `python scripts/benchmark_ffmpeg_process.py --baseline c0c2c11`。环境Linux/Python3.12.14/Qt6.12.0 offscreen/imageio-ffmpeg0.6.0，cgroup CPU配额4核（cpu.max=400000/100000）；交付采样部分与四个CPU burner并行，不把墙钟当Windows前后性能比较。代理首次安装66.700µs，tracemalloc测得保留4652字节；每个进程只安装一次。

创建边界OS录制器（仅该CPU部分模拟Windows；不创建真实Windows进程），每版本3轮×100000次：原版平均1.207/1.174/0.898µs，修复版6.265/5.354/5.982µs。代价只在新建FFmpeg时发生，不是每帧/每点击；没有逐帧新增工作。无新的运行期网络、磁盘读取、定时器或线程；既有媒体读取/缓存/后台线程不变。新Windows Job调用仅在此前绕过的探测/转换spawn发生，首建Job和每次adopt沿原服务，次数与实际子进程数相同，原生开销未测。

真实媒体（素材副本、无OS/Qt/解码mock）：版本4.603ms，metadata51.465ms，首帧28.526ms，fps37.479ms，缩略图89.680ms；三次reader真实Qt首帧送达53.818/52.423/52.617ms；原无损中间帧/白底反解Q70转换118帧23062.369ms。输出640×360 RGBA、alpha范围0..255、首帧与原SDK逐字节相同，SHA256 `3cb45b76820585d16a2f2c038cf7a05662387bc1c314608ea1687b13ff8eda18`。12个真实子进程全部退出。该单素材/单次转换数据不是全素材或Windows性能承诺；Pillow转换耗时属原策略，不做调参。

没有新的无界容器；两个代理/八个函数绑定常驻一次，捕获列表仍局限原上下文；原生命周期压力组三轮均正常收口。辅助EXE观察器的50ms可见窗口/进程抽样、目录查询与JSON写入仅手动诊断运行时存在，不进入产品后台或动画线程。

## 实机运行记录

用户已实测Windows10 22H2 x64 / 19045、Python3.12、Qt6.8.3、PyInstaller6.19.0：前轮Fake集中验收正常，约149MB绿色ZIP成功构建，EXE及独立设置窗口冒烟通过，Fake摸头“合成测试”和其它交互成功；偶发内置FFmpeg黑窗口是本轮待修故障。保留这些成功/失败证据，未把旧EXE写成未构建。

本机真实Linux运行命令为上述benchmark，无mock媒体或Qt事件循环：元数据118帧，透明QImage与SDK帧相同，三次start/stop均交付frameChanged，原后台转换发布118张WebP及meta，12进程正常退出。第一次诊断脚本曾在stop后调用终态cleanup再start，并用了不合法的无世代输出名；已按现有契约修正测试/脚本，而未改产品行为。最终脚本使用stop重启、finally cleanup及原clip_out_dir生成合法世代；最终实际运行rc=0。无需真实Provider或系统凭据。

不可自动完成的证据：`uname -s`返回Linux；`command -v powershell / pwsh / wine`均无可执行程序，工具目录没有可用Windows运行器；用户确认只有本地Win10、无可接入远程运行器。15个聚焦原生测试因此按平台跳过，不伪造控制台/内核/解析结果。

| 验收部分 | 状态 |
|---|---|
| 原版Windows绿色ZIP、桌宠EXE/独立设置窗口、Fake交互 | 用户已报告PASS；黑窗口故障同样有真实报告 |
| 本轮Linux真实FFmpeg/Qt帧、透明像素、转换、退出 | PASS，rc=0 |
| 本轮Windows5.1 BOM/真实ParseFile | NOT TESTED；已给自动化预检查/反例测试 |
| 本轮Windows源运行CREATE_NO_WINDOW/AttachConsole/Job强杀 | NOT TESTED；7情形及5个原Job测试准备，Linux跳过 |
| 本轮全新Windows绿色EXE构建、资源/DLL/两个GUI冒烟 | NOT TESTED；原门禁保留，按指南运行 |
| 本轮EXE八场景、两拓扑/主子宠、周期回收/无孤儿 | NOT TESTED；手动清单与观察工具准备 |
| 真实DeepSeek、真实Edge声音、安装版/自启 | NOT TESTED，本轮不联网/不使用Key |

## 测试结果

测试先红后绿：修复前在原c0c2c11产品上新增用例运行 `python -m pytest -q tests/test_ffmpeg_console_flags.py tests/test_powershell_encoding.py` → **22 failed in 0.80s**。其中转换16384缺少134217728，SDK便利函数绕过OS录制器，冷安装缺失、BOM缺失；不是把Linux结果当Windows控制台实测。扩展完成后如下真实结果：

| 命令/组 | 通过 / 跳过 / 警告 | 时长或说明 |
|---|---|---|
| pytest主组（CI四文件隔离） | 4828 / 48 / 18 | 815.41s，rc=0；警告均已有Qt弃用构造器 |
| pytest独立WebM三文件 | 41 / 0 / 0 | 26.44s，rc=0 |
| pytest独立low-priority-warm | 27 / 0 / 0 | 31.34s，rc=0，未重试 |
| pytest独立frameseq两文件 | 37 / 0 / 0 | 0.85s，rc=0；已在主组，不重复相加 |
| 最终聚焦9文件，Qt6.12 | 185 / 15 / 0 | 26.83s，rc=0 |
| 同9文件，Qt6.8.3 | 185 / 15 / 0 | 26.19s，rc=0；Linux不是Windows |
| 4 CPU burners×3轮 | 每轮174+41+27 / 0 / 0 | 三轮全部rc=0；各族独立进程 |
| 新增/报告最终检查6文件 | 133 / 15 / 0 | 1.51s，rc=0；与其它组重叠 |
| Node7文件 / bridge hermetic import | 34 / 0 / 0 | rc=0 / PASS |
| Ruff / compileall / git diff check | PASS | 见下面具体命令 |
| 安全源码ZIP / 四个ps1 BOM保留 | PASS | 真实打包并读取ZIP成员验证；不是Windows EXE |

唯一pytest完整集合 **4896通过、48跳过、18警告、0失败**（主4828 + WebM41 + low-warm27）；不把聚焦、压力、Node、frameseq重复项加到pytest总数。旧 `tests/smoke.py` 的51素材断言仍过时（106），不在CI可执行集合，本轮未削弱或修改。原资源/预算/性能/架构检查如test_settings_and_resources、test_meta_cache_budget、test_first_frame_budget、test_library_shared_media、test_architecture均随主组执行；本轮未新增素材或改资源预算。

可复现门禁：

```bash
source /workspace/.onboarding/dsh-pet-env.sh
python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py
python -m pytest -q tests/test_low_priority_warm_interaction_yield.py
python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py
python -m pytest -q tests/test_ffmpeg_console_flags.py tests/test_powershell_encoding.py tests/test_ffmpeg_windows_console.py tests/test_ffmpeg_job_object.py tests/test_windows_ffmpeg_observer.py tests/test_frameseq_provision.py tests/test_session_end_ffmpeg_guard.py tests/test_animation_thumbnail_cache.py tests/test_companion_build_workflow.py
/workspace/.venvs/dsh-pet-qt68/bin/python -m pytest -q tests/test_ffmpeg_console_flags.py tests/test_powershell_encoding.py tests/test_ffmpeg_windows_console.py tests/test_ffmpeg_job_object.py tests/test_windows_ffmpeg_observer.py tests/test_frameseq_provision.py tests/test_session_end_ffmpeg_guard.py tests/test_animation_thumbnail_cache.py tests/test_companion_build_workflow.py
python scripts/stress_ffmpeg_process.py
ruff check pet/ tests/ scripts/benchmark_ffmpeg_process.py scripts/stress_ffmpeg_process.py scripts/watch_windows_ffmpeg_console.py
python -m compileall -q pet packaging scripts
node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js
node integrations/dsh-pet-bridge/verify_import.mjs
python scripts/package_companion_test.py --output /tmp/ffmpeg-reviewed-source.zip
git diff HEAD --check
```

日志：`/tmp/ffmpeg-{red-corrected,focus-final,qt68,main,webm,lowwarm,frameseq,stress,node,bridge,final-additions,package}.log`、`/tmp/ffmpeg-runtime-delivery.json`。压力各族秒数：第一轮13.71/27.07/31.51，第二轮12.36/25.77/31.59，第三轮11.92/26.63/31.49。交付版压力脚本与实际运行的临时脚本只存在根目录解析差异，命令/组/CPU burner一致。

## 风险与下一步

Windows本轮仍须按指南第11节使用全新WorkDir/绿色目录与Fake数据执行实际EXE验收，保留用户旧目录和正式APPDATA。原生Job权限/父Job限制、AttachConsole行为、PyInstaller7.1 FFmpeg及Windows5.1解析还没有本次实机结果；原防护失败降级策略未改。Python3.12/Qt6.8.3已有用户实测，不外推全平台兼容。标准库便利函数绑定适用已支持Python3.11/3.12，升级SDK/Python时要保留这组契约与真实原生测试。

观察器50ms抽样可能漏过极短闪烁，按已知新包完整FFmpeg标题匹配；手工看到窗口仍判FAIL。工具不自动认证8个交互场景/帧率/声音，未观察到FFmpeg或非正常退出返回失败/NOT TESTED；孤儿只认已记录的PID+创建时间，避免PID复用误判，不删除用户文件、不批量杀进程。尚需人工确认快速切换/睡眠唤醒/长期回收的实际体验。本轮完成后停止开发，等待用户Windows验收；不进入新功能、不合并main。
