# Windows 10 22H2 x64：完整陪伴增强版集中验收

适用分支：**feature/win10-companion-memory**。最新修补：[FFmpeg 控制台与 PowerShell 5.1](PR-REPORT-FFMPEG-NO-CONSOLE-2026-10-13.md)，完整重新打包命令见第11节。关联：[完整交付报告](PR-REPORT-COMPANION-COMPLETE-2026-10-13.md)、[上一轮入口修补](PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md)、[原打包流水线](ONEDIR_PACKAGING.md)。

用户最新 Windows 10 22H2 x64 / 19045、Python3.12、PySide6 6.8.3、PyInstaller6.19.0 证据：前轮 Fake 集中验收正常；约149MB绿色ZIP构建成功，EXE桌宠及独立设置窗口冒烟通过，摸头“合成测试”等交互正常。旧包运行中偶发 FFmpeg 黑窗口是本轮待修故障。**本轮修复包原生构建/控制台/PowerShell5.1复验：NOT TESTED**；真实DeepSeek及Edge声音仍 **NOT TESTED**。Linux/offscreen 不替代 Windows 验收。无需 Git、GitHub Desktop、管理员权限或重新安装 Python；保留旧源码、环境、构建包与正式用户数据。

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
| 投喂图片/音频/ZIP/目录、多文件 | 立即吃文件动画、统计，随后安全元数据 AI 台词；不出现“读不了”，源文件原样 |
| 开启“拖文件后询问解读”并投喂文本/混合文件 | 只询问支持的文本。确认前不读内容；选择“不用了”后先统计再趣味 AI；选择“解读”后只走原内容解读，不用趣味气泡覆盖进度/结果 |
| 关闭 AI 投喂 | 原投喂动画、统计、基础反馈及独立解读确认仍正常 |
| 原待办面板建立1～2分钟后任务 | 只用原面板；即使主动关掉/额度满/无Key也显示基础提醒 |
| 待办删除、完成、禁用后退出重启 | 不复活；短时错过可在原10分钟内补发，几天旧任务不集中轰炸 |
| 记忆管理 | 合成偏好可查看、纠错、删除；关闭授权后不引用私人记忆 |
| 主动识屏活动记录 → 清除记录 | 仅清除原短期活动记录，AI长期记忆和普通主动配额保留 |
| 用户手动聊天时摸头/主动消息 | AI让路；手动会话不混入内部互动事件 |
| 子宠、角色、缩放、镜像、DPI100/125/150%、多屏 | 对应宠点击/投喂/设置归属正确，透明区域无互动 |
| 设置进程隔离开/关；进程关闭/启动失败 | 正确隔离目录/角色；启动失败能进程内回退 |
| 原语音试听、语音报时、点击朗读 | 原报时/节日设置保持；被动朗读控制摸头/点击/周期文字/趣味投喂，主动朗读独立控制主动气泡/待办，均只读实际显示文字（Fake合成记录） |
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

普通主动每日模型请求上限为**每日展示额度的两倍**，每次输出96token；输入也计费。9999/1不是保证发9999条，也不是每分钟必发。分类冷却、状态让路和语义去重仍约束调度。高额度费用可能明显增加。摸头/投喂正常完成后无固定成功冷却；共享单请求通路，忙时摸头不排队、投喂有界合并并保留约2秒统计展示协调。频繁互动可能增加API费用；模型失败120秒退避，没有自动付费重试；不计普通主动额度。模型失败降级文字不代表真实模型成功。

确认真实问候变化、角色、401/429/TLS/代理、取消、记忆撤销、费用和原Edge TTS试听。正常使用系统代理，不关闭证书校验。本轮真实DeepSeek与Windows声音均 **NOT TESTED**。

## 5. Windows 自动化检查（可选）

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pytest -q tests/test_companion_settings_entry.py tests/test_companion_acceptance_launcher.py tests/test_todo_delivery.py tests/test_companion_custom_limits.py tests/test_companion_touch.py tests/test_companion_interactions.py tests/test_companion_feeding.py tests/test_companion_final_settings.py tests/test_companion_data_migration.py tests/test_companion_build_workflow.py
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

完整CI分组命令见交付报告。Qt6.8.3已有原基线菜单包装对象回收普查失败，断言保留；offscreen有不支持raise/keyboardgrab提示，不代表原生Windows菜单结果。旧 `tests/smoke.py` 素材数51断言已过时（实际106），同样未削弱。

## 6. Windows 原生 Chat EXE 构建（进阶、可选）

用户此前已成功完成Windows绿色版构建及基本EXE冒烟；Linux无法重打本轮修复包，其新包原生验证 **NOT TESTED**。本轮请优先执行第11节的全新WorkDir流程；此节保留通用说明。

