# 大肥鱼 v1.0.0 Windows 安装器封装

基线：feature/win10-companion-memory，533eb1c487e79101c77d7ccec0c48df10a2f31d4。用户随后确认前轮十项Windows10实机均PASS，包含真实微软声音/双向音量/静音恢复/快速投喂/识屏前置+最终语音/岛聊天/授权/动画/拖动。本轮仅新增封装工具，不修改pet业务/依赖/AI/资源字节，不合并main、不tag、不Release。参见[逐条Windows构建与验收](WINDOWS-INSTALLER-V1-ACCEPTANCE.md)、[onedir原门禁](ONEDIR_PACKAGING.md)。

## 修改文件说明

| 文件 | + / − | 修改与原因 |
|---|---:|---|
| `CONTEXT.md` | 5 / 1 | 补记用户十项Win10体验均PASS，登记本轮纯封装范围和新安装器原生未测边界。 |
| `THIRD_PARTY_NOTICES.md` | 9 / 0 | 保存中文翻译原作者/官方来源、BOM/LF规范化及固定哈希，避免无署名或构建期浮动下载。 |
| `docs/INDEX.md` | 2 / 0 | 在构建入口及PR存档登记新指南/报告，供升级卸载审查检索。 |
| `docs/ONEDIR_PACKAGING.md` | 4 / 0 | 补充独立v1入口、真实ZIP根结构、原门禁和与通用上游安装器的边界。 |
| `docs/PR-REPORT-INSTALLER-V100-2026-10-14.md` | 68 / 0 | 新增逐文件/性能/测试/实机证据，明确没有在Linux制作Setup或执行安装。 |
| `docs/WINDOWS-INSTALLER-V1-ACCEPTANCE.md` | 124 / 0 | 新增一行一条PS5.1命令、全新目录、签名/自启/备份回退、12项实机验收。 |
| `docs/WINDOWS10-COMPANION-ACCEPTANCE.md` | 5 / 1 | 纠正已确认EXE根路径，补记前轮实机成功并链接本安装器验收指南。 |
| `packaging/ChineseSimplified.isl` | 417 / 0 | 新增官方6.5+中文向导翻译，文字和署名不变；UTF8 BOM/LF确保固定编码。 |
| `packaging/dafeiyu-v1.iss` | 146 / 0 | 新增固定AppId/1.0.0、当前用户完整离线安装、快捷方式/图标、退出与目录保护、数据安全卸载及显式已有自启迁移。 |
| `scripts/build_windows_installer.ps1` | 131 / 0 | 新增BOM一键构建；只读旧ZIP、新输出、复用安全/TTS/Qt/编码门禁，提取原图标、编译/签名/校验/日志，不重建应用。 |
| `scripts/verify_installer_payload.py` | 233 / 0 | 新增真实ZIP结构/PE/隐私/凭据/路径保护与流式完整文件哈希暂存，编译前后拒绝额外文件/篡改/链接。 |
| `tests/test_windows_installer.py` | 214 / 0 | 新增48项可在Linux执行的安全/文件/静态契约测试及2项Windows原生PS/ISCC门禁，不安装或启动合成EXE。 |

## 安装与安全工作流程

原已验收ZIP只读 → 全新OutputDir/build → 原package_companion_test安全源包只用于工具暂存 → 原生BOM/ParseFile → ZIP路径/隐私/结构/x64windowed PE检查 → 按原字节完整暂存EXE+_internal → 外部SHA256文件清单 → 原TTS归档/QtDLL/中文资源编码门禁 → 从同一EXE提取图标 → 编译前后完整清单复验 → ISCC → Setup大小/哈希/签名状态/输出清单。没有网络安装依赖，没有跳过门禁，没有重新生成动画/重编应用。

固定AppId 662C52E9-287D-43C4-90DE-4A0B9061C7C4，安装器1.0.0，主EXE名原样；只允许当前用户LocalAppData/Programs/DaFeiYuDesktopPet，已存在非本安装器登记目录拒绝覆盖。桌面图标默认可选、开始菜单、完成页可选启动、Apps & Features及卸载图标。CloseApplications=no，WMI按同一EXE名检测包括--settings子进程，PrepareToInstall/InitializeUninstall提示退出/重试/取消；失败闭锁，不强杀。

