# Windows 10 22H2 x64：完整陪伴增强版集中验收

适用分支：**feature/win10-companion-memory**。关联：[完整交付报告](PR-REPORT-COMPANION-COMPLETE-2026-10-13.md)、[上一轮入口修补](PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md)、[原打包流水线](ONEDIR_PACKAGING.md)。

用户已实测 Windows 10 / Python 3.12 x64 启动 GUI、桌宠可见、主动 AI 设置、灵动岛设置和临时注入 Fake 后的合成主动气泡。旧右键入口失败及旧默认 Fake 不发言也有用户证据。本轮正式入口修补及新增全部功能须按下表集中复验；不能把云端 Linux/offscreen 结果当成 Windows 验收。真实 DeepSeek：**NOT TESTED**。Windows EXE：**NOT BUILT**。现有 Python 3.12 环境可以继续使用，无需 Git、GitHub Desktop、管理员权限或重新安装 Python。

## 1. 下载与安全更新

1. 从托盘选择“全部退出”，关闭独立设置窗口。
2. 打开 [开发分支](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/tree/feature/win10-companion-memory)，点击 **Code → Download ZIP**。也可直接[下载分支 ZIP](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/archive/refs/heads/feature/win10-companion-memory.zip)。
3. 解压到新目录，例如 `D:\Code\FishFinal`。进入里面同时有 `pet`、`assets`、`scripts`、`requirements.txt` 的项目根目录。以下命令的第一行用这个实际路径替换。
4. 保留旧源码、`D:\Code\FishVenv312`、旧 `FishAcceptance` 及 `%APPDATA%` 数据。**不要把旧目录覆盖合并到新目录，也不要复制 `.bak` 或临时修补。** 本轮可独立运行。
5. 打开普通 PowerShell（标题不要出现“管理员”）。逐行执行：

```powershell
Set-Location 'D:\Code\FishFinal\实际项目目录'
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -c "import sys,struct,PySide6; print(sys.version, struct.calcsize('P')*8, PySide6.__version__)"
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pip check
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishAcceptanceFinal'
```

最后一个目录须是源码外部的新目录。首次创建的新 Fake 目录会开启主动 AI、摸头 AI 和 AI 投喂；**以后重启保留你的关闭选择**。正式产品三个开关默认关闭。首次合适时机显示带“合成测试”的主动气泡，控制台出现 `FAKE: synthetic proactive bubble displayed`。首次尝试约 1.5 秒，后续调度约30秒；隐藏、全屏、聊天、重要提示及离开电脑会延后。

没有马上发言时先检查总开关、可见性和聊天窗口，退出后换一个新外部目录复验首次展示。原验收目录已有额度/间隔状态，不应删 SQLite 或修改系统时钟。新目录无须真实 Key。

## 2. 依赖与 UTF-8

主要依赖为 PySide6/shiboken6、Pillow、imageio-ffmpeg（内带 ffmpeg）、keyring、certifi、tzdata、lunar_python、psutil、edge-tts，以及原 Windows 音频/媒体能力的 pycaw/comtypes/WinRT。SQLite 是 Python 标准库；不用安装数据库。pytest/Ruff 供自动测试，Node 20+ 仅供桥接门禁，不是启动依赖。

