# 大肥鱼 v1.0.1 安装目录与构建来源修补

基线 `843142cb9765c31dca17886287cdc384164fbc2d`；独立分支 `fix/installer-v101-custom-directory`，2026-10-14。关联[原生指南](WINDOWS-INSTALLER-V101-ACCEPTANCE.md)、[v1.0.0历史证据](PR-REPORT-INSTALLER-V100-2026-10-14.md)、[源码修复报告](PR-REPORT-SPEECH-LIFECYCLE-2026-10-14.md)。

## 修改文件说明

共14文件，仅安装封装/测试/CI/文档。相对843142c的 `git diff --numstat`：

| 文件 | 增删 | 原因与实际改动 |
|---|---|---|
| `.github/workflows/pr-test.yml` | +1/−0 | CI显式安装原已有构建工具锁定文件，真实PyInstaller归档测试不能因缺工具在收集期失败；运行依赖不变 |
| `CONTEXT.md` | +4/−0 | 登记1.0.1目录和强制新源码构建规则，与前轮业务区分 |
| `packaging/dafeiyu-v1.iss` | +88/−17 | 显示目录页、复用旧目录、校验实际所选路径；空目录/本AppId登记升级/换盘拒绝/系统数据及联接保护；版本/文件名1.0.1 |
| `scripts/build_windows_installer.ps1` | +35/−22 | 删除PortableZip输入，强制新WorkDir重新执行原构建，来源检查两次；新输出/版本/来源清单；签名及原门禁保留 |
| `scripts/verify_installer_payload.py` | +1/−1 | 独立安装器身份版本1.0.1；既有隐私/结构/PE/完整清单验证不变 |
| `scripts/verify_installer_source.py`（新增） | +133/−0 | 原始源码、暂存源码、实际PYZ全部pet模块、ZIP内EXE和收据一致性检查；至少八个关键修复模块必需；机器文件名差异不引发假失败 |
| `tests/test_windows_installer.py` | +74/−8 | 更新原专用契约；新增目录页/实际目标、目录安全/换盘、版本/名/新源码工作流和单行命令契约；原原生编译测试保留 |
| `tests/test_installer_source.py`（新增） | +113/−0 | 使用真实CArchive/PYZ读写验证旧EXE、旧ZIP、源码/暂存/收据篡改、缺源证据拒绝；真实修复源码编译；非关键pet模块也必须一致 |
| `docs/WINDOWS-INSTALLER-V101-ACCEPTANCE.md`（新增） | +143/−0 | 新源码ZIP→全新原生便携→Setup的逐条单行PowerShell、升级/换盘/卸载及数据/自启验收 |
| `docs/WINDOWS-INSTALLER-V1-ACCEPTANCE.md` | +2/−0 | 仅增加历史快照标记和新指南链接，旧报告/产物证据不覆盖 |
| `docs/ONEDIR_PACKAGING.md` | +5/−0 | 专用1.0.1流程入口；不混用旧通用ISS |
| `docs/STABLE_BUILDS.md` | +5/−1 | 登记独立新候选并保留旧稳定产物；补末尾换行 |
| `docs/INDEX.md` | +8/−0 | 新指南和报告互链登记 |
| 本报告（新增） | +75/−0 | 根因、测试、性能、原生边界和回退证据 |

`git diff --name-only 843142c -- pet assets requirements.txt packaging/constraints-win10-companion.txt`为空。摸头、识屏、授权解读、分页、TTS生命周期、报时、别名、模型、动画、微软接口及依赖版本无变化；旧通用 `dsh-pet.iss`无变化。用户文件/数据没有输入、修改或上传。

## 实现与安装安全

根因同时在 `DisableDirPage=yes` 和 `PrepareToInstall()` 的固定LocalAppData目标，两处共同造成不能选D盘。新版为 `DisableDirPage=no` / `UsePreviousAppDir=yes`，校验的Target来自实际 `{app}`，LocalAppData只做默认值。允许新/真正空的专用本地D/E目录。拒绝根目录、Windows/用户数据/个人根、链接/联接祖先、非空未登记目录及目录身份损坏；正常Inno权限检查仍在，不提升权限。

已登记本AppId时仅允许同目录升级，并要求原EXE/_internal/unins000.exe/dat齐全。选择不同目录会明确停止，要求正常卸载旧版、确认旧登记清除后重新安装；不自动搬目录或删旧登记，不静默遗留第二个安装。卸载按原Inno登记文件清理，保留自行添加文件及AppData/凭据/缓存。固定AppId `662C52E9-287D-43C4-90DE-4A0B9061C7C4`、当前用户安装、图标/快捷方式/卸载入口、拒绝强杀、WMI失败停止、可选原自启迁移和签名不变。换盘卸载会清理仅指向旧安装的自启，需要用户从原设置明确重新开启。

安装器1.0.1和新输出名独立，原内部应用版本4.2.1不变。构建入口不接受旧ZIP：当前安全源码ZIP→新的固定依赖venv/真实PyInstaller onedir→新portable→来源/隐私/资源/TTS/Qt/编码门→专用ISS。来源检查核对完整原源码/暂存哈希（仅原流水线重新生成的icon.ico例外）、实际PYZ全部pet代码结构和常量、ZIP内EXE。机器文件名/序列化interning不参与代码比较，源码哈希仍全保留。源文件、ZIP和EXE收据链供审查，不能冒充数字签名或对不可信来源的认证。

## 性能分析

实测Linux/Python3.12.14，cgroup `cpu.max=400000 100000`（4核配额），当前采样源码949文件、97,824,372字节，三轮源文件SHA256耗时0.0862/0.0932/0.0917秒；八个关键模块编译+代码结构签名0.0346/0.0442/0.0463秒，测量进程峰值RSS21,660KiB。均为本地文件真实读取/编译，不是Windows或真实149MB便携包耗时。