用户配置仍在原APPDATA变体目录，凭据仍在系统存储。安装/卸载不枚举、迁移或删除这些数据，不用UninstallDelete通配清理。原HKCU Run按变体单值；默认不创建自启。已有项只在明确勾选迁移时改原同名值，卸载只清理明确引用本安装路径的值，其他绿色版/变体保留。不改变系统设备/音乐/原语音通道。

包内隐私拒绝而非静默丢弃：配置/覆盖JSON、会话、SQLite及sidecar、日志、截图、个人缓存、密钥/凭据文件、除六个原静态声音外的MP3/WAV等。证书只允许certifi公开CA且不得含PRIVATE KEY；复用原credential_check扫描UTF8文本/JSON，不打印私人匹配值或路径。还拒绝路径穿越/ADS/设备名/重复大小写/链接/加密/混合根、限制32000项/2GiB解压/8MiB单文本。真实输入完整文件清单按SHA256保留，不复制运行中的用户目录。

Inno官方中文翻译固定在源码，不在安装期下载；需要6.5+，完整原署名及内容SHA256在Third Party Notices。默认无签名，SmartScreen可能未知发布者；可显式用本机证书存储的正规私钥让Inno签安装及卸载器，不导出、不传PFX密码，本轮未执行签名。不篡改原应用4.2.1/在线更新基准，1.0.0仅为这一安装产品版本。

## 性能分析

环境：Linux Python3.12.14，全部磁盘/ZIP/SHA256操作真实；PE、DLL和动画是合成文件边界，非原149MB便携ZIP/原生ISCC。在完整回归同时执行 `python /tmp/installer_benchmark.py`，537文件、67,109,525解压字节、67,180,717 ZIP字节，ZIP_STORED、临时目录且未清页缓存，三次新目录：暂存329.63/302.60/347.29ms（均值326.51ms），完整再验90.89/93.91/91.96ms（均值92.25ms）；原ZIP前后SHA256完全相同。进程峰值RSS88.34MiB含样本生成及SHA核对原ZIP整读，不能当作产品稳态内存或Windows构建耗时。

只在构建/安装/卸载调用这些工具，未向pet运行时加import、定时器、线程或系统调用，原已验收EXE逐字节复制。流式二进制读取1MiB块，文本最多8MiB，清单/ZIP索引按项数有界32000项；一次检查/复制/复验会有磁盘读取和哈希开销。ISCC压缩和原生Qt/编码门禁的时间、安装时WMI延迟、签名/时间戳延迟尚未测，不能按上述Linux纯I/O数字预估。未新增语音/网络/播放器通道；仅用户显式正规签名分支可能访问HTTPS时间戳。

## 实机运行记录

- 用户已确认的Win10基线十项全部PASS，前轮“未测”状态已由本次CONTEXT/指南补记，不用Linux覆盖这些成功证据。
- 本轮真实Linux Python3.12.14/Qt6.12 offscreen，真实ZIP/文件/进程测试；合成PE/DLL/资源只是文件结构输入。Windows安装动作、GUI启动、真实声音均未在这里执行。
- 探针：`command -v powershell.exe` / `pwsh` / `wine` 无结果；没有Windows运行器或用户便携ZIP文件接入。因此**Windows Setup NOT BUILT，PowerShell5.1新增脚本/ISCC编译/安装/升级/卸载/快捷方式及Windows11均 NOT TESTED**。原有用户Win10证据不等同安装器实测。
- 正式命令与全新D盘目录、旧包/数据备份回退及12项实机验收见指南。构建结束只报编译产物，不自动安装、不宣称通过安装验收。

## 测试与风险

首次红：公开ZIP安全验证模块尚不存在，新增测试收集失败；实现后可拒绝真实ZIP结构/路径/隐私/PE错误并通过安全测试。中间两项失败来自测试fixture仍提供替代PythonDLL及尚未编写ISS，修正fixture并补实现后聚焦通过；没有关闭断言或安全门禁。

