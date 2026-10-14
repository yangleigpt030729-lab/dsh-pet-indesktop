# 大肥鱼桌面宠物 v1.0.0：Windows 原生安装包构建与验收

> 历史 v1.0.0 快照，原产物与证据保留。当前 v1.0.1 必须按[新指南](WINDOWS-INSTALLER-V101-ACCEPTANCE.md)从最新源码重新构建；不要在新分支使用本页旧 PortableZip 命令。

基线为 `feature/win10-companion-memory` 的 `533eb1c`。用户已在 Windows10 22H2 x64 确认十项增量全部通过：微软语音、音量/静音/热更新/双向同步、静音投喂统计/及时回复朗读、识屏前置与最终回复、岛聊天/授权/动画/拖拽。**本轮仅封装安装器**，这些成功记录保留；新 Setup 的编译、安装、升级、卸载及 Windows11 均 **NOT TESTED**，直到本机执行。关联[交付报告](PR-REPORT-INSTALLER-V100-2026-10-14.md)、[onedir说明](ONEDIR_PACKAGING.md)、[原便携验收指南](WINDOWS10-COMPANION-ACCEPTANCE.md)。

## 1. 准备一次，不动旧包和数据

- 用普通 **Windows PowerShell 5.1 x64**，无需 Git/GitHub Desktop。先退出所有大肥鱼和独立设置窗口。
- 从 [Inno Setup 官方网站](https://jrsoftware.org/isdl.php) 安装 **Inno Setup 6.5+**。不自动下载安装、不改变 Defender/系统持久执行策略。默认路径自动查找；特殊安装目录可在构建命令加 `-IsccExe 'E:\tools\InnoSetup6\ISCC.exe'`。
- 保留 `FishCompanionBuildExperience20261013`、`FishPortableExperience20261013`、旧源码及原 ZIP。它们只是输入，不会被修改。已验收 ZIP 的 EXE 在解压根目录，旁边是完整 `_internal`。
- 构建用旧成功构建的 `build-venv\Scripts\python.exe`，其已有 PyInstaller/pefile/edge-tts/Qt；脚本不安装依赖、不修改该 venv。**最终使用 Setup 的用户不需要 Python、Qt、ffmpeg 或命令行**。
- 打开[开发分支](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/tree/feature/win10-companion-memory)，Code → Download ZIP，保存为 `D:\Code\FishInstallerSourceV100.zip`。不能使用旧构建暂存中的脚本代替新增入口。

下列每段只有一条命令，在同一 PowerShell 窗口逐条复制。若标注的全新目录已存在，统一改成 `R2` 等新后缀，绝不删除或覆盖旧产物。

```powershell
if (Test-Path 'D:\Code\FishInstallerSourceV100') { throw 'Use a NEW source directory.' }
```

```powershell
Expand-Archive -LiteralPath 'D:\Code\FishInstallerSourceV100.zip' -DestinationPath 'D:\Code\FishInstallerSourceV100'
```

```powershell
$installerSource = (Get-ChildItem 'D:\Code\FishInstallerSourceV100' -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'scripts\build_windows_installer.ps1') } | Select-Object -ExpandProperty FullName)
```

```powershell
if (-not $installerSource -or @($installerSource).Count -ne 1) { throw 'Expected one updated source root.' }
```

```powershell
Set-Location $installerSource
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\check_powershell_scripts.ps1
```

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Stop: PowerShell parse preflight failed.' }
```

`Bypass`仅限这次明确执行的已审查脚本进程，不写持久策略；脚本自身不运行 Set-ExecutionPolicy、不关闭系统安全功能。中文 `.ps1` 为 UTF-8 BOM，并由原 ParseFile 门禁检查。

## 2. 一条命令制作安装包

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_installer.ps1 -PortableZip 'D:\Code\FishCompanionBuildExperience20261013\dsh-pet-companion-win10\dist-onedir\dsh-pet-standalone-webm-chat-portable.zip' -OutputDir 'D:\Code\FishReleaseV100' -PythonExe 'D:\Code\FishCompanionBuildExperience20261013\build-venv\Scripts\python.exe'
```

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Build failed. Preserve FishReleaseV100 and build.log; do not distribute.' }
```

```powershell
Get-FileHash -LiteralPath 'D:\Code\FishReleaseV100\大肥鱼桌面宠物_Setup_v1.0.0.exe' -Algorithm SHA256
```

```powershell
Get-AuthenticodeSignature -FilePath 'D:\Code\FishReleaseV100\大肥鱼桌面宠物_Setup_v1.0.0.exe' | Select-Object Status
```

输出：Setup.exe、build.log、payload-manifest.json（每个安装文件的大小/SHA256及原ZIP校验）、setup-manifest.json（安装器版本/大小/校验/签名状态）和构建暂存 `build`。**只分发一个 Setup.exe**；不要分发 build、reviewed-source.zip 或用户备份。成功构建并不等于完成安装验收。

本轮无证书的结果应为 `NotSigned`；**Windows SmartScreen 可能显示未知发布者提示**。先核对来源与 SHA256；不宣称已获微软信誉认证。不要为安装关闭 Defender/SmartScreen。将来有正规 CurrentUser 证书时，可显式传入 `-SignToolExe`、`-CertificateThumbprint`、`-TimestampUrl`，脚本让 Inno 同时签 Setup/卸载器并检查 Setup 签名；证书私钥从本机证书存储使用，不导出、不传 PFX 密码。这条签名分支本轮 **NOT TESTED**。

## 3. 安装、启动、升级及卸载验收

建议先在 Windows10 的测试账户或隔离环境执行，避免试验污染日常数据。为现有普通模式数据做本地备份（不是验收 Fake 数据目录）；备份含私人聊天/缓存，仅自己保管，不上传：

```powershell
if (Test-Path 'D:\Code\FishUserDataBackupV100') { throw 'Use a NEW private backup directory.' }
```

```powershell
if (Test-Path "$env:APPDATA\dsh-pet-standalone-webm-chat") { Copy-Item -LiteralPath "$env:APPDATA\dsh-pet-standalone-webm-chat" -Destination 'D:\Code\FishUserDataBackupV100' -Recurse }
```

密钥仍在原 Windows 凭据存储；备份命令不导出凭据。安装器不读取/迁移/删除这些数据。原 Fake/live 验收目录仍独立，快捷方式启动的是正常模式，不能把此前 Fake 隔离目录误当作默认 APPDATA。

```powershell
Start-Process -FilePath 'D:\Code\FishReleaseV100\大肥鱼桌面宠物_Setup_v1.0.0.exe' -ArgumentList '/LOG=D:\Code\FishReleaseV100\install.log' -Wait
```

| 步骤 | 操作和通过标准 |
|---|---|
| 1–2 首次安装 | 从全新发布目录双击 Setup；当前用户安装，无强制管理员权限，目标 `%LOCALAPPDATA%\Programs\DaFeiYuDesktopPet`；完整离线复制 EXE和_internal。已存在但没有本 AppId 登记的同名目录必须停止，不覆盖旧绿色版 |
| 3–4 快捷方式 | 默认创建桌面图标，可取消；开始菜单图标始终创建，名称为大肥鱼桌面宠物，图标正确。分别启动成功，不需要 Python/命令行；完成页启动可取消 |
| 5 原界面 | 动画、透明边缘、拖动、右键设置/菜单及主子宠正常；未改WebM/运行策略 |
| 6–7 语音 | 真实微软在线试听、每宠音色，0–100热音量、静音恢复及已打开设置双向同步正常；冷/热缓存、关开朗读、统计静音回归 |
| 8 原AI | 岛聊天/投喂统计及及时趣味回复/明确授权文本解读/识屏提示与最终朗读正常；用无私人内容验收，DeepSeek/微软请求与Fake结果分开记录 |
| 9 运行中升级保护 | 运行桌宠或仅开独立设置时再开Setup，必须提示退出并允许重试/取消；未经确认不结束进程。WMI检测失败时停止，不能绕过保护 |
| 9–10 覆盖安装 | 完全退出全部窗口，同一个Setup再次覆盖安装（验证覆盖路径，不是假装已有v1.0.1）；固定AppId和安装路径复用、快捷方式不重复，原设置/音量/聊天/记忆/缓存/凭据仍在。真正新版本升级仍需未来版本实测 |
| 自启 | 首次未有自启时不创建Run项。已有本变体自启时，仅勾选迁移任务才改原同名Run值到安装路径；不会新增第二项。未勾选则保留原绿色版项，旧目录不删除。其他变体不动；再次登录验证已迁移项 |
| 11 卸载 | 完全退出，从Windows应用和功能卸载；显示大肥鱼桌面宠物、版本1.0.0；运行中卸载应提示退出/重试而非强杀 |
| 12 数据与清理 | 安装器登记的应用文件/快捷方式清理；不使用通配删除整个目录，用户自行加入的文件保留。APPDATA聊天/SQLite含WAL/配置/MP3/WAV缓存/凭据/独立便携目录与旧ZIP仍在。仅指向本安装路径的本变体Run值清理，其他便携自启保留 |

运行检查与打开应用和功能（各一条）：

```powershell
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\DaFeiYuDesktopPet\dsh-pet-standalone-webm-chat.exe"
```

```powershell
Start-Process 'ms-settings:appsfeatures'
```

安装器不提供选项删除个人数据、不修改系统默认扬声器/音量、不创建启动文件夹第二项。底层可执行文件名及内部上游应用版本保持原样：**本封装安装器的Apps & Features/VersionInfo版本是1.0.0**，不改原应用4.2.1更新检测基准，不发布tag/Release。未来更新此封装版本时维持固定AppId，配套更新版本/输出名和清单测试；不要混用旧通用dsh-pet.iss的AppId。

## 4. 故障、回退与反馈

- 出错保留新目录和build.log。输入ZIP只读，失败不去删除或修补旧绿色版。新输出目录不能复用；改用 `FishReleaseV100R2` 重试。
- 找不到ISCC：先安装官方6.5+或明确指定真实 `-IsccExe`。缺Python工具：用已成功构建的build-venv，不为了安装包改正式用户venv。安全/Qt/资源/编码检查失败必须停止，不加skip开关。
- Setup未安装成功时继续从 `D:\Code\FishPortableExperience20261013\dsh-pet-standalone-webm-chat.exe` 启动已验收旧版，路径确为解压根目录。安装后要回退则退出安装版再启动旧绿色版；用户自启由同一原设置开关管理。
- 反馈版本、源码提交、ZIP/Setup SHA256、Windows版本、Inno版本、build.log及每项PASS/FAIL/NOT TESTED。安装日志可能包含本机用户名/路径，分享前检查脱敏；**不上传个人APPDATA、数据库、凭据、语音文件或备份**。
- Windows11安装、真正跨版本升级、签名证书/时间戳、WMI限制环境、SmartScreen提示及真实网络/声音都按实际执行记录；模拟/编译成功不能代替。

可用新源码及成功构建venv跑自动化（不是安装验收）：

```powershell
& 'D:\Code\FishCompanionBuildExperience20261013\build-venv\Scripts\python.exe' -X utf8 -m pytest -q tests/test_windows_installer.py tests/test_powershell_encoding.py tests/test_companion_acceptance_package.py tests/test_autostart.py --basetemp='D:\Code\FishInstallerPytestV100'
```

仅在该venv已按此前指南安装pytest时执行；basetemp为专门全新测试临时目录，pytest会清理它，绝不能指向个人数据或旧构建。ISCC测试仅编译临时合成输入，不安装或启动；输出不能当作正式安装包。
