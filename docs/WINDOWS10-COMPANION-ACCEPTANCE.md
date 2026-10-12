# Windows 10 22H2 x64：P2-B 源码运行与实机验收

本指南面向 `feature/win10-companion-memory`，不是 main，也不是上游旧 Releases。
用户已在 **Windows 10 22H2 x64 / Python 3.12 x64** 实测 GUI 启动、桌宠可见、主动AI设置页面、灵动岛设置入口，以及临时显式注入 Fake 后的“合成测试”气泡。原版右键设置失败、默认 Fake 不触发也已记录。本轮正式修补的 Windows 复验、完整验收、真实 DeepSeek 联网、PowerShell 准备脚本及新 EXE 仍为 **NOT TESTED**。
本轮提供可复现源码测试包及固定依赖环境，不制作 P5 正式发行版。
关联：[实机问题修补报告](PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md)、[上一轮加固](PR-REPORT-COMPANION-PROACTIVE-HARDENING-2026-10-12.md)。

## 已有 Python 3.12 环境：最短更新与复测

1. 托盘“全部退出”，下载开发分支的**新 ZIP**，解压到新目录，例如 `D:\Code\FishRetest`；不要覆盖合并旧源码，不要复制临时修补或 `scripts\run_companion_acceptance.py.bak`。保留原 `D:\Code\FishVenv312` 和隔离数据 `D:\Code\FishAcceptance`，无需 Git、GitHub Desktop 或 EXE。
2. PowerShell 进入新解压根目录（有 `pet`、`assets`、`scripts` 的那一层），使用已经成功的解释器：

```powershell
Set-Location 'D:\Code\FishRetest\实际解压后的项目目录'
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -c "import sys,PySide6; print(sys.version,PySide6.__version__)"
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishAcceptance'
```

3. 右键“桌宠设置”应打开与灵动岛相同的设置窗口；重复点击只前置已有窗口，关闭后能重新打开。生成合成气泡后，控制台出现 `FAKE: synthetic proactive bubble displayed`。首次候选在约1.5秒尝试，失败条件则等待30秒调度；全屏、隐藏、聊天/重要提示、最近成功展示或离开电脑仍会延后，不能承诺固定时间必发。
4. 原测试数据可能已记下此前成功气泡，重启仍受30分钟间隔和每天10条限制。要复验首次展示，用新的**外部**目录，例如 `--data-dir 'D:\Code\FishAcceptanceRetest'`，不要删 SQLite 或修改系统时钟。测试资料仍须用合成信息，无需提供 API Key。
5. 分别设置 `$env:PET_RENDER_TOPOLOGY='legacy'` 和 `'overlay'`，每次全部退出后换独立目录；复验右键设置、灵动岛设置、关窗重开、多宠子宠对应角色、默认 Fake 气泡、手动聊天优先、退出。首次气泡不是完整Windows验收。

## 1. 用 GitHub 网页下载，不用 GitHub Desktop

1. 打开 https://github.com/yangleigpt030729-lab/dsh-pet-indesktop ，在左上分支选择器选 **feature/win10-companion-memory**。
2. 点击 **Code → Download ZIP**。亦可使用 https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/archive/refs/heads/feature/win10-companion-memory.zip 。
3. 右键 ZIP → 全部解压，放到普通本地目录，例如 `C:\DshPetTest`。不要直接在压缩包内运行。项目根目录应同时有 `pet`、`assets`、`requirements.txt`、`scripts`。
4. 使用交付消息中的新提交版本；`586b776` 是上轮版本，不含本轮收尾。需要固定快照时，GitHub 的 `/archive/<完整提交SHA>.zip` 可替换上述分支ZIP；无需安装Git。
5. 源码下载不是 EXE，以下通过 Python 运行。现有安装版先用托盘“全部退出”关闭。

## 2. Python 与依赖

安装 **Python 3.11 x64**，包含 Windows `py` launcher。官方安装器入口：https://www.python.org/downloads/windows/ 。选择3.11的Windows installer (64-bit)，不要选32位、embeddable或仅源码压缩包。
在解压目录空白处“在终端/PowerShell中打开”，或执行 `Set-Location 'C:\DshPetTest\实际解压后的项目文件夹'`。