已有环境安装成功且 `pip check` 通过时无需重装。若缺依赖，使用：

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pip install -r requirements.txt -c packaging\constraints-win10-companion.txt
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pip check
```

目标 Qt/PySide6 为 **6.8.3**，不要自行升级最新 Qt。所有 Python/pip 命令用 `-X utf8`，解决用户中文 Windows 上已遇到的 GBK requirements 解码错误。无需激活 venv 或修改全局执行策略。

新建环境可用 `py -3.12 -X utf8 -m venv D:\Code\FishVenv312`（仅当此目录不存在）。准备脚本支持 `-PythonVersion 3.12`，默认仍3.11。用户3.12基础流程已实测；本轮 Linux3.12/Qt6.8.3补测仅验证自动化行为，不代表所有3.12/Windows能力已通过。

## 3. 集中 Fake 验收清单

每项填 PASS / FAIL / NOT TESTED，记录时间、拓扑、角色、DPI与屏幕数。

| 操作 | 应看到什么 |
|---|---|
| 右键 → 桌宠设置；灵动岛 → 设置 | 同一套设置、同一隔离目录和角色；重复点击前置，关闭后可重开 |
| 右键 → 主动识屏 → 打开设置… | 定位“自动化与联动”；Windows主动识屏区域可见，不自动开启截图 |
| AI 与对话 → 主动 AI 陪伴 | 可直接输入每日1～9999、间隔1～99分钟；默认10/30；有费用说明 |
| 保存并退出重启 | 数值保持，配额/间隔不清零；已关闭功能保持关闭 |
| 旧每日0或旧间隔>99 | 普通主动发言停用并提示确认；原数值保留，不静默增加请求 |
| 单击可见头部核心（头顶中央、上半脸） | 开启摸头 AI 时只有摸头合成气泡；同次不出现普通自言自语 |
| 身体、头部边缘单击 | 原点击动画/Q弹/音效和配置允许的自言自语；不开摸头请求 |
| 关闭摸头后点头；按住拖动；右键 | 分别恢复普通点击、原拖拽、原菜单；拖拽无摸头或普通点击气泡 |
| 投喂中文名.py/.png/音频/ZIP/文件夹、多文件 | 立即吃文件动画，随后按类型的合成反馈，统计增加、源文件原样 |
| 关闭 AI 投喂 | 原投喂动画、统计、基础反馈及独立解读确认仍正常 |
| 原待办面板建立1～2分钟后任务 | 只用原面板；即使主动关掉/额度满/无Key也显示基础提醒 |
| 待办删除、完成、禁用后退出重启 | 不复活；短时错过可在原10分钟内补发，几天旧任务不集中轰炸 |
| 记忆管理 | 合成偏好可查看、纠错、删除；关闭授权后不引用私人记忆 |
| 主动识屏活动记录 → 清除记录 | 仅清除原短期活动记录，AI长期记忆和普通主动配额保留 |
| 用户手动聊天时摸头/主动消息 | AI让路；手动会话不混入内部互动事件 |
| 子宠、角色、缩放、镜像、DPI100/125/150%、多屏 | 对应宠点击/投喂/设置归属正确，透明区域无互动 |
| 设置进程隔离开/关；进程关闭/启动失败 | 正确隔离目录/角色；启动失败能进程内回退 |
| 原语音试听、语音报时、点击朗读 | 原设置保持；新增问候/摸头/投喂均不自动朗读 |
| 睡眠唤醒、锁屏/解锁、全屏、午夜、退出/注销 | 无陈旧回调、额度异常、后台请求风暴或卡死 |

身体自言自语是否发生依赖原开关，不要为验证新增 AI 关闭原声音配置。Fake 网络被禁用，真实 Edge TTS 音频/Provider联网需在独立 live 验收中测试；Fake 下网络试听失败不等于语音接线失效。

两个拓扑每次先全部退出，再各用新外部目录：

```powershell
$env:PET_RENDER_TOPOLOGY = 'legacy'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishFinalLegacy'
```

退出后：

```powershell
$env:PET_RENDER_TOPOLOGY = 'overlay'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishFinalOverlay'
```

结束后 `Remove-Item Env:PET_RENDER_TOPOLOGY -ErrorAction SilentlyContinue`。不要同时运行多个验收实例。

**拖文件出现🚫：**检查 PowerShell/桌宠是否管理员运行。普通文件资源管理器向高权限窗口拖放可能被 Windows UAC 拒绝；改为双方普通权限重新运行。不能关闭 UAC 或默认管理员运行来规避。若同权限仍失败，记录拓扑、命中位置、文件类型、是否主/子宠、是否鼠标穿透；这部分须 Windows 原生复验。

## 4. 真实 DeepSeek 的安全验收

Fake完成后全部退出，用另一新目录：

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --live --data-dir 'D:\Code\FishFinalLive'
```

首次 live 开关默认关闭。只在本机设置界面填写真实Provider、模型和Key；先测试连接/手动聊天，再分别授权三个增强开关。不要把Key放进命令行、源码、日志、截图、ZIP或发给助手。验收 ref 与生产 ref 隔离，仍须检查实际目录。无Key时 live 安全不发请求，显式互动可本地文字降级。

