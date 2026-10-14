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
AppVersion=1.0.1
VersionInfoVersion=1.0.1.0
UninstallDisplayName=大肥鱼桌面宠物
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile={#InstallerIcon}
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\DaFeiYuDesktopPet
DisableDirPage=no
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
OutputDir={#ReleaseDir}
OutputBaseFilename=大肥鱼桌面宠物_Setup_v1.0.1
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

function GetFileAttributesW(Name: String): Integer;
  external 'GetFileAttributesW@kernel32.dll stdcall';

function SameDirectory(Left, Right: String): Boolean;
begin
  Result := CompareText(AddBackslash(ExpandFileName(Left)), AddBackslash(ExpandFileName(Right))) = 0;
end;

function InDirectory(Target, Parent: String): Boolean;
begin
  Result := Pos(Lowercase(AddBackslash(ExpandFileName(Parent))), Lowercase(AddBackslash(Target))) = 1;
end;

function HasReparseAncestor(Target: String): Boolean;
var Current, Parent: String; Attributes: Integer;
begin
  Result := False;
  Current := Target;
  while Current <> '' do begin
    if DirExists(Current) or FileExists(Current) then begin
      Attributes := GetFileAttributesW(Current);
      if (Attributes = -1) or ((Attributes and $400) <> 0) then begin
        Result := True; Exit; { Reject junctions/symlinks and failed attribute checks. }
      end;
    end;
    Parent := ExtractFileDir(Current);
    if SameDirectory(Current, Parent) then Exit;
    Current := Parent;
  end;
end;

function DirectoryIsEmpty(Target: String): Boolean;
var Entry: TFindRec;
begin
  Result := False; { Enumeration failure is not proof that a directory is safe. }
  if FindFirst(AddBackslash(Target) + '*', Entry) then begin
    Result := True;
    try
      repeat
        if (Entry.Name <> '.') and (Entry.Name <> '..') then begin
          Result := False; Break;
        end;
      until not FindNext(Entry);
    finally
      FindClose(Entry);
    end;
  end;
end;

function ValidateInstallDirectory(Target: String): String;
var PreviousDir: String; Registered: Boolean;
begin
  Result := '';
  if (Length(ExtractFileDrive(Target)) <> 2) or
     (Copy(Target, 2, 2) <> ':\') or SameDirectory(Target, ExtractFileDrive(Target) + '\') or
     SameDirectory(Target, GetEnv('USERPROFILE')) or
     InDirectory(Target, ExpandConstant('{win}')) or
     InDirectory(Target, ExpandConstant('{userappdata}')) or
     (InDirectory(Target, ExpandConstant('{localappdata}')) and
      not InDirectory(Target, ExpandConstant('{localappdata}\Programs'))) or
     SameDirectory(Target, ExpandConstant('{localappdata}\Programs')) or
     FileExists(Target) or HasReparseAncestor(Target) then begin
    Result := '请选择有写入权限的本地磁盘专用目录，例如 D:\Apps\DaFeiYuDesktopPet；不能使用磁盘根目录、系统/用户数据目录或链接目录。';
    Exit;
  end;
  Registered := RegKeyExists(HKCU64, OwnUninstallKey);
  if Registered then begin
    if not RegQueryStringValue(HKCU64, OwnUninstallKey, 'InstallLocation', PreviousDir) or (PreviousDir = '') then begin
      Result := '既有安装登记缺少目录，请取消安装，通过原卸载入口修复；不会覆盖任何目录。'; Exit;
    end;
    if not SameDirectory(PreviousDir, Target) then begin
      Result := '已有安装位于 ' + PreviousDir + '。换盘前请先从 Windows 应用和功能正常卸载旧版本（保留用户数据），确认旧卸载登记消失后重新运行安装器；或选择原目录升级。'; Exit;
    end;
    if not (FileExists(AddBackslash(Target) + '{#AppExe}') and
            DirExists(AddBackslash(Target) + '_internal') and
            FileExists(AddBackslash(Target) + 'unins000.exe') and
            FileExists(AddBackslash(Target) + 'unins000.dat')) then begin
      Result := '登记目录缺少本安装的程序或卸载凭据，已停止覆盖。请保留目录并通过原卸载入口修复。'; Exit;
    end;
  end else if DirExists(Target) and not DirectoryIsEmpty(Target) then begin
    Result := '目标目录非空且没有本 AppId 安装登记。请选新的专用目录；不会覆盖无关文件或旧绿色版。'; Exit;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Failed: Boolean; Target: String;
begin
  Target := RemoveBackslashUnlessRoot(ExpandFileName(ExpandConstant('{app}')));
  Result := ValidateInstallDirectory(Target);
  if Result <> '' then Exit;
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