```powershell
py -3.11 -X utf8 --version
py -3.11 -X utf8 -c "import struct; print(struct.calcsize('P')*8)"
# 上一条应为64
py -3.11 -X utf8 -m venv .venv-win10
.\.venv-win10\Scripts\python.exe -X utf8 -m pip install -r requirements.txt -c packaging\constraints-win10-companion.txt
.\.venv-win10\Scripts\python.exe -X utf8 -m pip check
.\.venv-win10\Scripts\python.exe -X utf8 -c "import PySide6;from PySide6.QtCore import qVersion;print(PySide6.__version__,qVersion())"
```

末条目标为 **6.8.3 / 6.8.3**。测试配置选择Qt6.8版本线以覆盖Win10，而不是任意升级最新Qt；锁定文件不改变原requirements的运行声明。CI使用Python3.11；用户已用Python3.12 x64及此约束成功安装、启动GUI、显示临时修补后的Fake气泡。可继续使用已有3.12环境；新建3.12环境时将 `py -3.11` 换成 `py -3.12`。这只证明已报告的基础流程，不等于完整Python3.12/Win10验收，也不推广到其他平台或任意Qt版本。云端Python3.12的Qt6.12/6.8.3 offscreen结果另行记录。

主要依赖：PySide6/shiboken6（GUI），imageio-ffmpeg（自带ffmpeg轮子，无需另装系统ffmpeg）、Pillow、keyring/pywin32-ctypes（系统凭据）、certifi、tzdata、lunar-python；原版能力还用edge-tts、psutil、pycaw/comtypes及WinRT媒体投影包。安装edge-tts不代表主动聊天会调用语音。SQLite是Python标准库，无需安装数据库服务。pytest、Ruff用于自动化测试。完整版本及传递依赖见 `packaging/constraints-win10-companion.txt`。

所有安装命令显式加 `-X utf8`，避免中文Windows的GBK requirements解码问题；用户已验证此办法有效。上述直接命令不要求激活venv，也不要求修改PowerShell全局执行策略。可选的 `scripts\prepare_windows_companion.ps1 -PythonVersion 3.12 -RunFocusedTests` 准备3.12环境；默认仍3.11。脚本执行本轮未在Windows验证，下载脚本受执行策略限制时使用直接命令即可。