在普通 PowerShell、项目根目录、关闭旧Chat EXE后执行；WorkDir须全新：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_companion.ps1 -PythonExe 'D:\Code\FishVenv312\Scripts\python.exe' -WorkDir 'D:\Code\FishCompanionBuildFinal'
```

仅对这一次脚本进程设置执行策略。流程创建干净构建venv/安全源码暂存、固定Qt6.8.3及独立构建工具版本、执行原WebM Chat onedir、复制Qt/ffmpeg与素材、保留瘦身/中文/QtDLL/桥接校验、用临时Fake目录冒烟，再输出 portable ZIP 的真实SHA256。缺Node时原桥接import smoke跳过，交付前应另执行Node门禁。构建失败保留输出供诊断，不以单PID存活冒充成功。

成功时完整目录/ZIP位于：
`D:\Code\FishCompanionBuildFinal\dsh-pet-companion-win10\dist-onedir\dsh-pet-standalone-webm-chat*`。
只有Windows实构建成功后才能记录真实包大小/SHA；本报告没有虚构EXE。

绿色版须解压**整个目录**，不能单发EXE。双击正常运行不用用户安装Python，数据在 `%APPDATA%\dsh-pet-standalone-webm-chat`。新变体第一次从同base普通旧目录复制配置、会话、两份SQLite、待办/统计/短记录和槽文件，目标已有数据优先，源保留。SQLite用backup含WAL，失败保留pending并暂停普通主动请求；修复源/权限后重启重试。Fake自有base不会导入正式APPDATA。

冻结包的隔离验收入口：`exe --companion-acceptance --data-dir D:\Code\FishExeAcceptance`；此前用户已验证基本入口，本轮修复包仍须复验。卸载绿色版删除解压目录即可，**不删除APPDATA**；安装版按[原Inno Setup指南](ONEDIR_PACKAGING.md)构建，安装/卸载/自启仍须实机验收。

## 7. 出错、回退和记录

复制控制台完整异常栈、时间、版本、拓扑、操作步骤；不要复制Provider私密Prompt、Key或个人数据库。设置身份问题可只提供脱敏后的目录尾部和slot号。性能问题记录CPU/RSS、屏幕DPI、是否全屏及近期操作。

安全回退：全部退出 → 回旧源码目录 → 使用原venv/旧验收目录启动。不要删除两份SQLite、原待办JSON或迁移源；新状态格式在旧代码不识别时可能安全拒绝服务，应先关闭对应增强。升级前可在全部退出后把隔离数据目录复制为本地备份，不上传GitHub。若只要停用增强，关闭三个增强开关即可保留原桌宠功能。

## 8. 本轮最小复测：表达风格、摸头与投喂

沿用第1节网页 ZIP 更新方式与已安装的 `FishVenv312`。关闭旧程序，解压新 ZIP 到全新目录；不合并旧源码或 `.bak`。命令仍为：

```powershell
Set-Location 'D:\Code\FishFinal\实际项目目录'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishAcceptanceExpression'
```

首次新目录仅自动开启三种 AI 增强；**共享朗读仍默认关闭**。无需 Key、Git 或重新安装依赖。

1. 右键设置 → **互动 → 点击与音效 → 摸头 AI**，只有一个开关；搜索“摸头”可定位，AI 与对话页面保留“AI 投喂反馈”。“被动互动朗读”始终可见；旧“被动互动朗读”的同一字段与偏好保留，没有第二个重复开关。绑定和预缓存只依赖普通点击。
2. 保持“点击触发自言自语”关、打开“摸头 AI”和“被动互动朗读”。点头后只显示一个摸头气泡，控制台出现 `FAKE: synthetic speech requested; real audio NOT TESTED`。**Fake不会真正合成或播放声音**；关闭朗读后仍显示摸头文字但无新语音请求。趣味投喂也跟随被动朗读；主动问候跟随独立的“主动陪伴朗读”。
3. 在原“表达风格”切换并保存：默认 → 鲸鱼娘女仆 → 自定义 → 默认。下一次摸头/投喂及下一次满足普通调度的问候使用对应风格；女仆 Fake带“主人～”，默认不沿用该前缀。成功后可立即再次摸头；投喂仍先展示约2秒统计并合并短时元数据。原主动额度不变，勿通过删库或改系统时间强制触发。自定义固定台词原用途保留；其内容无云端授权，本轮AI采用角色自身加中性友善规则，不上传整份JSON或私人台词。
4. 保留“拖文件后询问解读”：拖 PNG、ZIP、目录，应先正常统计、后趣味AI，不出现“读不了”；拖 TXT 或 TXT+PNG，只询问TXT。等待期间再拖文件不覆盖当前确认，统计仍增加。选“不用了”恢复统计及安全元数据反馈；选“解读”后允许该文本文件名和内容进入原独立解读会话，图像/目录内容不发送。**完整路径不进入趣味请求**。
5. 关闭解读开关再投喂TXT，只有统计及趣味AI；关闭趣味AI，动画/统计/明确解读仍正常。模型失败仍有原动画/统计和可用的本地风格降级。
6. 生子宠，修改子宠自己的风格和朗读开关，分别点击/投喂主宠及子宠；气泡、授权解读会话、音色配置不得串用。保存退出重启，开关保持。生成中关闭朗读/摸头、换角色或退出，迟到结果不得发声。
7. 分别退出后设置 `$env:PET_RENDER_TOPOLOGY='legacy'` 或 `'overlay'` 启动复测；验收后用 `Remove-Item Env:PET_RENDER_TOPOLOGY -ErrorAction SilentlyContinue` 恢复默认。注意两只宠重叠时投喂命中最上层宠，先拖开再验证身份。

**真实语音单独验收（NOT TESTED）**：使用第4节的 `--live`，仅在本地设置中输入自有 Key；也可让无Key的摸头走本地降级文字，再验证已有 Edge TTS。普通点击关闭、摸头及共享朗读开启时应能听见同一句，音色/语速/音量来自对应宠配置；报时/节日/摸头共用原播放器，不叠音。动态台词未命中缓存时会由原在线TTS合成，朗读开启即使用该已有服务；网络/代理、音频设备和实际输出须记录。失败应保留摸头文字。Fake语音回调不能替代此项。

本轮 Linux Qt6.8.3/offscreen 自动化验证不等于 Win10音频、原生透明/DPI、多屏、真实拖放或EXE验收。真实DeepSeek语言效果和联网 **NOT TESTED**；本轮Windows EXE **NOT BUILT**。用户之前提及的 WebM reader 退役池及慢帧属于独立待排查问题；本轮未修改动画/解码器，也没有收到该次完整日志，复测若仍发生，请保留时间、拓扑和完整脱敏日志，不能据此宣称已修复。

## 9. 本轮收尾：用户 System Prompt 优先

关联：[人设优先交付报告](PR-REPORT-CHAT-PERSONA-PRIORITY-2026-10-13.md)。仍按第1节从开发分支网页下载新ZIP，保留旧源码及隔离目录，复用原Python3.12虚拟环境；启动命令和依赖不变。

- 在现有“AI 与对话”的 System Prompt 填入明确的人设，例如“你是图书管理员小树，禁止自称女仆”，保存并重启。即使角色manifest有默认人设，普通聊天、主动问候、摸头和趣味投喂的实际Provider请求都应使用该用户人设。角色外观/动画不因此改变。
- 未填写、清空或恢复出厂原句“你是一只可爱的桌面宠物，请用自然、友善的中文和用户交流。”时采用角色资源默认；资源无Prompt时才用出厂原句。旧存档中的非出厂自定义文本自动生效，无新增开关或编辑器。
- 切换表达风格不能覆盖上述人设；任务字数/安全限制、记忆授权及文件解读确认仍有效。子宠使用自己的已保存配置，不把主宠人设强写到子宠。
- 回复生成时保存另一人设：普通聊天取消旧请求并保留已存历史，未排出的新版聊天文字缓存不继续显示；下一次请求用新人设。问候/摸头/投喂沿原身份校验拒绝旧异步结果。
- **Fake只用于实际请求Prompt捕获和自动化验证**，其固定“合成测试”台词及本地降级文案不证明任意自定义人设的语言表现。真实DeepSeek对人设和语气的遵从、Windows原生设置保存/热更新仍待独立实机验收，**NOT TESTED**；不能把Linux Fake通过写成Windows模型成功。

## 10. 新增集中复测：取消互动成功冷却与双朗读开关

关联：[本轮交付报告](PR-REPORT-COMPANION-DUAL-SPEECH-2026-10-13.md)。**用户已报告上一轮 Windows10 Fake集中测试均正常通过**，保留此证据；以下是本轮新增需求，尚待Windows复验。真实DeepSeek、Edge声音、WindowsEXE仍分别为 **NOT TESTED / NOT TESTED / NOT BUILT**。

1. 完全退出旧程序，在GitHub网页选 `feature/win10-companion-memory` → Code → Download ZIP，解压到新目录。不覆盖旧源码，不复制 `.bak`，不要求Git/GitHub Desktop。复用 `D:\Code\FishVenv312` 和旧隔离验收目录即可保留朗读偏好，也可新建源码外的测试目录。Python3.12/Qt6.8.3依赖没有变动，安装仍用第2节UTF-8命令。

```powershell
Set-Location 'D:\Code\FishSpeechUpdate\实际项目目录'
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts\run_companion_acceptance.py --data-dir 'D:\Code\FishAcceptance'
```

2. 互动 → 点击与音效 → **被动互动朗读**，兼容旧 `self_talk_speak_enabled`，旧开/关保持。其与摸头AI、身体点击、定时气泡、AI投喂功能开关独立。AI与对话 → 主动AI陪伴 → **主动陪伴朗读**，新默认关闭，包含在线语音/私人待办文字发送提示。搜索这两个名称或使用相应深链可定位；保存立即落盘，退出重启保持。不要因为语音报时/节日开启就自动开启主动朗读。
3. 四种组合分别验收：都关→陪伴静音；仅被动→摸头、身体/周期文本、趣味投喂记录语音；仅主动→主动问候/喝水/休息/关怀和到期待办记录语音；都开→使用同一原通道。Fake只输出 `FAKE: synthetic speech requested; real audio NOT TESTED` 与有界合成记录，**没有真实声音、Edge或DeepSeek网络访问**。普通点击关闭时摸头仍可朗读；摸头关闭时周期文字仍可朗读。图片无声，加载失败实际回退为文本才可朗读。
4. 摸头一条完成后立即再次点击可发新请求，不必等10秒。处理中连续点击只保持原动画，不排队，不增加同一时刻请求。成功投喂后的下一批先显示原统计，约2秒后才有新的趣味回复，不必等20秒；短时投喂有界合并。**第一条统计永远无声，第二条趣味AI或本地备用回复仅朗读同一句一次**。正在处理的旧互动不得盖住新投喂统计。无Key的live可本地降级，模型错误保留独立120秒退避，不应宣传为“所有状态零冷却”。真实连续调用可能增加费用。
5. 创建一个未来几分钟内到期的合成待办。主动朗读开时只读成功显示的 `⏰ 待办提醒：...`；开关关时提醒仍显示。隐藏/设置抑制仅桌面通知时不读，删除/编辑/关闭待办或停止程序后不播放旧结果。不得重复创建或投递任务；原提前提醒/确认/删除/重试逻辑不变。用合成标题验收，不把私人标题贴入日志或截图。
6. 模型/TTS处理中关闭相应朗读、开关迅速关再开、换角色、改音色、隐藏、退出或撤销记忆授权，尚未播放的旧语音不得响；新文字覆盖旧文字时不念旧内容。已经开始的声音沿原播放器生命周期处理。TTS失败保留文字，不新增错误气泡。文本解读确认/进度仍优先；TXT明确同意前不发送内容，PNG/ZIP/目录不报“读不了”，趣味请求仍只用安全元数据，原文件不变。
7. 分别复测Legacy/Overlay与主/子宠：独立设置、角色、音色/语速/音调/音量不得串用。原固定点击台词预缓存、语音报时与节日提醒维持各自开关；关闭两种陪伴朗读不应关闭已启用的报时/节日服务。真实模式两个都开时应统一排队、不叠音；Fake合成记录不证明真实播放。

真实声音必须在用户本机显式同意在线语音后单独验收，目标仍Windows10 22H2 x64/Python3.12。可先在独立 `--live` 目录无DeepSeek Key下验证本地备用文字的Edge语音，再于原设置页本机填写自己的DeepSeek Key做模型验收；不要将密钥放入源码/命令行/报告。记录网络/代理与音频设备。Linux Qt6.12及6.8.3 offscreen/Fake不是Windows声音成功证据。完成本轮集中复测后再决定下一步开发。

## 11. FFmpeg 黑窗口修复：重新打包与原生复验

本节给出一次完整流程，每个代码块只有一条PowerShell命令。在**同一个普通 Windows PowerShell 5.1 窗口**按顺序运行。命令使用你的旧Python作为创建新构建环境的解释器，不安装/修改旧venv。保留 `D:\Code\dsh-pet-indesktop`、`FishCompanionBuildDualSpeech20261013`、`FishPortableTest20261013`、旧Fake目录与APPDATA。先从托盘全部退出旧桌宠并关闭独立设置窗口；不要用按名称批量强杀。

### 11.1 网页更新与预检查

浏览器进入[开发分支](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/tree/feature/win10-companion-memory)，**Code → Download ZIP**，将新ZIP保存为 `D:\Code\FishFFmpegSource20261013.zip`。不要覆盖旧ZIP。以下所有新目录若已存在，改用统一的新后缀（例如 `20261013R2`），不要删除或合并旧目录。

确认解压目标不存在：

```powershell
if (Test-Path 'D:\Code\FishFFmpegSource20261013') { throw 'Choose a NEW source directory; keep the old directory.' }
```

```powershell
Expand-Archive -LiteralPath 'D:\Code\FishFFmpegSource20261013.zip' -DestinationPath 'D:\Code\FishFFmpegSource20261013'
```

```powershell
$repairSource = (Get-ChildItem 'D:\Code\FishFFmpegSource20261013' -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'pet\__main__.py') } | Select-Object -ExpandProperty FullName)
```

```powershell
if (-not $repairSource -or @($repairSource).Count -ne 1) { throw 'Expected exactly one project root in the downloaded ZIP.' }
```

```powershell
Set-Location $repairSource
```

```powershell
$PSVersionTable.PSVersion
```

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -c "import sys,struct,PySide6,imageio_ffmpeg; print(sys.version,struct.calcsize('P')*8,PySide6.__version__,imageio_ffmpeg.__version__)"
```