命令先 `source /workspace/.onboarding/dsh-pet-env.sh`；offscreen/空keyring/隔离XDG保持原CI方式，没有全局关闭frameseq。

| 门禁/实际命令 | 真实结果 | 记录 |
|---|---|---|
| `python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py` | 5058 passed，50 skipped，18 warnings，817.82s | installer-main-verified.log |
| `python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py` | 41 passed，0 skipped，26.36s | installer-webm.log |
| `python -m pytest -q tests/test_low_priority_warm_interaction_yield.py` | 27 passed，0 skipped，31.39s；一次通过 | installer-lowwarm.log |
| `python -m pytest -q tests/test_frameseq_prefetch_watchdog.py tests/test_frameseq_clip.py` | 37 passed，0 skipped，0.90s；额外独立验证，已包含主组 | installer-frameseq.log |
| `python -m pytest -q tests/test_windows_installer.py tests/test_companion_acceptance_package.py tests/test_powershell_encoding.py tests/test_autostart.py tests/test_pr_report_discipline.py` | 163 passed，5 skipped，0.67s | installer-final-focus.log |
| `python /tmp/installer_pressure.py`，4 CPU burners×3 | 每轮66 passed、5 skipped，2.12/1.56/0.74s；无修改Qt时序代码，针对本轮文件I/O和旧门禁高负载复跑 | installer-pressure-verified.log |
| `node --test tests/test_bridge_hardfailure.js tests/test_bridge_interaction_dedup.js tests/test_bridge_manifest.js tests/test_bridge_question_callid.js tests/test_bridge_retry.js tests/test_bridge_root_control.js tests/test_bridge_user_action_guard.js` | 34 passed，0 skipped | installer-node.log |
| `node integrations/dsh-pet-bridge/verify_import.mjs` | zero-dependency smoke PASS | installer-bridge.log |
| `python -m ruff check pet/ tests/ scripts/verify_installer_payload.py`；`python -m compileall -q pet scripts tests`；`git diff --check` / `git diff --cached --check` | PASS：All checks passed、compileall成功、diff无空白问题 | installer-ruff/compile-final/diff-check.log |
| 原生PowerShell5.1 ParseFile、ISCC编译、真实ZIP/TTS/Qt gate、Setup安装/升级/卸载、签名分支 | NOT TESTED/NOT BUILT，等用户本机 | 新指南给出完整命令 |

末次发现大写.JSON绕过旧凭据助手的大小写判断，新增真实失败用例后将扩展名归一化再调用原助手，修后整族通过并再次完整重跑。前一完整主组5057 passed/50 skipped/18 warnings（811.80s）保留，不拿它充当最后代码结果。首次全量在补充安全用例时主动停止，未作为完整结果；四个追加拒绝用例修补前真实失败（db-wal/shm/journal及Authorization），修补后重新从头执行最终全量。另35项初版及中间聚焦不叠加最终计数。最终CI主组+41+27去重：5126 passed、50 skipped（5058+41+27），18条既有Qt弃用告警：QImage.mirrored、QDragEnterEvent/QHoverEvent旧构造，不改这些动画/事件接口。原native测试及平台skip不算安装成功。

风险与边界：Linux静态契约不能证明Pascal/PowerShell在原生平台执行；新native ISCC编译和PS现存输出保护用例在Linux跳过。用户必须先原生编译再完成12项验收；WMI不可用会拒绝安装/卸载而非绕过保护。未知任意ZIP不获得官方认证，真正分发须使用已经过原构建/本轮门禁的指定ZIP；无法从合成文件证明真实便携包没有个人数据。固定路径有意拒绝/DIR覆盖外部绿色目录。已有自启未勾选迁移时保留原路径，须保留旧目录或在应用中明确重新设置。无证书不伪造签名/信誉，真正跨版本升级与签名路径另需实测。完成提交后停止，等待用户Windows构建和安装验收。