普通主动每日模型请求上限为**每日展示额度的两倍**，每次输出96token；输入也计费。9999/1不是保证发9999条，也不是每分钟必发。分类冷却、状态让路和语义去重仍约束调度。高额度费用可能明显增加。摸头同宠10秒、投喂20秒冷却，共享独立单请求互动通路，失败120秒退避，没有自动付费重试；不计普通主动额度。模型失败降级文字不代表真实模型成功。

确认真实问候变化、角色、401/429/TLS/代理、取消、记忆撤销、费用和原Edge TTS试听。正常使用系统代理，不关闭证书校验。本轮真实DeepSeek与Windows声音均 **NOT TESTED**。

## 5. Windows 自动化检查（可选）

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pytest -q tests/test_companion_settings_entry.py tests/test_companion_acceptance_launcher.py tests/test_todo_delivery.py tests/test_companion_custom_limits.py tests/test_companion_touch.py tests/test_companion_interactions.py tests/test_companion_feeding.py tests/test_companion_final_settings.py tests/test_companion_data_migration.py tests/test_companion_build_workflow.py
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

完整CI分组命令见交付报告。Qt6.8.3已有原基线菜单包装对象回收普查失败，断言保留；offscreen有不支持raise/keyboardgrab提示，不代表原生Windows菜单结果。旧 `tests/smoke.py` 素材数51断言已过时（实际106），同样未削弱。

## 6. Windows 原生 Chat EXE 构建（进阶、可选）

本轮代码和安全流程已准备，Linux不能构建Windows EXE，状态 **NOT BUILT**。普通用户源码验收不需要做此节。

在普通 PowerShell、项目根目录、关闭旧Chat EXE后执行；WorkDir须全新：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_companion.ps1 -PythonExe 'D:\Code\FishVenv312\Scripts\python.exe' -WorkDir 'D:\Code\FishCompanionBuildFinal'
```

仅对这一次脚本进程设置执行策略。流程创建干净构建venv/安全源码暂存、固定Qt6.8.3及独立构建工具版本、执行原WebM Chat onedir、复制Qt/ffmpeg与素材、保留瘦身/中文/QtDLL/桥接校验、用临时Fake目录冒烟，再输出 portable ZIP 的真实SHA256。缺Node时原桥接import smoke跳过，交付前应另执行Node门禁。构建失败保留输出供诊断，不以单PID存活冒充成功。

成功时完整目录/ZIP位于：
`D:\Code\FishCompanionBuildFinal\dsh-pet-companion-win10\dist-onedir\dsh-pet-standalone-webm-chat*`。
只有Windows实构建成功后才能记录真实包大小/SHA；本报告没有虚构EXE。

绿色版须解压**整个目录**，不能单发EXE。双击正常运行不用用户安装Python，数据在 `%APPDATA%\dsh-pet-standalone-webm-chat`。新变体第一次从同base普通旧目录复制配置、会话、两份SQLite、待办/统计/短记录和槽文件，目标已有数据优先，源保留。SQLite用backup含WAL，失败保留pending并暂停普通主动请求；修复源/权限后重启重试。Fake自有base不会导入正式APPDATA。

冻结包的隔离验收入口：`exe --companion-acceptance --data-dir D:\Code\FishExeAcceptance`；尚需Windows构建后验证。卸载绿色版删除解压目录即可，**不删除APPDATA**；安装版按[原Inno Setup指南](ONEDIR_PACKAGING.md)构建，安装/卸载/自启仍须实机验收。

## 7. 出错、回退和记录

复制控制台完整异常栈、时间、版本、拓扑、操作步骤；不要复制Provider私密Prompt、Key或个人数据库。设置身份问题可只提供脱敏后的目录尾部和slot号。性能问题记录CPU/RSS、屏幕DPI、是否全屏及近期操作。

安全回退：全部退出 → 回旧源码目录 → 使用原venv/旧验收目录启动。不要删除两份SQLite、原待办JSON或迁移源；新状态格式在旧代码不识别时可能安全拒绝服务，应先关闭对应增强。升级前可在全部退出后把隔离数据目录复制为本地备份，不上传GitHub。若只要停用增强，关闭三个增强开关即可保留原桌宠功能。
