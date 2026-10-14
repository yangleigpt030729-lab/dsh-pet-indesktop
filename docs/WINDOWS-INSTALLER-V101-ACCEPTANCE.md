# 大肥鱼 v1.0.1：自选安装目录、重新构建和 Windows 验收

基线：`fix/tts-bubble-lifecycle-and-interactions` 的 `843142c`，发布修补分支 `fix/installer-v101-custom-directory`，2026-10-14。本轮仅改安装封装。**Windows Setup NOT BUILT**；Windows10/11 原生编译、路径检查执行、安装/升级/卸载均 **NOT TESTED**。此前用户的 Windows 语音/交互成功证据保留，不能代替本轮安装验收。相关：[报告](PR-REPORT-INSTALLER-V101-2026-10-14.md)、[历史 v1.0.0 指南](WINDOWS-INSTALLER-V1-ACCEPTANCE.md)、[源码修复指南](WINDOWS10-SPEECH-LIFECYCLE-ACCEPTANCE.md)、[onedir](ONEDIR_PACKAGING.md)。

## 1. 准备最新源码，保留全部旧目录

普通 Windows10 PowerShell5.1 **x64**，Python3.12 x64、Inno Setup **6.5+**（[官方](https://jrsoftware.org/isdl.php)）。不要改旧虚拟环境、用户数据或安全策略。构建会创建独立的新 venv，按现有 constraints 安装 Qt6.8.3 / PyInstaller6.19.0；构建阶段安装依赖需要网络，最终 Setup 是完整离线安装包。先从托盘退出所有桌宠并关闭独立设置窗口。

打开[发布修补分支](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/tree/fix/installer-v101-custom-directory)，Code → Download ZIP，保存为 `D:\Code\FishInstallerSourceV101.zip`。绝不能使用旧源码或旧 v1.0.0 portable ZIP；新入口没有 `-PortableZip` 参数。

以下每块一条完整命令，均在同一 PowerShell 窗口逐条复制。目录已存在时改成新 R2 后缀，不能删除或覆盖。旧 `FishReleaseV100`、`FishCompanionBuildExperience20261013`、`FishPortableExperience20261013`、旧 Setup/ZIP 和日志全部保留。

```powershell
if (Test-Path 'D:\Code\FishInstallerSourceV101') { throw 'Use a NEW source directory.' }
```

```powershell
Expand-Archive -LiteralPath 'D:\Code\FishInstallerSourceV101.zip' -DestinationPath 'D:\Code\FishInstallerSourceV101'
```

```powershell
$v101Source = @(Get-ChildItem 'D:\Code\FishInstallerSourceV101' -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'scripts\build_windows_installer.ps1') } | Select-Object -ExpandProperty FullName)
```

```powershell
if ($v101Source.Count -ne 1) { throw 'Expected exactly one new source root.' }
```

```powershell
Set-Location $v101Source[0]
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\check_powershell_scripts.ps1
```

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Stop: native PowerShell parse failed.' }
```

`Bypass`仅限这次已审查脚本进程，不修改持久执行策略。`.ps1`/`.iss`保留 UTF-8 BOM。

## 2. 一步重新构建便携版并制作安装包

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_installer.ps1 -PythonExe 'D:\Code\FishVenv312\Scripts\python.exe' -WorkDir 'D:\Code\FishCompanionBuildV101' -OutputDir 'D:\Code\FishReleaseV101'
```

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Build failed; retain both NEW directories and build.log; do not distribute.' }
```

特殊 Inno 路径可在上述同一行末尾加 `-IsccExe 'E:\tools\InnoSetup6\ISCC.exe'`。缺少编译器时脚本停止并给官方安装地址，不自动下载工具。不能加 SkipBuild/SkipSlim 或跳过门禁。PyInstaller 原安全门、资源/DLL/编码/微软 TTS/隔离 Fake EXE和设置窗口冒烟继续执行。

流程是：当前源码安全 ZIP → 新 WorkDir/venv → 真正 PyInstaller x64 windowed onedir → 新根目录 EXE + `_internal` portable ZIP → 原始源码/暂存源码哈希验证 → EXE 内真实 PYZ 的全部 `pet` 模块逐一与源码编译结果比较（至少包含八个关键修复模块）→ 完整 ZIP 隐私/PE/资源验证 → 原冻结 TTS/Qt/编码门 → Inno 大肥鱼专用配置 → 大小/SHA256/签名/来源清单。源码、便携 EXE、ZIP或暂存代码改变会停止；旧 EXE即使布局/名称正确也不能通过源码一致性检查。收据是可复查的构建证据，不是可信数字签名。

新 portable ZIP：`D:\Code\FishCompanionBuildV101\dsh-pet-companion-win10\dist-onedir\dsh-pet-standalone-webm-chat-portable.zip`；EXE在 ZIP 根目录，不能猜额外嵌套目录。

新正式候选：`D:\Code\FishReleaseV101\大肥鱼桌面宠物_Setup_v1.0.1.exe`。同目录的 `build.log`、`source-build-manifest.json`、`payload-manifest.json`、`setup-manifest.json`及新 WorkDir/依赖清单是证据，保留而不随 Setup 分发。

```powershell
Get-FileHash -LiteralPath 'D:\Code\FishReleaseV101\大肥鱼桌面宠物_Setup_v1.0.1.exe' -Algorithm SHA256
```

```powershell
Get-Content -LiteralPath 'D:\Code\FishReleaseV101\setup-manifest.json' -Encoding UTF8
```

```powershell
Get-AuthenticodeSignature -FilePath 'D:\Code\FishReleaseV101\大肥鱼桌面宠物_Setup_v1.0.1.exe' | Select-Object Status
```

没有正规证书时为未签名候选，**Windows SmartScreen 可能显示未知发布者提示**。不伪造发布者，不关闭 Defender/SmartScreen。可沿用显式 CurrentUser 证书的签名参数，此路径仍待原生验证。只有完成下面验收才能宣布正式包通过。

## 3. 自选目录和同目录升级

安装目录页现在一直显示。默认仍是 `%LOCALAPPDATA%\Programs\DaFeiYuDesktopPet`；已安装时默认使用登记的原目录。可以选择 `D:\Apps\DaFeiYuDesktopPet`、`E:\Apps\DaFeiYuDesktopPet`等当前用户有权限的**专用本地目录**，无需管理员。新目录或真正空目录可用；磁盘根、系统目录、用户数据目录、链接/联接目录、非空未登记目录及旧绿色版禁止。路径不允许网络共享；目录无写权限时安装不得成功。

存在本 AppId 的安装登记时只能同目录覆盖，并要求原 EXE、`_internal`和 `unins000.exe/dat`完整。安装和卸载均提示退出桌宠/独立设置，不强杀。不要手工删除卸载登记来绕过；损坏安装先用原卸载器处理并保留文件和日志。

```powershell
Start-Process -FilePath 'D:\Code\FishReleaseV101\大肥鱼桌面宠物_Setup_v1.0.1.exe' -ArgumentList '/LOG=D:\Code\FishReleaseV101\install.log' -Wait
```

已装 C 盘 v1.0.0、只想升级：确认退出后运行新 Setup，保持原目录。固定 AppId、快捷方式及卸载登记复用，应用和功能版本应为1.0.1。原内部上游应用版本保持4.2.1，不能把这个字段误当安装器版本。

## 4. C → D 安全迁移（先卸载，再安装）

1. 退出全部桌宠/设置。为当前用户 AppData 做**本地私人备份**，不导出系统凭据，不上传任何备份。记录音量、音色、聊天/长期记忆及缓存状态。

```powershell
if (Test-Path 'D:\Code\FishUserDataBackupV101') { throw 'Use a NEW private backup directory.' }
```

```powershell
if (Test-Path "$env:APPDATA\dsh-pet-standalone-webm-chat") { Copy-Item -LiteralPath "$env:APPDATA\dsh-pet-standalone-webm-chat" -Destination 'D:\Code\FishUserDataBackupV101' -Recurse }
```

2. 先运行新 Setup，选择 D 盘应提示先卸载而停止；取消，不能留下第二份安装。打开 Windows 应用和功能，正常卸载旧 v1.0.0。卸载只清理登记的安装文件/快捷方式及指向该安装的自启值，保留 AppData/凭据/缓存/其他绿色版。

```powershell
Start-Process 'ms-settings:appsfeatures'
```

3. 确认原 AppId 卸载登记消失。以下命令是只读校验；未消失就停止，不手工删登记。旧安装目录中若有自行添加文件，保留，不用 Remove-Item 清空。

```powershell
if (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{662C52E9-287D-43C4-90DE-4A0B9061C7C4}_is1') { throw 'Old installation is still registered; stop and use its official uninstaller.' }
```

4. 再运行同一个 v1.0.1 Setup，选全新 `D:\Apps\DaFeiYuDesktopPet`。确认旧卸载器登记清除且 D 盘只有一个新登记。新快捷方式启动，原配置/聊天/记忆/缓存仍可用。不搬动 AppData、不自动复制旧应用目录、不删除旧便携版。

```powershell
Start-Process -FilePath 'D:\Code\FishReleaseV101\大肥鱼桌面宠物_Setup_v1.0.1.exe' -ArgumentList '/LOG=D:\Code\FishReleaseV101\relocate-install.log' -Wait
```

```powershell
Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{662C52E9-287D-43C4-90DE-4A0B9061C7C4}_is1' | Select-Object DisplayName,DisplayVersion,InstallLocation
```

首次安装不启用开机自启。同目录升级保留既有值，只有显式勾选迁移才改同名 Run 值。换盘时旧卸载会清理指向旧安装的自启；需要继续自启时，安装后通过原设置开关显式重新开启，检查同一值指向新目录且无第二项。

## 5. 必须记录的 Windows 验收

| 场景 | 通过标准（尚未执行） |
|---|---|
| 全新 D/E 目录及已有空目录 | 目录页能选、实际文件和卸载登记在所选路径；安装不要求管理员 |
| 保护路径 | 根目录、系统/AppData、无权限目录、联接目录、旧 portable、含 keep.txt 的无关目录应拒绝；keep.txt 和旧 EXE哈希不变 |
| C 盘 v1.0.0 → 同目录1.0.1 | 完全退出后升级成功，固定登记/快捷方式；设置、记忆、聊天、密钥和缓存保留 |
| C → D | 旧登记存在时拒绝改盘；正常卸载保留数据、登记消失后允许新 D 安装，无旧启动入口残留 |
| 运行中安装/卸载 | 主宠、子宠、仅独立设置运行均提示退出；WMI失败停止；不强杀 |
| 快捷方式/资源 | 桌面可选、开始菜单及完成页启动；完整 `_internal`，动画/拖拽/右键/岛聊天正确 |
| 已修复业务 | 微软试听、音量/静音/双向同步、摸头、识屏前置/最终回复、授权解读、分页/TTS生命周期、整点报时、别名；真实网络/声音独立记录 |
| D盘卸载/重新安装 | 应用登记文件清理，自行添加文件保留；AppData/聊天/SQLite含WAL/凭据/语音缓存和旧发布目录不变；可重新选择全新目录 |
| 版本/来源 | Apps & Features及Setup1.0.1；保留源码ZIP/新portable/Setup三个哈希及来源收据，不使用v1.0.0旧ZIP |

如已安装 pytest，可用旧成功构建 venv只运行测试，不改其依赖：

```powershell
& 'D:\Code\FishCompanionBuildExperience20261013\build-venv\Scripts\python.exe' -X utf8 -m pytest -q tests/test_windows_installer.py tests/test_installer_source.py tests/test_powershell_encoding.py tests/test_companion_acceptance_package.py tests/test_autostart.py --basetemp='D:\Code\FishInstallerPytestV101'
```

basetemp须专用新目录，pytest会清理，绝不能用旧构建或个人数据目录。ISCC测试只编译合成输入，不安装/启动，测试输出不能发布。构建失败保留新日志/目录，改用 R2 重试；业务回退继续保留的旧绿色版，完全退出新程序后再启动，勿同时运行。分享日志先脱敏本机路径，不上传 AppData/收据外的私人文件。Windows11、签名、真实安装/升级/卸载均按实际填写 PASS/FAIL/NOT TESTED。