可复现源哈希测量：在已激活Python的仓库执行 `python -c "from pathlib import Path; from time import perf_counter; from scripts.package_companion_test import source_files; from scripts.verify_installer_source import sha256; p=list(source_files(Path.cwd())); t=perf_counter(); h={n:sha256(f) for n,f in p}; print(len(h),sum(f.stat().st_size for _,f in p),perf_counter()-t)"`；八模块按 `MODULES` 逐一 `code_signature(compile(path.read_bytes(),str(path),'exec',optimize=0))`测量。源码数量/总字节为采样时值，文档最终补证后可能变化。

四个CPU忙循环下运行 `python -m pytest -q tests/test_windows_installer.py tests/test_installer_source.py`三次：每轮69通过2跳过；pytest1.43/1.34/1.95秒，包含启动开销的墙钟1.975/1.937/2.613秒。测试用合成归档，不能代表原生压缩/安装性能。

应用稳态成本变化为零：pet运行代码未改。新增源校验仅在构建后和Inno前各一次，顺序磁盘读取/哈希和逐模块内存编译，无新增服务、线程或网络。完整payload既有逐文件哈希门保留；收据/日志仅在新发布目录增长，程序用户缓存不增长。新venv依赖安装和PyInstaller重建仍会有原网络/磁盘/CPU开销，原生总耗时NOT TESTED；不宣传构建零耗时。

## 实机运行记录

只读核对远端修复分支HEAD为843142c。现场源码读到旧 `DisableDirPage=yes`及固定LocalAppData强制比较，新增两条契约测试在修补前确实2 failed（日志 `/tmp/installer-v101-red.log`），修补后通过。源码归档测试使用真实PyInstaller格式和文件系统，并实际拒绝旧代码/旧ZIP/篡改；这些合成归档不是可运行Windows程序。

环境探针：`uname -s`输出Linux，`python --version`为3.12.14；`command -v powershell.exe pwsh wine ISCC.exe`没有结果。不存在可执行Windows安装程序的环境。**Windows Setup NOT BUILT**，原生Inno编译、目录策略执行、安装/同目录升级/卸载迁移/签名/Windows11均 **NOT TESTED**。PowerShell BOM/静态合同通过不等于原生5.1解析成功。用户先前真实Windows语音及交互成功记录保持，不把本轮Linux/Fake结果冒充新Setup验收。安全失败测试确实保留原输入/既有输出/收据且拒绝篡改。

## 测试与验证

| 检查与命令 | 本次真实结果 |
|---|---|
| 修补前 `pytest -q tests/test_windows_installer.py -k v101` | 2 failed、50 deselected，目录页和旧PortableZip入口原问题 |
| 聚焦（见下方文件族）/主Qt6.12.0 | 227 passed、5 skipped，1.40秒 |
| 相同聚焦/Qt6.8.3 | 227 passed、5 skipped，1.27秒；补安装原已有构建工具pin后成功，无产品依赖变化 |
| 4核满载三轮 | 每轮69 passed、2 skipped；无失败 |
| CI主套件四个ignore，日志installer-v101-full | 5159 passed、50 skipped、19 warnings，815.94秒；XML零failure/error |
| CI独立WebM三文件 | 41 passed、25.92秒 |
| CI低优预热 | 27 passed、31.32秒，首次通过 |
| CIframeseq/prefetch | 37 passed、0.85秒，首次通过 |
| Node既有七个文件/verify_import.mjs | 34 passed、0 skipped；hermetic import门PASS |
| `ruff check pet/ tests/ scripts/verify_installer_source.py scripts/verify_installer_payload.py` | PASS |
| `python -m compileall -q pet scripts tests` / Git staged及未暂存diff check | PASS |
| 安全源码ZIP制作/验证 | PASS：949源码文件SHA256/凭据检查；仅源码ZIP，不是EXE |

聚焦文件：`tests/test_windows_installer.py tests/test_installer_source.py tests/test_powershell_encoding.py tests/test_companion_acceptance_package.py tests/test_verify_bundle_tts.py tests/test_bundle_slim.py tests/test_bundle_encoding_check.py tests/test_autostart.py tests/test_architecture.py tests/test_pr_report_discipline.py`。

主套件命令：`python -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py`。WebM独立命令：`python -m pytest -q tests/test_webm_reader_lifecycle.py tests/test_webm_clip_lifecycle.py tests/test_webm_first_frame_lock.py`。其余独立命令与CI一致，见日志及下方结果。聚焦5跳过为Windows原生PowerShell/ISCC能力；目录安全测试是明确标记的静态Inno契约，真正分支执行必须走Windows指南。主套件19条Qt旧API弃用告警；50跳过含平台原生API/真实音频和可选能力。CI四分组去除frameseq重复执行项，共5227 passed、50 skipped；frame37项在主套件中已有一次。最终主套件以独立完整执行的XML计数为准；早期被中断的测试子进程已清理，不计入结果。

## 风险与回滚

原生编译和目录规则仍需Windows10 x64/PowerShell5.1/Inno6.5+实际执行：新D/E目录、空目录、无权限/非空/portable/联接拒绝、C原位升级及官方卸载后D重装、卸载保留数据。不得先宣布正式验收。损坏卸载登记须通过原官方卸载入口处理，不手动删除或强行覆盖。新输出只有 `大肥鱼桌面宠物_Setup_v1.0.1.exe`，未签名时SmartScreen可能未知发布者。原v1.0.0包、原源码/构建、旧ZIP和既有用户数据均保留；不合并main、不发布Release。失败保留新日志和目录，使用新R2目录重试；已验证旧便携版保留为回退，先完全退出新程序。没有修改运行期配置迁移或用户文件。