## 3. 先进行独立 Fake 验收（无真实Key）

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
$env:PYTHONUTF8 = '1'
# 新测试目录在源码目录以外，不使用原版用户数据或凭据
.\.venv-win10\Scripts\python.exe -X utf8 scripts\run_companion_acceptance.py --data-dir C:\DshPetAcceptance
```

默认 **FAKE**：所有ChatService使用合成Provider，不读取/写入系统密钥；urllib联网禁用，设置中的连接测试明确标为模拟。初次测试Provider有独立凭据ref。文字含“合成测试”，用于验证窗口、线程、记忆及频控，**不证明真实模型动态生成**。这只改变独立测试进程/目录；不改变产品默认入口或原版设置。

如果C盘根目录不可写，可用 `--data-dir "$env:LOCALAPPDATA\DshPetCompanionAcceptance"`，但测试数据仍须放在源码目录外。

测试配置与SQLite在 `C:\DshPetAcceptance\dsh-pet-standalone\`。原源码入口通常使用 `%APPDATA%\dsh-pet-standalone\`，原打包变体还可能使用 `%APPDATA%\dsh-pet-standalone-webm-chat\`；验收启动器拒绝源码内部或原版默认目录，默认保留进程内设置。本轮两种右键拓扑都复用ModernSettingsDialog；多宠子设置按slot身份落盘。独立设置进程现在明确携带 `--settings-base` 和角色 `--instance`，Fake验收子进程另携带 `--settings-fake`；即使本机开启进程隔离，也继续使用隔离配置和Fake，不借用生产目录或系统密钥。

- 等待首次合适时机的合成气泡；启用后仍尊重隐藏、全屏、重要提示、聊天窗和30分钟间隔。
- 右键设置 → AI 与对话：检查主动AI开关、每天上限10、最短30分钟、日程增强“尚未实现”。
- 开启长期记忆，在手动聊天用合成信息“请记住我喜欢蓝色”；查看记忆管理，再关闭授权。别用真实住址、号码或公司机密做验收。
- 打开聊天/开始输入，验证普通主动结果让路；分别测试拖动、点击、文件投喂、设置、托盘、角色切换、多宠、透明窗口。文件投喂仍按原有授权规则。
- 同日跨退出/重启，额度不清零；关闭开关后不安排请求。10条及30分钟的快速逻辑验证用下方虚拟时钟自动测试，**不要改系统时钟或把间隔降到0来加速**。

分别测试两种拓扑，每次先从托盘全部退出：

```powershell
$env:PET_RENDER_TOPOLOGY = 'legacy'
.\.venv-win10\Scripts\python.exe -X utf8 scripts\run_companion_acceptance.py --data-dir C:\DshPetAcceptanceLegacy
# 关闭之后，测试overlay
$env:PET_RENDER_TOPOLOGY = 'overlay'
.\.venv-win10\Scripts\python.exe -X utf8 scripts\run_companion_acceptance.py --data-dir C:\DshPetAcceptanceOverlay
```

Overlay本轮选择主宠；主宠被单独隐藏时暂缓，不能在隐藏主宠的位置显示气泡。多宠不能广播同一条普通主动消息。测试完可 `Remove-Item Env:PET_RENDER_TOPOLOGY` 恢复原默认选择。

## 4. 由用户进行真实 DeepSeek 验收

Fake通过后，先全部退出；选新独立目录，显式启用live：

```powershell
.\.venv-win10\Scripts\python.exe -X utf8 scripts\run_companion_acceptance.py --live --data-dir C:\DshPetAcceptanceLive
```

首次新目录主动开关仍默认关闭。设置 → AI与对话：填实际Provider地址、账户可用模型和Key，使用原有本地设置/系统凭据入口保存，先测试连接和手动聊天。**Key只在本机填写，不写源码、约束文件、命令行、截图或ZIP，不发给开发助手。** 新测试目录使用独立的 `provider/acceptance-…` 引用，不覆盖原版Provider的凭据ref。

确认手动聊天后，再明确开启主动陪伴。记录首次问候是否自然、角色是否正确、80字附近长度、气泡是否确实更新；至少观察一轮真正30分钟间隔与下一条不同主题。饮水候选需持续活动1.5小时，休息候选1小时，关心2小时；睡眠/离开/暂停会重置活动。只在关心主题且双授权时读取少量安全记忆。模型若拒绝全system任务/模型名/代理/TLS，记录错误类型及时间，不暴露Key和私人Prompt；此兼容性当前仍NOT TESTED。

原系统代理由Provider正常使用；不要用关闭SSL校验掩盖代理证书问题。真实网络、401/429和费用以用户账户记录验证；云端仅模拟。默认每天最多20次模型尝试、每次96输出token预算，**输入token也计费，次数上限不是人民币费用上限**。

标准产品入口也可直接运行 `.\.venv-win10\Scripts\python.exe -X utf8 -m pet`；它使用正常用户目录，故本轮优先用上述隔离启动器验收。无需打包EXE即可运行原版动画、设置、聊天与本轮功能。

## 5. Windows 自动化复验

下面是子进程offscreen自动测试；完成后移除QT_QPA_PLATFORM再跑真实桌面。

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv-win10\Scripts\python.exe -X utf8 -m pytest -q tests\test_companion_settings_entry.py tests\test_companion_proactive_hardening.py tests\test_companion_proactive_state.py tests\test_companion_proactive_service.py tests\test_companion_proactive_failures.py tests\test_companion_proactive_network.py tests\test_companion_proactive_ui.py tests\test_companion_proactive_schedule.py tests\test_companion_acceptance_package.py tests\test_companion_acceptance_launcher.py tests\test_companion_chat.py
.\.venv-win10\Scripts\python.exe -X utf8 -m pytest -q --ignore=tests/test_webm_reader_lifecycle.py --ignore=tests/test_webm_clip_lifecycle.py --ignore=tests/test_webm_first_frame_lock.py --ignore=tests/test_low_priority_warm_interaction_yield.py
.\.venv-win10\Scripts\python.exe -X utf8 -m pytest -q tests\test_webm_reader_lifecycle.py tests\test_webm_clip_lifecycle.py tests\test_webm_first_frame_lock.py
.\.venv-win10\Scripts\python.exe -X utf8 -m pytest -q tests\test_low_priority_warm_interaction_yield.py
.\.venv-win10\Scripts\python.exe -X utf8 -m pytest -q tests\test_frameseq_prefetch_watchdog.py tests\test_frameseq_clip.py
.\.venv-win10\Scripts\python.exe -X utf8 -m ruff check pet tests
.\.venv-win10\Scripts\python.exe -X utf8 -m compileall -q pet packaging scripts
Remove-Item Env:QT_QPA_PLATFORM
```