预期Python3.12 x64 / Qt6.8.3 / imageio-ffmpeg0.6.0。以下预解析须用 `powershell.exe`（Windows PowerShell5.1），不是仅用 `pwsh`（7.x）。四个正式 `.ps1` 应输出BOM/语法PASS；有错误就停止构建，保留输出，不手工把中文乱码改成“能解析”。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\check_powershell_scripts.ps1
```

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

```powershell
$env:PYTHONUTF8 = '1'
```

```powershell
$env:PYTHONIOENCODING = 'utf-8'
```

### 11.2 新 WorkDir 构建、保留日志与安全检查

```powershell
New-Item -ItemType Directory -Path 'D:\Code\FishFFmpegLogs20261013' -ErrorAction Stop
```

```powershell
Start-Transcript -Path 'D:\Code\FishFFmpegLogs20261013\build.log' -NoClobber
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_companion.ps1 -PythonExe 'D:\Code\FishVenv312\Scripts\python.exe' -WorkDir 'D:\Code\FishCompanionBuildFFmpeg20261013'
```

必须检查构建退出码为0，资源/编码/Qt DLL/瘦身门禁与**EXE及独立设置窗口**冒烟均通过。桥接import smoke依赖已有Node，若跳过就单独记录NOT TESTED。任何阶段失败时保留新WorkDir，不继续启动产物，不用跳过检查参数重试；修复后另选R2目录重建。

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Build failed. Keep the work directory and transcript for diagnosis.' }
```

