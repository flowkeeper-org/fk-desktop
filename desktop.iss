[Setup]
AppName=Flowkeeper
AppVersion={#GetEnv('FK_VERSION')}
AppPublisher=Vilia SARL
AppPublisherURL=https://flowkeeper.org
AppSupportURL=https://flowkeeper.org
AppUpdatesURL=https://flowkeeper.org
DefaultDirName={userpf}\Flowkeeper
DefaultGroupName=Flowkeeper
SetupIconFile=res\flowkeeper.ico
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Launch Flowkeeper when the system boots"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\Flowkeeper.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Flowkeeper"; Filename: "{app}\Flowkeeper.exe"
Name: "{userdesktop}\Flowkeeper"; Filename: "{app}\Flowkeeper.exe"; Tasks: desktopicon
Name: "{userstartup}\Flowkeeper"; Filename: "{app}\Flowkeeper.exe"; Tasks: autostart

[Run]
Filename: "{app}\Flowkeeper.exe"; Description: "Launch Flowkeeper"; Flags: nowait postinstall skipifsilent
