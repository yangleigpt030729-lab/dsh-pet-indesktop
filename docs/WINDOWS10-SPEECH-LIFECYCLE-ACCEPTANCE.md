# Windows 10：气泡朗读生命周期与定点修复验收

修复分支：`fix/tts-bubble-lifecycle-and-interactions`，起始基线 `5556459`，目标 Python 3.12 / PySide6 6.8.3。对应[交付报告](PR-REPORT-SPEECH-LIFECYCLE-2026-10-14.md)。此前用户确认的新微软语音接口、音量热更新、投喂、灵动岛聊天、识屏朗读继续作为保护基线；本轮新增行为仍**待 Windows 10 本地验收**。

本轮只交付源码和 PR，不重新打包、安装或发布，不改已经存在的 v1.0.0 安装包。保留原 EXE、ZIP、安装目录和所有 AppData。**不要将新源码直接解压覆盖旧目录或 `D:\Code\pet`；不要删除配置来测试。**

## 1. 获取源码与自动测试（网页 ZIP，无需 Git）

在 GitHub 打开本修复分支，选择 Code → Download ZIP，手工解压至一个全新目录，例如 `D:\Code\PetSpeechLifecycleSource20261014`。找到包含 `AGENTS.md`、`pet`、`tests`、`scripts` 的源码根目录。下列命令每行独立复制到 PowerShell 5.1；仅将第一行路径改成该根目录。如果你已手工把 PR 变更合入本地 `D:\Code\pet`，第一行可用该路径，先自行保留旧源码。

```powershell
Set-Location 'D:\Code\PetSpeechLifecycleSource20261014\你的源码根目录'
```

使用原有已安装项目依赖的 Python，不更新依赖、不修改虚拟环境。没有 pytest 时只安装测试工具（此操作由用户自行选择）：

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pip install pytest
```

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
```

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 -m pytest -q tests/test_speech_binding.py tests/test_manual_screen_speech.py tests/test_companion_completion.py tests/test_chat_display_name.py tests/test_chime_time_context.py tests/test_voice_chime_service.py tests/test_companion_head_speech.py tests/test_voice_chime.py --basetemp 'D:\Code\FishSpeechPytest20261014'
```

pytest 使用临时合成数据，网络及声卡边界为模拟；**这不是实声验收**。指定的 `--basetemp` 仅供 pytest 使用，pytest 会清理其自己的内容，绝不能指向源码、安装目录、AppData 或现有用户文件夹。

## 2. 独立 GUI 验收目录

关闭旧版桌宠及设置窗口（正常退出，不强杀）。取消 offscreen 环境变量：

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
```

先运行完全离线的 Fake GUI，使用全新的测试数据目录：

```powershell
$env:PET_RENDER_TOPOLOGY = 'legacy'
```

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts/run_companion_acceptance.py --data-dir 'D:\Code\FishSpeechGuiAcceptance20261014'
```

Fake 会显示合成互动文字并记录合成朗读请求，**不会连接 DeepSeek、Edge TTS 或播放真实声音**。它不能验证读完才消失的硬件行为；没有播放时，绑定恢复普通气泡计时。

要验证真实微软语音，正常退出 Fake 后，用同一隔离目录显式启动 live：

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts/run_companion_acceptance.py --live --data-dir 'D:\Code\FishSpeechGuiAcceptance20261014'
```

通过设置自行选择音色并同意在线朗读，启用需要测试的两个朗读开关；TTS 可直接试听，不需要 DeepSeek Key。摸头或视觉 AI 的真实回复需要你在本地设置中配置相应 Provider，未经配置不应发出模型请求。密钥只留在本地，不发送给 开发者，不抄进命令或验收反馈。识屏会按原功能授权向视觉 Provider 发送截图，请只截取无私人信息的测试屏幕。

Overlay 复验：正常退出上一进程，再执行两条独立命令，仍使用隔离目录：

```powershell
$env:PET_RENDER_TOPOLOGY = 'overlay'
```

```powershell
& 'D:\Code\FishVenv312\Scripts\python.exe' -X utf8 scripts/run_companion_acceptance.py --live --data-dir 'D:\Code\FishSpeechGuiAcceptance20261014'
```

结束测试后清除本终端的拓扑变量：

```powershell
Remove-Item Env:PET_RENDER_TOPOLOGY -ErrorAction SilentlyContinue
```

## 3. 必查清单

| 操作 | 预期 |
|---|---|
| 主宠、子宠分别摸头/投喂/点击/定时文字台词 | 开被动朗读时只读实际展示的同一句；合成/排队/播放期间气泡不按旧倒计时消失；读完单页关闭 |
| 两页或多页长回复 | 原完整文本只合成、朗读一次；依次翻页不断音；所有页都能看到，最后页至少有约 1.5 秒阅读时间 |
| 新气泡覆盖旧回复 | 旧语音任务撤销；其结束事件不能关新气泡 |
| 关闭朗读/静音/隐藏/删子宠/换角色/退出 | 不播迟到的旧任务；失败/取消后按普通规则隐藏，不能永久挂泡 |
| TTS 断网或媒体失败 | 原回复仍显示，不被 TTS 错误气泡覆盖；不会永久等待 |
| 右键「看看屏幕」，自动识屏关、白名单空 | 手动功能不需要自动识屏；主动朗读开时读前置提示和最终回复；关闭主动朗读时只有文字 |
| 最终识屏回复先于提示合成完成 | 过期提示不再播放；最终回复优先且只读一次；错误详情保持静音 |
| 子宠发起识屏、主宠再触发其他气泡 | 结果留在原子宠；不得借主宠显示或朗读；旧回执不误关另一只气泡 |
| 摸头 AI 正常短句/接近80字 | 气泡与语音文本一致；明确 length/断流走本地备用，不追加标点伪造完整句，不自动重试收费 |
| 改名“大肥鱼”，开经典/现代 AI 对话 | 标题即时更新；关闭重开及切角色正确；历史、角色内部 ID 不变 |
| 报时各时段、中文及英文音色 | 默认附加文案符合本地时段；英文不读中文默认台词；准确时间保持原口播/数字显示设计 |
| 自定义中英文报时文案、关附加台词 | 自定义仍优先；关附加台词只报时间；预缓存和到点文案一致 |
| 关闭报时气泡、节日语音及普通审批 | 关闭气泡不强行显示；节日仍用共享通道；审批 sticky、图片、计数、余额、进度及无 TTS 的气泡保持原行为 |
| 已验收保护功能 | 微软新接口试听、音量0–100热调/静音/设置同步、投喂静音统计后趣味回复、岛聊天、文件授权、动画拖拽均复验 |

真实音频网络延迟无法消除；记录首次冷合成与第二次缓存播放的区别。长播放超过30秒不应被固定超时终止；真正无进度180秒的播放停滞会释放绑定，等待/合成/排队最长120秒，摸头等业务已有更短的待播过期规则仍生效。先关闭朗读再静音/恢复时，旧任务不得重新发声。

## 4. 反馈与回退

只反馈 Windows版本、Python/Qt版本、渲染拓扑、主/子宠、具体操作及观察结果、pytest汇总。不要上传完整配置、API Key、聊天/记忆数据库或截图。无需安装新 EXE；回退时正常退出源码进程，启动原已验证的安装版/便携 EXE即可。隔离目录留作自己的验收资料，不自动清理；正式 AppData 未由本任务改写。