```powershell
Stop-Transcript
```

```powershell
$repairStage = 'D:\Code\FishCompanionBuildFFmpeg20261013\dsh-pet-companion-win10'
```

```powershell
$repairPython = 'D:\Code\FishCompanionBuildFFmpeg20261013\build-venv\Scripts\python.exe'
```

```powershell
Get-FileHash (Join-Path $repairStage 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip') -Algorithm SHA256
```

```powershell
Get-Item (Join-Path $repairStage 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip') | Select-Object Name,Length
```

可复现依赖快照在新WorkDir的 `build-dependencies.txt`；本轮不改正式依赖版本，也不打包任何Key。以下pytest工具只安装到**新构建venv**，产物已构建，不改变旧环境或绿色包。

```powershell
Set-Location $repairStage
```

```powershell
& $repairPython -X utf8 -m pip install pytest -c packaging\constraints-win10-companion.txt
```

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
```

```powershell
& $repairPython -X utf8 -m pytest -q tests/test_ffmpeg_console_flags.py tests/test_ffmpeg_windows_console.py tests/test_ffmpeg_job_object.py tests/test_powershell_encoding.py tests/test_windows_ffmpeg_observer.py tests/test_session_end_ffmpeg_guard.py tests/test_frameseq_provision.py tests/test_animation_thumbnail_cache.py tests/test_companion_build_workflow.py --junitxml='D:\Code\FishFFmpegLogs20261013\native-tests.xml'
```

Windows专用测试必须实际执行，不能把SKIP当PASS：真实FFmpeg版本/元数据/首帧/reader重启/fps/缩略图/后台转换，断言CREATE_NO_WINDOW、没有可附着的控制台、正常出帧和退出；Job测试包含reader及转换父进程强杀防孤儿，另有绕过Job的反例对照（测试自行清理自己的反例进程）。PowerShell测试用真实5.1解析器验证有效脚本、缺BOM和语法错误三种结果。源码测试通过仍不等于原生EXE通过。

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

### 11.3 启动新绿色版，实际复现全部场景

```powershell
if (Test-Path 'D:\Code\FishPortableFFmpeg20261013') { throw 'Choose a NEW portable directory; retain the old portable build.' }
```

```powershell
Expand-Archive -LiteralPath (Join-Path $repairStage 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip') -DestinationPath 'D:\Code\FishPortableFFmpeg20261013'
```

```powershell
$repairExe = 'D:\Code\FishPortableFFmpeg20261013\dsh-pet-standalone-webm-chat\dsh-pet-standalone-webm-chat.exe'
```

原包装ZIP若目录结构变化，先在资源管理器定位同时带 `_internal` 的EXE，再只修改上一行变量。不要移动EXE脱离 `_internal`，本轮不要双击无参数启动（那会使用正式APPDATA）。观察器会以 `--companion-acceptance` 和新的外部data-dir启动真实冻结EXE，Fake完全离线；程序、动画和设置都运行原产品路径。

先验Legacy默认自动转换模式：

```powershell
$env:PET_RENDER_TOPOLOGY = 'legacy'
```

```powershell
Remove-Item Env:PET_FRAMESEQ -ErrorAction SilentlyContinue
```

```powershell
& $repairPython -X utf8 scripts\watch_windows_ffmpeg_console.py --exe $repairExe --data-dir 'D:\Code\FishFFmpegAcceptanceLegacy20261013' --report 'D:\Code\FishFFmpegLogs20261013\legacy-console.json' --seconds 1200
```

观察期间按下表操作；完成后**从托盘“全部退出”**，观察器才能记录正常退出与无残留。上限20分钟，超时/按Ctrl+C不算完整通过；观察器不会强杀已有桌宠，也不会删除数据，超时后它新启动的桌宠须自行从托盘退出。不要同时开旧EXE。

| 场景 | 操作与预期 |
|---|---|
| 首次启动 / 冷版本、元数据 | 新目录第一次启动、等桌宠出帧；无FFmpeg黑窗口，尺寸/透明边缘/速度正常 |
| 素材切换 / 缩略图 | 在原动画菜单展开不同分类、切换素材和角色；缩略图/透明动画正常，无黑窗口 |
| 连续摸头 | 连续进行多次真实点击；动画、合成AI及原两个朗读开关行为与前轮一致，不弹控制台 |
| 文件投喂 | PNG/ZIP/TXT/目录及多文件（使用无私人内容的副本），先统计后趣味合成；原文件不变，不弹控制台 |
| 首帧预热 | 新角色/冷动画，快速切换、拖动、摸头；首帧/取消/再次播放正常，无控制台/挂住 |
| 后台帧序列转换 | 默认PET_FRAMESEQ未禁用；新绿色目录启动后保留运行，检查原后台供给/缓存日志或frameseq世代出现；不能只验已缓存动画 |
| 周期性回收 | 用下面Overlay WebM专测运行至少12分钟，保持可见闲置后再次互动；原10分钟reader回收后新进程仍无控制台（若被暂停/隐藏导致未到圈边界，应延长并记录） |
| 退出 / 无孤儿 | 托盘全部退出；观察报告exit/orphan PASS，任务管理器无该新包的FFmpeg残留，之后可重启 |

再验Overlay：必须先全部退出Legacy。此进程专测禁用frameseq，保证普通WebM reader和原定期回收实际被执行；不改源文件/持久设置、不删除已有缓存，结束后移除环境变量恢复默认。

```powershell
$env:PET_RENDER_TOPOLOGY = 'overlay'
```

```powershell
$env:PET_FRAMESEQ = '0'
```

```powershell
& $repairPython -X utf8 scripts\watch_windows_ffmpeg_console.py --exe $repairExe --data-dir 'D:\Code\FishFFmpegAcceptanceOverlay20261013' --report 'D:\Code\FishFFmpegLogs20261013\overlay-console.json' --seconds 1200
```

两拓扑均测试主/子宠对应角色与独立设置窗口，并补睡眠唤醒、快速换素材/退出。观察工具每50ms抽样可见窗口，按新包FFmpeg的完整标题路径匹配，仅记录句柄/合成二进制标识，不保存其它窗口标题或私人文字。它不是每个窗口创建事件的无漏报证明；短暂闪烁可能漏采样，人工看到任何黑窗口仍判FAIL。无观察到FFmpeg进程、未正常退出或工具异常不报告完整PASS；报告不自动认证交互场景，必须逐项人工填写。

### 11.4 收集证据与恢复默认环境

```powershell
Get-Content 'D:\Code\FishFFmpegLogs20261013\legacy-console.json' -Encoding UTF8
```

```powershell
Get-Content 'D:\Code\FishFFmpegLogs20261013\overlay-console.json' -Encoding UTF8
```

```powershell
Get-ChildItem 'D:\Code\FishFFmpegLogs20261013' | Select-Object Name,Length
```

```powershell
Remove-Item Env:PET_RENDER_TOPOLOGY -ErrorAction SilentlyContinue
```

```powershell
Remove-Item Env:PET_FRAMESEQ -ErrorAction SilentlyContinue
```

反馈：源码分支/提交号、Windows19045/Python/Qt/PyInstaller版本、ZIP字节数与SHA256、build.log、native-tests.xml、两个console.json，以及上述八项各自PASS/FAIL/NOT TESTED和实际时间。若再出现黑窗口，记录标题/操作/拓扑/角色/运行多久/是否后台转换或回收，截取仅该控制台的脱敏图片。不要上传APPDATA、API Key、个人SQLite或聊天/待办内容。失败保留新目录，退出后可回到旧 `FishPortableTest20261013`；绝不覆盖旧包。真实DeepSeek、真实Edge声音、本轮新EXE控制台修复，在拿到实际结果前仍为 **NOT TESTED**。


## 12. 微软新语音接口、岛聊天与两类回复朗读：更新和试听

本节对应[交付报告](PR-REPORT-EDGE-TTS-ISLAND-RESULT-SPEECH-2026-10-13.md)。用户已在Windows10 19045验证：旧 `speech.platform.bing.com` 返回403，临时将SDK地址改为 `api.msedgeservices.com` 后成功生成并播放MP3。本次将这个兼容修复放在项目原语音worker中，**不要求修改旧虚拟环境**。此次新产品代码、原生EXE、真实Edge声音与真实DeepSeek在本Linux环境中均 **NOT TESTED**；Linux冻结诊断包的离线PASS只证明适配模块被收集和执行，不能作为Windows便携版交付。

### 12.1 网页下载与全新目录构建

保留旧源码、旧ZIP、旧构建/绿色目录、APPDATA及个人数据库；先从托盘全部退出旧桌宠。打开[开发分支](https://github.com/yangleigpt030729-lab/dsh-pet-indesktop/tree/feature/win10-companion-memory)，Code → Download ZIP，保存为 `D:\Code\FishEdgeSource20261013.zip`。不要覆盖旧文件。下列命令逐条在同一个普通Windows PowerShell5.1执行；任何新目录已存在则统一换R2后缀，不合并、不删除旧目录。

```powershell
if (Test-Path 'D:\Code\FishEdgeSource20261013') { throw 'Choose a NEW source directory.' }
```

```powershell
Expand-Archive -LiteralPath 'D:\Code\FishEdgeSource20261013.zip' -DestinationPath 'D:\Code\FishEdgeSource20261013'
```

```powershell
$edgeSource = (Get-ChildItem 'D:\Code\FishEdgeSource20261013' -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'pet\__main__.py') } | Select-Object -ExpandProperty FullName)
```

```powershell
if (-not $edgeSource -or @($edgeSource).Count -ne 1) { throw 'Expected one downloaded project root.' }
```

```powershell
Set-Location $edgeSource
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\check_powershell_scripts.ps1
```

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

```powershell
New-Item -ItemType Directory -Path 'D:\Code\FishEdgeLogs20261013' -ErrorAction Stop
```

```powershell
Start-Transcript -Path 'D:\Code\FishEdgeLogs20261013\build.log' -NoClobber
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows_companion.ps1 -PythonExe 'D:\Code\FishVenv312\Scripts\python.exe' -WorkDir 'D:\Code\FishCompanionBuildEdgeTts20261013'
```

```powershell
if ($LASTEXITCODE -ne 0) { throw 'Build failed; retain the new WorkDir and transcript.' }
```

```powershell
Stop-Transcript
```

构建使用全新venv、Python3.12 x64、Qt6.8.3、PyInstaller6.19及原约束安装；旧venv不变。原BOM/预解析、资源/编码、DLL/瘦身、安全源码、EXE/独立设置窗口冒烟继续执行；本次新增实际TTS归档门禁，缺 `pet.edge_tts_compat` 或原语音依赖会停止构建，不产出可发放ZIP。日志必须含 `[tts] bundle TTS stack OK`。没有Key写进源码、ZIP或日志。

```powershell
$edgeStage = 'D:\Code\FishCompanionBuildEdgeTts20261013\dsh-pet-companion-win10'
```

```powershell
$edgePython = 'D:\Code\FishCompanionBuildEdgeTts20261013\build-venv\Scripts\python.exe'
```

```powershell
$edgeZip = Join-Path $edgeStage 'dist-onedir\dsh-pet-standalone-webm-chat-portable.zip'
```

```powershell
Get-FileHash -LiteralPath $edgeZip -Algorithm SHA256
```

```powershell
if (Test-Path 'D:\Code\FishPortableEdgeTts20261013') { throw 'Choose a NEW portable directory; keep the old portable.' }
```

```powershell
Expand-Archive -LiteralPath $edgeZip -DestinationPath 'D:\Code\FishPortableEdgeTts20261013'
```

```powershell
$edgeExe = 'D:\Code\FishPortableEdgeTts20261013\dsh-pet-standalone-webm-chat\dsh-pet-standalone-webm-chat.exe'
```

使用完整解压目录，不能只替换EXE或把EXE移出 `_internal`。若ZIP层级不同，用资源管理器确认EXE与 `_internal` 同级，再修改上一行变量。新包保留上一轮FFmpeg无控制台与严格FreeConsole探针修复；Windows原生专项测试与观察仍按§11执行，不因本轮声音变化免除。

### 12.2 最简单的在线试听及离线复验

首先在**全新隔离目录**启动真实语音模式；下列 `--live` 允许联网，但未填写DeepSeek Key时不得发出模型请求。不要在命令行写密钥。语音本身不需要DeepSeek Key。

```powershell
& $edgeExe --companion-acceptance --live --data-dir 'D:\Code\FishEdgeLiveAcceptance20261013'
```

右键桌宠 → 桌宠设置 → 语音设置，选择原微软音色并点击「立即试听」。全新目录避免旧缓存造成假成功；也可改变音色/语速生成新缓存。明确同意在线语音：实际播报文本可能发送微软服务。保留系统原代理设置，不关闭TLS验证，不改SDK文件；记录MP3新生成、确实听到声音或原失败状态。在线失败不应抹掉文字或造成新气泡覆盖。

随后分别打开/关闭「被动互动朗读」「主动陪伴朗读」验证四种组合；它们仍默认关闭，报时/节日开关独立，旧用户原被动开关偏好保留。

| 项目 | 操作与预期 |
|---|---|
| 岛聊天 | Legacy与Overlay展开灵动岛，实际点击聊天，卡片收起且对话气泡出现；宠物隐藏时走岛聊天；无聊天变体不打开聊天 |
| 被动文件回复 | 用合成TXT拖入，未确认不读取/调用模型/朗读；明确确认后只有成功展示的「解读完成：…」同一句朗读一次；进度、耗时、开始/失败不朗读 |
| 主动识屏回复 | 主动识屏自己开启并获得截图授权；普通主动AI陪伴可关闭。只在实际成功显示AI回复时按主动朗读开关读一次；「让我看看…」、失败和统计静音 |
| 原功能 | 摸头、点击/定时文字、趣味投喂仍走被动开关；普通主动问候/喝水/休息/关怀/待办仍走主动开关。投喂先统计（静音）后趣味回复，内容解读原授权优先权不变 |
| 失效撤销 | 合成或排队时关闭对应声音/业务、隐藏、换角色/宠物、换文本/音色、取消文件任务或退出，未开始播放的旧声音不得响；已开始的沿原播放器生命周期 |
| 静音排除 | 余额/余额变化、Agent消费、累计计数、纯图片、投喂统计、识屏前置提示、文件进度/字数/耗时/失败均不读 |
| 多宠 | 主/子宠各自音色、语速、音调、音量和开关；两开关都开仍共用原有有界语音队列，不叠音 |

文件AI解读与识屏AI需要用户在本机原设置中自行配置可用模型，绝不要发送真实Key给开发者。不要用私人文件或屏幕验收；推荐合成文本与测试窗口，保留截图/文件授权规则。

全部退出live后可启动Fake进行GUI/合成记录验证（默认不会访问真实Edge/DeepSeek/系统凭据）：

```powershell
& $edgeExe --companion-acceptance --data-dir 'D:\Code\FishEdgeFakeAcceptance20261013'
```

Fake日志中的 `synthetic speech requested; real audio NOT TESTED` 不是声音成功。需要源码离线回归时，在新构建venv安装pytest，不动旧环境：

```powershell
Set-Location $edgeStage
```

```powershell
& $edgePython -X utf8 -m pip install pytest -c packaging\constraints-win10-companion.txt
```

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
```

