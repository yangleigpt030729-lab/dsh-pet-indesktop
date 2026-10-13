; UTF-8 BOM is applied by the repository writer. Inno Setup 6.5+.
#ifndef PayloadDir
#error PayloadDir must point at the fresh, verified portable payload
#endif
#ifndef ReleaseDir
#error ReleaseDir must be a new output directory
#endif
#ifndef InstallerIcon
#error InstallerIcon must be extracted from the verified application EXE
#endif
#define AppExe "dsh-pet-standalone-webm-chat.exe"
#define CompanionAppId "{662C52E9-287D-43C4-90DE-4A0B9061C7C4}"

[Setup]
AppId={{662C52E9-287D-43C4-90DE-4A0B9061C7C4}
AppName=大肥鱼桌面宠物
AppVersion=1.0.0
VersionInfoVersion=1.0.0.0
UninstallDisplayName=大肥鱼桌面宠物
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile={#InstallerIcon}
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\DaFeiYuDesktopPet
DisableDirPage=yes
UsePreviousAppDir=no
DisableProgramGroupPage=yes
OutputDir={#ReleaseDir}
OutputBaseFilename=大肥鱼桌面宠物_Setup_v1.0.0
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.17763
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
AlwaysRestart=no
#ifdef SignToolName
SignTool={#SignToolName}
SignedUninstaller=yes
#endif

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："
Name: "migrateautostart"; Description: "将本变体已开启的自启改为安装目录（不会新增自启项）"; Flags: unchecked; Check: HasExistingAutostart

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\大肥鱼桌面宠物"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"
Name: "{userdesktop}\大肥鱼桌面宠物"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "启动大肥鱼桌面宠物"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
const
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';
  RunValue = 'dsh-pet-standalone-webm-chat';
  OwnUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{662C52E9-287D-43C4-90DE-4A0B9061C7C4}_is1';

function HasExistingAutostart: Boolean;
var Command: String;
begin
  Result := RegQueryStringValue(HKCU, RunKey, RunValue, Command) and (Command <> '');
end;

function PetsRunning(var DetectionFailed: Boolean): Boolean;
var Locator, Services, Processes: Variant;
begin
  DetectionFailed := False;
  Result := True;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Services := Locator.ConnectServer('.', 'root\CIMV2');
    Processes := Services.ExecQuery('SELECT ProcessId FROM Win32_Process WHERE Name = ''{#AppExe}''');
    Result := Processes.Count > 0;
  except
    DetectionFailed := True; { Fail closed; never kill processes or inspect private command lines. }
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Failed: Boolean; PreviousDir, Target: String;
begin
  Result := '';
  Target := ExpandConstant('{localappdata}\Programs\DaFeiYuDesktopPet');
  if CompareText(AddBackslash(ExpandConstant('{app}')), AddBackslash(Target)) <> 0 then begin
    Result := '只允许安装到当前用户的固定应用目录，避免覆盖旧绿色版。';
    Exit;
  end;
  if DirExists(Target) then begin
    if not RegQueryStringValue(HKCU64, OwnUninstallKey, 'InstallLocation', PreviousDir) then begin
      Result := '目标目录已存在，但不是本安装器登记的安装。请保留或移走该目录后重试，不会覆盖它。';
      Exit;
    end;
    if CompareText(AddBackslash(PreviousDir), AddBackslash(Target)) <> 0 then begin
      Result := '既有安装身份与目录不一致，请取消并保留日志。';
      Exit;
    end;
  end;
  if PetsRunning(Failed) then begin
    if Failed then Result := '无法确认桌宠已退出（WMI 检查失败），已停止安装。请重试。'
    else Result := '请从托盘退出所有大肥鱼桌宠，并关闭独立设置窗口，再点重试。安装器不会强制结束进程。';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Command: String;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('migrateautostart') and HasExistingAutostart then begin
    Command := 'cmd /c start "" /D "' + ExpandConstant('{app}') + '" "' + ExpandConstant('{app}\{#AppExe}') + '" --slot 0';
    if not RegWriteStringValue(HKCU, RunKey, RunValue, Command) then
      MsgBox('软件已安装，但自启迁移未保存。请在桌宠设置中关闭再开启自启。', mbInformation, MB_OK);
  end;
end;

function InitializeUninstall: Boolean;
var Failed: Boolean;
begin
  Result := False;
  while PetsRunning(Failed) do begin
    if Failed then begin
      MsgBox('无法确认桌宠已退出，已停止卸载。请保留用户数据并重试。', mbError, MB_OK);
      Exit;
    end;
    if MsgBox('请从托盘退出大肥鱼并关闭独立设置窗口，再点重试。不会强制关闭，也不会删除用户数据。', mbInformation, MB_RETRYCANCEL) <> IDRETRY then Exit;
  end;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Command, OwnExe: String;
begin
  if CurUninstallStep = usPostUninstall then begin
    OwnExe := '"' + ExpandConstant('{app}\{#AppExe}') + '"';
    if RegQueryStringValue(HKCU, RunKey, RunValue, Command) then
      if Pos(Lowercase(OwnExe), Lowercase(Command)) > 0 then
        RegDeleteValue(HKCU, RunKey, RunValue); { Only this installation's auto-start; preserve portable/other variants. }
  end;
end;