如要跑原CI完整桥接门禁，另装Node20+，使用仓库 `.github/workflows/pr-test.yml` 的七个node测试和verify_import命令；Node不是Python源码桌宠的启动依赖。既有 `tests/smoke.py` 固定51素材断言过时，实际106，本轮没有削弱它；请用 `scripts/smoke_companion_proactive.py` 作有界Fake冒烟，但它的offscreen结果不代替桌面人工验收。

## 6. 安全、可复现的测试构建

本轮构建的是 **源码测试ZIP**，不是Linux交叉编译的Windows EXE，不冒充正式发行。首次取GitHub ZIP后、输入任何真实凭据前，在外部输出目录执行：

```powershell
.\.venv-win10\Scripts\python.exe -X utf8 scripts\package_companion_test.py --output C:\DshPetTestArtifacts\companion-win10-source.zip
.\.venv-win10\Scripts\python.exe -X utf8 scripts\package_companion_test.py --verify C:\DshPetTestArtifacts\companion-win10-source.zip
Get-FileHash C:\DshPetTestArtifacts\companion-win10-source.zip -Algorithm SHA256
```

相同源码字节生成相同ZIP：路径排序、时间戳/权限固定，内含逐文件SHA256。真实Git checkout只选已跟踪公开文件；GitHub ZIP无.git时按相同顶层白名单选择。用户config、SQLite、日志、.env、私钥、venv及node_modules均不进入；非空JSON凭据字段、密钥格式文本、外部symlink使整个构建失败，且不覆盖先前成功ZIP。**不要手工复制APPDATA、聊天库或系统凭据到包中。** 解压后再次按固定约束创建venv即可。

如后来确实需要Windows测试EXE，可在Windows专用干净venv按原 [ONEDIR_PACKAGING](ONEDIR_PACKAGING.md) 使用 `scripts\build_onedir.ps1 -Variant webm-chat`，额外需要PyInstaller和Node；保留原编码/瘦身校验，构建完成检查根目录未夹带数据。该流程已有项目实现，本轮没有改写、没有执行Windows EXE构建，也没有给出可下载新EXE：**NOT TESTED / NOT BUILT**。

## 7. 实机记录（不要记录秘密）

提交给审查时填：源码提交/ZIP SHA256、winver显示22H2/build19045、x64、Python/Qt版本、DPI/屏幕数、拓扑、测试命令及真实结果。人工逐项记录PASS/FAIL/NOT TESTED：透明/置顶、拖动点击、投喂、两套聊天窗、旧气泡拒绝与新内容回执、开关撤销、记忆查看/删除、不说话时动画推进、角色切换、多宠、全屏、Win+L锁屏、睡眠/恢复、退出/注销/关机、跨午夜/重启、真实Provider生成/取消/费用。

普通消息午夜前5秒暂缓，不是夜间免打扰；跨日/时区突变或过期回执不转借新日额度。不确定的崩溃展示保守占位；校验失败不伪造成功。SQLite v1主动库迁移到v2，长期记忆库schema不变。回滚只关闭功能或恢复源码，**不删除两份用户SQLite**；旧v1代码不识别v2状态库时应安全拒绝服务。

P2-C可靠日程/outbox/补发、P3/P4未实施；本轮结束后等待用户实机验收，不推进这些阶段。