自动化测试使用空密钥后端，避免岛卡片附带的余额刷新接触本机真实凭据；仅限本轮pytest，结束恢复原环境。

```powershell
$edgeOldKeyringBackend = $env:PYTHON_KEYRING_BACKEND
```

```powershell
$env:PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring'
```

```powershell
& $edgePython -X utf8 -m pytest -q tests/test_edge_tts_endpoint.py tests/test_island_overlay_chat_entry.py tests/test_companion_result_speech.py tests/test_companion_dual_speech.py tests/test_voice_chime_edge_voice.py tests/test_powershell_encoding.py --basetemp='D:\Code\FishEdgePytestTemp20261013' --junitxml='D:\Code\FishEdgeLogs20261013\tests.xml'
```

```powershell
if ($edgeOldKeyringBackend) { $env:PYTHON_KEYRING_BACKEND = $edgeOldKeyringBackend } else { Remove-Item Env:PYTHON_KEYRING_BACKEND -ErrorAction SilentlyContinue }
```

`--basetemp` 必须是专门的全新测试临时目录，pytest会清理其中内容，不能指向源码、用户数据或旧绿色目录。

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

反馈构建提交/日期、版本、SHA256、build.log/tests.xml、立即试听与上表逐项PASS/FAIL/NOT TESTED。不要上传私人MP3、屏幕/文件内容、会话、SQLite或Key。若失败，托盘全部退出新包，再启动原 `FishPortableTest20261013`；新旧文件夹独立保留，正式用户数据不被删除或覆盖。通过后才能将新包作为正式候选版。当前没有可从Linux交付的原生Windows绿色ZIP，不将诊断包冒充该产物。
